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

    def test_reader_contract_control_remains_verified_without_data_gap_script(self):
        from ci.install_kit import _read_kit
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = json.loads(SAFE.read_text(encoding='utf-8'))
            plan['read'] = ('SELECT id, fulfillment_bin AS value FROM stock_items UNION ALL '
                            'SELECT id, fulfillment_bin AS value FROM stock_items ORDER BY id')
            control_path = root / 'duplicate-reader.json'
            control_path.write_text(json.dumps(plan), encoding='utf-8')
            output = root / 'kit.zip'
            process = self.run_cli('--ci-kit', output, '--ci-control', control_path)
            self.assertEqual(process.returncode, 0, process.stderr)
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn('evidence/unsafe-control-witness.py', archive.namelist())
                self.assertIn(b'full reader-contract failure', archive.read('README.md'))
                control = json.loads(archive.read('evidence/unsafe-control-report.json'))
                self.assertEqual((control['status'], control['passed'], control['total']), ('blocked', 40, 124))
            self.assertTrue(_read_kit(output)[4])
            # Exact pre-correction witness source remains acceptable for old kits;
            # altered source is rejected, and it is never executed by the installer.
            from cutover.reporting import render_reproduction
            contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
            with zipfile.ZipFile(output) as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
            witness_name = 'evidence/unsafe-control-witness.py'
            files[witness_name] = render_reproduction(control, contract).encode('utf-8')
            legacy = root / 'legacy-kit.zip'
            with zipfile.ZipFile(legacy, 'w') as archive:
                for name, content in files.items():
                    archive.writestr(name, content)
            self.assertTrue(_read_kit(legacy)[4])
            files[witness_name] += b'altered script'
            with zipfile.ZipFile(legacy, 'w') as archive:
                for name, content in files.items():
                    archive.writestr(name, content)
            with self.assertRaisesRegex(ValueError, 'witness differs'):
                _read_kit(legacy)
            refused = root / 'not-a-data-gap.py'
            process = self.run_cli('--plan', control_path, '--repro', refused)
            self.assertEqual(process.returncode, 2)
            self.assertIn('no reproducible data gap', process.stderr)
            self.assertFalse(refused.exists())

    def test_real_value_gap_control_still_requires_its_witness(self):
        from ci.install_kit import _read_kit
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'kit.zip'
            process = self.run_cli('--ci-kit', output, '--ci-control', UNSAFE)
            self.assertEqual(process.returncode, 0, process.stderr)
            with zipfile.ZipFile(output) as archive:
                files = {name: archive.read(name) for name in archive.namelist()
                         if name != 'evidence/unsafe-control-witness.py'}
            with zipfile.ZipFile(output, 'w') as archive:
                for name, content in files.items():
                    archive.writestr(name, content)
            with self.assertRaisesRegex(ValueError, 'data-gap witness is missing'):
                _read_kit(output)

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
