"""Local demo server. No persistence or production database access."""
import argparse
import json
import mimetypes
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from cutover.engine import repair_brief
from cutover.reporting import render_markdown
from cutover.service import catalog, run_rehearsal, validate_imported_contract

STATIC = Path(__file__).parent / 'public'
SLOTS = threading.BoundedSemaphore(2)


class Handler(BaseHTTPRequestHandler):
    def send(self, code, content, content_type='application/json; charset=utf-8'):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/catalog':
            return self.send(200, catalog())
        if path == '/api/health':
            return self.send(200, {'ok': True, 'engine': 'SQLite', 'bob_session_verified': False})
        files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}
        if path not in files:
            return self.send(404, {'error': 'Not found'})
        file = STATIC / files[path]
        self.send(200, file.read_bytes(), mimetypes.guess_type(file)[0] + '; charset=utf-8')

    def do_POST(self):
        if self.path not in ('/api/rehearse', '/api/brief', '/api/contract/validate'):
            return self.send(404, {'error': 'Not found'})
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self.send(403, {'error': 'Cross-origin requests are not allowed'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send(415, {'error': 'Expected application/json'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 65536:
                return self.send(413, {'error': 'Request must be between 1 byte and 64 KiB'})
            if not SLOTS.acquire(blocking=False):
                return self.send(429, {'error': 'Two rehearsals are already running; retry shortly.'})
            try:
                body = json.loads(self.rfile.read(size))
                if self.path == '/api/contract/validate':
                    self.send(200, validate_imported_contract(body['contract']))
                else:
                    contract = body.get('contract')
                    if self.path == '/api/brief' and contract is not None:
                        raise ValueError('Bob MCP repair briefs currently support bundled sample projects only')
                    report = run_rehearsal(body['case'], body['plan'], contract)
                    if self.path == '/api/brief':
                        self.send(200, repair_brief(report))
                    else:
                        report['review_markdown'] = render_markdown(report)
                        self.send(200, report)
            finally:
                SLOTS.release()
        except subprocess.TimeoutExpired:
            self.send(422, {'error': 'Rehearsal exceeded its 8 second budget. No passing result was produced.'})
        except (ValueError, KeyError, TypeError) as exc:
            self.send(400, {'error': str(exc)})

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args()
    print(f'Cutover: http://{args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
