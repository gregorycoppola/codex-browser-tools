"""Generate browser-only Codex TOML using this checkout and desktop session."""

import argparse
import json
import os
from pathlib import Path
import shutil
import tomllib


def generate(repo, node, browser, profile_root, personal_profile, desktop):
    cli = str(repo / 'node_modules/@playwright/mcp/cli.js')
    entries = {
        'playwright': [cli, '--executable-path', browser, '--sandbox',
                       '--user-data-dir', str(profile_root / 'playwright')],
        'chrome-devtools': [
            str(repo / 'node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js'),
            '--executablePath=' + browser,
            '--user-data-dir=' + str(profile_root / 'chrome-devtools'),
            '--no-usage-statistics', '--no-performance-crux', '--no-page-id-routing',
        ],
    }
    if personal_profile:
        entries['playwright-personal'] = [
            cli, '--extension', '--executable-path', browser,
            '--user-data-dir', str(personal_profile),
        ]
    lines = ['# Generated browser entries. Merge into your Codex config; do not replace it.', '']
    for name, args in entries.items():
        lines += [f'[mcp_servers.{name}]', f'command = {json.dumps(node)}',
                  f'args = {json.dumps(args)}', '', f'[mcp_servers.{name}.env]']
        env = dict(desktop)
        if name == 'chrome-devtools':
            env['CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS'] = '1'
        for key, value in env.items():
            lines.append(f'{key} = {json.dumps(value)}')
        if name == 'playwright-personal':
            lines.append('# Optional: add PLAYWRIGHT_MCP_EXTENSION_TOKEN here in your LOCAL Codex config.')
        lines.append('')
    text = '\n'.join(lines)
    tomllib.loads(text)
    return text


def executable(value, candidates):
    for candidate in ([value] if value else candidates):
        found = shutil.which(candidate)
        if found:
            # Preserve wrappers and version-manager symlinks; do not resolve them.
            return os.path.abspath(found)
    raise ValueError('Executable not found: ' + (value or ', '.join(candidates)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', help='Node executable (default: node on PATH)')
    parser.add_argument('--browser', help='Browser executable (default: chromium/chromium-browser/google-chrome)')
    parser.add_argument('--profile-root', type=Path, default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'codex-browser-tools/profiles')
    parser.add_argument('--personal-profile', type=Path, help='Optional browser user-data root, the parent of Default/Profile N shown at chrome://version')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'config/local.toml')
    args = parser.parse_args()
    desktop = {key: os.environ[key] for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR', 'XAUTHORITY') if os.environ.get(key)}
    if not (desktop.get('DISPLAY') or desktop.get('WAYLAND_DISPLAY')):
        parser.error('Run from a terminal inside your graphical desktop; no DISPLAY or WAYLAND_DISPLAY found.')
    repo = Path(__file__).resolve().parents[1]
    if not (repo / 'node_modules/@playwright/mcp/cli.js').is_file():
        parser.error('Install the locked packages first: npm ci (see README).')
    try:
        node = executable(args.node, ['node'])
        browser = executable(args.browser, ['chromium', 'chromium-browser', 'google-chrome'])
    except ValueError as error:
        parser.error(str(error))
    personal = args.personal_profile.expanduser().absolute() if args.personal_profile else None
    if personal and not personal.is_dir():
        parser.error('--personal-profile must be an existing browser user-data directory.')
    text = generate(repo, node, browser, args.profile_root.expanduser().absolute(), personal, desktop)
    output = args.output.expanduser().absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text)
    output.chmod(0o600)
    print(f'Wrote {output}. Merge its browser sections into your Codex config, then restart Codex.')
    print('No token was read or written. Existing Codex settings were not modified.')


if __name__ == '__main__':
    main()
