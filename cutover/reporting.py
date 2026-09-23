"""Review-ready Markdown from an already executed Cutover report."""

from __future__ import annotations

import json
import re


def inline(value):
    """Keep untrusted labels from becoming Markdown or HTML structure."""
    return (str(value).replace('\r', ' ').replace('\n', ' ').replace('\\', '\\\\')
            .replace('`', '\\`').replace('*', '\\*').replace('_', '\\_')
            .replace('[', '\\[').replace(']', '\\]')
            .replace('<', '&lt;').replace('>', '&gt;').replace('|', '\\|'))


def fenced(value, language='text'):
    body = str(value).rstrip('\n')
    longest = max((len(match.group()) for match in re.finditer(r'~+', body)), default=0)
    marker = '~' * max(3, longest + 1)
    return f'{marker}{language}\n{body}\n{marker}'


def structured(value):
    return fenced(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), 'json')


def render_reproduction(report, contract):
    """Export a standalone, in-memory Python replay of an observed data gap."""
    witness = report.get('witness')
    kind = witness.get('failure', {}).get('kind') if witness else None
    if kind not in ('data_mismatch', 'target_mismatch'):
        raise ValueError('A failing data mismatch witness is required for a runnable reproduction')
    steps = [{key: event[key] for key in ('action', 'status', 'sql', 'params', 'expected', 'actual')
              if key in event} for event in witness['trace']]
    constants = ('#!/usr/bin/env python3\n'
                 '# Cutover standalone witness. Runs candidate SQL in disposable in-memory SQLite.\n'
                 'import json\nimport sqlite3\nimport time\n\n'
                 f'PROBE = {witness["id"]!r}\n'
                 f'FAILURE_KIND = {kind!r}\n'
                 f'PLAN_HASH = {report["plan_hash"]!r}\n'
                 f'SCHEMA = {contract["schema"]!r}\n'
                 f'SEED_SQL = {contract["seed_sql"]!r}\n'
                 f'SEED = {contract["seed"]!r}\n'
                 f'STEPS = {steps!r}\n\n')
    runner = '''def reproduce():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA recursive_triggers=ON')
    denied = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA,
              sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT}

    def authorize(action, a, b, database, source):
        if action in denied or (action == sqlite3.SQLITE_FUNCTION and
                                str(b).lower() in ('load_extension', 'writefile', 'readfile')):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    db.set_authorizer(authorize)
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1000000)
    db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 20000)
    db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    deadline = time.monotonic() + 3
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        db.executescript(SCHEMA)
        db.executemany(SEED_SQL, SEED)
        for step in STEPS:
            action = step['action']
            if action == 'migrate' or action.startswith('migration.statement.'):
                db.executescript(step['sql'])
            elif action.endswith('.write') or action.endswith('.insert'):
                count = db.execute(step['sql'], step['params']).rowcount
                if count != 1:
                    raise AssertionError(f'{action} affected {count} records instead of one')
            else:
                rows = db.execute(step['sql']).fetchmany(100)
                actual = {str(row['id']): row['value'] for row in rows}
                recorded = {str(key): value for key, value in step['actual'].items()}
                expected = {str(key): value for key, value in step['expected'].items()}
                if actual != recorded:
                    raise AssertionError(f'{action} no longer matches the recorded observation')
                if step['status'] == 'fail':
                    if actual == expected:
                        raise AssertionError('The recorded data gap is no longer reproducible')
                    print(json.dumps({'status': 'REPRODUCED', 'probe': PROBE,
                                      'failure_kind': FAILURE_KIND, 'plan_hash': PLAN_HASH,
                                      'expected': expected, 'actual': actual,
                                      'sqlite_version': sqlite3.sqlite_version},
                                     ensure_ascii=False, sort_keys=True))
                    return
                if actual != expected:
                    raise AssertionError(f'{action} diverged before the recorded failure')
        raise AssertionError('The recorded failure step was not reached')
    finally:
        db.close()


if __name__ == '__main__':
    reproduce()
'''
    return constants + runner


def replay_section(probe, title):
    lines = [f'## {title}', '',
             f'Probe: **`{probe["id"]}`** — {inline(probe["title"])}', '',
             'Input:', '', structured(probe['payload']), '']
    if 'seed_id' in probe:
        lines += [f'Row shown in this replay: `{probe["seed_id"]}`.', '',
                  'Seed IDs checked before this verdict:', '', structured(probe['seed_ids_tested']), '']
    if 'insert_id' in probe:
        lines += [f'Inserted ID shown in this replay: `{probe["insert_id"]}`.', '',
                  'Insert IDs checked before this verdict:', '', structured(probe['insert_ids_tested']), '']
    for event in probe['trace']:
        lines += [f'### {event["step"]}. {inline(event["action"])} — {inline(event["status"])}', '']
        if event.get('sql'):
            lines += ['Executed SQL:', '', fenced(event['sql'], 'sql'), '']
        if event.get('params'):
            lines += ['Bound inputs:', '', structured(event['params']), '']
        if 'expected' in event:
            lines += ['Expected ledger:', '', structured(event['expected']), '',
                      'Observed:', '', structured(event['actual']), '']
        if event.get('detail'):
            lines += [inline(event['detail']), '']
    if probe.get('failure'):
        lines += [f'Failure: **{inline(probe["failure"]["kind"])}** — '
                  f'{inline(probe["failure"]["message"])}', '']
    return lines


def render_markdown(report):
    """Render the report object returned by a real rehearsal, without rerunning SQL."""
    if report.get('status') not in ('pass', 'blocked') or not isinstance(report.get('results'), list):
        raise ValueError('Expected a complete executed Cutover report')
    completed = [row for row in report['categories'] if row['id'] != 'migration_window']
    windows = next((row for row in report['categories'] if row['id'] == 'migration_window'), None)
    completed_passed = sum(row['passed'] for row in completed)
    completed_total = sum(row['total'] for row in completed)
    lines = [f'# Cutover review: {inline(report["plan"]["name"])}', '',
             f'**Verdict:** {report["status"].upper()} — '
             f'{report["passed"]}/{report["total"]} rollout and window probes passed.', '',
             f'**Contract:** {inline(report["project"])} (`{inline(report["case"])}`)', '',
             '| Evidence group | Passed | Total |', '| --- | ---: | ---: |',
             f'| Same-version baseline | {report["baseline"]["passed"]} | {report["baseline"]["total"]} |',
             f'| Completed rollout | {completed_passed} | {completed_total} |']
    if windows:
        lines.append(f'| Migration-statement windows | {windows["passed"]} | {windows["total"]} |')
    lines += ['', 'The baseline is separate from the rollout total. Each probe executes against a fresh '
              'disposable SQLite database and checks acknowledged values against an independent ledger.', '']

    if report['witness']:
        lines += replay_section(report['witness'], 'Shortest observed failing replay')
    else:
        example = next((row for row in report['results']
                        if row['category'] == 'migration_window' and row['passed']), None)
        if example:
            lines += replay_section(example, 'Example passing migration-window replay')
        lines += ['**A pass is bounded to this suite; it is not a deployment approval.**', '']

    lines += ['## Evidence identity', '',
              f'- Plan SHA-256: `{report["plan_hash"]}`',
              f'- Contract SHA-256: `{report["contract_hash"]}`',
              f'- Suite SHA-256: `{report["suite_hash"]}`',
              f'- Engine SHA-256: `{report["engine_sha256"]}`',
              f'- SQLite version: `{inline(report["sqlite_version"])}`',
              f'- Generated UTC: `{inline(report["created_at"])}`', '',
              '## Scope and limits', '', inline(report['scope']), '']
    lines += [f'- {inline(item)}' for item in report['limitations']]
    lines += ['', 'This report documents executed SQL only. It does not establish IBM Bob authorship, '
              'production safety, or behavior outside the reported contract and schedules.', '']
    return '\n'.join(lines)
