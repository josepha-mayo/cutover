"""Verify offline reviews retain audited evidence and cannot turn SQL values into markup."""
import base64
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

from cutover.bundle import render_comparison_bundle
from cutover.engine import rehearse
from cutover.review_html import render_review, SCRIPT, STYLE

ROOT = Path(__file__).resolve().parents[1]


class OfflineReviewTests(unittest.TestCase):
    def test_git_provenance_is_visible_but_cannot_inject_markup(self):
        page = render_review(self.reports, {'commit': 'abc123', 'path': '<img src=x>.sql', 'blob': 'def456'})
        self.assertIn('abc123', page)
        self.assertIn('def456', page)
        self.assertIn('&lt;img src=x&gt;.sql', page)
        self.assertNotIn('<img src=x>', page)
        self.assertIn('Only baseline migration SQL', page)

    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT/'examples/warehouse/contract.json').read_text(encoding='utf-8'))
        cls.payload = '</script><img src="https://example.invalid/leak" onerror="alert(1)">'
        cls.contract['payloads'][0] = cls.payload
        unsafe = json.loads((ROOT/'examples/warehouse/late_bridge.json').read_text(encoding='utf-8'))
        safe = json.loads((ROOT/'examples/warehouse/bridge.json').read_text(encoding='utf-8'))
        cls.reports = (rehearse('custom', unsafe, cls.contract), rehearse('custom', safe, cls.contract))

    def test_data_is_inert_and_round_trips_without_losing_the_recorded_values(self):
        content = render_review(self.reports)
        payload = re.search(r'<script id="recorded-data" type="application/json">(.*?)</script>', content, re.S)[1]
        self.assertEqual(json.loads(payload), json.loads(json.dumps(self.reports)))
        self.assertNotIn(self.payload, content)
        class Tags(HTMLParser):
            def __init__(self):
                super().__init__(); self.tags=[]
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
        tags = Tags(); tags.feed(content)
        self.assertEqual(tags.tags.count('script'), 2)
        self.assertNotIn('img', tags.tags)
        for kind, source in [('script', SCRIPT), ('style', STYLE)]:
            digest = base64.b64encode(hashlib.sha256(source.encode()).digest()).decode()
            self.assertIn(f"{kind}-src 'sha256-{digest}'", content)
        self.assertIn("default-src 'none'", content)

    def test_cli_generates_after_audit_and_refuses_tampered_or_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet=root/'comparison.zip'; packet.write_bytes(render_comparison_bundle(*self.reports,self.contract))
            output=root/'review.html'
            def run(bundle, html):
                return subprocess.run([sys.executable,'-S','-m','cutover.audit_bundle','--bundle',str(bundle),
                                       '--html',str(html)],cwd=ROOT,capture_output=True,timeout=120)
            audited = run(packet, output)
            self.assertEqual(audited.returncode, 1, audited.stderr)  # verified blocked baseline
            self.assertEqual(output.read_text(encoding='utf-8'), render_review(self.reports))
            old = output.read_bytes()
            self.assertEqual(run(packet, output).returncode, 2)
            self.assertEqual(output.read_bytes(), old)
            bad=root/'altered.zip'
            with zipfile.ZipFile(packet) as source, zipfile.ZipFile(bad,'w') as destination:
                for name in source.namelist():
                    raw=source.read(name)
                    destination.writestr(name, raw+b'changed' if name=='baseline/review.md' else raw)
            refused=root/'unverified.html'
            self.assertEqual(run(bad, refused).returncode, 2)
            self.assertFalse(refused.exists())
