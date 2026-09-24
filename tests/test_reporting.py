import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cutover.engine import load_case, load_plan, rehearse
from cutover.reporting import fenced, render_markdown, render_reproduction


ROOT = Path(__file__).resolve().parents[1]


class ReviewReportTests(unittest.TestCase):
    def test_blocked_and_passing_reports_show_actual_replays(self):
        blocked = rehearse('parcel', load_plan('parcel', 'late_bridge'))
        blocked_md = render_markdown(blocked)
        self.assertIn('Completed rollout | 76 | 76', blocked_md)
        self.assertIn('Migration-statement windows | 32 | 48', blocked_md)
        self.assertIn('window_write_after_2-0', blocked_md)
        self.assertIn('18 Marina Road', blocked_md)
        self.assertIn('4 Broad Street', blocked_md)
        self.assertIn(blocked['plan_hash'], blocked_md)
        passing = rehearse('parcel', load_plan('parcel', 'bridge'))
        passing_md = render_markdown(passing)
        self.assertIn('Example passing migration-window replay', passing_md)
        self.assertIn('124/124 rollout and window probes passed', passing_md)
        self.assertIn('not a deployment approval', passing_md)

    def test_sql_with_markdown_fences_cannot_break_its_code_block(self):
        rendered = fenced('SELECT 1;\n~~~~~\nSELECT 2;', 'sql')
        self.assertTrue(rendered.startswith('~~~~~~sql\n'))
        self.assertTrue(rendered.endswith('\n~~~~~~'))

    def test_review_identifies_later_seed_that_exposes_false_pass(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] = plan['migration'].replace(
            'WHEN NEW.delivery_address IS NOT NEW.shipping_address',
            'WHEN NEW.id = 101 AND NEW.delivery_address IS NOT NEW.shipping_address')
        review = render_markdown(rehearse('parcel', plan))
        self.assertIn('Row shown in this replay: `102`', review)
        self.assertIn('Seed IDs checked before this verdict:', review)

    def test_review_identifies_later_insert_id_that_exposes_false_pass(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] = plan['migration'].replace(
            'WHEN NEW.shipping_address IS NULL',
            'WHEN NEW.id = 103 AND NEW.shipping_address IS NULL')
        review = render_markdown(rehearse('parcel', plan))
        self.assertIn('Inserted ID shown in this replay: `104`', review)
        self.assertIn('Insert IDs checked before this verdict:', review)

    def test_cli_writes_json_and_review_from_the_same_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.json'
            review = Path(temporary) / 'review.md'
            replay = Path(temporary) / 'replay.py'
            result = subprocess.run(
                [sys.executable, '-m', 'cutover', '--reference', 'late_bridge',
                 '--output', str(report), '--markdown', str(review), '--repro', str(replay)],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
            self.assertEqual(result.returncode, 1)
            data = json.loads(report.read_text(encoding='utf-8'))
            markdown = review.read_text(encoding='utf-8')
            self.assertEqual(data['status'], 'blocked')
            self.assertIn(data['plan_hash'], markdown)
            self.assertIn(data['witness']['id'], markdown)
            self.assertIn(data['witness']['failure']['expected']['101'], markdown)
            reproduced = subprocess.run([sys.executable, '-I', str(replay)],
                                        cwd=temporary, capture_output=True, text=True,
                                        encoding='utf-8', timeout=15)
            self.assertEqual(reproduced.returncode, 0, reproduced.stderr)
            self.assertEqual(json.loads(reproduced.stdout)['probe'], data['witness']['id'])
            audited = subprocess.run(
                [sys.executable, '-m', 'cutover.audit_report', '--report', str(report),
                 '--plan', str(ROOT / 'examples' / 'parcel' / 'late_bridge.json')],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=25)
            self.assertEqual(audited.returncode, 1, audited.stderr)
            self.assertIn('VERIFIED BLOCKED: 108/124', audited.stdout)

    def test_audit_cli_accepts_replayed_safe_report_and_rejects_forged_bob_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'safe.json'
            plan = ROOT / 'examples' / 'parcel' / 'bridge.json'
            generated = subprocess.run(
                [sys.executable, '-m', 'cutover', '--plan', str(plan), '--output', str(report)],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=25)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            command = [sys.executable, '-m', 'cutover.audit_report', '--report', str(report), '--plan', str(plan)]
            audited = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                     encoding='utf-8', timeout=25)
            self.assertEqual(audited.returncode, 0, audited.stderr)
            self.assertIn('VERIFIED PASS: 124/124', audited.stdout)
            data = json.loads(report.read_text(encoding='utf-8'))
            data['bob']['verified'] = True
            report.write_text(json.dumps(data), encoding='utf-8')
            forged = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                    encoding='utf-8', timeout=25)
            self.assertEqual(forged.returncode, 2)
            self.assertIn('fresh replay: bob', forged.stderr)

    def test_downloadable_witness_reexecutes_the_failure(self):
        for case in ('parcel', 'contacts'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                report = rehearse(case, load_plan(case, 'late_bridge'))
                script = Path(temporary) / 'reproduce.py'
                script.write_text(render_reproduction(report, load_case(case)), encoding='utf-8')
                result = subprocess.run([sys.executable, '-I', str(script)],
                                        cwd=temporary, capture_output=True, text=True,
                                        encoding='utf-8', timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                outcome = json.loads(result.stdout)
                self.assertEqual(outcome['status'], 'REPRODUCED')
                self.assertEqual(outcome['probe'], report['witness']['id'])
                self.assertEqual(outcome['failure_kind'], report['witness']['failure']['kind'])

    def test_standalone_witness_reexecutes_mid_migration_old_read_failure(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] = plan['migration'].replace(
            'WHEN NEW.delivery_address IS NOT NEW.shipping_address',
            "WHEN NEW.delivery_address IS NOT NEW.shipping_address AND NEW.delivery_address != 'temporary'")
        plan['migration'] += "\nUPDATE orders SET delivery_address = 'temporary' WHERE id = 102;"
        plan['migration'] += '\nUPDATE orders SET delivery_address = shipping_address WHERE id = 102;'
        report = rehearse('parcel', plan)
        self.assertEqual(report['witness']['failure']['action'], 'old.read')
        review = render_markdown(report)
        self.assertIn('old.read', review)
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'reproduce.py'
            script.write_text(render_reproduction(report, load_case('parcel')), encoding='utf-8')
            result = subprocess.run([sys.executable, '-I', str(script)], cwd=temporary,
                                    capture_output=True, text=True, encoding='utf-8', timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            outcome = json.loads(result.stdout)
            self.assertEqual(outcome['status'], 'REPRODUCED')
            self.assertEqual(outcome['probe'], report['witness']['id'])
            self.assertEqual(outcome['actual']['102'], 'temporary')

    def test_cross_record_witness_reexecutes_both_write_targets(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] += '''
CREATE TRIGGER reset_first AFTER UPDATE OF delivery_address ON orders
WHEN NEW.id = 102
BEGIN
  UPDATE orders SET delivery_address = '4 Broad Street',
                    shipping_address = '4 Broad Street' WHERE id = 101;
END;
'''
        report = rehearse('parcel', plan)
        self.assertEqual(report['witness']['write_targets'], [101, 102])
        review = render_markdown(report)
        self.assertIn('Cross-record paths checked before this verdict:', review)
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'reproduce.py'
            script.write_text(render_reproduction(report, load_case('parcel')), encoding='utf-8')
            result = subprocess.run([sys.executable, '-I', str(script)],
                                    cwd=temporary, capture_output=True, text=True,
                                    encoding='utf-8', timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'REPRODUCED')

    def test_standalone_witness_uses_separate_worker_connections(self):
        plan = load_plan('parcel', 'bridge')
        plan['read'] = ('SELECT id, CAST(last_insert_rowid() AS TEXT) || '
                        'substr(shipping_address, 1, 0) AS value FROM orders ORDER BY id')
        report = rehearse('parcel', plan)
        self.assertEqual(report['witness']['failure']['kind'], 'data_mismatch')
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / 'reproduce.py'
            script.write_text(render_reproduction(report, load_case('parcel')), encoding='utf-8')
            result = subprocess.run([sys.executable, '-I', str(script)], cwd=temporary,
                                    capture_output=True, text=True, encoding='utf-8', timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            outcome = json.loads(result.stdout)
            self.assertEqual(outcome['probe'], report['witness']['id'])
            self.assertEqual(outcome['actual']['101'], '0')

    def test_passing_report_has_no_failure_reproduction(self):
        report = rehearse('parcel', load_plan('parcel', 'bridge'))
        with self.assertRaisesRegex(ValueError, 'data mismatch'):
            render_reproduction(report, load_case('parcel'))

        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / 'evidence.json'
            replay = Path(temporary) / 'replay.py'
            result = subprocess.run([sys.executable, '-m', 'cutover', '--reference', 'bridge',
                                     '--output', str(evidence), '--repro', str(replay)],
                                    cwd=ROOT, capture_output=True, text=True,
                                    encoding='utf-8', timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(evidence.exists())
            self.assertFalse(replay.exists())


if __name__ == '__main__':
    unittest.main()
