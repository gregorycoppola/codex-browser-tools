import os
from pathlib import Path
import runpy
import subprocess
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
generate = runpy.run_path(str(ROOT / 'scripts/generate-config.py'))['generate']


class ConfigurationTests(unittest.TestCase):
    def test_paths_with_spaces_and_quotes_round_trip(self):
        repo = Path('/tmp/other user/project "quoted"')
        result = tomllib.loads(generate(
            repo, '/tmp/other user/node', '/tmp/browser wrapper',
            Path('/tmp/profiles'), Path('/tmp/regular profile'),
            {'DISPLAY': ':7', 'WAYLAND_DISPLAY': 'wayland-9'},
        ))['mcp_servers']
        self.assertEqual(result['playwright']['args'][0], str(repo / 'node_modules/@playwright/mcp/cli.js'))
        self.assertIn('/tmp/regular profile', result['playwright-personal']['args'])
        self.assertIn('--extension', result['playwright-personal']['args'])
        self.assertEqual(result['chrome-devtools']['env']['DISPLAY'], ':7')
        self.assertNotIn('PLAYWRIGHT_MCP_EXTENSION_TOKEN', result['playwright-personal']['env'])

    def test_personal_connection_is_optional(self):
        result = tomllib.loads(generate(Path('/tmp/repo'), '/usr/bin/node', '/usr/bin/chromium',
                                       Path('/tmp/profiles'), None, {'DISPLAY': ':0'}))
        self.assertEqual(set(result['mcp_servers']), {'playwright', 'chrome-devtools'})

    def test_missing_desktop_fails_before_writing(self):
        env = {key: value for key, value in os.environ.items() if key not in ('DISPLAY', 'WAYLAND_DISPLAY')}
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/generate-config.py')],
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('graphical desktop', result.stderr)


if __name__ == '__main__':
    unittest.main()
