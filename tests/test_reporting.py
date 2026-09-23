import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cutover.engine import load_plan, rehearse
from cutover.reporting import fenced, render_markdown


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
            result = subprocess.run(
                [sys.executable, '-m', 'cutover', '--reference', 'late_bridge',
                 '--output', str(report), '--markdown', str(review)],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
            self.assertEqual(result.returncode, 1)
            data = json.loads(report.read_text(encoding='utf-8'))
            markdown = review.read_text(encoding='utf-8')
            self.assertEqual(data['status'], 'blocked')
            self.assertIn(data['plan_hash'], markdown)
            self.assertIn(data['witness']['id'], markdown)
            self.assertIn(data['witness']['failure']['expected']['101'], markdown)


if __name__ == '__main__':
    unittest.main()
