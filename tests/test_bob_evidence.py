"""The public Bob evidence summary must never copy task content."""

import json
import tempfile
import unittest
from pathlib import Path

from bob_sessions.summarize_shell import summarize


class BobEvidenceTests(unittest.TestCase):
    def test_metadata_preserves_failures_without_private_content(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "task.ndjson"
            events = [
                {"type": "message", "timestamp": "2026-09-25T15:01:00Z", "role": "user", "content": "SECRET_PROMPT"},
                {"type": "tool_use", "timestamp": "2026-09-25T15:01:01Z", "tool_name": "mcp__cutover__rehearse_candidate", "tool_id": "x1", "parameters": {"token": "SECRET_KEY"}},
                {"type": "tool_result", "timestamp": "2026-09-25T15:01:02Z", "tool_id": "x1", "status": "error", "output": "SECRET_OUTPUT"},
                {"type": "tool_use", "timestamp": "2026-09-25T15:01:03Z", "tool_name": "mcp__cutover__rehearse_candidate", "tool_id": "x2", "parameters": {}},
                {"type": "result", "timestamp": "2026-09-25T15:01:04Z", "status": "success", "stats": {"task_id": "a" * 32, "duration_ms": 4000, "tool_calls": 2, "session_costs": "SECRET_COSTS"}},
            ]
            transcript.write_text("\n".join(json.dumps(item) for item in events) + "\n", encoding="utf-8")
            summary = summarize(transcript)
            rendered = json.dumps(summary)
            self.assertEqual(summary["terminal"]["task_id"], "a" * 32)
            self.assertEqual([item["status"] for item in summary["tool_calls"]], ["error", "missing_result"])
            self.assertEqual(summary["message_role_counts"], {"user": 1})
            for secret in ("SECRET_PROMPT", "SECRET_KEY", "SECRET_OUTPUT", "SECRET_COSTS"):
                self.assertNotIn(secret, rendered)

    def test_rejects_truncated_json_without_writing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "broken.ndjson"
            transcript.write_text('{"type":', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Line 1"):
                summarize(transcript)


if __name__ == "__main__":
    unittest.main()
