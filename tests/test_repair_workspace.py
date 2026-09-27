import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from cutover.engine import load_case, load_plan
from cutover.repair_workspace import render_repair_workspace
from cutover.service import run_rehearsal


class RepairWorkspaceTests(unittest.TestCase):
    def test_selected_failure_is_retained_without_replacing_full_evidence(self):
        probe = next(p for p in self.report['results'] if not p['passed'] and p['id'] != self.report['witness']['id'])
        packet = render_repair_workspace(self.report, self.contract, probe)
        with zipfile.ZipFile(io.BytesIO(packet)) as archive:
            self.assertEqual(json.loads(archive.read('selected-failure.json')), probe)
            self.assertEqual(json.loads(archive.read('baseline-report.json')), self.report)
            task = archive.read('TASK.md')
            self.assertIn(probe['id'].encode(), task)
            self.assertIn(b'## Recorded row difference', task)
            self.assertIn(b'Expected by contract:', task)
            self.assertIn(b'Reader observed:', task)
            self.assertIn(b'independently rerun the entire fixed suite', task)
            manifest = json.loads(archive.read('WORKSPACE_MANIFEST.json'))
            self.assertIn('selected-failure.json', manifest['files'])
        for invalid in ([], dict(probe, payload='Changed'), {'id': 'nonexistent'}, next(p for p in self.report['results'] if p['passed'])):
            with self.assertRaises(ValueError):
                render_repair_workspace(self.report, self.contract, invalid)
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(Path('examples/warehouse/contract.json').read_text(encoding='utf-8'))
        cls.baseline = json.loads(Path('examples/warehouse/late_bridge.json').read_text(encoding='utf-8'))
        cls.report = run_rehearsal('custom', cls.baseline, cls.contract)
        cls.packet = render_repair_workspace(cls.report, cls.contract)

    def test_extracted_workspace_independently_blocks_then_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zipfile.ZipFile(io.BytesIO(self.packet)).extractall(root)
            blocked = subprocess.run([sys.executable, 'verify_workspace.py', '--candidate',
                                      'baseline-plan.json'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(blocked.returncode, 1, blocked.stderr)
            self.assertIn(b'Independent replay matched', blocked.stdout)
            self.assertEqual(len(list((root/'work').glob('verification-*/audit.log'))), 1)
            from cutover.review_html import render_review
            html_path = next((root/'work').glob('verification-*/review.html'))
            html_report = json.loads((html_path.parent/'report.json').read_text(encoding='utf-8'))
            self.assertEqual(html_path.read_text(encoding='utf-8'), render_review([html_report]))
            self.assertEqual(next((root/'work').glob('verification-*/candidate.json')).read_bytes(),
                             (root/'baseline-plan.json').read_bytes())
            report = json.loads(next((root/'work').glob('verification-*/report.json')).read_text(encoding='utf-8'))
            self.assertEqual((report['passed'], report['total']), (108, 124))
            self.assertEqual(len(list((root/'work').glob('verification-*/review.md'))), 1)
            (root/'work/bob-candidate.json').write_text(json.dumps(json.loads(Path('examples/warehouse/bridge.json').read_text(encoding='utf-8'))), encoding='utf-8')
            passing = subprocess.run([sys.executable, 'verify_workspace.py', '--candidate',
                                      'work/bob-candidate.json', '--comparison'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(passing.returncode, 0, passing.stderr)
            self.assertIn(b'Independent replay matched', passing.stdout)
            self.assertEqual(len(list((root/'work').glob('verification-*/review.html'))), 2)
            comparison = next((root/'work').glob('verification-*/comparison.zip'))
            with zipfile.ZipFile(comparison) as archive:
                before = json.loads(archive.read('baseline/report.json'))
                after = json.loads(archive.read('candidate/report.json'))
            self.assertEqual((before['status'], after['status']), ('blocked', 'pass'))
            self.assertEqual((comparison.parent/'comparison.html').read_text(encoding='utf-8'),
                             render_review([before, after]))
            self.assertIn('108/124', (comparison.parent/'comparison.md').read_text(encoding='utf-8'))
            self.assertIn(b'VERIFIED PACKET', (comparison.parent/'comparison-audit.log').read_bytes())
            reports = [json.loads(p.read_text(encoding='utf-8')) for p in (root/'work').glob('verification-*/report.json')]
            self.assertEqual(len(reports), 2)
            report = next(r for r in reports if r['status'] == 'pass')
            self.assertEqual((report['passed'], report['total']), (124, 124))
            kit = subprocess.run([sys.executable, '-m', 'cutover', '--contract', 'contract.json',
                                  '--plan', 'work/bob-candidate.json', '--ci-kit', 'work/pr-kit.zip',
                                  '--ci-control', 'baseline-plan.json'], cwd=root,
                                 capture_output=True, timeout=120)
            self.assertEqual(kit.returncode, 0, kit.stderr)
            with zipfile.ZipFile(root/'work/pr-kit.zip') as archive:
                self.assertEqual(json.loads(archive.read('evidence/report.json'))['status'], 'pass')
                self.assertEqual(json.loads(archive.read('evidence/unsafe-control-report.json'))['status'], 'blocked')

    def test_extracted_workspace_exports_and_audits_local_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zipfile.ZipFile(io.BytesIO(self.packet)).extractall(root)
            (root/'candidate.json').write_bytes(Path('examples/warehouse/bridge.json').read_bytes())
            result = subprocess.run([sys.executable, '-m', 'cutover', '--contract', 'contract.json',
                '--plan', 'candidate.json', '--baseline-plan', 'baseline-plan.json',
                '--bundle', 'comparison.zip'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            audit = subprocess.run([sys.executable, '-m', 'cutover.audit_bundle', '--bundle',
                'comparison.zip', '--markdown', 'review.md'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(audit.returncode, 1, audit.stderr)
            self.assertIn('108/124', (root/'review.md').read_text(encoding='utf-8'))
            self.assertIn('124/124', (root/'review.md').read_text(encoding='utf-8'))

    def test_changed_contract_stops_before_candidate_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zipfile.ZipFile(io.BytesIO(self.packet)).extractall(root)
            (root/'contract.json').write_text('{}', encoding='utf-8')
            result = subprocess.run([sys.executable, 'verify_workspace.py', '--candidate',
                                     'baseline-plan.json'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'Packaged fixed file changed: contract.json', result.stderr)
            self.assertFalse((root/'work').exists())

    def test_independent_audit_refuses_a_report_changed_after_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zipfile.ZipFile(io.BytesIO(self.packet)).extractall(root)
            runner = '''import json, runpy, subprocess, sys
from pathlib import Path
original_run = subprocess.run
def execute(args, **kwargs):
    result = original_run(args, **kwargs)
    if args[2] == 'cutover':
        report_path = Path(args[args.index('--output')+1])
        report = json.loads(report_path.read_text(encoding='utf-8'))
        report['passed'] += 1
        report_path.write_text(json.dumps(report), encoding='utf-8')
    return result
subprocess.run = execute
sys.argv = ['verify_workspace.py', '--candidate', 'baseline-plan.json']
runpy.run_path('verify_workspace.py', run_name='__main__')
'''
            (root/'tamper_control.py').write_text(runner, encoding='utf-8')
            result = subprocess.run([sys.executable, 'tamper_control.py'], cwd=root,
                                    capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(b'Independent replay refused', result.stderr)
            log = next((root/'work').glob('verification-*/audit.log')).read_bytes()
            self.assertIn(b'UNVERIFIED', log)
            self.assertNotIn(b'Independent replay matched', result.stdout)
            self.assertFalse(list((root/'work').glob('verification-*/review.html')))

    def test_archive_has_no_machine_configuration_or_passing_references(self):
        names = set(zipfile.ZipFile(io.BytesIO(self.packet)).namelist())
        self.assertNotIn('.bob/mcp.json', names)
        self.assertFalse(any(name.endswith('/bridge.json') for name in names))
        self.assertIn('configure_bob.py', names)
        self.assertIn('contract.json', names)

    def test_changed_inputs_and_passing_reports_are_rejected(self):
        changed = dict(self.contract, project='Changed contract')
        with self.assertRaisesRegex(ValueError, 'do not match'):
            render_repair_workspace(self.report, changed)
        passed = run_rehearsal('custom', json.loads(Path('examples/warehouse/bridge.json').read_text(encoding='utf-8')), self.contract)
        with self.assertRaisesRegex(ValueError, 'blocked rehearsal'):
            render_repair_workspace(passed, self.contract)
