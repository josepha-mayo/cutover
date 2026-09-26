"""Replay uploaded packets without trusting their claimed verdict or scripts."""
import hashlib
import io
import json
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server
from cutover.bundle import render_bundle, render_comparison_bundle
from cutover.engine import load_case, load_plan, rehearse


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/ci_browser_action_control'


def repack(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


class PacketImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.http.server_port}/api/audit-bundle'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()

    def upload(self, payload, **headers):
        headers.setdefault('Content-Type', 'application/zip')
        request = urllib.request.Request(self.url, payload, headers)
        try:
            response = urllib.request.urlopen(request, timeout=120)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_real_ci_packets_restore_the_exact_pass_and_lost_write(self):
        for state, counts in [('safe', (124, 124)), ('blocked', (80, 116))]:
            with self.subTest(state=state):
                payload = (EVIDENCE / state / 'review.zip').read_bytes()
                code, result = self.upload(payload)
                self.assertEqual(code, 200, result)
                self.assertEqual(result['audit'], 'verified')
                self.assertEqual(result['archive_sha256'], hashlib.sha256(payload).hexdigest())
                self.assertEqual(len(result['reports']), 1)
                actual = result['reports'][0]
                original = json.loads((EVIDENCE / state / 'report.json').read_text(encoding='utf-8'))
                self.assertEqual((actual['passed'], actual['total']), counts)
                self.assertEqual(actual['plan_hash'], original['plan_hash'])
                self.assertEqual(actual['plan'], original['plan'])
                self.assertEqual(actual['witness'], original['witness'])
                self.assertIn('review_markdown', actual)
                self.assertEqual(result['contract']['project'], 'Dispatch handover')
                if state == 'blocked':
                    self.assertEqual(actual['witness']['failure']['expected']['1'], 'DOCK-07')
                    self.assertEqual(actual['witness']['failure']['actual']['1'], 'A-01')
                    self.assertIn('reproduction_python', actual)

    def test_comparison_restores_both_independently_verified_reports(self):
        before = json.loads((EVIDENCE / 'blocked/report.json').read_text(encoding='utf-8'))
        after = json.loads((EVIDENCE / 'safe/report.json').read_text(encoding='utf-8'))
        with zipfile.ZipFile(EVIDENCE / 'safe/review.zip') as archive:
            contract = json.loads(archive.read('contract.json'))
        code, result = self.upload(render_comparison_bundle(before, after, contract))
        self.assertEqual(code, 200, result)
        self.assertEqual([item['status'] for item in result['reports']], ['blocked', 'pass'])
        self.assertEqual([item['plan_hash'] for item in result['reports']],
                         [before['plan_hash'], after['plan_hash']])

    def test_bundled_case_remains_a_bundled_case(self):
        report = rehearse('parcel', load_plan('parcel', 'late_bridge'))
        code, result = self.upload(render_bundle(report, load_case('parcel')))
        self.assertEqual(code, 200, result)
        self.assertEqual(result['reports'][0]['case'], 'parcel')
        self.assertEqual(result['contract'], load_case('parcel'))

    def test_altered_review_or_script_is_rejected_without_execution(self):
        with zipfile.ZipFile(EVIDENCE / 'blocked/review.zip') as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / 'must-not-exist.txt'
            bad = {
                'review.md': files['review.md'].replace(b'80/116', b'116/116'),
                'witness.py': f'from pathlib import Path\nPath({str(marker)!r}).write_text("executed")\n'.encode(),
            }
            for name, changed in bad.items():
                with self.subTest(file=name):
                    self.assertNotEqual(changed, files[name])
                    code, result = self.upload(repack({**files, name: changed}))
                    self.assertEqual(code, 400, result)
                    self.assertIn('differs from the verified report', result['error'])
                    self.assertNotIn('reports', result)
                    self.assertFalse(marker.exists())

    def test_upload_limits_fail_closed_and_release_the_worker_slot(self):
        packet = (EVIDENCE / 'safe/review.zip').read_bytes()
        for field, expected in [('PACKET_UPLOAD_LIMIT', 413),
                                ('PACKET_MEMBER_LIMIT', 400), ('PACKET_TOTAL_LIMIT', 400)]:
            with self.subTest(limit=field), patch.object(server, field, 32):
                code, result = self.upload(packet)
                self.assertEqual(code, expected, result)
                self.assertNotIn('reports', result)
        self.assertEqual(self.upload(b'not a zip')[0], 400)
        corrupt = bytearray(packet)
        with zipfile.ZipFile(io.BytesIO(packet)) as archive:
            member = next(item for item in archive.infolist()
                          if item.compress_type == zipfile.ZIP_DEFLATED)
        name_size, extra_size = struct.unpack_from('<HH', packet, member.header_offset + 26)
        data_start = member.header_offset + 30 + name_size + extra_size
        # Invalid DEFLATE block type: reject a valid ZIP header with corrupt data.
        corrupt[data_start] = (corrupt[data_start] & ~6) | 6
        self.assertEqual(self.upload(bytes(corrupt))[0], 400)
        self.assertEqual(self.upload(packet)[0], 200)

    def test_packet_upload_preserves_origin_and_content_type_checks(self):
        packet = (EVIDENCE / 'safe/review.zip').read_bytes()
        self.assertEqual(self.upload(packet, Origin='https://unrelated.example')[0], 403)
        self.assertEqual(self.upload(packet, **{'Content-Type': 'application/json'})[0], 415)


if __name__ == '__main__':
    unittest.main()
