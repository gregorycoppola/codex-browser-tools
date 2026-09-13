"""Verify the regular browser extension connection; optionally check GitHub login."""
import argparse
import json
from mcp_client import Client, config_path, load_entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=config_path(), help='Codex TOML file to test')
    parser.add_argument('--github-login', action='store_true', help='Open a temporary GitHub tab and read signed-in username metadata')
    parser.add_argument('--show-details', action='store_true', help='Print personal tab titles/URLs or GitHub username; do not share this output')
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
                    'function': '() => ({signedIn: Boolean(document.querySelector(\'meta[name="user-login"]\')?.content)' + (', login: document.querySelector(\'meta[name="user-login"]\')?.content || null' if args.show_details else '') + '})',
                })
            finally:
                client.call('browser_tabs', dict(action='close'))
        if args.show_details:
            for content in result.get('content', []):
                if content.get('type') == 'text':
                    print(client.redact(content['text']), flush=True)
        elif args.github_login:
            # Playwright wraps the evaluated JSON in a Result section. Never echo
            # the rest: it can include open tabs, page content, and executed code.
            signed_in = None
            for content in result.get('content', []):
                if content.get('type') != 'text':
                    continue
                section = content.get('text', '').split('### Result\n', 1)
                if len(section) == 2:
                    try:
                        value, _ = json.JSONDecoder().raw_decode(section[1].lstrip())
                        if isinstance(value, dict) and type(value.get('signedIn')) is bool:
                            signed_in = value['signedIn']
                    except ValueError:
                        pass
            print('GitHub signed-in metadata:', {True: 'present', False: 'absent', None: 'unavailable'}[signed_in])
        print('PASS: extension connection established. Artifacts:', client.artifacts)


if __name__ == '__main__':
    main()
