"""Exercise browser transport against actual local HTTP responses and stalls."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node.js is needed for the browser module')
class BrowserRequestTests(unittest.TestCase):
    def run_check(self, mode):
        result = subprocess.run(
            ['node', 'tests/check_browser_request.mjs', mode], cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8', timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])

    def test_json_and_binary_preserve_measured_body_and_headers(self):
        self.run_check('success')

    def test_service_errors_never_become_evidence_or_silent_retries(self):
        self.run_check('errors')

    def test_deadline_covers_headers_json_and_binary_body(self):
        self.run_check('deadlines')
