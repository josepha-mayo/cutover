"""Fresh, complete observations for one selected failure, inside the worker."""
import copy
import json

from .engine import load_case, migration_statements, rehearse, replay
from .reporting import render_reproduction, replay_section, fenced


IDENTITIES = ('plan_hash', 'contract_hash', 'engine_sha256', 'suite_hash')


def row_observation_summary(trace):
    """Describe retained row observations without inferring missing database state."""
    event = next((step for step in trace if step['status'] == 'fail'
                  and isinstance(step.get('expected'), dict)
                  and isinstance(step.get('actual'), dict)), None)
    if event is None:
        return []
    expected, actual = event['expected'], event['actual']
    keys = list(dict.fromkeys([*expected, *actual]))
    changed = [key for key in keys if (key in expected) != (key in actual)
               or expected.get(key) != actual.get(key)]
    if not changed:
        return []
    def shown(values, key):
        if key not in values:
            return 'Row not returned'
        if values[key] is None:
            return 'SQL null'
        return json.dumps(values[key], ensure_ascii=False)
    rows = ['Row ' + json.dumps(str(key), ensure_ascii=False) + '\n'
            'Expected by contract: ' + shown(expected, key) + '\n'
            'Reader observed: ' + shown(actual, key) for key in changed]
    return ['## Recorded row difference', '',
            f'{len(changed)} mismatched row(s); {len(keys) - len(changed)} other recorded row(s) unchanged.', '',
            fenced('\n\n'.join(rows)), '',
            'This summary describes the failed reader observation. The full executed SQL and observations follow.', '']


def rehearse_selected(case, plan, probe_id, identities, observed_probe, contract=None, *, review_only=False):
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
    failed_read = next((event for event in probe['trace'] if event['status'] == 'fail'
                        and isinstance(event.get('expected'), dict)
                        and isinstance(event.get('actual'), dict)), None)
    eligible = ((probe.get('failure') or {}).get('kind') in ('data_mismatch', 'target_mismatch')
                and failed_read is not None and failed_read['expected'] != failed_read['actual'])
    if probe['passed'] or (not eligible and not review_only):
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
    script = render_reproduction({**report, 'witness': selected}, source, ascii_output=True) if eligible else None
    note = '\n'.join(['# Cutover selected failure review', '',
                      f'Suite result: {report["passed"]}/{report["total"]} probes passed.', '',
                      'This selected failure was freshly rerun and matched the displayed observation. '
                      'It is not necessarily the shortest witness. This note does not establish Bob authorship '
                      'or production safety.', '',
                      *(['Recorded row values agree, but the reader failed. Row maps do not retain duplicate '
                         'returned rows or prove adapter-contract compliance. Inspect the executed SQL and '
                         'replay the original packet to diagnose this failure.', '']
                        if failed_read is not None and failed_read['expected'] == failed_read['actual'] else []),
                      *row_observation_summary(selected['trace']),
                      *replay_section(selected, 'Selected executed failure'),
                      '## Evidence identity', '',
                      *[f'- {key}: `{report[key]}`' for key in IDENTITIES], ''])
    return {**{key: report[key] for key in IDENTITIES}, 'probe_id': probe_id,
            'script': script, 'review_markdown': note}
