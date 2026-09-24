"""Summarize Bob Shell NDJSON without publishing prompts or tool payloads.

The original transcript stays private. This metadata binds a task to its raw
stream and optional candidate files; IDE history/screenshots remain separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SAFE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,127}\Z")
TASK_ID = re.compile(r"[0-9a-f]{32}\Z")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_name(value: object) -> str:
    return value if isinstance(value, str) and SAFE_NAME.fullmatch(value) else "unrecognized"


def timestamp(value: object, line_number: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Line {line_number} has no timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Line {line_number} has an invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"Line {line_number} has no timestamp offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def summarize(transcript: Path, artifacts: list[Path] | None = None) -> dict:
    transcript = transcript.resolve()
    if not transcript.is_file():
        raise ValueError("Transcript does not exist")
    messages = Counter()
    types = Counter()
    calls = []
    outstanding = {}
    orphan_results = 0
    result = None
    first = last = None
    with transcript.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {line_number} is not valid JSON") from exc
            if not isinstance(event, dict):
                raise ValueError(f"Line {line_number} is not a JSON object")
            event_time = timestamp(event.get("timestamp"), line_number)
            first = first or event_time
            last = event_time
            kind = safe_name(event.get("type"))
            types[kind] += 1
            if kind == "message":
                messages[safe_name(event.get("role"))] += 1
            elif kind == "tool_use":
                tool_id = event.get("tool_id")
                if not isinstance(tool_id, str) or not tool_id or tool_id in outstanding:
                    raise ValueError(f"Line {line_number} has a missing or duplicate tool ID")
                call = {"tool": safe_name(event.get("tool_name")),
                        "at_utc": event_time, "status": "missing_result"}
                calls.append(call)
                outstanding[tool_id] = call
            elif kind == "tool_result":
                call = outstanding.pop(event.get("tool_id"), None)
                if call is None:
                    orphan_results += 1
                else:
                    call["status"] = safe_name(event.get("status"))
            elif kind == "result":
                if result is not None:
                    raise ValueError("Transcript has more than one terminal result")
                stats = event.get("stats") if isinstance(event.get("stats"), dict) else {}
                task_id = stats.get("task_id")
                result = {"status": safe_name(event.get("status")),
                          "task_id": task_id if isinstance(task_id, str) and TASK_ID.fullmatch(task_id) else None,
                          "duration_ms": stats.get("duration_ms") if type(stats.get("duration_ms")) is int else None,
                          "reported_tool_calls": stats.get("tool_calls") if type(stats.get("tool_calls")) is int else None}
    if not types:
        raise ValueError("Transcript has no events")
    files = []
    for path in artifacts or []:
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"Artifact does not exist: {path.name}")
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema_version": 1,
        "source": "Bob Shell NDJSON metadata; raw transcript is retained separately",
        "transcript": {"name": transcript.name, "bytes": transcript.stat().st_size,
                       "sha256": sha256(transcript)},
        "first_event_utc": first,
        "last_event_utc": last,
        "terminal": result,
        "event_counts": dict(sorted(types.items())),
        "message_role_counts": dict(sorted(messages.items())),
        "tool_calls": calls,
        "orphan_tool_results": orphan_results,
        "artifacts": files,
        "limits": "Metadata only. A task ID or tool name does not prove the quality of Bob's work; inspect the original task history, files, screenshots, and independent replay.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.transcript.resolve():
        parser.error("Output must not overwrite the raw transcript")
    report = summarize(args.transcript, args.artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote metadata for {len(report['tool_calls'])} tool calls to {args.output}")


if __name__ == "__main__":
    main()
