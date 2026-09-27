import argparse
import json
import subprocess
import sys
from pathlib import Path
from .engine import load_case, load_plan
from .bundle import render_bundle, render_comparison_bundle
from .reporting import render_markdown, render_reproduction, has_reproducible_data_gap
from .service import WORKER_TIMEOUT_SECONDS, run_rehearsal, run_selected_replay, verify_report_against_replay
from .selected_replay import IDENTITIES

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(errors='backslashreplace')

parser = argparse.ArgumentParser(description="Rehearse old/new application contracts on disposable SQLite databases.")
parser.add_argument("--case", choices=["parcel", "contacts"], default="parcel")
parser.add_argument("--reference", choices=["rename", "backfill", "late_bridge", "bridge"], default="rename")
parser.add_argument("--plan", type=Path, help="Candidate plan JSON. Overrides --reference.")
parser.add_argument("--migration-file", type=Path, help="UTF-8 .sql file overriding only the candidate migration; requires --plan.")
parser.add_argument("--contract", type=Path, help="A bounded SQL contract JSON; requires --plan.")
parser.add_argument("--output", type=Path)
parser.add_argument("--markdown", type=Path, help="Review-ready Markdown from the same executed report.")
parser.add_argument("--repro", type=Path, help="Standalone Python replay of a failing data mismatch witness.")
parser.add_argument("--selected-probe", help="Exact failed probe ID for --markdown/--repro; report and bundle retain the canonical suite witness.")
parser.add_argument("--bundle", type=Path, help="ZIP with inputs, executed evidence, review and any replayable witness.")
parser.add_argument("--ci-kit", type=Path, help="Independently audited passing custom-contract PR gate kit, generated entirely locally.")
parser.add_argument("--ci-control", type=Path, help="Optional unsafe plan JSON for the local CI kit; must independently reproduce a data mismatch under the same contract.")
parser.add_argument("--baseline-plan", type=Path, help="Rerun this plan locally against the same contract and export both independently audited reports in --bundle.")
parser.add_argument("--baseline-migration-file", type=Path, help="UTF-8 .sql file overriding the baseline migration; requires --baseline-plan.")
args = parser.parse_args()
if args.baseline_migration_file and not args.baseline_plan:
    parser.error("--baseline-migration-file requires --baseline-plan")
if args.baseline_plan and not args.bundle:
    parser.error("--baseline-plan requires --bundle")
if args.ci_kit and not args.contract:
    parser.error("--ci-kit requires --contract and --plan")
if args.ci_control and not args.ci_kit:
    parser.error("--ci-control requires --ci-kit")
if args.selected_probe and not (args.markdown or args.repro):
    parser.error("--selected-probe requires --markdown or --repro")
if args.migration_file and not args.plan:
    parser.error("--migration-file requires a candidate --plan for its application queries")
if args.contract and not args.plan:
    parser.error("--contract requires a candidate --plan")
if args.contract and args.case != 'parcel':
    parser.error("--case selects a bundled example and cannot be combined with --contract")
destinations = [path.resolve() for path in (args.output, args.markdown, args.repro, args.bundle, args.ci_kit) if path]
if len(destinations) != len(set(destinations)):
    parser.error("Evidence outputs must be different files")
inputs = {path.resolve() for path in (args.contract, args.plan, args.migration_file, args.ci_control, args.baseline_plan, args.baseline_migration_file) if path}
for destination in (args.output, args.markdown, args.repro, args.bundle, args.ci_kit):
    if destination and destination.resolve() in inputs:
        parser.error("Evidence outputs cannot overwrite a contract, candidate plan or migration source")
if args.baseline_plan and args.bundle.exists():
    parser.error("Comparison output already exists; choose a new file")
if args.ci_kit and args.ci_kit.exists():
    parser.error("CI kit output already exists; choose a new file")


def read_json(path, label):
    try:
        if path.stat().st_size > 65536:
            parser.error(f"{label} JSON must be at most 64 KiB")
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot read {label} JSON: {exc}")


def with_migration_file(plan, path):
    if path is None:
        return plan
    try:
        if path.stat().st_size > 65536:
            parser.error("Migration SQL must be at most 64 KiB")
        sql = path.read_bytes().decode('utf-8-sig')
        if not sql.strip() or '\0' in sql or len(sql) > 12000:
            parser.error("Expected nonempty UTF-8 migration SQL without NUL characters, up to 12,000 characters")
        if not isinstance(plan, dict):
            parser.error("Candidate plan must be a JSON object")
        return dict(plan, migration=sql, name=f'Imported SQL: {path.name}'[:100])
    except (OSError, UnicodeError) as exc:
        parser.error(f"Cannot read migration SQL: {exc}")


contract = read_json(args.contract, 'Contract') if args.contract else None
plan = with_migration_file(read_json(args.plan, 'Plan') if args.plan else load_plan(args.case, args.reference),
                           args.migration_file)
baseline_plan = (with_migration_file(read_json(args.baseline_plan, 'Baseline plan'), args.baseline_migration_file)
                 if args.baseline_plan else None)

try:
    report = run_rehearsal('custom' if contract is not None else args.case, plan, contract)
except subprocess.TimeoutExpired:
    parser.error(f'Rehearsal exceeded its {WORKER_TIMEOUT_SECONDS} second budget; no verdict was produced')
except ValueError as exc:
    parser.error(str(exc))
kit = None
if args.ci_kit:
    try:
        from .ci_kit import render_ci_kit
        if report['status'] != 'pass':
            raise ValueError('CI kit requires a passing candidate; no kit was written')
        verify_report_against_replay('custom', plan, report, contract)
        control = None
        if args.ci_control:
            control_plan = read_json(args.ci_control, 'Unsafe control')
            control = run_rehearsal('custom', control_plan, contract)
            if (control['status'] != 'blocked' or not control.get('witness') or
                    control['witness']['failure']['kind'] != 'data_mismatch' or
                    any(control[key] != report[key] for key in
                        ('contract_hash', 'engine_sha256', 'suite_hash'))):
                raise ValueError('CI control must reproduce a comparable blocked data mismatch')
            verify_report_against_replay('custom', control_plan, control, contract)
        kit, kit_slug = render_ci_kit(report, contract, control)
    except (ValueError, subprocess.TimeoutExpired) as exc:
        parser.error(f'Local CI kit not verified: {exc}')
try:
    selected_export = None
    if args.selected_probe:
        probe = next((item for item in report['results'] if item['id'] == args.selected_probe), None)
        if probe is None:
            raise ValueError('Selected probe is not present in the executed report')
        selected_export = run_selected_replay('custom' if contract is not None else args.case, plan,
                                             args.selected_probe, {key: report[key] for key in IDENTITIES},
                                             probe, contract, review_only=not args.repro)
    if args.repro and not selected_export and not has_reproducible_data_gap(report):
        raise ValueError('Recorded rows contain no reproducible data gap. Export the full review bundle or Markdown to retain this reader-contract failure.')
    reproduction = (selected_export['script'] if selected_export else
                    render_reproduction(report, contract if contract is not None else load_case(args.case))) if args.repro else None
except subprocess.TimeoutExpired:
    parser.error('Selected replay exceeded its worker budget; no selected evidence was exported')
except ValueError as exc:
    parser.error(str(exc))
try:
    if args.baseline_plan:
        baseline = run_rehearsal('custom' if contract is not None else args.case, baseline_plan, contract)
        for executed in (baseline, report):
            verify_report_against_replay('custom' if contract is not None else args.case,
                                         executed['plan'], executed, contract)
        bundle = render_comparison_bundle(baseline, report, contract if contract is not None else load_case(args.case))
    else:
        bundle = render_bundle(report, contract if contract is not None else load_case(args.case)) if args.bundle else None
except (ValueError, subprocess.TimeoutExpired) as exc:
    parser.error(f'Local comparison not verified: {exc}')
output = json.dumps(report, ensure_ascii=False, indent=2)
try:
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes((output + "\n").encode("utf-8"))
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_bytes((selected_export['review_markdown'] if selected_export else render_markdown(report)).encode("utf-8"))
    if args.repro:
        args.repro.parent.mkdir(parents=True, exist_ok=True)
        args.repro.write_bytes(reproduction.encode("utf-8"))
    if args.bundle:
        args.bundle.parent.mkdir(parents=True, exist_ok=True)
        if args.baseline_plan:
            with args.bundle.open('xb') as target:
                target.write(bundle)
        else:
            args.bundle.write_bytes(bundle)
except OSError as exc:
    parser.error(f'Cannot export evidence: {exc}')
if args.baseline_plan:
    print(f"Independently replayed comparison saved to {args.bundle}: baseline {baseline['status']} {baseline['passed']}/{baseline['total']} -> candidate {report['status']} {report['passed']}/{report['total']}")
if kit is not None:
    try:
        args.ci_kit.parent.mkdir(parents=True, exist_ok=True)
        with args.ci_kit.open('xb') as target:
            target.write(kit)
    except OSError as exc:
        parser.error(f'Cannot write new CI kit: {exc}')
    print(f"Local PR gate kit: {args.ci_kit}; independently replayed; {kit_slug}")
print(f"{report['status'].upper()}: {report['passed']}/{report['total']} rollout and window probes; "
      f"same-version baseline {report['baseline']['passed']}/{report['baseline']['total']}; "
      f"plan {report['plan_hash'][:12]}")
if report['witness']:
    if selected_export:
        print(f"Selected Markdown/replay export: {selected_export['probe_id']}")
        print(f"Canonical suite witness (report/bundle): {report['witness']['id']}")
    print("Suite witness:" if selected_export else "Witness:",
          " -> ".join(e['action'] for e in report['witness']['trace']))
    print(report['witness']['failure']['message'])
sys.exit(0 if report["status"] == "pass" else 1)
