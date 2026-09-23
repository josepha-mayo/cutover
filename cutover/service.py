import json
import subprocess
import sys
from .engine import ROOT, load_case, load_plan, repair_brief, validate_contract, validate_plan

WORKER_TIMEOUT_SECONDS = 30


def run_rehearsal(case, plan, contract=None):
    if contract is None:
        load_case(case)
    else:
        if case != 'custom':
            raise ValueError('Imported contracts require case=custom')
        validate_contract(contract)
    validate_plan(plan)
    return run_worker({'case': case, 'plan': plan, 'contract': contract})


def validate_imported_contract(contract):
    validate_contract(contract)
    return run_worker({'operation': 'validate_contract', 'contract': contract})


def run_worker(request):
    process = subprocess.run([sys.executable, '-m', 'cutover.worker'],
                             input=json.dumps(request),
                             capture_output=True, text=True, encoding='utf-8', cwd=ROOT,
                             timeout=WORKER_TIMEOUT_SECONDS,
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
    fresh = run_rehearsal(case, plan, contract)
    deterministic_fields = (
        'schema_version', 'engine_version', 'engine_sha256', 'case', 'project',
        'plan', 'plan_hash', 'contract_hash', 'suite_hash', 'status', 'passed',
        'failed', 'total', 'baseline', 'categories', 'witness', 'results',
        'scope', 'limitations',
    )
    for field in deterministic_fields:
        if report.get(field) != fresh.get(field):
            raise ValueError(f'Candidate report differs from a fresh replay: {field}')


def catalog():
    return {'cases': [{'id': name, **load_case(name),
                       'plans': {p: load_plan(name, p) for p in ('rename', 'backfill', 'late_bridge', 'bridge')}}
                      for name in ('parcel', 'contacts')]}
