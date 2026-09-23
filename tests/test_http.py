import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from server import Handler
from cutover.engine import load_case, load_plan

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

    def request(self, path, data=None, **headers):
        if data is not None:
            data = json.dumps(data).encode()
            headers.setdefault('Content-Type', 'application/json')
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as response:
            with response:
                return response.code, response.read()

    def test_execute_edited_candidate_via_http(self):
        plan = load_plan('parcel', 'bridge')
        plan['migration'] += '\nDROP TRIGGER sync_new_update;'
        code, data = self.request('/api/rehearse', {'case': 'parcel', 'plan': plan})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(data)['status'], 'blocked')

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

    def test_private_files_not_served(self):
        for path in ('/../server.py', '/.bob/mcp.json', '/examples/parcel/bridge.json'):
            self.assertEqual(self.request(path)[0], 404)

    def test_invalid_input_fails_without_result(self):
        code, body = self.request('/api/rehearse', {'case': '../../', 'plan': {}})
        self.assertEqual(code, 400)
        self.assertNotIn('passed', json.loads(body))

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

        code, body = self.request('/api/rehearse', {'case': 'custom', 'contract': contract, 'plan': repaired})
        passing = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual((passing['status'], passing['passed'], passing['total']), ('pass', 124, 124))
        self.assertIn(passing['plan_hash'], passing['review_markdown'])

        repaired['migration'] += '\nDROP TRIGGER sync_new_update;'
        code, body = self.request('/api/rehearse', {'case': 'custom', 'contract': contract, 'plan': repaired})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)['status'], 'blocked')

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
