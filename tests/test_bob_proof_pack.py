import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from cutover.bob_proof_pack import render_bob_proof_pack

ROOT = Path(__file__).resolve().parents[1]


class BobProofPackTests(unittest.TestCase):
    def test_recorded_review_keeps_its_original_packet_and_exact_saved_bob_candidate(self):
        from cutover.audit_bundle import audit_files, members
        with zipfile.ZipFile(io.BytesIO(render_bob_proof_pack())) as archive:
            inventory = json.loads(archive.read('RECORDED_REVIEW_INVENTORY.json'))
            for name, digest in inventory.items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
            self.assertEqual(archive.read('recorded-review.html'), (ROOT/'public/bob-review-example.html').read_bytes())
            packet = archive.read('recorded-comparison.zip')
            self.assertEqual(packet, (ROOT/'evidence/bob_review_walkthrough/comparison.zip').read_bytes())
            with zipfile.ZipFile(io.BytesIO(packet)) as comparison:
                reports = audit_files(members(comparison))
            self.assertEqual((reports[0]['passed'], reports[0]['total']), (108,124))
            self.assertEqual((reports[1]['passed'], reports[1]['total']), (116,116))
            self.assertEqual(reports[1]['plan'], json.loads(archive.read('bob_sessions/warehouse-07a20bdb56f5-candidate.json')))
            window = next(c for c in reports[0]['categories'] if c['id']=='migration_window')
            self.assertEqual(reports[0]['passed']-window['passed'], reports[0]['total']-window['total'])
            self.assertIn(b'not new runs', archive.read('README.md'))

    def test_original_evidence_and_both_fresh_repairs_verify_without_site_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_bob_proof_pack())) as archive:
                inventory = json.loads(archive.read('BOB_EVIDENCE_INVENTORY.json'))
                for name, digest in inventory.items():
                    content = archive.read(name)
                    self.assertEqual(hashlib.sha256(content).hexdigest(), digest)
                    source = (ROOT/name).read_bytes()
                    self.assertEqual(content, source if name.endswith('.png') else source.replace(b'\r\n', b'\n'))
                self.assertIn(b'Attempt 1 blocked', archive.read('bob_sessions/cutover_task01_parcel_warehouse_repair_07a20bdb_history.md'))
                archive.extractall(root)
            for case in ('parcel', 'warehouse'):
                command = [sys.executable, '-S', '-m', 'cutover', '--plan',
                    f'bob_sessions/{case}-07a20bdb56f5-candidate.json', '--bundle', f'{case}.zip']
                command += ['--case', 'parcel'] if case == 'parcel' else ['--contract', 'examples/warehouse/contract.json']
                run = subprocess.run(command, cwd=root, capture_output=True, timeout=120)
                self.assertEqual(run.returncode, 0, run.stderr)
                with zipfile.ZipFile(root/f'{case}.zip') as archive:
                    report = json.loads(archive.read('report.json'))
                    self.assertEqual((report['passed'], report['total']), (116, 116))
                audit = subprocess.run([sys.executable, '-S', '-m', 'cutover.audit_bundle', '--bundle',
                    f'{case}.zip'], cwd=root, capture_output=True, timeout=120)
                self.assertEqual(audit.returncode, 0, audit.stderr)
