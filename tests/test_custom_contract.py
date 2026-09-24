import copy
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from cutover.engine import rehearse, validate_contract
from cutover.service import run_rehearsal, validate_imported_contract, verify_report_against_replay


ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / 'examples' / 'warehouse'


def fixture(name):
    return json.loads((WAREHOUSE / name).read_text(encoding='utf-8'))


class CustomContractTests(unittest.TestCase):
    def test_imported_warehouse_finds_gap_and_accepts_its_repair(self):
        contract = fixture('contract.json')
        late = run_rehearsal('custom', fixture('late_bridge.json'), contract)
        safe = run_rehearsal('custom', fixture('bridge.json'), contract)
        self.assertEqual((late['baseline']['passed'], late['passed'], late['total']), (8, 108, 124))
        self.assertEqual((safe['status'], safe['passed'], safe['total']), ('pass', 124, 124))
        self.assertEqual(late['witness']['id'], 'window_write_after_2-0')
        self.assertEqual(late['witness']['failure']['expected']['11'], 'R-07')
        self.assertEqual(late['witness']['failure']['actual']['11'], 'A-01')
        self.assertEqual(late['contract_hash'], safe['contract_hash'])
        self.assertNotEqual(late['plan_hash'], safe['plan_hash'])
        verify_report_against_replay('custom', fixture('late_bridge.json'), late, contract)

    def test_imported_contract_negative_control_changes_verdict(self):
        plan = fixture('bridge.json')
        plan['migration'] = re.sub(r'CREATE TRIGGER sync_old_update.*?END;', '',
                                   plan['migration'], flags=re.S)
        result = rehearse('custom', plan, fixture('contract.json'))
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(any(row['failure'] for row in result['results']))

    def test_domain_payloads_are_part_of_the_suite_identity(self):
        contract = fixture('contract.json')
        plan = fixture('bridge.json')
        original = rehearse('custom', plan, contract)
        changed = copy.deepcopy(contract)
        changed['payloads'][0] = 'Q-99'
        revised = rehearse('custom', plan, changed)
        self.assertEqual(original['total'], revised['total'])
        self.assertNotEqual(original['suite_hash'], revised['suite_hash'])
        self.assertEqual(original['results'][0]['payload'], 'R-07')
        self.assertEqual(revised['results'][0]['payload'], 'Q-99')

    def test_contract_identifier_case_follows_sqlite_semantics(self):
        contract = fixture('contract.json')
        contract['table'] = contract['table'].upper()
        contract['new_column'] = contract['new_column'].upper()
        result = rehearse('custom', fixture('bridge.json'), contract)
        self.assertEqual((result['status'], result['passed'], result['total']),
                         ('pass', 124, 124))

    def test_rejects_invalid_shape_and_seed_before_execution(self):
        base = fixture('contract.json')
        variants = []
        duplicate = copy.deepcopy(base)
        duplicate['seed'][1][0] = duplicate['seed'][0][0]
        variants.append(duplicate)
        unsafe_identifier = copy.deepcopy(base)
        unsafe_identifier['table'] = 'stock_items; DROP TABLE stock_items'
        variants.append(unsafe_identifier)
        same_column = copy.deepcopy(base)
        same_column['new_column'] = 'PICK_BIN'
        variants.append(same_column)
        extra_field = copy.deepcopy(base)
        extra_field['oracle'] = {}
        variants.append(extra_field)
        for contract in variants:
            with self.subTest(contract=contract):
                with self.assertRaises(ValueError):
                    validate_contract(contract)

    def test_bad_old_adapter_and_preexisting_target_are_rejected(self):
        contract = fixture('contract.json')
        bad_reader = copy.deepcopy(contract)
        bad_reader['old']['read'] = 'SELECT id, pick_bin FROM stock_items ORDER BY id'
        with self.assertRaisesRegex(ValueError, 'id and value'):
            rehearse('custom', fixture('bridge.json'), bad_reader)
        preexisting = copy.deepcopy(contract)
        preexisting['schema'] = ('CREATE TABLE stock_items '
                                 '(id INTEGER PRIMARY KEY, pick_bin TEXT NOT NULL, '
                                 'fulfillment_bin TEXT);')
        with self.assertRaisesRegex(ValueError, 'not the new column'):
            rehearse('custom', fixture('bridge.json'), preexisting)

    def test_later_payload_must_work_for_old_updates_and_inserts(self):
        base = fixture('contract.json')
        base['payloads'][1] = 'LONG-BIN'
        schemas = (
            'CREATE TABLE stock_items (id INTEGER PRIMARY KEY, '
            'pick_bin TEXT NOT NULL CHECK(length(pick_bin) <= 4));',
            'CREATE TABLE stock_items (id INTEGER PRIMARY KEY, '
            'pick_bin TEXT NOT NULL CHECK(id <= 33 OR length(pick_bin) <= 4));',
        )
        for schema in schemas:
            with self.subTest(schema=schema):
                contract = copy.deepcopy(base)
                contract['schema'] = schema
                with self.assertRaisesRegex(ValueError, 'payload index 1'):
                    validate_imported_contract(contract)
                with self.assertRaisesRegex(ValueError, 'payload index 1'):
                    run_rehearsal('custom', fixture('bridge.json'), contract)

    def test_initial_schema_and_every_seed_update_are_checked(self):
        base = fixture('contract.json')
        extra_table = copy.deepcopy(base)
        extra_table['schema'] += '\nCREATE TABLE hidden (id INTEGER);'
        with self.assertRaisesRegex(ValueError, 'exactly the named table'):
            rehearse('custom', fixture('bridge.json'), extra_table)
        trigger = copy.deepcopy(base)
        trigger['schema'] += ('\nCREATE TRIGGER hidden_update AFTER UPDATE ON stock_items '
                              'BEGIN SELECT 1; END;')
        with self.assertRaisesRegex(ValueError, 'no views or triggers'):
            rehearse('custom', fixture('bridge.json'), trigger)
        partial_updater = copy.deepcopy(base)
        partial_updater['old']['write'] += ' AND id = 11'
        with self.assertRaisesRegex(ValueError, 'every seed ID'):
            rehearse('custom', fixture('bridge.json'), partial_updater)

    def test_contract_schema_is_authorized_before_it_runs(self):
        contract = fixture('contract.json')
        contract['schema'] += "\nATTACH DATABASE ':memory:' AS forbidden;"
        with self.assertRaisesRegex(ValueError, 'not authorized'):
            rehearse('custom', fixture('bridge.json'), contract)

    def test_cli_accepts_custom_contract_and_keeps_blocked_exit_code(self):
        command = [sys.executable, '-m', 'cutover', '--contract',
                   str(WAREHOUSE / 'contract.json'), '--plan',
                   str(WAREHOUSE / 'late_bridge.json')]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 1)
        self.assertIn('BLOCKED: 108/124', result.stdout)
        self.assertIn('window', result.stdout)

    def test_cli_refuses_to_replace_its_candidate_input(self):
        plan_path = WAREHOUSE / 'bridge.json'
        before = plan_path.read_bytes()
        result = subprocess.run(
            [sys.executable, '-m', 'cutover', '--contract', str(WAREHOUSE / 'contract.json'),
             '--plan', str(plan_path), '--output', str(plan_path)],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertIn('cannot overwrite', result.stderr)
        self.assertEqual(plan_path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
