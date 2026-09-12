import json, os, re, selectors, subprocess, threading, http.server

BASE = '/home/myuser/.local/share/codex-browser-tools/node_modules/'
NODE = '/home/myuser/.local/share/mise/installs/node/latest/bin/node'
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
for name, script, args in [
    ('playwright', '@playwright/mcp/cli.js', ['--executable-path', '/usr/local/bin/chromium', '--isolated', '--sandbox']),
    ('chrome-devtools', 'chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js', ['--executablePath=/usr/local/bin/chromium', '--isolated', '--no-usage-statistics', '--no-performance-crux', '--no-page-id-routing']),
]:
    log = open('/tmp/codex-' + name + '-smoke.log', 'w')
    env = dict(os.environ, CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS='1')
    p = subprocess.Popen([NODE, BASE + script] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, env=env)
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
            call('browser_close', {})
        else:
            call('new_page', dict(url=url))
            result = call('evaluate_script', dict(function="() => { document.querySelector('button').click(); return document.title; }"))
        assert 'Clicked successfully' in json.dumps(result), result
        print(name, 'PASS: launched Chromium, loaded page, clicked button, verified title', flush=True)
    finally:
        p.stdin.close()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.terminate(); p.wait(timeout=5)
        log.close(); sel.close()
server.shutdown()
