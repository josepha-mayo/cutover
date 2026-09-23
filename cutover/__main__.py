import argparse
import json
import sys
from pathlib import Path
from .engine import load_plan, rehearse

parser = argparse.ArgumentParser(description="Rehearse old/new application contracts on disposable SQLite databases.")
parser.add_argument("--case", choices=["parcel", "contacts"], default="parcel")
parser.add_argument("--reference", choices=["rename", "backfill", "bridge"], default="rename")
parser.add_argument("--plan", type=Path, help="Candidate plan JSON. Overrides --reference.")
parser.add_argument("--output", type=Path)
args = parser.parse_args()
plan = json.loads(args.plan.read_text(encoding="utf-8")) if args.plan else load_plan(args.case, args.reference)
report = rehearse(args.case, plan)
output = json.dumps(report, ensure_ascii=False, indent=2)
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output + "\n", encoding="utf-8")
print(f"{report['status'].upper()}: {report['passed']}/{report['total']} rollout probes; "
      f"same-version baseline {report['baseline']['passed']}/{report['baseline']['total']}; "
      f"plan {report['plan_hash'][:12]}")
if report['witness']:
    print("Witness:", " -> ".join(e['action'] for e in report['witness']['trace']))
    print(report['witness']['failure']['message'])
sys.exit(0 if report["status"] == "pass" else 1)
