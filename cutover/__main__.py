import argparse
import json
import subprocess
import sys
from pathlib import Path
from .engine import load_case, load_plan
from .bundle import render_bundle
from .reporting import render_markdown, render_reproduction
from .service import WORKER_TIMEOUT_SECONDS, run_rehearsal

parser = argparse.ArgumentParser(description="Rehearse old/new application contracts on disposable SQLite databases.")
parser.add_argument("--case", choices=["parcel", "contacts"], default="parcel")
parser.add_argument("--reference", choices=["rename", "backfill", "late_bridge", "bridge"], default="rename")
parser.add_argument("--plan", type=Path, help="Candidate plan JSON. Overrides --reference.")
parser.add_argument("--migration-file", type=Path, help="UTF-8 .sql file overriding only the candidate migration; requires --plan.")
parser.add_argument("--contract", type=Path, help="A bounded SQL contract JSON; requires --plan.")
parser.add_argument("--output", type=Path)
parser.add_argument("--markdown", type=Path, help="Review-ready Markdown from the same executed report.")
parser.add_argument("--repro", type=Path, help="Standalone Python replay of a failing data mismatch witness.")
parser.add_argument("--bundle", type=Path, help="ZIP with inputs, executed evidence, review and any replayable witness.")
args = parser.parse_args()
if args.migration_file and not args.plan:
    parser.error("--migration-file requires a candidate --plan for its application queries")
if args.contract and not args.plan:
    parser.error("--contract requires a candidate --plan")
if args.contract and args.case != 'parcel':
    parser.error("--case selects a bundled example and cannot be combined with --contract")
destinations = [path.resolve() for path in (args.output, args.markdown, args.repro, args.bundle) if path]
if len(destinations) != len(set(destinations)):
    parser.error("Evidence outputs must be different files")
inputs = {path.resolve() for path in (args.contract, args.plan, args.migration_file) if path}
for destination in (args.output, args.markdown, args.repro, args.bundle):
    if destination and destination.resolve() in inputs:
        parser.error("Evidence outputs cannot overwrite a contract, candidate plan or migration source")


def read_json(path, label):
    try:
        if path.stat().st_size > 65536:
            parser.error(f"{label} JSON must be at most 64 KiB")
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot read {label} JSON: {exc}")


contract = read_json(args.contract, 'Contract') if args.contract else None
plan = read_json(args.plan, 'Plan') if args.plan else load_plan(args.case, args.reference)
if args.migration_file:
    try:
        if args.migration_file.stat().st_size > 65536:
            parser.error("Migration SQL must be at most 64 KiB")
        sql = args.migration_file.read_bytes().decode('utf-8-sig')
        if not sql.strip() or '\0' in sql or len(sql) > 12000:
            parser.error("Expected nonempty UTF-8 migration SQL without NUL characters, up to 12,000 characters")
        if not isinstance(plan, dict):
            parser.error("Candidate plan must be a JSON object")
        plan = dict(plan, migration=sql, name=f'Imported SQL: {args.migration_file.name}'[:100])
    except (OSError, UnicodeError) as exc:
        parser.error(f"Cannot read migration SQL: {exc}")
try:
    report = run_rehearsal('custom' if contract is not None else args.case, plan, contract)
except subprocess.TimeoutExpired:
    parser.error(f'Rehearsal exceeded its {WORKER_TIMEOUT_SECONDS} second budget; no verdict was produced')
except ValueError as exc:
    parser.error(str(exc))
try:
    reproduction = render_reproduction(report, contract if contract is not None else load_case(args.case)) if args.repro else None
except ValueError as exc:
    parser.error(str(exc))
bundle = render_bundle(report, contract if contract is not None else load_case(args.case)) if args.bundle else None
output = json.dumps(report, ensure_ascii=False, indent=2)
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((output + "\n").encode("utf-8"))
if args.markdown:
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_bytes(render_markdown(report).encode("utf-8"))
if args.repro:
    args.repro.parent.mkdir(parents=True, exist_ok=True)
    args.repro.write_bytes(reproduction.encode("utf-8"))
if args.bundle:
    args.bundle.parent.mkdir(parents=True, exist_ok=True)
    args.bundle.write_bytes(bundle)
print(f"{report['status'].upper()}: {report['passed']}/{report['total']} rollout and window probes; "
      f"same-version baseline {report['baseline']['passed']}/{report['baseline']['total']}; "
      f"plan {report['plan_hash'][:12]}")
if report['witness']:
    print("Witness:", " -> ".join(e['action'] for e in report['witness']['trace']))
    print(report['witness']['failure']['message'])
sys.exit(0 if report["status"] == "pass" else 1)
