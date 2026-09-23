import json
import subprocess
import sys
from .engine import ROOT, load_case, load_plan, repair_brief, validate_plan


def run_rehearsal(case, plan):
    load_case(case)
    validate_plan(plan)
    process = subprocess.run([sys.executable, '-m', 'cutover.worker'],
                             input=json.dumps({'case': case, 'plan': plan}),
                             capture_output=True, text=True, encoding='utf-8', cwd=ROOT,
                             timeout=8, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if process.returncode:
        raise ValueError('Rehearsal worker failed; no passing result was produced.')
    return json.loads(process.stdout)


def catalog():
    return {'cases': [{'id': name, **load_case(name),
                       'plans': {p: load_plan(name, p) for p in ('rename', 'backfill', 'late_bridge', 'bridge')}}
                      for name in ('parcel', 'contacts')]}
