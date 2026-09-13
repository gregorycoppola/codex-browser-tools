"""Small stdio MCP client shared by the browser checks (Python 3.11+)."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time
import tomllib
from urllib.parse import quote, quote_plus


def config_path():
    return Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'config.toml'


def load_entries(path):
    return tomllib.loads(Path(path).expanduser().read_text())['mcp_servers']


class Client:
    def __init__(self, entry, name, isolated=False, timeout=120):
        self.entry, self.name, self.timeout = entry, name, timeout
        self.sequence, self.buffer = 0, b''
        env = dict(os.environ, **entry.get('env', {}))
        self.token = env.get('PLAYWRIGHT_MCP_EXTENSION_TOKEN', '')
        self.artifacts = Path(tempfile.mkdtemp(prefix='codex-browser-check-'))
        self.log = (self.artifacts / 'server.log').open('wb')
        args, skip = [], False
        for arg in entry['args']:
            if skip:
                skip = False
            elif isolated and arg == '--user-data-dir':
                skip = True
            elif not (isolated and arg.startswith('--user-data-dir=')):
                args.append(arg)
        if isolated:
            args.append('--isolated')
        if name != 'chrome-devtools':
            args += ['--output-dir', str(self.artifacts)]
        try:
            self.process = subprocess.Popen(
                [entry['command'], *args], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            )
        except Exception:
            self.log.close()
            raise
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)

    def redact(self, text):
        if self.token:
            for value in sorted({self.token, quote(self.token, safe=''), quote_plus(self.token)}, key=len, reverse=True):
                text = text.replace(value, '[REDACTED]')
        return text

    def send(self, message):
        self.process.stdin.write(json.dumps(dict(jsonrpc='2.0', **message)).encode() + b'\n')
        self.process.stdin.flush()

    def request(self, method, params):
        self.sequence += 1
        self.send(dict(id=self.sequence, method=method, params=params))
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if not self.selector.select(min(1, max(0, deadline - time.monotonic()))):
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError(f'Server exited; logs: {self.artifacts}')
            self.buffer += chunk
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                message = json.loads(line)
                if message.get('id') != self.sequence:
                    continue
                result = message.get('result', {})
                if 'error' in message or result.get('isError'):
                    # Server errors can embed page contents, URLs, and credentials.
                    raise RuntimeError(f'{method} failed; server response omitted for privacy')
                return result
        raise TimeoutError(f'{method} timed out; check extension approval and logs: {self.artifacts}')

    def call(self, name, arguments):
        return self.request('tools/call', dict(name=name, arguments=arguments))

    def __enter__(self):
        try:
            self.request('initialize', dict(protocolVersion='2024-11-05', capabilities={},
                         clientInfo=dict(name='Codex browser check: ' + self.name, version='1')))
            self.send(dict(method='notifications/initialized'))
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdout.close()
        self.selector.close()
        self.log.close()
