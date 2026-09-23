import copy
import json
import re
import unittest
from cutover.engine import load_case, load_plan, migration_statements, rehearse, replay, validate_plan
from cutover.service import run_rehearsal


class RehearsalTests(unittest.TestCase):
    def test_green_baseline_does_not_hide_broken_old_workers(self):
        for case in ('parcel', 'contacts'):
            with self.subTest(case=case):
                report = rehearse(case, load_plan(case, 'rename'))
                self.assertEqual(report['baseline']['passed'], 8)
                self.assertEqual(sum(not r['passed'] for r in report['results'] if r['category'] != 'migration_window'), 60)
                self.assertEqual(report['witness']['failure']['action'], 'old.read')
                self.assertEqual(len(report['witness']['trace']), 2)

    def test_one_time_backfill_silently_loses_visibility(self):
        report = rehearse('parcel', load_plan('parcel', 'backfill'))
        self.assertEqual(report['baseline']['passed'], 8)
        result = next(r for r in report['results'] if r['id'] == 'new_to_old-0')
        self.assertEqual(result['failure']['kind'], 'data_mismatch')
        self.assertEqual(result['failure']['expected'][101], '18 Marina Road')
        self.assertEqual(result['failure']['actual'][101], '4 Broad Street')

    def test_bridge_preserves_updates_inserts_and_rollback(self):
        for case in ('parcel', 'contacts'):
            with self.subTest(case=case):
                report = rehearse(case, load_plan(case, 'bridge'))
                self.assertEqual(report['passed'], 124)
                self.assertEqual(report['failed'], 0)
                self.assertFalse(report['bob']['verified'])

    def test_migration_windows_find_the_backfill_trigger_gap(self):
        plan = load_plan('parcel', 'late_bridge')
        statements = migration_statements(load_plan('parcel', 'bridge')['migration'])
        self.assertEqual(len(statements), 5)
        self.assertIn('END;', statements[1])
        report = rehearse('parcel', plan)
        self.assertEqual(sum(not r['passed'] for r in report['results'] if r['category'] != 'migration_window'), 0)
        self.assertEqual(report['failed'], 16)
        gap = next(r for r in report['results'] if r['id'] == 'window_write_after_2-0')
        self.assertEqual(gap['failure']['kind'], 'data_mismatch')
        self.assertEqual(gap['failure']['expected'][101], '18 Marina Road')
        self.assertEqual(gap['failure']['actual'][101], '4 Broad Street')

    def test_reference_bridge_covers_each_statement_boundary(self):
        report = rehearse('parcel', load_plan('parcel', 'bridge'))
        phase = [r for r in report['results'] if r['category'] == 'migration_window']
        self.assertEqual(len(phase), 48)
        self.assertTrue(all(r['passed'] for r in phase))

    def test_comments_and_empty_sql_do_not_inflate_migration_windows(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] = '; -- harmless opening note\n' + plan['migration'] + '\n;; /* trailing note */ -- final note'
        self.assertEqual(len(migration_statements(plan['migration'])), 5)
        report = rehearse('parcel', plan)
        self.assertEqual((report['passed'], report['total']), (124, 124))
        self.assertEqual(next(c['total'] for c in report['categories'] if c['id'] == 'migration_window'), 48)

    def test_deleting_any_sync_trigger_is_detected(self):
        for trigger in ('sync_old_update', 'sync_new_update', 'sync_old_insert'):
            with self.subTest(trigger=trigger):
                plan = load_plan('parcel', 'bridge')
                plan['migration'] = re.sub(r'CREATE TRIGGER ' + trigger + r'.*?END;', '', plan['migration'], flags=re.S)
                report = rehearse('parcel', plan)
                self.assertEqual(report['status'], 'blocked')
                self.assertTrue(any(r['failure'] and r['failure']['kind'] == 'data_mismatch' for r in report['results']))

    def test_sql_injection_characters_are_bound_as_data(self):
        contract = load_case()
        plan = load_plan('parcel', 'bridge')
        value = "'); DROP TABLE orders; --"
        report = replay(contract, plan, ['migrate', 'old.write', 'new.read'], value)
        self.assertTrue(report['passed'])
        self.assertEqual(report['trace'][-1]['actual'][101], value)

    def test_additional_seed_rows_and_values_are_not_hardcoded(self):
        contract = load_case()
        contract['seed'] = [[401, 'alpha'], [607, 'beta'], [999, 'third']]
        plan = load_plan('parcel', 'bridge')
        for actions in (['migrate', 'new.write', 'old.read'], ['migrate', 'old.insert', 'new.read']):
            self.assertTrue(replay(contract, plan, actions, 'a completely unseen value')['passed'])

    def test_dropped_unmodified_records_are_detected(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] += '\nDELETE FROM orders WHERE id = 102;'
        self.assertEqual(rehearse('parcel', plan)['status'], 'blocked')

    def test_cross_record_write_bug_is_detected(self):
        plan = load_plan('parcel', 'bridge')
        plan['write'] = 'UPDATE orders SET shipping_address = :value'
        self.assertEqual(rehearse('parcel', plan)['status'], 'blocked')

    def test_noop_write_cannot_claim_success(self):
        plan = load_plan('parcel', 'bridge')
        plan['write'] = 'UPDATE orders SET shipping_address = :value WHERE id = -1'
        report = rehearse('parcel', plan)
        self.assertTrue(any(r['failure'] and r['failure']['kind'] == 'write_not_acknowledged' for r in report['results']))

    def test_old_column_only_plan_cannot_pass_as_a_migration(self):
        old = load_case('parcel')['old']
        plan = {'name': 'No migration', 'migration': 'SELECT 1;', **old}
        report = rehearse('parcel', plan)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['baseline']['passed'], 0)
        self.assertTrue(all(not result['passed'] for result in report['results']))

    def test_new_adapter_must_really_use_target_column(self):
        old = load_case('parcel')['old']
        for operation in ('read', 'write'):
            with self.subTest(operation=operation):
                plan = load_plan('parcel', 'bridge')
                plan[operation] = old[operation]
                report = rehearse('parcel', plan)
                self.assertEqual(report['status'], 'blocked')
                self.assertTrue(any(result['failure'] and result['failure']['kind'] == 'adapter_contract'
                                    for result in report['results']))

    def test_target_ledger_catches_stale_column_masked_by_adapter(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] = re.sub(r'CREATE TRIGGER sync_old_update.*?END;', '', plan['migration'], flags=re.S)
        plan['read'] = ('SELECT id, delivery_address || substr(shipping_address, 1, 0) AS value '
                        'FROM orders ORDER BY id')
        report = rehearse('parcel', plan)
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(any(result['failure'] and result['failure']['kind'] == 'target_mismatch'
                            for result in report['results']))

    def test_file_database_and_extension_access_denied(self):
        for sql in ("ATTACH DATABASE ':memory:' AS other;", 'PRAGMA writable_schema=ON;', "SELECT load_extension('anything');"):
            plan = load_plan('parcel', 'bridge')
            plan['migration'] = sql
            report = replay(load_case(), plan, ['migrate'], 'x')
            self.assertFalse(report['passed'])
            self.assertEqual(report['failure']['kind'], 'sql_error')

    def test_runaway_query_is_interrupted(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] = 'WITH RECURSIVE forever(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM forever) SELECT sum(x) FROM forever;'
        result = replay(load_case(), plan, ['migrate'], 'x')
        self.assertFalse(result['passed'])
        self.assertIn('interrupted', result['failure']['message'])

    def test_hashes_track_inputs_and_remain_deterministic(self):
        a = rehearse('parcel', load_plan('parcel', 'rename'))
        b = rehearse('parcel', load_plan('parcel', 'bridge'))
        c = rehearse('parcel', load_plan('parcel', 'rename'))
        self.assertEqual(a['suite_hash'], b['suite_hash'])
        self.assertEqual(a['contract_hash'], b['contract_hash'])
        self.assertNotEqual(a['plan_hash'], b['plan_hash'])
        self.assertEqual(a['plan_hash'], c['plan_hash'])
        self.assertEqual(a['results'], c['results'])

    def test_cannot_supply_replacement_oracle_or_schedules(self):
        plan = load_plan('parcel', 'bridge')
        plan['oracle'] = {}
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_worker_process_returns_executed_result(self):
        result = run_rehearsal('parcel', load_plan('parcel', 'bridge'))
        self.assertEqual(result['passed'], 124)
        self.assertIsNone(result['witness'])


if __name__ == '__main__':
    unittest.main()
