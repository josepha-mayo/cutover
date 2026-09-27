"""Private before/after evidence must remain independently auditable."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class LocalComparisonTests(unittest.TestCase):
    def run_cli(self, candidate, baseline, output):
        return subprocess.run([sys.executable, '-m', 'cutover', '--contract',
            str(ROOT / 'examples/warehouse/contract.json'), '--plan', str(candidate),
            '--baseline-plan', str(baseline), '--bundle', str(output)], cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8')

    def test_repair_and_regression_both_export_verified_comparisons(self):
        safe = ROOT / 'examples/warehouse/bridge.json'
        unsafe = ROOT / 'examples/warehouse/late_bridge.json'
        with tempfile.TemporaryDirectory() as directory:
            for candidate, baseline, exit_code in ((safe, unsafe, 0), (unsafe, safe, 1)):
                output = Path(directory) / f'comparison-{exit_code}.zip'
                process = self.run_cli(candidate, baseline, output)
                self.assertEqual(process.returncode, exit_code, process.stderr)
                with zipfile.ZipFile(output) as archive:
                    summary = json.loads(archive.read('comparison.json'))
                    self.assertFalse(summary['window_probes_paired'])
                    self.assertEqual(summary['contract_hash'], json.loads(archive.read('candidate/report.json'))['contract_hash'])
                    self.assertGreater(summary['migration_window_failures']['candidate' if exit_code else 'baseline']['failed'], 0)
                audit = subprocess.run([sys.executable, '-m', 'cutover.audit_bundle', '--bundle', str(output)],
                    cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(audit.returncode, 1, audit.stderr)

    def test_actual_sql_files_override_both_embedded_migrations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            safe = json.loads((ROOT/'examples/warehouse/bridge.json').read_text(encoding='utf-8'))
            unsafe = json.loads((ROOT/'examples/warehouse/late_bridge.json').read_text(encoding='utf-8'))
            candidate_sql = '-- candidate 東京\r\n' + safe['migration'].replace('\n', '\r\n')
            baseline_sql = '-- baseline O\'Connell\n' + unsafe['migration']
            (root/'candidate.sql').write_bytes(b'\xef\xbb\xbf' + candidate_sql.encode('utf-8'))
            (root/'baseline.sql').write_bytes(baseline_sql.encode('utf-8'))
            for name, plan in (('candidate', safe), ('baseline', unsafe)):
                (root/f'{name}.json').write_text(json.dumps(dict(plan, migration='SELECT 1;')), encoding='utf-8')
            output = root/'comparison.zip'
            result = subprocess.run([sys.executable, '-m', 'cutover', '--contract',
                str(ROOT/'examples/warehouse/contract.json'), '--plan', str(root/'candidate.json'),
                '--migration-file', str(root/'candidate.sql'), '--baseline-plan', str(root/'baseline.json'),
                '--baseline-migration-file', str(root/'baseline.sql'), '--bundle', str(output)],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                before = json.loads(archive.read('baseline/report.json'))
                after = json.loads(archive.read('candidate/report.json'))
                self.assertEqual(before['plan']['migration'], baseline_sql)
                self.assertEqual(after['plan']['migration'], candidate_sql)
                self.assertEqual((before['status'], after['status']), ('blocked', 'pass'))
            audit = subprocess.run([sys.executable, '-m', 'cutover.audit_bundle', '--bundle', str(output)],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(audit.returncode, 1, audit.stderr)
            # Every output protects the actual baseline SQL source as an input.
            collision = subprocess.run([sys.executable, '-m', 'cutover', '--baseline-plan', str(root/'baseline.json'),
                '--baseline-migration-file', str(root/'baseline.sql'), '--bundle', str(root/'baseline.sql')],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(collision.returncode, 2)
            self.assertEqual((root/'baseline.sql').read_bytes(), baseline_sql.encode('utf-8'))

    def test_existing_evidence_is_not_overwritten(self):
        safe = ROOT / 'examples/warehouse/bridge.json'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'keep.zip'
            output.write_bytes(b'original evidence')
            process = self.run_cli(safe, safe, output)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(output.read_bytes(), b'original evidence')
