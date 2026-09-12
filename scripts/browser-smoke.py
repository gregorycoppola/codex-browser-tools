import json, os, re, selectors, subprocess, threading, http.server, time, tomllib
from pathlib import Path

CONFIG = tomllib.loads((Path.home() / '.codex/config.toml').read_text())['mcp_servers']

def verify_window():
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        clients = json.loads(subprocess.check_output(['hyprctl', 'clients', '-j']))
        if any(c['mapped'] and 'Clicked successfully' in c['title'] for c in clients):
            return
        time.sleep(0.1)
    raise AssertionError('No mapped Chromium test window found on the desktop')
class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<title>Browser test</title><button onclick="document.title=\'Clicked successfully\'">Test button</button>')
    def log_message(self, *args): pass
server = http.server.HTTPServer(('127.0.0.1', 0), Page)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = 'http://127.0.0.1:' + str(server.server_port)
for name in ['playwright', 'chrome-devtools']:
    config = CONFIG[name]
    # Exercise the installed configuration, replacing only the persistent profile.
    args = []
    skip = False
    for arg in config['args']:
        if skip:
            skip = False
            continue
        if arg == '--user-data-dir':
            skip = True
        elif not arg.startswith('--user-data-dir='):
            args.append(arg)
    args.append('--isolated')
    log = open('/tmp/codex-' + name + '-smoke.log', 'w')
    env = dict(os.environ, **config.get('env', {}))
    p = subprocess.Popen([config['command']] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, env=env)
    sel = selectors.DefaultSelector(); sel.register(p.stdout, selectors.EVENT_READ)
    seq = 0
    def send(message):
        p.stdin.write(json.dumps(dict(jsonrpc='2.0', **message)) + '\n'); p.stdin.flush()
    def request(method, params):
        global seq
        seq += 1
        send(dict(id=seq, method=method, params=params))
        while sel.select(45):
            line = p.stdout.readline()
            if not line: raise RuntimeError('server exited; see smoke log')
            msg = json.loads(line)
            if msg.get('id') == seq:
                if 'error' in msg: raise RuntimeError(str(msg['error']))
                result = msg['result']
                if result.get('isError'): raise RuntimeError(str(result))
                return result
        raise TimeoutError(method)
    try:
        init = request('initialize', dict(protocolVersion='2024-11-05', capabilities={}, clientInfo=dict(name='local-browser-check', version='1')))
        send(dict(method='notifications/initialized'))
        ts = request('tools/list', {})
        print(name, 'connected:', len(ts['tools']), 'tools', flush=True)
        def call(tool, arguments): return request('tools/call', dict(name=tool, arguments=arguments))
        if name == 'playwright':
            loaded = call('browser_navigate', dict(url=url))
            loaded = call('browser_snapshot', {})
            snapshot = '\n'.join(c.get('text', '') for c in loaded['content'])
            ref = re.search(r'button "Test button" \[ref=([^\]]+)\]', snapshot).group(1)
            call('browser_click', dict(target=ref))
            result = call('browser_snapshot', {})
        else:
            call('new_page', dict(url=url))
            result = call('evaluate_script', dict(function="() => { document.querySelector('button').click(); return document.title; }"))
        assert 'Clicked successfully' in json.dumps(result), result
        verify_window()
        print(name, 'PASS: visible desktop window, loaded page, clicked button, verified title', flush=True)
        if name == 'playwright':
            call('browser_close', {})
    finally:
        p.stdin.close()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.terminate(); p.wait(timeout=5)
        log.close(); sel.close()
server.shutdown()
