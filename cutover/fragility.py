"""Challenge a passing migration by omitting each executed SQL statement once."""

import subprocess

from .engine import migration_statements
from .service import run_rehearsal


def challenge_steps(case, plan, contract, expected_plan_hash, expected_contract_hash):
    original = run_rehearsal(case, plan, contract, timeout_seconds=10)
    if (original['plan_hash'] != expected_plan_hash or
            original['contract_hash'] != expected_contract_hash):
        raise ValueError('Fresh rehearsal differs from the displayed candidate')
    if original['status'] != 'pass':
        raise ValueError('Challenge requires a passing candidate')
    statements = migration_statements(plan['migration'])
    if not 2 <= len(statements) <= 8:
        raise ValueError('Challenge supports passing migrations with 2 to 8 statements')

    challenges = []
    for index, statement in enumerate(statements):
        altered = {**plan, 'name': f'Omit migration step {index + 1}',
                   'migration': '\n'.join(sql for position, sql in enumerate(statements)
                                          if position != index)}
        entry = {'step': index + 1, 'sql': statement, 'plan': altered}
        try:
            result = run_rehearsal(case, altered, contract, timeout_seconds=10)
        except subprocess.TimeoutExpired:
            entry.update(outcome='unreplayable', reason='This omission exceeded its 10-second challenge budget')
        except ValueError as exc:
            entry.update(outcome='unreplayable', reason=str(exc))
        else:
            entry.update(outcome='blocked' if result['status'] == 'blocked' else 'still_passes',
                         passed=result['passed'], total=result['total'],
                         plan_hash=result['plan_hash'])
            if result['witness']:
                witness = result['witness']
                entry['witness'] = {
                    'id': witness['id'], 'title': witness['title'],
                    'payload': witness.get('payload'),
                    'failure': witness['failure'],
                    'trace': [event for event in witness['trace']
                              if event.get('status') == 'fail'][:1],
                }
        challenges.append(entry)
    return {
        'case': case, 'plan_hash': original['plan_hash'],
        'contract_hash': original['contract_hash'],
        'original': {'passed': original['passed'], 'total': original['total']},
        'challenges': challenges,
        'scope': ('Each run removes one complete SQLite migration statement and reruns '
                  'the bounded suite. Probe totals change with statement boundaries. '
                  'A still-passing omission is only redundant under these tested schedules; '
                  'an unreplayable omission is not a verified data-loss witness.'),
    }
