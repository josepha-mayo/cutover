"""Bind source annotations to executed window traces and exact SQL file lines."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ci.witness_source import window_source
from cutover.engine import load_case, load_plan, PAYLOADS
from cutover.service import run_rehearsal

ROOT = Path(__file__).resolve().parents[1]


def annotated_late_sql():
    plan = json.loads((ROOT / 'examples/warehouse/late_bridge.json').read_text(encoding='utf-8'))
    sql = '-- Reviewed SQL; this is a comment.\n/* Another comment.\n   Still a comment.\n*/\n' + plan['migration']
    return sql.replace('UPDATE stock_items SET fulfillment_bin = pick_bin;',
                       '-- Copy current values; ``` is comment text.\n'
                       'UPDATE stock_items\nSET fulfillment_bin = pick_bin;')


class WitnessSourceTests(unittest.TestCase):
    def test_actual_gate_annotates_boundary_in_lf_and_bom_crlf_sources(self):
        script = annotated_late_sql()
        self.assertEqual(script.splitlines()[7], 'SET fulfillment_bin = pick_bin;')
        for encoding in ('lf', 'bom_crlf'):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = script.encode('utf-8') if encoding == 'lf' else b'\xef\xbb\xbf' + script.replace('\n', '\r\n').encode('utf-8')
                sql = root / 'migration.sql'
                sql.write_bytes(source)
                out = root / 'review'
                result = subprocess.run(
                    [sys.executable, str(ROOT / 'ci/review_gate.py'),
                     '--contract', str(ROOT / 'examples/warehouse/contract.json'),
                     '--plan', str(ROOT / 'examples/warehouse/bridge.json'),
                     '--migration-file', str(sql), '--output-dir', str(out)],
                    cwd=ROOT, env={**os.environ, 'GITHUB_ACTIONS': 'true', 'GITHUB_WORKSPACE': str(root)},
                    capture_output=True, text=True, encoding='utf-8', timeout=300,
                )
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                verdict = json.loads((out / 'verdict.json').read_text(encoding='utf-8'))
                report = json.loads((out / 'report.json').read_text(encoding='utf-8'))
                location = verdict['witness_source']
                self.assertEqual(location['probe_id'], report['witness']['id'])
                self.assertEqual(location['operation'], 'old.write')
                self.assertEqual(location['after_statement'], 2)
                self.assertEqual(location['statement_count'], 5)
                self.assertEqual(location['line'], 8)
                self.assertEqual((location['statement_start_line'], location['statement_end_line']), (6, 8))
                self.assertEqual(location['path'], 'migration.sql')
                self.assertEqual(location['sql_file_sha256'], hashlib.sha256(source).hexdigest())
                self.assertIn('::error file=migration.sql,line=8,endLine=8,', result.stdout)
                self.assertIn('Observed old.write after SQL statement 2 of 5 (SQL line 8).', result.stdout)
                summary = (out / 'summary.md').read_text(encoding='utf-8')
                self.assertIn('````sql\n', summary)
                self.assertIn('not a claim that this SQL line alone caused the defect.', summary)
                self.assertIn('SET fulfillment_bin = pick_bin;', summary)

    def test_location_requires_a_matching_successful_execution_prefix(self):
        plan = json.loads((ROOT / 'examples/warehouse/late_bridge.json').read_text(encoding='utf-8'))
        plan['migration'] = annotated_late_sql()
        contract = json.loads((ROOT / 'examples/warehouse/contract.json').read_text(encoding='utf-8'))
        report = run_rehearsal('custom', plan, contract)
        source = {'path': 'migration.sql', 'sha256': hashlib.sha256(plan['migration'].encode()).hexdigest()}
        self.assertEqual(window_source(report, source)['line'], 8)
        self.assertIsNone(window_source(report, None))
        for change in ('wrong_boundary', 'failed_prefix', 'different_sql', 'missing_operation'):
            broken = copy.deepcopy(report)
            if change == 'wrong_boundary':
                broken['witness']['id'] = 'window_write_after_3-0'
            elif change == 'failed_prefix':
                broken['witness']['trace'][0]['status'] = 'fail'
            elif change == 'different_sql':
                broken['witness']['trace'][0]['sql'] = 'SELECT 1;'
            else:
                broken['witness']['trace'] = [step for step in broken['witness']['trace'] if step['action'] != 'old.write']
            with self.subTest(change=change):
                self.assertIsNone(window_source(broken, source))

    def test_completed_rollout_failure_does_not_invent_a_migration_line(self):
        plan = load_plan('parcel', 'cross_record')
        report = run_rehearsal('custom', plan, {**load_case('parcel'), 'payloads': PAYLOADS})
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['witness']['id'].startswith('window_'))
        self.assertIsNone(window_source(report, {'path': 'migration.sql', 'sha256': '0' * 64}))
