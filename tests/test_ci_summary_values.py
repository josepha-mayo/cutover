"""Review summaries preserve row presence and hostile Markdown payloads."""
import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from ci.review_gate import _build_summary, _emit_annotation


class SummaryValueTests(unittest.TestCase):
    def test_annotation_distinguishes_absence_from_null(self):
        for actual, observed in (({}, "ROW NOT RETURNED"), ({"1": None}, "null")):
            report = {"witness": {"id": "reader", "failure": {
                "expected": {"1": "address"}, "actual": actual}}}
            output = StringIO()
            with patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}), redirect_stdout(output):
                _emit_annotation("verified_block", Path("candidate.json"), report, 1, 1)
            self.assertIn("observed " + observed, output.getvalue())

    def summary_value(self, expected, actual):
        report = {"witness": {"id": "reader", "failure": {
            "expected": expected, "actual": actual}}}
        text = _build_summary("verified_block", 1, 1, "", "", "", report)
        body = text.split("~~~json\n", 1)[1].split("\n~~~", 1)[0]
        return json.loads(body), text

    def test_missing_row_is_different_even_when_expected_is_null(self):
        value, _ = self.summary_value({"1": None}, {})
        self.assertFalse(value["reader_returned_row"])
        self.assertNotIn("actual", value)
        self.assertIsNone(value["expected"])

    def test_returned_null_is_explicit(self):
        value, _ = self.summary_value({"1": "address"}, {"1": None})
        self.assertTrue(value["reader_returned_row"])
        self.assertIsNone(value["actual"])

    def test_markdown_and_unicode_are_preserved_in_fenced_json(self):
        payload = "東京 | `value`\n~~~\n# injected heading"
        report = {"witness": {"id": "reader", "failure": {
            "expected": {"1": payload}, "actual": {"1": "old"}}}}
        text = _build_summary("verified_block", 1, 1, "", "", "", report)
        body = text.split("~~~~json\n", 1)[1].split("\n~~~~", 1)[0]
        self.assertEqual(json.loads(body)["expected"], payload)
