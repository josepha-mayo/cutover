"""Run the reusable action entrypoint from an unrelated consumer checkout."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cutover.audit_bundle import audit


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'ci/action_entry.py'


def consumer(root):
    plan = json.loads((ROOT / 'ci/candidate.json').read_text(encoding='utf-8'))
    (root / 'contract.json').write_bytes((ROOT / 'examples/warehouse/contract.json').read_bytes())
    (root / 'adapters.json').write_text(json.dumps({k: v for k, v in plan.items() if k != 'migration'}), encoding='utf-8')
    (root / 'migration.sql').write_bytes(plan['migration'].encode('utf-8'))
    # Consumer code must not replace the action's evaluator just because the
    # calling workflow starts in this directory.
    (root / 'cutover').mkdir()
    (root / 'cutover/__init__.py').write_text('raise RuntimeError("WRONG consumer package loaded")', encoding='utf-8')


def run(root, **overrides):
    env = {**os.environ, 'GITHUB_WORKSPACE': str(root), 'GITHUB_ACTIONS': 'true',
           'GITHUB_OUTPUT': str(root / 'action-outputs.txt'),
           'GITHUB_STEP_SUMMARY': str(root / 'job-summary.md'),
           'CUTOVER_CONTRACT': 'contract.json', 'CUTOVER_PLAN': 'adapters.json',
           'CUTOVER_MIGRATION_FILE': 'migration.sql', 'CUTOVER_OUTPUT_DIR': 'review',
           'CUTOVER_ACTION_REPOSITORY': 'josepha-mayo/cutover',
           'CUTOVER_ACTION_REF': 'local-test', **overrides}
    return subprocess.run([sys.executable, str(ENTRY)], cwd=root, env=env,
                          text=True, encoding='utf-8', capture_output=True, timeout=300)


class PortableActionTests(unittest.TestCase):
    def test_foreign_checkout_uses_pinned_engine_for_pass_and_sql_only_block(self):
        for state in ('safe', 'blocked'):
            with self.subTest(state=state), tempfile.TemporaryDirectory(prefix='cutover-consumer-') as tmp:
                root = Path(tmp)
                consumer(root)
                before = (root / 'adapters.json').read_bytes()
                if state == 'blocked':
                    sql = (root / 'migration.sql').read_text(encoding='utf-8')
                    start = sql.index('CREATE TRIGGER sync_pick_to_fulfillment')
                    end = sql.index('CREATE TRIGGER sync_insert_to_fulfillment')
                    (root / 'migration.sql').write_text(sql[:start] + sql[end:], encoding='utf-8')
                result = run(root)
                self.assertEqual(result.returncode, 0 if state == 'safe' else 1, result.stdout + result.stderr)
                report = audit(root / 'review/review.zip')[0]
                expected = (116, 116) if state == 'safe' else (72, 108)
                self.assertEqual((report['passed'], report['total']), expected)
                verdict = json.loads((root / 'review/verdict.json').read_text(encoding='utf-8'))
                self.assertEqual(verdict['migration_source']['path'], 'migration.sql')
                self.assertEqual(verdict['migration_source']['sha256'], hashlib.sha256((root / 'migration.sql').read_bytes()).hexdigest())
                outputs = (root / 'action-outputs.txt').read_text(encoding='utf-8')
                self.assertIn(f'coverage={expected[0]}/{expected[1]}', outputs)
                self.assertIn('classification=' + ('verified_pass' if state == 'safe' else 'verified_block'), outputs)
                self.assertEqual((root / 'adapters.json').read_bytes(), before)
                self.assertFalse((root / 'ci').exists())
                if state == 'blocked':
                    self.assertIn('::error file=migration.sql,', result.stdout)
                    self.assertIn('expected "R-07", observed "A-01"', result.stdout)

    def test_missing_sql_is_unverified_and_retains_failure_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer(root)
            result = run(root, CUTOVER_MIGRATION_FILE='missing.sql')
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            verdict = json.loads((root / 'review/verdict.json').read_text(encoding='utf-8'))
            self.assertEqual(verdict['classification'], 'unverified')
            self.assertIn('missing.sql', (root / 'review/summary.md').read_text(encoding='utf-8'))
            self.assertFalse((root / 'review/report.json').exists())

    def test_reused_evidence_is_preserved_and_not_selected_for_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer(root)
            (root / 'review').mkdir()
            (root / 'review/verdict.json').write_text('previous evidence', encoding='utf-8')
            result = run(root)
            self.assertEqual(result.returncode, 2)
            self.assertEqual((root / 'review/verdict.json').read_text(), 'previous evidence')
            outputs = (root / 'action-outputs.txt').read_text()
            self.assertIn('classification=unverified', outputs)
            self.assertNotIn('evidence-path=', outputs)

    def test_paths_outside_consumer_checkout_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer(root)
            result = run(root, CUTOVER_CONTRACT='../contract.json')
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads((root / 'review/verdict.json').read_text())['classification'], 'unverified')
            self.assertFalse((root / 'review/report.json').exists())


if __name__ == '__main__':
    unittest.main()
