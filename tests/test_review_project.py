import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from cutover.local_starter import render_local_starter


class LocalProjectReviewTests(unittest.TestCase):
    def test_blocked_repair_and_malformed_attempts_keep_separate_evidence_and_gate_only_the_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            def run(module, args):
                return subprocess.run([sys.executable, '-S', '-m', module, *args], cwd=root,
                                      capture_output=True, timeout=120)
            setup = run('cutover.init_contract', ['--project', 'Private dispatch', '--table', 'shipments',
                '--old-column', 'loading_bay', '--new-column', 'dispatch_bay', '--first-value', "O'Connell",
                '--second-value', '東京-棚', '--incoming-value', 'GATE-09', '--out', 'my-release'])
            self.assertEqual(setup.returncode, 0, setup.stderr)
            blocked = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-1'])
            self.assertEqual(blocked.returncode, 1, blocked.stderr)
            self.assertFalse((root/'review-1/pr-kit.zip').exists())
            before = (root/'review-1/comparison.zip').read_bytes()
            # Separate supplied reference SQL is a test repair, not generated Bob output.
            reference = json.loads((root/'examples/warehouse/bridge.json').read_text(encoding='utf-8'))
            sql = reference['migration'].replace('stock_items', 'shipments').replace('pick_bin', 'loading_bay').replace('fulfillment_bin', 'dispatch_bay')
            sql = sql.replace('\n', '\r\n')
            (root/'my-release/migration.sql').write_bytes(sql.encode('utf-8'))
            repaired = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-2'])
            self.assertEqual(repaired.returncode, 0, repaired.stderr)
            note = (root/'review-2/review.md').read_text(encoding='utf-8')
            self.assertIn('| Baseline | BLOCKED | 55/125', note)
            self.assertIn('| Candidate | PASS | 155/155', note)
            with zipfile.ZipFile(root/'review-2/pr-kit.zip') as archive:
                report = json.loads(archive.read('evidence/report.json'))
                self.assertEqual(report['plan']['migration'], sql)
                self.assertEqual(report['status'], 'pass')
                self.assertIn('evidence/unsafe-control-report.json', archive.namelist())
                workflow = next(name for name in archive.namelist() if name.startswith('.github/'))
                self.assertIn(report['contract_hash'], archive.read(workflow).decode())
            self.assertEqual((root/'review-1/comparison.zip').read_bytes(), before)
            self.assertEqual((root/'review-2/inputs/migration.sql').read_bytes().decode('utf-8'), sql)
            repeat = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-2'])
            self.assertEqual(repeat.returncode, 2)
            (root/'my-release/candidate.json').write_text('{broken', encoding='utf-8')
            malformed = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-3'])
            self.assertEqual(malformed.returncode, 2)
            status = json.loads((root/'review-3/review-status.json').read_text(encoding='utf-8'))
            self.assertEqual(status['status'], 'unverified')
            self.assertFalse((root/'review-3/pr-kit.zip').exists())
