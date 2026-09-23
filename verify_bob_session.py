"""Verify a reference-withheld Bob workspace against its committed source.

Run before and after the actual Bob task. Files under work/ may contain Bob's
candidate and notes; the copied evaluator, old contract, and failing samples
must remain byte-for-byte identical to their recorded source commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WITHHELD = {"examples/parcel/bridge.json", "examples/contacts/bridge.json"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(workspace: Path) -> dict[str, object]:
    workspace = workspace.resolve()
    manifest_path = workspace / "SESSION_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    revision = manifest["source_revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Manifest source revision is not a full Git commit hash")
    copied = manifest["copied_sha256"]
    errors: list[str] = []

    for name, expected_hash in copied.items():
        path = (workspace / name).resolve()
        if not path.is_relative_to(workspace) or not path.is_file():
            errors.append(f"Missing or out-of-workspace source: {name}")
            continue
        actual_hash = sha256(path.read_bytes())
        if actual_hash != expected_hash:
            errors.append(f"Changed workspace source: {name}")
        committed = subprocess.run(
            ["git", "show", f"{revision}:{name}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if committed.returncode or sha256(committed.stdout) != expected_hash:
            errors.append(f"Manifest does not match source commit: {name}")

    if copied.get("cutover/engine.py") != manifest.get("evaluator_sha256"):
        errors.append("Evaluator hash disagrees with copied source list")
    if set(manifest.get("withheld", [])) != WITHHELD:
        errors.append("Withheld-reference list is incomplete")
    for name in WITHHELD:
        if (workspace / name).exists():
            errors.append(f"Passing reference leaked into workspace: {name}")
    if (workspace / "presentation").exists():
        errors.append("Presentation material leaked into repair workspace")
    if not (workspace / "TASK.md").is_file():
        errors.append("Bob task brief is missing")

    config_path = workspace / ".bob" / "mcp.json"
    if not config_path.is_file():
        errors.append("Project-local Bob MCP configuration is missing")
    else:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        server = config.get("mcpServers", {}).get("cutover", {})
        if server.get("disabled") is not False or server.get("alwaysAllow") != []:
            errors.append("Cutover MCP server is disabled or has automatic tool approval")
        if not Path(server.get("command", "")).is_file():
            errors.append("Configured MCP Python interpreter is missing")
        if server.get("args") != [str(workspace / "mcp_server.py")]:
            errors.append("MCP server path points outside the workspace")
        if server.get("cwd") != str(workspace):
            errors.append("MCP server working directory is not the workspace")

    return {
        "workspace": str(workspace),
        "source_revision": revision,
        "verified_source_files": len(copied),
        "evaluator_sha256": manifest.get("evaluator_sha256"),
        "passing_references_absent": all(not (workspace / name).exists() for name in WITHHELD),
        "status": "pass" if not errors else "fail",
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.workspace)
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
