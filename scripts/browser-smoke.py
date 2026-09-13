"""Exercise configured dedicated browsers against a local page and check visibility."""
import argparse
import http.server
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from mcp_client import Client, config_path, load_entries


def verify_window(title):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        clients = json.loads(subprocess.check_output(['hyprctl', 'clients', '-j']))
        if any(c['mapped'] and title in c['title'] for c in clients):
            return
        time.sleep(0.1)
    raise AssertionError('No mapped test window found on the Hyprland desktop')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=config_path(), help='Codex TOML file to test')
    parser.add_argument('--skip-window-check', action='store_true', help='For non-Hyprland desktops; verifies interaction only, not visibility')
    args = parser.parse_args()
    if not args.skip_window_check and not (shutil.which('hyprctl') and os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')):
        parser.error('Window verification requires a Hyprland session. Elsewhere, use --skip-window-check and inspect visibility manually.')
    entries = load_entries(args.config)
    title = 'Clicked successfully ' + uuid.uuid4().hex

    class Page(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(('<title>Browser test</title><button onclick="document.title=\'' + title + '\'">Test button</button>').encode())

        def log_message(self, *_):
            pass

    server = http.server.HTTPServer(('127.0.0.1', 0), Page)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:' + str(server.server_port)
    try:
        for name in ['playwright', 'chrome-devtools']:
            with Client(entries[name], name, isolated=True) as client:
                tools = client.request('tools/list', {})
                print(name, 'connected:', len(tools['tools']), 'tools', flush=True)
                if name == 'playwright':
                    client.call('browser_navigate', dict(url=url))
                    snapshot = client.call('browser_snapshot', {})
                    text = '\n'.join(c.get('text', '') for c in snapshot['content'])
                    ref = re.search(r'button "Test button" \[ref=([^\]]+)\]', text).group(1)
                    client.call('browser_click', dict(target=ref))
                    result = client.call('browser_snapshot', {})
                else:
                    client.call('new_page', dict(url=url))
                    result = client.call('evaluate_script', dict(function="() => { document.querySelector('button').click(); return document.title; }"))
                assert title in json.dumps(result), 'Expected test title missing; response omitted for privacy'
                if not args.skip_window_check:
                    verify_window(title)
                print(name, 'PASS: clicked button and verified title;' + (' visibility NOT checked' if args.skip_window_check else ' desktop window verified'), flush=True)
                print('Artifacts:', client.artifacts)
                if name == 'playwright':
                    client.call('browser_close', {})
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
