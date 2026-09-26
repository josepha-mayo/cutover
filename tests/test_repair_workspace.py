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
            report = json.loads(next((root/'work').glob('verification-*/report.json')).read_text(encoding='utf-8'))
            self.assertEqual((report['passed'], report['total']), (108, 124))
            self.assertEqual(len(list((root/'work').glob('verification-*/review.md'))), 1)
            (root/'work/bob-candidate.json').write_text(json.dumps(json.loads(Path('examples/warehouse/bridge.json').read_text(encoding='utf-8'))), encoding='utf-8')
            passing = subprocess.run([sys.executable, 'verify_workspace.py', '--candidate',
                                      'work/bob-candidate.json'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(passing.returncode, 0, passing.stderr)
            reports = [json.loads(p.read_text(encoding='utf-8')) for p in (root/'work').glob('verification-*/report.json')]
            self.assertEqual(len(reports), 2)
            report = next(r for r in reports if r['status'] == 'pass')
            self.assertEqual((report['passed'], report['total']), (124, 124))

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
