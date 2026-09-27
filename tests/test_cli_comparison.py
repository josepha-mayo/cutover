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
    def test_pr_handoff_audit_writes_fresh_regression_review_and_refuses_altered_inventory(self):
        from cutover.review_project import review
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); project = root/'project'; project.mkdir()
            contract = json.loads((ROOT/'examples/warehouse/contract.json').read_text(encoding='utf-8'))
            safe = json.loads((ROOT/'examples/warehouse/bridge.json').read_text(encoding='utf-8'))
            broken = {**safe, 'write': 'UPDATE stock_items SET fulfillment_bin = :value'}
            for name, value in (('contract', contract), ('baseline', safe), ('candidate', broken)):
                (project/f'{name}.json').write_text(json.dumps(value), encoding='utf-8')
            (project/'migration.sql').write_text(safe['migration'], encoding='utf-8')
            self.assertEqual(review(project, root/'review'), 1)
            bundle = root/'review/pr-review.zip'
            def audit_handoff(packet, label):
                return subprocess.run([sys.executable, '-S', '-m', 'cutover.audit_bundle',
                    '--bundle', str(packet), '--markdown', str(root/(label+'.md')),
                    '--html', str(root/(label+'.html'))], cwd=ROOT, capture_output=True, timeout=120)
            result = audit_handoff(bundle, 'fresh')
            self.assertEqual(result.returncode, 1, result.stderr)
            note = (root/'fresh.md').read_text(encoding='utf-8')
            self.assertIn('## First new regression', note)
            self.assertIn('outer notes, HTML, optional kits and Git labels', note)
            self.assertTrue((root/'fresh.html').exists())
            altered = root/'altered.zip'
            with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(altered, 'w', zipfile.ZIP_DEFLATED) as destination:
                for name in source.namelist():
                    raw = source.read(name)
                    destination.writestr(name, raw+b'changed' if name=='pr-summary.md' else raw)
            refused = audit_handoff(altered, 'refused')
            self.assertEqual(refused.returncode, 2, refused.stderr)
            self.assertIn(b'inventory', refused.stderr)
            self.assertFalse((root/'refused.md').exists())
            self.assertFalse((root/'refused.html').exists())
            self.assertFalse((root/'SHA256SUMS.json').exists())

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

    def test_unwritable_output_is_an_export_error_not_a_blocked_verdict(self):
        safe = ROOT / 'examples/warehouse/bridge.json'
        unsafe = ROOT / 'examples/warehouse/late_bridge.json'
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / 'retained-review'
            parent.write_text('Existing reviewer notes', encoding='utf-8')
            result = self.run_cli(safe, unsafe, parent/'comparison.zip')
            self.assertEqual(result.returncode, 2)
            self.assertIn('Cannot export evidence:', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertNotIn('Independently replayed comparison saved', result.stdout)
            self.assertEqual(parent.read_text(encoding='utf-8'), 'Existing reviewer notes')

    def test_existing_evidence_is_not_overwritten(self):
        safe = ROOT / 'examples/warehouse/bridge.json'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'keep.zip'
            output.write_bytes(b'original evidence')
            process = self.run_cli(safe, safe, output)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(output.read_bytes(), b'original evidence')
