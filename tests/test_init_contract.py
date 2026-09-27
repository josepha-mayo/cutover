import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from cutover.local_starter import render_local_starter


class LocalContractSetupTests(unittest.TestCase):
    def test_supplied_sql_is_the_executed_original_and_invalid_inputs_create_no_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            raw = b'\xef\xbb\xbfALTER TABLE "shipments" ADD COLUMN "dispatch_bay" TEXT;\r\n-- original reader sees NULL, not a generated copy\r\n'
            source = root/'original.sql'; source.write_bytes(raw)
            args = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'Actual SQL',
                    '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                    '--first-value', 'A-01', '--second-value', 'B-02', '--incoming-value', 'GATE-09',
                    '--migration-file', 'original.sql', '--out', 'release']
            def run(command):
                return subprocess.run(command, cwd=root, capture_output=True, timeout=120)
            result = run(args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root/'release/migration.sql').read_bytes(), raw)
            for name in ('baseline.json', 'candidate.json'):
                self.assertEqual(json.loads((root/'release'/name).read_text(encoding='utf-8'))['migration'], raw.decode('utf-8-sig'))
            reviewed = run([sys.executable, '-S', '-m', 'cutover.review_project', '--project', 'release', '--out', 'review'])
            self.assertEqual(reviewed.returncode, 1, reviewed.stderr)
            with zipfile.ZipFile(root/'review/comparison.zip') as archive:
                for prefix in ('baseline/', 'candidate/'):
                    self.assertEqual(json.loads(archive.read(prefix+'report.json'))['plan']['migration'], raw.decode('utf-8-sig'))
            self.assertEqual(source.read_bytes(), raw)
            readme = (root/'release/README.md').read_text(encoding='utf-8')
            self.assertIn('No verdict is inferred', readme)
            self.assertNotIn('generated one-time backfill should block', readme)
            for invalid in (b'', b'\xff', b'x'*65537, b'x'*12001, b'SELECT 1;\0'):
                source.write_bytes(invalid)
                bad = args[:-1]+['invalid-release']
                self.assertEqual(run(bad).returncode, 2)
                self.assertFalse((root/'invalid-release').exists())

    def test_actual_extracted_private_setup_blocks_replays_and_preserves_existing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            setup = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'Private dispatch',
                '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                '--first-value', "O'Connell", '--second-value', '東京-棚', '--incoming-value', '',
                '--out', 'my-release']
            run = subprocess.run(setup, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(run.returncode, 0, run.stderr)
            contract = json.loads((root/'my-release/contract.json').read_text(encoding='utf-8'))
            self.assertEqual(contract['seed'], [[1, "O'Connell"], [2, '東京-棚']])
            self.assertEqual(contract['payloads'][0], '')
            args = [sys.executable, '-S', '-m', 'cutover', '--contract', 'my-release/contract.json',
                    '--plan', 'my-release/baseline.json', '--bundle', 'my-release/unsafe.zip']
            run = subprocess.run(args, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(run.returncode, 1, run.stderr)
            with zipfile.ZipFile(root/'my-release/unsafe.zip') as archive:
                report = json.loads(archive.read('report.json'))
                self.assertEqual(report['witness']['payload'], '')
                self.assertEqual(report['status'], 'blocked')
            audit = subprocess.run([sys.executable, '-S', '-m', 'cutover.audit_bundle',
                '--bundle', 'my-release/unsafe.zip'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(audit.returncode, 1, audit.stderr)
            original = (root/'my-release/contract.json').read_bytes()
            again = subprocess.run(setup, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(again.returncode, 2)
            self.assertEqual((root/'my-release/contract.json').read_bytes(), original)
            invalid = setup.copy()
            invalid[invalid.index('shipments')] = 'shipments; DROP TABLE shipments'
            invalid[-1] = 'invalid-release'
            rejected = subprocess.run(invalid, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(rejected.returncode, 2)
            self.assertFalse((root/'invalid-release').exists())
