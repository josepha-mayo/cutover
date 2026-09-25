import json
import subprocess
import sys
from .engine import ROOT, load_case, load_plan, repair_brief, validate_contract, validate_plan
from .reporting import render_markdown, render_reproduction

WORKER_TIMEOUT_SECONDS = 90


def run_rehearsal(case, plan, contract=None, timeout_seconds=WORKER_TIMEOUT_SECONDS):
    if contract is None:
        load_case(case)
    else:
        if case != 'custom':
            raise ValueError('Imported contracts require case=custom')
        validate_contract(contract)
    validate_plan(plan)
    return run_worker({'case': case, 'plan': plan, 'contract': contract}, timeout_seconds)


def validate_imported_contract(contract):
    validate_contract(contract)
    return run_worker({'operation': 'validate_contract', 'contract': contract})


def run_worker(request, timeout_seconds=WORKER_TIMEOUT_SECONDS):
    process = subprocess.run([sys.executable, '-m', 'cutover.worker'],
                             input=json.dumps(request),
                             capture_output=True, text=True, encoding='utf-8', cwd=ROOT,
                             timeout=timeout_seconds,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if process.returncode:
        if process.returncode == 2:
            try:
                error = json.loads(process.stdout).get('error')
                if isinstance(error, str) and error:
                    raise ValueError(error)
            except json.JSONDecodeError:
                pass
        raise ValueError('Rehearsal worker failed; no passing result was produced.')
    return json.loads(process.stdout)


def verify_report_against_replay(case, plan, report, contract=None):
    """Reject a final artifact whose claimed evidence differs from a fresh worker run."""
    if not isinstance(report, dict):
        raise ValueError('Candidate report must be a JSON object')
    fresh = run_rehearsal(case, plan, contract)
    presentation_fields = {'review_markdown', 'reproduction_python'}
    if (fresh.keys() - report.keys() or
            report.keys() - fresh.keys() - presentation_fields):
        raise ValueError('Candidate report fields differ from a fresh replay')
    # Time, duration and the host SQLite version are observations, not claims
    # that can be reproduced on a different machine. All evidence and Bob
    # attribution fields, including the shown passing replay, must match.
    for field in fresh:
        if field in ('created_at', 'duration_ms', 'sqlite_version'):
            continue
        if report.get(field) != fresh.get(field):
            raise ValueError(f'Candidate report differs from a fresh replay: {field}')
    if 'review_markdown' in report and report['review_markdown'] != render_markdown(report):
        raise ValueError('Candidate report differs from its rendered Markdown review')
    if 'reproduction_python' in report:
        try:
            reproduction = render_reproduction(report, contract if contract is not None else load_case(case))
        except ValueError as exc:
            raise ValueError('Candidate report has no replayable data mismatch witness') from exc
        if report['reproduction_python'] != reproduction:
            raise ValueError('Candidate report differs from its standalone reproduction')


def catalog():
    return {'cases': [{'id': name, **load_case(name),
                       'plans': {p: load_plan(name, p) for p in ('rename', 'backfill', 'late_bridge', 'bridge', 'cross_record')}}
                      for name in ('parcel', 'contacts')]}
