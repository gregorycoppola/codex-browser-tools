import contextlib
import io
import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch
from urllib.parse import quote, quote_plus

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from mcp_client import Client


class PrivacyTests(unittest.TestCase):
    def test_inherited_token_and_encoded_forms_are_redacted(self):
        token = 'synthetic/token +value'
        # Initialize a real child to check the effective environment path.
        with patch.dict(os.environ, {'PLAYWRIGHT_MCP_EXTENSION_TOKEN': token}):
            client = Client({'command': sys.executable, 'args': ['-c', 'pass']}, 'chrome-devtools')
        try:
            for value in (token, quote(token, safe=''), quote_plus(token)):
                self.assertEqual(client.redact(value), '[REDACTED]')
        finally:
            client.__exit__()

    def test_server_errors_do_not_echo_private_content(self):
        payload = 'private-person@example.invalid secret-page-token'
        code = 'import sys,json; m=json.loads(input()); print(json.dumps({"id":m["id"],"error":{"message":' + repr(payload) + '}}),flush=True)'
        client = Client({'command': sys.executable, 'args': ['-c', code]}, 'chrome-devtools')
        try:
            with self.assertRaises(RuntimeError) as caught:
                client.request('tools/call', {})
            self.assertNotIn(payload, str(caught.exception))
            self.assertIn('omitted for privacy', str(caught.exception))
        finally:
            client.__exit__()

    def test_default_checks_do_not_echo_tabs_or_username(self):
        for github in (False, True):
            with self.subTest(github=github):
                class FakeClient:
                    artifacts = '/tmp/private-test-artifacts'
                    def __init__(self, *args): pass
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def call(self, name, args):
                        if name == 'browser_evaluate':
                            self_outer.assertNotIn('login:', args['function'])
                        return {'content': [{'type': 'text', 'text': '### Result\n{"signedIn": true}\n### Open tabs\nprivate-person@example.invalid https://private.invalid/?token=secret'}]}
                self_outer = self
                main = runpy.run_path(str(ROOT / 'scripts/personal-browser-check.py'))['main']
                output = io.StringIO()
                with patch.dict(main.__globals__, {'Client': FakeClient, 'load_entries': lambda _: {'playwright-personal': {}}}), patch.object(sys, 'argv', ['check'] + (['--github-login'] if github else [])), contextlib.redirect_stdout(output):
                    main()
                self.assertNotIn('private-person', output.getvalue())
                self.assertNotIn('private.invalid', output.getvalue())
                self.assertNotIn('secret', output.getvalue())
                self.assertIn('PASS', output.getvalue())
                if github:
                    self.assertIn('metadata: present', output.getvalue())


if __name__ == '__main__':
    unittest.main()
