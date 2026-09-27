import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from cutover.local_starter import render_local_starter


class LocalStarterTests(unittest.TestCase):
    def test_extracted_starter_runs_and_audits_without_site_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                inventory = json.loads(archive.read('SOURCE_INVENTORY.json'))
                for name, digest in inventory.items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
                self.assertNotIn('mcp_server.py', archive.namelist())
                self.assertFalse(any(name.startswith('bob_sessions/') for name in archive.namelist()))
                archive.extractall(root)
            command = [sys.executable, '-S', '-m', 'cutover', '--contract',
                'examples/warehouse/contract.json', '--plan', 'examples/warehouse/bridge.json',
                '--baseline-plan', 'examples/warehouse/late_bridge.json', '--bundle', 'comparison.zip']
            result = subprocess.run(command, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            audit = subprocess.run([sys.executable, '-S', '-m', 'cutover.audit_bundle', '--bundle',
                'comparison.zip', '--markdown', 'review.md'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(audit.returncode, 1, audit.stderr)
            note = (root/'review.md').read_text(encoding='utf-8')
            self.assertIn('| Baseline | BLOCKED | 108/124', note)
            self.assertIn('| Candidate | PASS | 124/124', note)
