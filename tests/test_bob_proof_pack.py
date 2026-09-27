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
