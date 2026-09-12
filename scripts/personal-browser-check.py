"""Verify the regular browser extension connection; optionally check GitHub login."""
import argparse
from mcp_client import Client, config_path, load_entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=config_path(), help='Codex TOML file to test')
    parser.add_argument('--github-login', action='store_true', help='Open a temporary GitHub tab and read signed-in username metadata')
    args = parser.parse_args()
    entry = load_entries(args.config)['playwright-personal']
    if entry.get('env', {}).get('PLAYWRIGHT_MCP_EXTENSION_TOKEN'):
        print('Connecting with the locally configured extension token.', flush=True)
    else:
        print('Select a tab and approve the connection in Chromium when prompted.', flush=True)
    with Client(entry, 'playwright-personal') as client:
        result = client.call('browser_tabs', dict(action='list'))
        if args.github_login:
            client.call('browser_tabs', dict(action='new', url='https://github.com/'))
            try:
                result = client.call('browser_evaluate', {
                    'function': '() => ({host: location.hostname, login: document.querySelector(\'meta[name="user-login"]\')?.content || null})',
                })
            finally:
                client.call('browser_tabs', dict(action='close'))
        for content in result.get('content', []):
            if content.get('type') == 'text':
                print(client.redact(content['text']), flush=True)
        print('PASS: extension connection established. Artifacts:', client.artifacts)


if __name__ == '__main__':
    main()
