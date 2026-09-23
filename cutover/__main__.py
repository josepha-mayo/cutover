import argparse
import json
import sys
from pathlib import Path
from .engine import load_plan, rehearse
from .reporting import render_markdown

parser = argparse.ArgumentParser(description="Rehearse old/new application contracts on disposable SQLite databases.")
parser.add_argument("--case", choices=["parcel", "contacts"], default="parcel")
parser.add_argument("--reference", choices=["rename", "backfill", "late_bridge", "bridge"], default="rename")
parser.add_argument("--plan", type=Path, help="Candidate plan JSON. Overrides --reference.")
parser.add_argument("--contract", type=Path, help="A bounded SQL contract JSON; requires --plan.")
parser.add_argument("--output", type=Path)
parser.add_argument("--markdown", type=Path, help="Review-ready Markdown from the same executed report.")
args = parser.parse_args()
if args.contract and not args.plan:
    parser.error("--contract requires a candidate --plan")
if args.contract and args.case != 'parcel':
    parser.error("--case selects a bundled example and cannot be combined with --contract")
if args.output and args.markdown and args.output.resolve() == args.markdown.resolve():
    parser.error("--output and --markdown must be different files")
inputs = {path.resolve() for path in (args.contract, args.plan) if path}
for destination in (args.output, args.markdown):
    if destination and destination.resolve() in inputs:
        parser.error("Evidence outputs cannot overwrite a contract or candidate plan")


def read_json(path, label):
    try:
        if path.stat().st_size > 65536:
            parser.error(f"{label} JSON must be at most 64 KiB")
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot read {label} JSON: {exc}")


contract = read_json(args.contract, 'Contract') if args.contract else None
plan = read_json(args.plan, 'Plan') if args.plan else load_plan(args.case, args.reference)
try:
    report = rehearse('custom' if contract is not None else args.case, plan, contract)
except ValueError as exc:
    parser.error(str(exc))
output = json.dumps(report, ensure_ascii=False, indent=2)
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output + "\n", encoding="utf-8")
if args.markdown:
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
print(f"{report['status'].upper()}: {report['passed']}/{report['total']} rollout and window probes; "
      f"same-version baseline {report['baseline']['passed']}/{report['baseline']['total']}; "
      f"plan {report['plan_hash'][:12]}")
if report['witness']:
    print("Witness:", " -> ".join(e['action'] for e in report['witness']['trace']))
    print(report['witness']['failure']['message'])
sys.exit(0 if report["status"] == "pass" else 1)
