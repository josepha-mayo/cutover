import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from cutover.bundle import render_comparison_bundle
from cutover.engine import load_case, load_plan, rehearse


ROOT = Path(__file__).resolve().parents[1]


class VerifiedMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = rehearse('parcel', load_plan('parcel', 'late_bridge'))
        cls.after = rehearse('parcel', load_plan('parcel', 'bridge'))
        cls.packet = render_comparison_bundle(cls.before, cls.after, load_case('parcel'))

    def run_cli(self, packet, output):
        return subprocess.run([sys.executable, '-m', 'cutover.audit_bundle', '--bundle', str(packet),
                               '--markdown', str(output)], cwd=ROOT, capture_output=True,
                              text=True, encoding='utf-8', timeout=30)

    def test_verified_block_writes_comparison_and_actual_witness(self):
        with tempfile.TemporaryDirectory() as folder:
            packet, output = Path(folder) / 'pair.zip', Path(folder) / 'review.md'
            packet.write_bytes(self.packet)
            result = self.run_cli(packet, output)
            self.assertEqual(result.returncode, 1, result.stderr)
            text = output.read_text(encoding='utf-8')
            self.assertIn('Independently verified', text)
            self.assertIn('"paired_probes": 76', text)
            self.assertIn('"window_probes_paired": false', text)
            self.assertIn('window_write_after_2-0', text)
            self.assertIn('18 Marina Road', text)
            self.assertIn('4 Broad Street', text)
            self.assertIn(self.before['plan_hash'], text)
            self.assertIn(self.after['plan_hash'], text)
            self.assertIn('### migration', text)

    def test_changed_comparison_refuses_output(self):
        with tempfile.TemporaryDirectory() as folder:
            packet, output = Path(folder) / 'pair.zip', Path(folder) / 'review.md'
            packet.write_bytes(self.packet)
            with zipfile.ZipFile(packet) as archive:
                files = {name: archive.read(name) for name in archive.namelist()}
            changed = json.loads(files['comparison.json'])
            changed['paired_probes'] += 1
            files['comparison.json'] = json.dumps(changed).encode('utf-8')
            with zipfile.ZipFile(packet, 'w') as archive:
                for name, body in files.items():
                    archive.writestr(name, body)
            result = self.run_cli(packet, output)
            self.assertEqual(result.returncode, 2)
            self.assertIn('UNVERIFIED', result.stderr)
            self.assertFalse(output.exists())

    def test_output_never_overwrites_existing_file_or_input_packet(self):
        with tempfile.TemporaryDirectory() as folder:
            packet, output = Path(folder) / 'pair.zip', Path(folder) / 'review.md'
            packet.write_bytes(self.packet)
            output.write_text('Retained review', encoding='utf-8')
            self.assertEqual(self.run_cli(packet, output).returncode, 2)
            self.assertEqual(output.read_text(encoding='utf-8'), 'Retained review')
            self.assertEqual(self.run_cli(packet, packet).returncode, 2)
            self.assertEqual(packet.read_bytes(), self.packet)
