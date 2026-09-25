"""Local demo server. No persistence or production database access."""
import argparse
import hashlib
import json
import mimetypes
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from cutover.bundle import render_bundle, render_comparison_bundle
from cutover.engine import load_case, repair_brief
from cutover.reporting import render_markdown, render_reproduction
from cutover.service import WORKER_TIMEOUT_SECONDS, catalog, run_rehearsal, validate_imported_contract

STATIC = Path(__file__).parent / 'public'
VIDEO = STATIC / 'demo.mp4'
WAREHOUSE = Path(__file__).parent / 'examples' / 'warehouse'
BOB_SESSION = Path(__file__).parent / 'bob_sessions'
BOB_REPAIR_ID = '07a20bdb56f5'
SLOTS = threading.BoundedSemaphore(2)


def bob_repair_example():
    """Serve the reviewed event candidate only while its published evidence matches."""
    evidence = json.loads((BOB_SESSION / f'warehouse-{BOB_REPAIR_ID}-evidence.json').read_text(encoding='utf-8'))
    candidate = BOB_SESSION / f'warehouse-{BOB_REPAIR_ID}-candidate.json'
    report = BOB_SESSION / f'warehouse-{BOB_REPAIR_ID}-report.json'
    contract = WAREHOUSE / 'contract.json'
    for path, key in ((candidate, 'candidate_sha256'), (report, 'report_sha256'),
                      (contract, 'contract_sha256')):
        # Git may check out text with CRLF on Windows; the published blobs use LF.
        canonical = path.read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(canonical).hexdigest() != evidence.get(key):
            raise ValueError('Published Bob evidence does not match its recorded hash')
    if (evidence.get('status') != 'pass' or evidence.get('independent_audit_exit') != 0 or
            not isinstance(evidence.get('passed'), int) or evidence['passed'] < 1 or
            evidence['passed'] != evidence.get('total') or
            not str(evidence.get('bob_task_id', '')).startswith(BOB_REPAIR_ID)):
        raise ValueError('Published Bob repair is not independently verified')
    result = json.loads(report.read_text(encoding='utf-8'))
    if (result.get('status'), result.get('passed'), result.get('total')) != (
            'pass', evidence['passed'], evidence['total']):
        raise ValueError('Published Bob report disagrees with the reviewed evidence')
    return {
        'contract': json.loads(contract.read_text(encoding='utf-8')),
        'plan': json.loads(candidate.read_text(encoding='utf-8')),
        'source': 'IBM Bob IDE event repair; independently replayed',
        'task_id': evidence['bob_task_id'],
        'coverage': f"{evidence['passed']}/{evidence['total']}",
    }


class Handler(BaseHTTPRequestHandler):
    def send(self, code, content, content_type='application/json; charset=utf-8', headers=None):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/demo.mp4':
            return self.send_video()
        if path == '/watch' and not VIDEO.is_file():
            return self.send(404, {'error': 'The final presentation has not been published yet'})
        if path == '/api/catalog':
            return self.send(200, catalog())
        if path == '/api/example/warehouse':
            return self.send(200, {
                'contract': json.loads((WAREHOUSE / 'contract.json').read_text(encoding='utf-8')),
                'plan': json.loads((WAREHOUSE / 'late_bridge.json').read_text(encoding='utf-8')),
                'source': 'prewritten warehouse example',
            })
        if path == '/api/example/bob-repair':
            try:
                return self.send(200, bob_repair_example())
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                return self.send(503, {'error': 'Reviewed Bob repair evidence is unavailable'})
        if path == '/api/health':
            return self.send(200, {'ok': True, 'engine': 'SQLite'})
        task_images = {
            '/proof/task-1.png': 'cutover_task01_parcel_warehouse_repair_07a20bdb_summary.png',
            '/proof/task-2.png': 'cutover_task02_ci_review_gate_9aa1e2a2_summary.png',
        }
        if path in task_images:
            image = Path(__file__).parent / 'bob_sessions' / task_images[path]
            return self.send(200, image.read_bytes(), 'image/png')
        files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css',
                 '/watch': 'watch.html', '/watch.css': 'watch.css', '/watch.js': 'watch.js',
                 '/proof': 'proof.html', '/proof.css': 'proof.css'}
        if path not in files:
            return self.send(404, {'error': 'Not found'})
        file = STATIC / files[path]
        self.send(200, file.read_bytes(), mimetypes.guess_type(file)[0] + '; charset=utf-8')

    def do_HEAD(self):
        if urlparse(self.path).path == '/demo.mp4':
            return self.send_video(head_only=True)
        self.send_response(404)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def send_video(self, head_only=False):
        if not VIDEO.is_file():
            return self.send(404, {'error': 'The final presentation has not been published yet'})
        size = VIDEO.stat().st_size
        if size == 0:
            return self.send(404, {'error': 'The final presentation is empty'})
        start, end = 0, size - 1
        requested = self.headers.get('Range')
        if requested:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
            if not match or not any(match.groups()):
                return self.send_video_range_error(size)
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), end) if last else end
            else:
                start = max(0, size - int(last))
            if start > end or start >= size:
                return self.send_video_range_error(size)
        self.send_response(206 if requested else 200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if requested:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if head_only:
            return
        with VIDEO.open('rb') as video:
            video.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = video.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def send_video_range_error(self, size):
        self.send_response(416)
        self.send_header('Content-Range', f'bytes */{size}')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        if self.path not in ('/api/rehearse', '/api/brief', '/api/bundle',
                             '/api/comparison-bundle', '/api/contract/validate'):
            return self.send(404, {'error': 'Not found'})
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self.send(403, {'error': 'Cross-origin requests are not allowed'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send(415, {'error': 'Expected application/json'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            limit = 131072 if self.path == '/api/comparison-bundle' else 65536
            if not 0 < size <= limit:
                return self.send(413, {'error': f'Request must be between 1 byte and {limit // 1024} KiB'})
            if not SLOTS.acquire(blocking=False):
                return self.send(429, {'error': 'Two rehearsals are already running; retry shortly.'})
            try:
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError('Expected a JSON object')
                if self.path == '/api/contract/validate':
                    self.send(200, validate_imported_contract(body['contract']))
                elif self.path == '/api/comparison-bundle':
                    contract = body.get('contract')
                    before = run_rehearsal(body['case'], body['baseline_plan'], contract)
                    after = run_rehearsal(body['case'], body['candidate_plan'], contract)
                    if (before['plan_hash'] != body['baseline_plan_hash'] or
                            after['plan_hash'] != body['candidate_plan_hash'] or
                            before['contract_hash'] != body['contract_hash'] or
                            after['contract_hash'] != body['contract_hash']):
                        raise ValueError('Fresh before/after results differ from the displayed comparison')
                    source_contract = contract if contract is not None else load_case(body['case'])
                    self.send(200, render_comparison_bundle(before, after, source_contract),
                              'application/zip', {
                                  'Content-Disposition': 'attachment; filename="cutover-comparison.zip"',
                                  'X-Cutover-Baseline-SHA256': before['plan_hash'],
                                  'X-Cutover-Candidate-SHA256': after['plan_hash'],
                                  'X-Cutover-Contract-SHA256': before['contract_hash'],
                                  'X-Cutover-Engine-SHA256': before['engine_sha256'],
                                  'X-Cutover-Suite-SHA256': before['suite_hash'],
                                  'X-Cutover-Baseline-Status': before['status'],
                                  'X-Cutover-Candidate-Status': after['status'],
                                  'X-Cutover-Baseline-Coverage': f"{before['passed']}/{before['total']}",
                                  'X-Cutover-Candidate-Coverage': f"{after['passed']}/{after['total']}",
                              })
                else:
                    contract = body.get('contract')
                    if self.path == '/api/brief' and contract is not None:
                        raise ValueError('Bob MCP repair briefs currently support bundled sample projects only')
                    report = run_rehearsal(body['case'], body['plan'], contract)
                    if self.path == '/api/brief':
                        self.send(200, repair_brief(report))
                    elif self.path == '/api/bundle':
                        source_contract = contract if contract is not None else load_case(body['case'])
                        self.send(200, render_bundle(report, source_contract), 'application/zip', {
                            'Content-Disposition': f'attachment; filename="cutover-review-{report["plan_hash"][:10]}.zip"',
                            'X-Cutover-Plan-SHA256': report['plan_hash'],
                            'X-Cutover-Contract-SHA256': report['contract_hash'],
                            'X-Cutover-Status': report['status'],
                            'X-Cutover-Coverage': f'{report["passed"]}/{report["total"]}',
                        })
                    else:
                        report['review_markdown'] = render_markdown(report)
                        if report['witness'] and report['witness']['failure']['kind'] in ('data_mismatch', 'target_mismatch'):
                            report['reproduction_python'] = render_reproduction(
                                report, contract if contract is not None else load_case(body['case']))
                        self.send(200, report)
            finally:
                SLOTS.release()
        except subprocess.TimeoutExpired:
            self.send(422, {'error': f'Rehearsal exceeded its {WORKER_TIMEOUT_SECONDS} second budget. No passing result was produced.'})
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
