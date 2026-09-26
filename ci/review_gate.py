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
import re
import subprocess
import sys
from pathlib import Path

# Resolve presentation helpers from this gate's checkout, including in a consumer Action.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci.witness_source import describe as describe_source, window_source

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


def _workspace_relative(path: Path) -> Path:
    """Display consumer inputs relative to their checkout in reusable Actions."""
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if path.is_absolute() and workspace:
        try:
            return path.resolve().relative_to(Path(workspace).resolve())
        except ValueError:
            pass
    return path


def _emit_annotation(classification: str, plan: Path, report: dict,
                     cli_exit: int | None, audit_exit: int | None,
                     reason: str = "", location: dict | None = None) -> None:
    """Place a bounded verdict on the PR's candidate file in GitHub Checks."""
    if os.environ.get("GITHUB_ACTIONS") != "true" or classification == "verified_pass":
        return
    plan = _workspace_relative(plan)
    file = plan.as_posix()
    if plan.is_absolute() or ".." in plan.parts or not re.fullmatch(r"[A-Za-z0-9_./-]+", file):
        file = ".github/workflows/cutover-review.yml"
        location = None
    if classification == "verified_block":
        witness = report.get("witness") or {}
        failure = witness.get("failure") or {}
        expected, actual = failure.get("expected") or {}, failure.get("actual") or {}
        row = next((key for key in expected if expected.get(key) != actual.get(key)), None)
        message = (f"Verified block: {report.get('passed')}/{report.get('total')} probes passed; "
                   f"first witness {witness.get('id', 'unknown')}.")
        if location:
            message += ' ' + describe_source(location)
        if row is not None:
            value = lambda item: json.dumps(item, ensure_ascii=False)
            message += (f" Row {row}: expected {value(expected[row])}, "
                        f"observed {value(actual.get(row))}.")
        title = "Cutover verified data-safety block"
    else:
        message = (f"Unverified: CLI exit {cli_exit}, audit exit {audit_exit}. "
                   "No passing result was established; inspect verdict.json and summary.md.")
        if reason:
            message = reason + " " + message
        title = "Cutover could not verify candidate"
    # GitHub's workflow command protocol uses one log line. Escape values so
    # imported payloads cannot create another command or annotation property.
    def escape(value: str) -> str:
        return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    position = f",line={location['line']},endLine={location['line']}" if location else ''
    print(f"::error file={escape(file)}{position},title={title}::{escape(message[:500])}")


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
    migration_source: dict | None = None,
    contract_lock: dict | None = None,
    location: dict | None = None,
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
    if contract_lock:
        lines.append(f"| Contract lock | `{contract_lock['status']}` |")
        lines.append(f"| Expected contract hash | `{contract_lock['expected']}` |")
        lines.append(f"| Observed contract hash | `{contract_lock['actual']}` |")
    if migration_source:
        source_path = migration_source["path"].replace("|", "&#124;").replace("`", "&#96;")
        source_path = source_path.replace("\r", " ").replace("\n", " ")
        lines.append(f"| SQL source file | `{source_path}` |")
        lines.append(f"| SQL file SHA-256 | `{migration_source['sha256']}` |")
    lines.append("")
    if contract_lock:
        lines += ["The contract hash covers the agreed schema, old-worker adapters,",
                  "seed records and payloads. A changed contract requires a separate",
                  "review; it is not evidence that the migration was repaired.", ""]
    if migration_source:
        lines += ["The migration was loaded from this SQL file. `effective-plan.json`",
                  "retains the SQL and adapters supplied to the CLI and independent audit.", ""]

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
        if location:
            context = location['sql_context']
            if len(context) > 1600:
                context = context[:1600] + '\n-- Excerpt truncated; inspect the SQL source.'
            fence = '`' * max(3, 1 + max((len(run) for run in re.findall(r'`+', context)), default=0))
            lines += [f"**Replay location:** {describe_source(location)}", "",
                      "The annotation marks the observed old-worker operation's boundary,",
                      "not a claim that this SQL line alone caused the defect.", "",
                      f"{fence}sql", context, fence, ""]

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


def _input_failure(out: Path, reason: str, annotation_path: Path,
                   contract_lock: dict | None = None) -> int:
    verdict = {"classification": "unverified", "cli_exit": None,
               "audit_exit": None, "reason": reason}
    if contract_lock:
        verdict["contract_lock"] = contract_lock
    (out / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    summary = _build_summary("unverified", None, None, "", "", reason, {},
                             contract_lock=contract_lock)
    (out / "summary.md").write_text(summary + "\n", encoding="utf-8")
    _append_step_summary(summary)
    _emit_annotation("unverified", annotation_path, {}, None, None, reason)
    sys.stderr.write(f"ERROR: {reason}\n")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cutover PR gate: run CLI + audit, write verdict.json."
    )
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--migration-file", default="",
                        help="Use this checked-in SQL file instead of the plan's migration text")
    parser.add_argument("--expected-contract-hash",
                        help="Require this reviewed canonical contract SHA-256; changed contracts are unverified")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    report_path = out / "report.json"
    review_path = out / "review.md"
    bundle_path = out / "review.zip"
    summary_path = out / "summary.md"
    verdict_path = out / "verdict.json"

    migration_path = Path(args.migration_file) if args.migration_file else None
    annotation_path = migration_path or args.plan
    inputs = [("contract", args.contract), ("plan", args.plan)]
    if migration_path:
        inputs.append(("migration", migration_path))
    for label, path in inputs:
        if not path.is_file():
            return _input_failure(out, f"{label} file not found: {path}", annotation_path)

    contract_lock = None
    if args.expected_contract_hash is not None:
        expected = args.expected_contract_hash.lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            return _input_failure(out, "Expected contract hash must be 64 hexadecimal characters", args.contract)
        try:
            if args.contract.stat().st_size > 65536:
                raise ValueError("Contract JSON must be at most 64 KiB")
            contract = json.loads(args.contract.read_text(encoding="utf-8"))
            actual = hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")).encode("utf-8")).hexdigest()
        except (OSError, ValueError, TypeError) as exc:
            return _input_failure(out, f"Contract lock could not be checked: {exc}", args.contract)
        contract_lock = {"expected": expected, "actual": actual,
                         "status": "matched" if actual == expected else "changed"}
        if actual != expected:
            return _input_failure(out, "Contract changed from the reviewed lock; review the test contract separately",
                                  args.contract, contract_lock)

    contract_hash = _sha256(args.contract)
    plan_hash = _sha256(args.plan)
    review_plan = args.plan
    migration_source = None
    if migration_path:
        try:
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            if not isinstance(plan, dict):
                raise ValueError("Candidate plan must be a JSON object")
            sql_bytes = migration_path.read_bytes()
            plan["migration"] = sql_bytes.decode("utf-8-sig")
            review_plan = out / "effective-plan.json"
            if review_plan.resolve() in {path.resolve() for _, path in inputs}:
                raise ValueError("Effective plan output would overwrite a source input")
            review_plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            migration_source = {"path": _workspace_relative(migration_path).as_posix(),
                                "sha256": hashlib.sha256(sql_bytes).hexdigest()}
        except (OSError, ValueError, TypeError) as exc:
            return _input_failure(out, f"SQL source could not be loaded: {exc}", annotation_path)

    # ── Step 1: CLI rehearsal ──────────────────────────────────────────────
    cli_cmd = [
        sys.executable, "-m", "cutover",
        "--contract", str(args.contract),
        "--plan", str(review_plan),
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
            "--plan", str(review_plan),
            "--contract", str(args.contract),
        ]
        audit_exit, audit_stdout, audit_stderr = _run(audit_cmd, AUDIT_TIMEOUT)
    else:
        audit_stderr = "Skipped: CLI did not produce report.json"

    # ── Parse report (best-effort; may be absent on CLI error) ────────────
    report = _read_report(report_path) if report_path.exists() else {}

    # ── Classify ───────────────────────────────────────────────────────────
    classification = _classify(cli_exit, audit_exit)
    lock_reason = ""
    if contract_lock and report and report.get("contract_hash") != contract_lock["expected"]:
        contract_lock["status"] = "changed"
        contract_lock["actual"] = report.get("contract_hash", "")
        classification = "unverified"
        lock_reason = "Executed report does not match the reviewed contract lock"
        audit_stderr = (audit_stderr + "\n" + lock_reason).strip()

    # ── Write verdict.json (always) ────────────────────────────────────────
    # Use report-embedded hashes when available; fall back to file SHA-256.
    verdict: dict = {
        "classification": classification,
        "cli_exit": cli_exit,
        "audit_exit": audit_exit,
        "contract_hash": report.get("contract_hash") or contract_hash,
        "plan_hash": report.get("plan_hash") or plan_hash,
    }
    if migration_source:
        verdict["migration_source"] = migration_source
        verdict["source_plan_sha256"] = plan_hash
    if contract_lock:
        verdict["contract_lock"] = contract_lock
    if lock_reason:
        verdict["reason"] = lock_reason
    location = window_source(report, migration_source) if classification == 'verified_block' else None
    if location:
        verdict['witness_source'] = location
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
        migration_source,
        contract_lock,
        location,
    )
    summary_path.write_text(summary + "\n", encoding="utf-8")
    _append_step_summary(summary)
    _emit_annotation(classification, args.contract if lock_reason else annotation_path,
                     report, cli_exit, audit_exit, lock_reason, location)

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
