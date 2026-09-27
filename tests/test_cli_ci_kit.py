"""A private local rehearsal can produce the same independently audited PR kit."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'examples/warehouse/contract.json'
SAFE = ROOT / 'examples/warehouse/bridge.json'
UNSAFE = ROOT / 'examples/warehouse/late_bridge.json'


class LocalKitTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'cutover', '--contract', str(CONTRACT),
                               '--plan', str(SAFE), *map(str, args)], cwd=ROOT,
                              capture_output=True, text=True, encoding='utf-8')

    def test_local_red_green_kit_independently_verifies(self):
        from ci.install_kit import _read_kit
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'private-kit.zip'
            process = self.run_cli('--ci-kit', output, '--ci-control', UNSAFE)
            self.assertEqual(process.returncode, 0, process.stderr)
            with zipfile.ZipFile(output) as archive:
                passing = json.loads(archive.read('evidence/report.json'))
                control = json.loads(archive.read('evidence/unsafe-control-report.json'))
                self.assertEqual((passing['status'], control['status']), ('pass', 'blocked'))
                self.assertEqual(passing['contract_hash'], control['contract_hash'])
                workflow = next(n for n in archive.namelist() if n.endswith('.yml'))
                self.assertIn(passing['contract_hash'], archive.read(workflow).decode())
            verified = _read_kit(output)
            self.assertIsNotNone(verified)

    def test_nonfailing_control_and_blocked_candidate_do_not_write_kit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'kit.zip'
            process = self.run_cli('--ci-kit', output, '--ci-control', SAFE)
            self.assertEqual(process.returncode, 2)
            self.assertFalse(output.exists())
            process = self.run_cli('--plan', UNSAFE, '--ci-kit', output)
            self.assertEqual(process.returncode, 2)
            self.assertFalse(output.exists())

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'kit.zip'
            output.write_bytes(b'keep existing evidence')
            process = self.run_cli('--ci-kit', output)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(output.read_bytes(), b'keep existing evidence')
