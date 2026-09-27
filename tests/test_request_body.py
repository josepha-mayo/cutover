"""Interrupted and slowly streamed uploads must not retain rehearsal slots."""
import http.client
import json
import socket
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import server


class UploadBodyTests(unittest.TestCase):
    def setUp(self):
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.sockets = []

    def tearDown(self):
        for connection in self.sockets:
            connection.close()
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()

    def partial(self, path, content_type):
        connection = socket.create_connection(self.http.server_address, timeout=5)
        self.sockets.append(connection)
        connection.sendall((f'POST {path} HTTP/1.0\r\nHost: 127.0.0.1:{self.http.server_port}\r\n'
                            f'Content-Type: {content_type}\r\nContent-Length: 100\r\n\r\n').encode() + b'{')
        return connection

    def response(self, connection):
        response = http.client.HTTPResponse(connection)
        response.begin()
        body = response.read()
        return response.status, json.loads(body)

    def test_incomplete_json_and_zip_time_out_without_execution_then_slots_recover(self):
        slots = threading.BoundedSemaphore(2)
        with patch.object(server, 'REQUEST_BODY_TIMEOUT_SECONDS', 0.4), patch.object(server, 'SLOTS', slots), \
                patch.object(server, 'run_rehearsal') as rehearse, \
                patch.object(server, 'audit_upload_bytes') as audit, \
                patch.object(server, 'validate_imported_contract', return_value={'status': 'valid'}):
            connections = [self.partial('/api/rehearse', 'application/json'),
                           self.partial('/api/audit-bundle', 'application/zip')]
            for connection in connections:
                status, body = self.response(connection)
                self.assertEqual(status, 408)
                self.assertIn('No SQL or packet replay was started', body['error'])
            for connection in connections:
                self.assertEqual(connection.recv(1), b'')
            rehearse.assert_not_called()
            audit.assert_not_called()
            self.assertTrue(slots.acquire(blocking=False))
            self.assertTrue(slots.acquire(blocking=False))
            self.assertFalse(slots.acquire(blocking=False))
            slots.release()
            slots.release()
            healthy = http.client.HTTPConnection(*self.http.server_address, timeout=5)
            try:
                healthy.request('POST', '/api/contract/validate', body=b'{"contract":{}}',
                                headers={'Content-Type': 'application/json'})
                response = healthy.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {'status': 'valid'})
            finally:
                healthy.close()

    def test_tiny_chunks_do_not_extend_the_total_upload_deadline(self):
        stopped = threading.Event()
        with patch.object(server, 'REQUEST_BODY_TIMEOUT_SECONDS', 0.35), \
                patch.object(server, 'run_rehearsal') as rehearse:
            connection = self.partial('/api/rehearse', 'application/json')
            def drip():
                while not stopped.wait(0.05):
                    try:
                        connection.sendall(b' ')
                    except OSError:
                        break
            sender = threading.Thread(target=drip, daemon=True)
            started = time.monotonic()
            sender.start()
            try:
                status, body = self.response(connection)
                self.assertEqual(status, 408)
                self.assertLess(time.monotonic() - started, 2)
                self.assertIn('retry explicitly', body['error'])
                rehearse.assert_not_called()
            finally:
                stopped.set()
                sender.join(2)

    def test_early_body_eof_is_rejected_without_execution(self):
        with patch.object(server, 'run_rehearsal') as rehearse:
            connection = self.partial('/api/rehearse', 'application/json')
            connection.shutdown(socket.SHUT_WR)
            status, body = self.response(connection)
            self.assertEqual(status, 400)
            self.assertIn('before its declared Content-Length', body['error'])
            rehearse.assert_not_called()
