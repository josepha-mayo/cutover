"""Private local exports retain the selected failure and canonical suite report."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SelectedCliTests(unittest.TestCase):
    def test_selected_unicode_exports_and_canonical_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, note, script = [root / name for name in ('report.json', 'review.md', 'replay.py')]
            result = subprocess.run([sys.executable, '-m', 'cutover', '--reference', 'late_bridge',
                '--selected-probe', 'window_write_after_2-3', '--output', str(report),
                '--markdown', str(note), '--repro', str(script)], cwd=ROOT,
                capture_output=True, text=True, encoding='utf-8', timeout=60)
            self.assertEqual(result.returncode, 1, result.stderr)
            suite = json.loads(report.read_text(encoding='utf-8'))
            self.assertNotEqual(suite['witness']['id'], 'window_write_after_2-3')
            self.assertIn('**`window_write_after_2-3`**', note.read_text(encoding='utf-8'))
            replay = subprocess.run([sys.executable, '-I', str(script)], cwd=directory,
                capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            observed = json.loads(replay.stdout)
            self.assertEqual(observed['probe'], 'window_write_after_2-3')
            self.assertEqual(observed['expected']['101'], '12 Àdéníran • 東京')
            self.assertEqual(observed['actual']['101'], '4 Broad Street')
            self.assertEqual(observed['plan_hash'], suite['plan_hash'])

    def test_passing_or_missing_selection_writes_no_evidence(self):
        for probe in ('window_write_after_3-3', 'missing-probe'):
            with self.subTest(probe=probe), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'report.json'
                note = Path(directory) / 'review.md'
                result = subprocess.run([sys.executable, '-m', 'cutover', '--reference', 'late_bridge',
                    '--selected-probe', probe, '--output', str(output), '--markdown', str(note)],
                    cwd=ROOT, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.exists())
                self.assertFalse(note.exists())

    def test_selection_requires_an_export(self):
        result = subprocess.run([sys.executable, '-m', 'cutover', '--selected-probe', 'missing'],
                                cwd=ROOT, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'requires --markdown or --repro', result.stderr)
