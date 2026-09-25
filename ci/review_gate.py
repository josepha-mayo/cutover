"""Pull-request gate: run the Cutover CLI and independent audit, emit verdict.json.

Usage:
    python ci/review_gate.py --contract PATH --plan PATH --output-dir DIR

Exit codes:
    0  verified_pass  (CLI exit 0 AND audit exit 0)
    1  verified_block (CLI exit 1 AND audit exit 1)
    2  unverified     (any other outcome: timeout, error, mismatch pair)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# Per-command wall-clock budget (seconds).  The engine's own worker has a
# 90-second internal cap; we add headroom for process startup and I/O.
CLI_TIMEOUT = 120
AUDIT_TIMEOUT = 120


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _run(cmd: list[str], timeout: int) -> tuple[int | None, str, str]:
    """Run *cmd*, return (returncode, stdout, stderr).

    Returns (None, '', message) on timeout so the caller can treat it uniformly.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return None, "", f"Process timed out after {timeout}s: {exc}"
    except Exception as exc:  # noqa: BLE001
        return None, "", f"Process could not be started: {exc}"


def _classify(cli_exit: int | None, audit_exit: int | None) -> str:
    if cli_exit == 0 and audit_exit == 0:
        return "verified_pass"
    if cli_exit == 1 and audit_exit == 1:
        return "verified_block"
    return "unverified"


def _read_report(report_path: Path) -> dict:
    """Return parsed report dict, or {} on any read/parse error."""
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _build_summary(
    classification: str,
    cli_exit: int | None,
    audit_exit: int | None,
    cli_stdout: str,
    audit_stdout: str,
    audit_stderr: str,
    report: dict,
) -> str:
    """Build the Markdown job summary.

    *report* is the parsed report.json (may be empty dict when unavailable).
    Hashes and witness fields are read from the report so they reflect the
    executed evidence, not raw file checksums.
    """
    icon = {"verified_pass": "✅", "verified_block": "❌", "unverified": "⚠️"}.get(
        classification, "⚠️"
    )

    # Prefer report-embedded hashes; fall back to empty string when absent.
    plan_hash = report.get("plan_hash", "")
    contract_hash = report.get("contract_hash", "")

    lines = [
        f"## Cutover PR gate — {icon} {classification.upper()}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Classification | `{classification}` |",
        f"| CLI exit | `{cli_exit}` |",
        f"| Audit exit | `{audit_exit}` |",
    ]
    if contract_hash:
        lines.append(f"| Contract hash (report) | `{contract_hash}` |")
    if plan_hash:
        lines.append(f"| Plan hash (report) | `{plan_hash}` |")
    lines.append("")

    passed = report.get("passed")
    total = report.get("total")
    coverage = f"{passed}/{total}" if passed is not None and total is not None else None

    if classification == "verified_block":
        witness = report.get("witness") or {}
        failure = witness.get("failure") or {}
        witness_id = witness.get("id", "")
        expected = failure.get("expected") or {}
        actual = failure.get("actual") or {}

        lines += [
            "### ❌ Verified block — candidate has a data-safety gap",
            "",
            "The CLI executed the candidate and observed at least one failing probe.",
            "The independent audit confirmed the same result from the checked-in inputs.",
            "",
        ]
        if coverage:
            lines += [f"**Coverage:** {coverage} probes passed.", ""]
        if witness_id:
            lines += [f"**Probe:** `{witness_id}`", ""]

        # Show the first key where expected ≠ actual (the most informative pair).
        differing_key = next(
            (k for k in expected if expected.get(k) != actual.get(k)), None
        )
        if differing_key is not None:
            lines += [
                "**First differing value (row `" + str(differing_key) + "`):**",
                "",
                "| | Value |",
                "| --- | --- |",
                f"| Expected | `{expected[differing_key]}` |",
                f"| Actual   | `{actual.get(differing_key)}` |",
                "",
            ]

        lines += [
            "Review `report.json` and `review.md` in the uploaded artifacts for the",
            "full witness trace.",
            "",
        ]
    elif classification == "verified_pass":
        lines += [
            "### ✅ Verified pass — all probes passed",
            "",
            "Both the CLI and the independent audit agree: the candidate passed all",
            "rollout and migration-window probes in this bounded suite.",
            "",
            "> **A pass is bounded to this suite; it is not a deployment approval.**",
            "",
        ]
        if coverage:
            lines += [f"**Coverage:** {coverage} probes passed.", ""]
        if cli_stdout:
            first = next(
                (ln for ln in cli_stdout.splitlines() if ln.strip()), ""
            )
            if first:
                lines += [f"CLI: `{first.strip()}`", ""]
    else:
        lines += [
            "### ⚠️ Unverified — evidence could not be independently confirmed",
            "",
            "The gate could not produce a definitive verdict.",
            "Possible causes: timeout, invalid inputs, process error, or a",
            "CLI/audit exit-code pair that does not map to a known outcome.",
            "",
        ]
        if audit_stderr:
            lines += [
                "**Audit stderr:**",
                "",
                "```",
                audit_stderr.strip()[:2000],
                "```",
                "",
            ]

    lines += [
        "---",
        "_Evidence artifacts are uploaded unconditionally; see the Actions run._",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cutover PR gate: run CLI + audit, write verdict.json."
    )
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    report_path = out / "report.json"
    review_path = out / "review.md"
    bundle_path = out / "review.zip"
    summary_path = out / "summary.md"
    verdict_path = out / "verdict.json"

    # Validate inputs exist before touching subprocesses.
    for label, path in (("contract", args.contract), ("plan", args.plan)):
        if not path.exists():
            verdict = {
                "classification": "unverified",
                "cli_exit": None,
                "audit_exit": None,
                "reason": f"{label} file not found: {path}",
            }
            verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
            summary = _build_summary(
                "unverified", None, None, "", "", f"{label} not found: {path}", {}
            )
            summary_path.write_text(summary + "\n", encoding="utf-8")
            _append_step_summary(summary)
            sys.stderr.write(f"ERROR: {label} file not found: {path}\n")
            return 2

    contract_hash = _sha256(args.contract)
    plan_hash = _sha256(args.plan)

    # ── Step 1: CLI rehearsal ──────────────────────────────────────────────
    cli_cmd = [
        sys.executable, "-m", "cutover",
        "--contract", str(args.contract),
        "--plan", str(args.plan),
        "--output", str(report_path),
        "--markdown", str(review_path),
        "--bundle", str(bundle_path),
    ]
    cli_exit, cli_stdout, cli_stderr = _run(cli_cmd, CLI_TIMEOUT)

    # ── Step 2: independent audit (only if report was written) ─────────────
    audit_exit: int | None = None
    audit_stdout = ""
    audit_stderr = ""

    if report_path.exists():
        audit_cmd = [
            sys.executable, "-m", "cutover.audit_report",
            "--report", str(report_path),
            "--plan", str(args.plan),
            "--contract", str(args.contract),
        ]
        audit_exit, audit_stdout, audit_stderr = _run(audit_cmd, AUDIT_TIMEOUT)
    else:
        audit_stderr = "Skipped: CLI did not produce report.json"

    # ── Parse report (best-effort; may be absent on CLI error) ────────────
    report = _read_report(report_path) if report_path.exists() else {}

    # ── Classify ───────────────────────────────────────────────────────────
    classification = _classify(cli_exit, audit_exit)

    # ── Write verdict.json (always) ────────────────────────────────────────
    # Use report-embedded hashes when available; fall back to file SHA-256.
    verdict: dict = {
        "classification": classification,
        "cli_exit": cli_exit,
        "audit_exit": audit_exit,
        "contract_hash": report.get("contract_hash") or contract_hash,
        "plan_hash": report.get("plan_hash") or plan_hash,
    }
    witness = report.get("witness") or {}
    if witness.get("id"):
        verdict["witness_id"] = witness["id"]
    failure = witness.get("failure") or {}
    if failure.get("expected") and failure.get("actual"):
        verdict["witness_failure"] = {
            "expected": failure["expected"],
            "actual": failure["actual"],
        }
    verdict_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")

    # ── Write summary.md (always) ──────────────────────────────────────────
    summary = _build_summary(
        classification,
        cli_exit,
        audit_exit,
        cli_stdout or "",
        audit_stdout or "",
        audit_stderr or "",
        report,
    )
    summary_path.write_text(summary + "\n", encoding="utf-8")
    _append_step_summary(summary)

    # ── Log to stdout for workflow visibility ──────────────────────────────
    print(f"classification: {classification}")
    print(f"cli_exit: {cli_exit}  audit_exit: {audit_exit}")
    if cli_stdout:
        print("--- CLI stdout ---")
        print(cli_stdout.rstrip())
    if audit_stdout:
        print("--- Audit stdout ---")
        print(audit_stdout.rstrip())
    if audit_stderr and classification != "verified_pass":
        print("--- Audit stderr ---")
        print(audit_stderr.rstrip())

    # ── Exit code ──────────────────────────────────────────────────────────
    # 0 = verified pass; anything else fails the step so the upload still runs.
    if classification == "verified_pass":
        return 0
    if classification == "verified_block":
        return 1
    return 2  # unverified


def _append_step_summary(text: str) -> None:
    """Append *text* to $GITHUB_STEP_SUMMARY when running in GitHub Actions."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)
            fh.write("\n")
    except OSError:
        pass  # Non-fatal; summary is cosmetic.


if __name__ == "__main__":
    sys.exit(main())
