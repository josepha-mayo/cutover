"""Hold the agreed contract fixed instead of treating changed tests as a repair."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cutover.audit_bundle import audit
from cutover.engine import PAYLOADS, digest, load_case, load_plan

ROOT = Path(__file__).resolve().parents[1]


def check(root, contract, plan, expected=None, label='review', pretty=False):
    contract_path = root / 'contract.json'
    text = json.dumps(contract, ensure_ascii=False, sort_keys=pretty,
                      indent=4 if pretty else None)
    contract_path.write_bytes(text.replace('\n', '\r\n').encode('utf-8') if pretty else text.encode('utf-8'))
    (root / 'adapters.json').write_text(json.dumps({k: v for k, v in plan.items()
                                                 if k != 'migration'}), encoding='utf-8')
    (root / 'migration.sql').write_text(plan['migration'], encoding='utf-8')
    env = {**os.environ, 'GITHUB_WORKSPACE': str(root), 'GITHUB_ACTIONS': 'true',
           'GITHUB_OUTPUT': str(root / f'{label}-outputs.txt'),
           'GITHUB_STEP_SUMMARY': str(root / f'{label}-summary.md'),
           'CUTOVER_CONTRACT': 'contract.json', 'CUTOVER_PLAN': 'adapters.json',
           'CUTOVER_MIGRATION_FILE': 'migration.sql', 'CUTOVER_OUTPUT_DIR': label,
           'CUTOVER_EXPECTED_CONTRACT_HASH': expected or ''}
    result = subprocess.run([sys.executable, str(ROOT / 'ci/action_entry.py')],
                            cwd=root, env=env, text=True, encoding='utf-8',
                            capture_output=True, timeout=300)
    verdict = json.loads((root / label / 'verdict.json').read_text(encoding='utf-8'))
    return result, verdict


class ContractLockTests(unittest.TestCase):
    def test_unchanged_sql_can_pass_changed_tests_but_not_the_original_lock(self):
        contract = {**load_case('parcel'), 'payloads': PAYLOADS}
        altered = copy.deepcopy(contract)
        altered['seed'] = [[record_id + 1000, value] for record_id, value in altered['seed']]
        unsafe = load_plan('parcel', 'cross_record')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scenarios = [
                ('unsafe-original', contract, unsafe, digest(contract), 1, (100, 132)),
                ('changed-unlocked', altered, unsafe, None, 0, (132, 132)),
                ('changed-locked', altered, unsafe, digest(contract), 2, None),
                ('repaired-original', contract, load_plan('parcel', 'bridge'), digest(contract), 0, (124, 124)),
            ]
            hashes = []
            for label, data, plan, lock, exit_code, counts in scenarios:
                with self.subTest(label=label):
                    result, verdict = check(root, data, plan, lock, label)
                    self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
                    self.assertEqual(verdict['classification'],
                                     {0: 'verified_pass', 1: 'verified_block', 2: 'unverified'}[exit_code])
                    if counts:
                        report = audit(root / label / 'review.zip')[0]
                        self.assertEqual((report['passed'], report['total']), counts)
                        hashes.append(report['plan_hash'])
                    else:
                        self.assertEqual(verdict['contract_lock'], {
                            'expected': digest(contract), 'actual': digest(altered), 'status': 'changed'})
                        self.assertIn('Contract changed', verdict['reason'])
                        self.assertFalse((root / label / 'report.json').exists())
                        self.assertFalse((root / label / 'review.zip').exists())
                        summary = (root / label / 'summary.md').read_text(encoding='utf-8')
                        self.assertIn(digest(contract), summary)
                        self.assertIn(digest(altered), summary)
                        self.assertIn('::error file=contract.json,', result.stdout)
                        self.assertIn('Contract changed', result.stdout)
                        self.assertNotIn('coverage=', (root / f'{label}-outputs.txt').read_text())
            self.assertEqual(hashes[0], hashes[1], 'Only the test contract changed, not the unsafe SQL')

    def test_json_layout_and_line_endings_do_not_change_the_lock(self):
        contract = json.loads((ROOT / 'examples/warehouse/contract.json').read_text(encoding='utf-8'))
        plan = json.loads((ROOT / 'ci/candidate.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result, verdict = check(root, contract, plan, digest(contract).upper(), pretty=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(verdict['contract_lock'], {
                'expected': digest(contract), 'actual': digest(contract), 'status': 'matched'})
            report = audit(root / 'review/review.zip')[0]
            self.assertEqual(report['contract_hash'], verdict['contract_lock']['expected'])

    def test_invalid_lock_retains_an_unverified_error_without_running_sql(self):
        contract = {**load_case('parcel'), 'payloads': PAYLOADS}
        for lock in ('abc', 'g' * 64, '0' * 65, ' ' * 64):
            with self.subTest(lock=lock), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                result, verdict = check(root, contract, load_plan('parcel', 'bridge'), lock)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(verdict['classification'], 'unverified')
                self.assertIn('64 hexadecimal', verdict['reason'])
                self.assertFalse((root / 'review/report.json').exists())
                self.assertTrue((root / 'review/summary.md').exists())


if __name__ == '__main__':
    unittest.main()
