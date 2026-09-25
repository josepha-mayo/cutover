"""Focused tests for ci/review_gate.py.

Tests exercise:
  - verified_pass   (safe bridge plan)
  - verified_block  (late_bridge — missing pre-migration triggers)
  - unverified      (malformed JSON plan)

Each test inspects verdict.json, summary.md exit code, and — for the block
case — that summary.md contains the report-embedded plan_hash, contract_hash,
witness.id, and at least one exact expected/actual value pair from
witness.failure.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_GATE = ROOT / "ci" / "review_gate.py"
WAREHOUSE = ROOT / "examples" / "warehouse"
CONTRACT = WAREHOUSE / "contract.json"
BRIDGE = WAREHOUSE / "bridge.json"
LATE_BRIDGE = WAREHOUSE / "late_bridge.json"
PARCEL_CONTRACT = ROOT / "ci" / "parcel-contract.json"
BOB_PARCEL = ROOT / "ci" / "parcel-candidate.json"


def _run_gate(plan: Path, output_dir: Path, contract: Path = CONTRACT,
              env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CI_GATE),
         "--contract", str(contract),
         "--plan", str(plan),
         "--output-dir", str(output_dir)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=300,
    )


class GateVerifiedPassTests(unittest.TestCase):
    def test_distinct_bob_parcel_candidate_is_verified_pass(self):
        from cutover.engine import PAYLOADS

        bundled = json.loads((ROOT / "examples" / "parcel" / "contract.json").read_text(encoding="utf-8"))
        imported = json.loads(PARCEL_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(imported, {**bundled, "payloads": PAYLOADS})
        self.assertEqual(BOB_PARCEL.read_bytes(),
                         (ROOT / "bob_sessions" / "parcel-07a20bdb56f5-candidate.json").read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = _run_gate(BOB_PARCEL, out, PARCEL_CONTRACT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict["classification"], "verified_pass")
            self.assertEqual((report["passed"], report["total"]), (116, 116))
            self.assertEqual(verdict["contract_hash"], report["contract_hash"])
            self.assertEqual(verdict["plan_hash"], report["plan_hash"])
            self.assertTrue((out / "review.zip").exists())

    def test_safe_bridge_is_verified_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = _run_gate(BRIDGE, out)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict["classification"], "verified_pass")
            self.assertEqual(verdict["cli_exit"], 0)
            self.assertEqual(verdict["audit_exit"], 0)
            self.assertIn("plan_hash", verdict)
            self.assertIn("contract_hash", verdict)

            report = json.loads((out / "report.json").read_text(encoding="utf-8"))

            summary = (out / "summary.md").read_text(encoding="utf-8")
            self.assertIn("verified_pass", summary.lower())
            self.assertIn(verdict["plan_hash"], summary)
            self.assertIn(verdict["contract_hash"], summary)
            self.assertIn("bounded to this suite", summary)
            # Exact coverage from report
            self.assertIn(f"{report['passed']}/{report['total']}", summary)

            # Report and review artifacts must exist
            self.assertTrue((out / "report.json").exists())
            self.assertTrue((out / "review.md").exists())
            self.assertTrue((out / "review.zip").exists())


class GateVerifiedBlockTests(unittest.TestCase):
    def test_github_check_annotates_exact_failure_without_exposing_workflow_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = _run_gate(LATE_BRIDGE, out, env={**os.environ, "GITHUB_ACTIONS": "true"})
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            failure = report["witness"]["failure"]
            row = next(key for key in failure["expected"]
                       if failure["expected"][key] != failure["actual"].get(key))
            annotations = [line for line in result.stdout.splitlines() if line.startswith("::error ")]
            self.assertEqual(result.returncode, 1)
            self.assertEqual(len(annotations), 1)
            self.assertIn("Cutover verified data-safety block", annotations[0])
            self.assertIn(report["witness"]["id"], annotations[0])
            self.assertIn(str(row), annotations[0])
            self.assertIn(str(failure["expected"][row]), annotations[0])
            self.assertIn(str(failure["actual"].get(row)), annotations[0])

    def test_late_bridge_is_verified_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = _run_gate(LATE_BRIDGE, out)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

            verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict["classification"], "verified_block")
            self.assertEqual(verdict["cli_exit"], 1)
            self.assertEqual(verdict["audit_exit"], 1)

            # Report-embedded hashes (not file SHA-256)
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict["plan_hash"], report["plan_hash"])
            self.assertEqual(verdict["contract_hash"], report["contract_hash"])

            # Witness identity from the report
            self.assertEqual(verdict.get("witness_id"), report["witness"]["id"])

            # At least one exact expected/actual pair
            self.assertIn("witness_failure", verdict)
            wf = verdict["witness_failure"]
            failure = report["witness"]["failure"]
            self.assertEqual(wf["expected"], failure["expected"])
            self.assertEqual(wf["actual"], failure["actual"])
            # Confirm at least one key differs
            diffs = {k for k in wf["expected"] if wf["expected"][k] != wf["actual"].get(k)}
            self.assertTrue(diffs, "witness_failure shows no differing value")

            # summary.md must carry report hashes, witness id, coverage, and a value pair
            summary = (out / "summary.md").read_text(encoding="utf-8")
            self.assertIn("verified_block", summary.lower())
            self.assertIn(report["plan_hash"], summary)
            self.assertIn(report["contract_hash"], summary)
            self.assertIn(report["witness"]["id"], summary)
            # Exact coverage from report (e.g. "108/124")
            self.assertIn(f"{report['passed']}/{report['total']}", summary)
            # At least one exact expected value must appear in the summary
            differing_key = next(iter(diffs))
            self.assertIn(str(failure["expected"][differing_key]), summary)
            self.assertIn(str(failure["actual"][differing_key]), summary)

            # All evidence artifacts must still exist
            self.assertTrue((out / "report.json").exists())
            self.assertTrue((out / "review.md").exists())
            self.assertTrue((out / "review.zip").exists())

    def test_block_is_not_classified_as_unverified(self):
        """verified_block and unverified are visibly different outcomes."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            _run_gate(LATE_BRIDGE, out)
            verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
            self.assertNotEqual(verdict["classification"], "unverified")


class GateUnverifiedTests(unittest.TestCase):
    def test_malformed_plan_is_unverified_not_verified_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            malformed = Path(tmp) / "bad_plan.json"
            malformed.write_text("{not valid json", encoding="utf-8")

            result = _run_gate(malformed, out)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

            verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict["classification"], "unverified")
            self.assertNotEqual(verdict["classification"], "verified_block")
            self.assertIsNone(verdict["audit_exit"])

            # verdict.json and summary.md must always exist
            self.assertTrue((out / "verdict.json").exists())
            self.assertTrue((out / "summary.md").exists())

    def test_missing_plan_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            missing = Path(tmp) / "no_such_plan.json"

            result = _run_gate(missing, out)

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            verdict = json.loads((out / "verdict.json").read_text(encoding="utf-8"))
            self.assertEqual(verdict["classification"], "unverified")
            self.assertIsNone(verdict["cli_exit"])
            self.assertIsNone(verdict["audit_exit"])


if __name__ == "__main__":
    unittest.main()
