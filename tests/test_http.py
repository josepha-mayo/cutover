import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
import server
from server import Handler
from cutover.engine import load_case, load_plan
from cutover.service import verify_report_against_replay

WAREHOUSE = Path(__file__).resolve().parents[1] / 'examples' / 'warehouse'


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, data=None, timeout=15, **headers):
        if data is not None:
            data = json.dumps(data).encode()
            headers.setdefault('Content-Type', 'application/json')
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as response:
            with response:
                return response.code, response.read()

    def test_scenario_builder_module_is_served(self):
        code, body = self.request('/scenario.js')
        self.assertEqual(code, 200)
        self.assertIn(b'export function buildScenario', body)

    def test_fragility_challenge_replays_each_removed_statement(self):
        from cutover.service import run_rehearsal
        plan = load_plan('parcel', 'bridge')
        original = run_rehearsal('parcel', plan)
        request = {'case': 'parcel', 'plan': plan,
                   'plan_hash': original['plan_hash'],
                   'contract_hash': original['contract_hash']}
        code, body = self.request('/api/fragility', request, timeout=90)
        self.assertEqual(code, 200)
        result = json.loads(body)
        self.assertEqual(result['original'], {'passed': 124, 'total': 124})
        self.assertEqual(len(result['challenges']), 5)
        self.assertTrue(all(item['outcome'] == 'blocked' and item['witness']['failure']
                            for item in result['challenges']))
        opened = result['challenges'][1]
        full_replay = run_rehearsal('parcel', opened['plan'])
        self.assertEqual((full_replay['plan_hash'], full_replay['passed'], full_replay['total']),
                         (opened['plan_hash'], opened['passed'], opened['total']))
        self.assertEqual(full_replay['witness']['id'], opened['witness']['id'])
        self.assertEqual(self.request('/api/fragility', {
            **request, 'plan_hash': '0' * 64}, timeout=90)[0], 400)
        blocked = load_plan('parcel', 'late_bridge')
        blocked_report = run_rehearsal('parcel', blocked)
        self.assertEqual(self.request('/api/fragility', {
            **request, 'plan': blocked, 'plan_hash': blocked_report['plan_hash']},
            timeout=90)[0], 400)

    def test_ci_kit_binds_a_passing_custom_plan_to_gate_inputs(self):
        contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
        plan = json.loads((WAREHOUSE / 'bridge.json').read_text(encoding='utf-8'))
        from cutover.service import run_rehearsal
        report = run_rehearsal('custom', plan, contract)
        blocked_plan = json.loads((WAREHOUSE / 'late_bridge.json').read_text(encoding='utf-8'))
        blocked = run_rehearsal('custom', blocked_plan, contract)
        self.assertEqual(blocked['status'], 'blocked')
        request = {'case': 'custom', 'plan': plan, 'contract': contract,
                   'plan_hash': report['plan_hash'],
                   'contract_hash': report['contract_hash'],
                   'baseline_plan': blocked_plan,
                   'baseline_plan_hash': blocked['plan_hash']}
        code, body = self.request('/api/ci-kit', request, timeout=90)
        self.assertEqual(code, 200)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            entry = json.loads(archive.read('manifest-entry.json'))
            self.assertEqual(entry['slug'], 'release-warehouse-bin-relocation')
            self.assertEqual(json.loads(archive.read(entry['contract'])), contract)
            self.assertEqual(json.loads(archive.read(entry['plan'])), plan)
            retained = json.loads(archive.read('evidence/report.json'))
            self.assertEqual((retained['status'], retained['passed'], retained['total']),
                             ('pass', 124, 124))
            verify_report_against_replay('custom', plan, retained, contract)
            unsafe_name = 'ci/release-warehouse-bin-relocation-unsafe-control.json'
            self.assertEqual(json.loads(archive.read(unsafe_name)), blocked_plan)
            unsafe_report = json.loads(archive.read('evidence/unsafe-control-report.json'))
            self.assertEqual(unsafe_report['status'], 'blocked')
            verify_report_against_replay('custom', blocked_plan, unsafe_report, contract)
            self.assertIn(b'Prove this gate can go red', archive.read('README.md'))
            witness = archive.read('evidence/unsafe-control-witness.py')
            self.assertIn(b'def reproduce()', witness)
            with tempfile.TemporaryDirectory() as directory:
                from ci.discover_cases import discover
                root = Path(directory)
                for name in (entry['contract'], entry['plan']):
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
                (root / 'ci/cases.json').write_text(json.dumps([entry]), encoding='utf-8')
                self.assertEqual(discover(root)['include'], [entry])
            workflow_name = f'.github/workflows/cutover-{entry["slug"]}.yml'
            workflow = archive.read(workflow_name).decode('utf-8')
            inputs = dict(re.findall(r'^          ([a-z-]+): (.+)$', workflow, re.M))
            self.assertIn('on: pull_request\n', workflow)
            self.assertIn('uses: josepha-mayo/cutover@a5bf69f6e8f94788eade58691d292941e009f8ac', workflow)
            self.assertNotIn('migration', json.loads(archive.read(inputs['plan'])))
            with tempfile.TemporaryDirectory(prefix='cutover-downloaded-consumer-') as directory:
                root = Path(directory)
                for name in (workflow_name, inputs['contract'], inputs['plan'], inputs['migration-file']):
                    destination = root / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(name))
                env = {**os.environ, 'GITHUB_WORKSPACE': str(root),
                       'CUTOVER_CONTRACT': inputs['contract'], 'CUTOVER_PLAN': inputs['plan'],
                       'CUTOVER_MIGRATION_FILE': inputs['migration-file'],
                       'CUTOVER_OUTPUT_DIR': inputs['output-dir'], 'PYTHONIOENCODING': 'utf-8'}
                result = subprocess.run([sys.executable, str(WAREHOUSE.parents[1] / 'ci/action_entry.py')],
                                        cwd=root, env=env, capture_output=True, text=True,
                                        encoding='utf-8', timeout=300)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                evidence = root / inputs['output-dir']
                from cutover.audit_bundle import audit
                replayed = audit(evidence / 'review.zip')[0]
                self.assertEqual((replayed['plan_hash'], replayed['contract_hash']),
                                 (report['plan_hash'], report['contract_hash']))
                self.assertEqual((replayed['passed'], replayed['total']), (124, 124))
                self.assertFalse((root / 'cutover').exists())
                self.assertFalse((root / 'ci/cases.json').exists())
        altered = {**request, 'plan_hash': '0' * 64}
        self.assertEqual(self.request('/api/ci-kit', altered)[0], 400)
        altered_control = {**request, 'baseline_plan_hash': '0' * 64}
        self.assertEqual(self.request('/api/ci-kit', altered_control, timeout=90)[0], 400)
        self.assertEqual(self.request('/api/ci-kit', {
            **request, 'plan': blocked_plan, 'plan_hash': blocked['plan_hash']}, timeout=90)[0], 400)

    def test_watch_chapter_script_is_served(self):
        code, body = self.request('/watch')
        self.assertEqual(code, 200)
        self.assertIn(b'/watch.js', body)
        self.assertIn(b'/captions.en.vtt', body)
        code, body = self.request('/watch.js')
        self.assertEqual(code, 200)
        self.assertIn(b'currentTime', body)
        with urllib.request.urlopen(self.base + '/captions.en.vtt', timeout=15) as response:
            self.assertEqual(response.headers.get_content_type(), 'text/vtt')
            self.assertTrue(response.read().replace(b'\r\n', b'\n').startswith(b'WEBVTT\n'))

    def test_execute_edited_candidate_via_http(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] += '\nDROP TRIGGER sync_new_update;'
        code, data = self.request('/api/rehearse', {'case': 'parcel', 'plan': plan})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data)['status'], 'blocked')

    def test_published_bob_repair_runs_as_a_fresh_warehouse_rehearsal(self):
        code, body = self.request('/api/example/bob-repair')
        self.assertEqual(code, 200)
        example = json.loads(body)
        self.assertEqual(example['task_id'], '07a20bdb56f595035652c2e6732b2c53')
        self.assertEqual(example['coverage'], '116/116')
        code, body = self.request('/api/rehearse', {
            'case': 'custom', 'contract': example['contract'], 'plan': example['plan']})
        self.assertEqual(code, 200)
        report = json.loads(body)
        self.assertEqual((report['status'], report['passed'], report['total']),
                         ('pass', 116, 116))

    def test_noop_old_adapter_is_blocked_through_public_api(self):
        plan = {'name': 'No migration', 'migration': 'SELECT 1;', **load_case('parcel')['old']}
        code, data = self.request('/api/rehearse', {'case': 'parcel', 'plan': plan})
        report = json.loads(data)
        self.assertEqual(code, 200)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['baseline']['passed'], 0)

    def test_hostile_origin_rejected(self):
        code, _ = self.request('/api/rehearse', {'case': 'parcel', 'plan': load_plan()}, Origin='https://unrelated.example')
        self.assertEqual(code, 403)
        code, _ = self.request('/api/bundle', {'case': 'parcel', 'plan': load_plan()}, Origin='https://unrelated.example')
        self.assertEqual(code, 403)

    def test_review_packet_reexecutes_and_retains_auditable_blocked_witness(self):
        contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
        plan = json.loads((WAREHOUSE / 'late_bridge.json').read_text(encoding='utf-8'))
        payload = json.dumps({'case': 'custom', 'contract': contract, 'plan': plan,
                              'report': {'status': 'pass', 'passed': 124}}).encode()
        req = urllib.request.Request(self.base + '/api/bundle', data=payload,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers['Content-Type'], 'application/zip')
            self.assertIn('attachment; filename="cutover-review-', response.headers['Content-Disposition'])
            packet = response.read()
            with zipfile.ZipFile(io.BytesIO(packet)) as archive:
                self.assertEqual(set(archive.namelist()), {
                    'README.md', 'contract.json', 'plan.json', 'report.json', 'review.md', 'witness.py'})
                saved = json.loads(archive.read('report.json'))
                self.assertEqual(json.loads(archive.read('contract.json')), contract)
                self.assertEqual(json.loads(archive.read('plan.json')), plan)
                self.assertEqual((saved['status'], saved['passed'], saved['total']), ('blocked', 108, 124))
                self.assertEqual(response.headers['X-Cutover-Plan-SHA256'], saved['plan_hash'])
                self.assertEqual(response.headers['X-Cutover-Contract-SHA256'], saved['contract_hash'])
                self.assertEqual(response.headers['X-Cutover-Status'], 'blocked')
                self.assertEqual(response.headers['X-Cutover-Coverage'], '108/124')
                verify_report_against_replay('custom', plan, saved, contract)

    def test_review_packet_rejects_invalid_candidate_without_zip(self):
        code, body = self.request('/api/bundle', {'case': '../../', 'plan': {}})
        self.assertEqual(code, 400)
        self.assertIn('error', json.loads(body))

    def test_comparison_packet_reexecutes_both_and_keeps_independent_audits(self):
        baseline = load_plan('parcel', 'late_bridge')
        candidate = load_plan('parcel', 'bridge')
        old = json.loads(self.request('/api/rehearse', {'case': 'parcel', 'plan': baseline})[1])
        new = json.loads(self.request('/api/rehearse', {'case': 'parcel', 'plan': candidate})[1])
        request = {'case': 'parcel', 'baseline_plan': baseline, 'candidate_plan': candidate,
                   'baseline_plan_hash': old['plan_hash'],
                   'candidate_plan_hash': new['plan_hash'],
                   'contract_hash': old['contract_hash']}
        payload = json.dumps(request).encode()
        http = urllib.request.Request(self.base + '/api/comparison-bundle', data=payload,
                                      headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(http, timeout=30) as response:
            self.assertEqual(response.headers['Content-Type'], 'application/zip')
            self.assertEqual(response.headers['X-Cutover-Baseline-SHA256'], old['plan_hash'])
            self.assertEqual(response.headers['X-Cutover-Candidate-SHA256'], new['plan_hash'])
            self.assertEqual(response.headers['X-Cutover-Baseline-Coverage'], '108/124')
            self.assertEqual(response.headers['X-Cutover-Candidate-Coverage'], '124/124')
            with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                summary = json.loads(archive.read('comparison.json'))
                self.assertEqual(summary['paired_probes'], 76)
                self.assertFalse(summary['window_probes_paired'])
                self.assertEqual(summary['resolved_probe_ids'], [])
                self.assertEqual(summary['regressed_probe_ids'], [])
                self.assertEqual(summary['migration_window_failures'], {
                    'baseline': {'failed': 16, 'total': 48},
                    'candidate': {'failed': 0, 'total': 48}})
                self.assertTrue(summary['first_failed_window_probe']['baseline'].startswith('window_'))
                self.assertIsNone(summary['first_failed_window_probe']['candidate'])
                for label, plan, status in (('baseline', baseline, 'blocked'),
                                            ('candidate', candidate, 'pass')):
                    saved = json.loads(archive.read(f'{label}/report.json'))
                    self.assertEqual(saved['status'], status)
                    self.assertEqual(json.loads(archive.read(f'{label}/plan.json')), plan)
                    verify_report_against_replay('parcel', plan, saved)
        request['candidate_plan_hash'] = '0' * 64
        code, body = self.request('/api/comparison-bundle', request)
        self.assertEqual(code, 400)
        self.assertIn('differ', json.loads(body)['error'])

    def test_comparison_packet_supports_an_imported_contract(self):
        contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
        baseline = json.loads((WAREHOUSE / 'late_bridge.json').read_text(encoding='utf-8'))
        candidate = json.loads((WAREHOUSE / 'bridge.json').read_text(encoding='utf-8'))
        old = json.loads(self.request('/api/rehearse', {
            'case': 'custom', 'contract': contract, 'plan': baseline})[1])
        new = json.loads(self.request('/api/rehearse', {
            'case': 'custom', 'contract': contract, 'plan': candidate})[1])
        request = {'case': 'custom', 'contract': contract,
                   'baseline_plan': baseline, 'candidate_plan': candidate,
                   'baseline_plan_hash': old['plan_hash'],
                   'candidate_plan_hash': new['plan_hash'],
                   'contract_hash': old['contract_hash']}
        code, body = self.request('/api/comparison-bundle', request)
        self.assertEqual(code, 200)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertEqual(json.loads(archive.read('baseline/contract.json')), contract)
            self.assertEqual(json.loads(archive.read('candidate/contract.json')), contract)
            for label, plan in (('baseline', baseline), ('candidate', candidate)):
                saved = json.loads(archive.read(f'{label}/report.json'))
                verify_report_against_replay('custom', plan, saved, contract)

    def test_comparison_packet_names_newly_failing_paired_probes(self):
        baseline = load_plan('parcel', 'bridge')
        candidate = dict(baseline)
        candidate['name'] = 'Wrong target reader'
        candidate['read'] = baseline['read'].replace('shipping_address AS', "shipping_address || '-wrong' AS")
        old = json.loads(self.request('/api/rehearse', {'case': 'parcel', 'plan': baseline})[1])
        new = json.loads(self.request('/api/rehearse', {'case': 'parcel', 'plan': candidate})[1])
        self.assertEqual(old['status'], 'pass')
        self.assertEqual(new['status'], 'blocked')
        code, body = self.request('/api/comparison-bundle', {
            'case': 'parcel', 'baseline_plan': baseline, 'candidate_plan': candidate,
            'baseline_plan_hash': old['plan_hash'], 'candidate_plan_hash': new['plan_hash'],
            'contract_hash': old['contract_hash']})
        self.assertEqual(code, 200)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            summary = json.loads(archive.read('comparison.json'))
            self.assertTrue(summary['window_probes_paired'])
            self.assertGreater(summary['regressed_in_paired_probes'], 0)
            self.assertEqual(len(summary['regressed_probe_ids']), summary['regressed_in_paired_probes'])
            by_id = {item['id']: item for item in new['results']}
            self.assertTrue(all(not by_id[probe_id]['passed'] for probe_id in summary['regressed_probe_ids']))
            self.assertTrue(any(by_id[probe_id]['category'] == 'migration_window'
                                for probe_id in summary['regressed_probe_ids']))
            self.assertIn(summary['first_failed_window_probe']['candidate'], summary['regressed_probe_ids'])

    def test_private_files_not_served(self):
        for path in ('/../server.py', '/.bob/mcp.json', '/examples/parcel/bridge.json'):
            self.assertEqual(self.request(path)[0], 404)

    def test_public_video_page_waits_for_final_file_and_supports_seek(self):
        with tempfile.TemporaryDirectory() as temporary:
            video = Path(temporary) / 'demo.mp4'
            with mock.patch.object(server, 'VIDEO', video):
                self.assertEqual(self.request('/watch')[0], 404)
                self.assertEqual(self.request('/demo.mp4')[0], 404)
                video.write_bytes(b'0123456789abcdef')
                code, page = self.request('/watch')
                self.assertEqual(code, 200)
                self.assertIn(b'<video controls', page)
                req = urllib.request.Request(self.base + '/demo.mp4', headers={'Range': 'bytes=4-8'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    self.assertEqual((response.status, response.read()), (206, b'45678'))
                    self.assertEqual(response.headers['Content-Range'], 'bytes 4-8/16')
                    self.assertEqual(response.headers['Accept-Ranges'], 'bytes')
                self.assertEqual(self.request('/demo.mp4', Range='bytes=16-')[0], 416)
                req = urllib.request.Request(self.base + '/demo.mp4', method='HEAD')
                with urllib.request.urlopen(req, timeout=15) as response:
                    self.assertEqual(response.headers['Content-Length'], '16')
                    self.assertEqual(response.read(), b'')

    def test_invalid_input_fails_without_result(self):
        code, body = self.request('/api/rehearse', {'case': '../../', 'plan': {}})
        self.assertEqual(code, 400)
        self.assertNotIn('passed', json.loads(body))

    def test_non_object_json_returns_client_error(self):
        for endpoint in ('/api/rehearse', '/api/brief', '/api/contract/validate'):
            for payload in ([], 42):
                with self.subTest(endpoint=endpoint, payload=payload):
                    code, body = self.request(endpoint, payload)
                    self.assertEqual(code, 400)
                    self.assertEqual(json.loads(body), {'error': 'Expected a JSON object'})

    def test_imported_contract_blocks_late_bridge_and_exports_matching_review(self):
        contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
        late = json.loads((WAREHOUSE / 'late_bridge.json').read_text(encoding='utf-8'))
        repaired = json.loads((WAREHOUSE / 'bridge.json').read_text(encoding='utf-8'))

        code, body = self.request('/api/contract/validate', {'contract': contract})
        validated = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(validated['status'], 'valid')
        self.assertEqual(validated['seed_count'], 3)
        self.assertEqual(validated['payload_count'], 4)

        code, body = self.request('/api/rehearse', {'case': 'custom', 'contract': contract, 'plan': late})
        blocked = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual((blocked['status'], blocked['passed'], blocked['total']), ('blocked', 108, 124))
        self.assertEqual(blocked['contract_hash'], validated['contract_hash'])
        self.assertIn('R-07', json.dumps(blocked['witness']))
        self.assertIn('A-01', json.dumps(blocked['witness']))
        self.assertIn(blocked['plan_hash'], blocked['review_markdown'])
        self.assertIn('reproduction_python', blocked)
        with tempfile.TemporaryDirectory() as temporary:
            replay = Path(temporary) / 'replay.py'
            replay.write_text(blocked['reproduction_python'], encoding='utf-8')
            reproduced = subprocess.run([sys.executable, '-I', str(replay)], cwd=temporary,
                                        capture_output=True, text=True, encoding='utf-8', timeout=15)
            self.assertEqual(reproduced.returncode, 0, reproduced.stderr)
            self.assertEqual(json.loads(reproduced.stdout)['probe'], blocked['witness']['id'])

        code, body = self.request('/api/rehearse', {'case': 'custom', 'contract': contract, 'plan': repaired})
        passing = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual((passing['status'], passing['passed'], passing['total']), ('pass', 124, 124))
        self.assertIn(passing['plan_hash'], passing['review_markdown'])
        self.assertNotIn('reproduction_python', passing)

        repaired['migration'] += '\nDROP TRIGGER sync_new_update;'
        code, body = self.request('/api/rehearse', {'case': 'custom', 'contract': contract, 'plan': repaired})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['status'], 'blocked')

    def test_warehouse_walkthrough_loads_real_fixture_and_unsafe_plan(self):
        code, body = self.request('/api/example/warehouse')
        example = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(example['contract'], json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8')))
        self.assertEqual(example['plan'], json.loads((WAREHOUSE / 'late_bridge.json').read_text(encoding='utf-8')))
        self.assertEqual(example['source'], 'prewritten warehouse example')

    def test_cross_record_control_is_available_and_exposes_its_write_path(self):
        code, body = self.request('/api/catalog')
        self.assertEqual(code, 200)
        for case in json.loads(body)['cases']:
            with self.subTest(case=case['id']):
                plan = case['plans']['cross_record']
                self.assertEqual(plan, load_plan(case['id'], 'cross_record'))
                code, body = self.request('/api/rehearse', {'case': case['id'], 'plan': plan})
                self.assertEqual(code, 200)
                result = json.loads(body)
                self.assertEqual((result['status'], result['baseline']['passed']), ('blocked', 8))
                self.assertEqual((result['passed'], result['total']), (100, 132))
                self.assertEqual(result['witness']['write_targets'], [101, 102])
                self.assertEqual(result['witness']['failure']['kind'], 'data_mismatch')
                self.assertEqual(next(row for row in result['categories']
                                      if row['id'] == 'migration_window')['passed'], 56)

    def test_import_validation_rejects_broken_old_contract_and_no_green_result(self):
        contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
        plan = json.loads((WAREHOUSE / 'bridge.json').read_text(encoding='utf-8'))
        contract['old']['read'] = 'SELECT id, pick_bin FROM stock_items ORDER BY id'
        for endpoint, request in (
            ('/api/contract/validate', {'contract': contract}),
            ('/api/rehearse', {'case': 'custom', 'contract': contract, 'plan': plan}),
        ):
            code, body = self.request(endpoint, request)
            response = json.loads(body)
            self.assertEqual(code, 400)
            self.assertIn('id and value', response['error'])
            self.assertNotIn('passed', response)

    def test_import_validation_rejects_later_payload_before_a_verdict(self):
        contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
        contract['payloads'][1] = 'LONG-BIN'
        contract['schema'] = ('CREATE TABLE stock_items (id INTEGER PRIMARY KEY, '
                              'pick_bin TEXT NOT NULL CHECK(length(pick_bin) <= 4));')
        plan = json.loads((WAREHOUSE / 'bridge.json').read_text(encoding='utf-8'))
        for endpoint, request in (
            ('/api/contract/validate', {'contract': contract}),
            ('/api/rehearse', {'case': 'custom', 'contract': contract, 'plan': plan}),
        ):
            with self.subTest(endpoint=endpoint):
                code, body = self.request(endpoint, request)
                response = json.loads(body)
                self.assertEqual(code, 400)
                self.assertIn('payload index 1', response['error'])
                self.assertNotIn('passed', response)

    def test_imported_contract_cannot_replace_bundled_case_or_bob_brief(self):
        contract = json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8'))
        plan = json.loads((WAREHOUSE / 'bridge.json').read_text(encoding='utf-8'))
        for endpoint, request in (
            ('/api/rehearse', {'case': 'parcel', 'contract': contract, 'plan': plan}),
            ('/api/brief', {'case': 'custom', 'contract': contract, 'plan': plan}),
        ):
            code, body = self.request(endpoint, request)
            self.assertEqual(code, 400)
            self.assertNotIn('passed', json.loads(body))


if __name__ == '__main__':
    unittest.main()
