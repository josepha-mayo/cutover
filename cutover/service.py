import json
import subprocess
import sys
from .engine import ROOT, load_case, load_plan, repair_brief, validate_contract, validate_plan


def run_rehearsal(case, plan, contract=None):
    if contract is None:
        load_case(case)
    else:
        validate_contract(contract)
    validate_plan(plan)
    process = subprocess.run([sys.executable, '-m', 'cutover.worker'],
                             input=json.dumps({'case': case, 'plan': plan, 'contract': contract}),
                             capture_output=True, text=True, encoding='utf-8', cwd=ROOT,
                             timeout=8, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if process.returncode:
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
