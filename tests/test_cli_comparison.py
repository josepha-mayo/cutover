"""Private before/after evidence must remain independently auditable."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class LocalComparisonTests(unittest.TestCase):
    def run_cli(self, candidate, baseline, output):
        return subprocess.run([sys.executable, '-m', 'cutover', '--contract',
            str(ROOT / 'examples/warehouse/contract.json'), '--plan', str(candidate),
            '--baseline-plan', str(baseline), '--bundle', str(output)], cwd=ROOT,
            capture_output=True, text=True, encoding='utf-8')

    def test_repair_and_regression_both_export_verified_comparisons(self):
        safe = ROOT / 'examples/warehouse/bridge.json'
        unsafe = ROOT / 'examples/warehouse/late_bridge.json'
        with tempfile.TemporaryDirectory() as directory:
            for candidate, baseline, exit_code in ((safe, unsafe, 0), (unsafe, safe, 1)):
                output = Path(directory) / f'comparison-{exit_code}.zip'
                process = self.run_cli(candidate, baseline, output)
                self.assertEqual(process.returncode, exit_code, process.stderr)
                with zipfile.ZipFile(output) as archive:
                    summary = json.loads(archive.read('comparison.json'))
                    self.assertFalse(summary['window_probes_paired'])
                    self.assertEqual(summary['contract_hash'], json.loads(archive.read('candidate/report.json'))['contract_hash'])
                    self.assertGreater(summary['migration_window_failures']['candidate' if exit_code else 'baseline']['failed'], 0)
                audit = subprocess.run([sys.executable, '-m', 'cutover.audit_bundle', '--bundle', str(output)],
                    cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(audit.returncode, 1, audit.stderr)

    def test_existing_evidence_is_not_overwritten(self):
        safe = ROOT / 'examples/warehouse/bridge.json'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'keep.zip'
            output.write_bytes(b'original evidence')
            process = self.run_cli(safe, safe, output)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(output.read_bytes(), b'original evidence')
