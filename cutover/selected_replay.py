"""Fresh, complete observations for one selected failure, inside the worker."""
import copy
import json

from .engine import load_case, migration_statements, rehearse, replay
from .reporting import render_reproduction


IDENTITIES = ('plan_hash', 'contract_hash', 'engine_sha256', 'suite_hash')


def rehearse_selected(case, plan, probe_id, identities, observed_probe, contract=None):
    if not isinstance(probe_id, str) or not probe_id:
        raise ValueError('Select a probe from the executed report')
    if contract is not None and case != 'custom':
        raise ValueError('Imported contracts require case=custom')
    report = rehearse(case, plan, contract)
    if any(report[key] != identities[key] for key in IDENTITIES):
        raise ValueError('Fresh replay differs from the displayed evidence. Rerun the candidate.')
    probe = next((row for row in report['results'] if row['id'] == probe_id), None)
    if probe is None:
        raise ValueError('Select a probe from the executed report')
    if probe['passed'] or (probe.get('failure') or {}).get('kind') not in ('data_mismatch', 'target_mismatch'):
        raise ValueError('A failing data mismatch witness is required for a runnable reproduction')
    if json.loads(json.dumps(probe)) != observed_probe:
        raise ValueError('Fresh selected failure differs from the displayed evidence. Rerun the candidate.')

    source = contract if contract is not None else load_case(case)
    # The matrix compacts passing observations. Execute this exact retained path
    # again to obtain them; never fill them with assumed ledger values.
    repeated = replay(source, plan, probe['actions'], probe['payload'],
                      migration_statements(plan['migration']), probe.get('seed_id'),
                      probe.get('insert_id'), probe.get('write_targets'))
    compact_trace = copy.deepcopy(repeated['trace'])
    for event in compact_trace:
        if event['status'] == 'pass':
            event.pop('expected', None)
            event.pop('actual', None)
    if (repeated['passed'] != probe['passed'] or repeated['failure'] != probe['failure'] or
            compact_trace != probe['trace']):
        raise ValueError('The selected failure changed on replay. No reproduction was exported.')

    # Keep the suite's canonical shortest witness and all packet formats intact.
    selected = {**probe, **repeated}
    script = render_reproduction({**report, 'witness': selected}, source, ascii_output=True)
    return {**{key: report[key] for key in IDENTITIES}, 'probe_id': probe_id, 'script': script}
