"""Locate an observed migration boundary in the exact SQL supplied to the gate.

This is a replay location, not an inference about which line caused the defect.
Keep it outside the evaluator: source presentation must not change probe results.
"""
import re

from cutover.engine import migration_statements


def window_source(report, source):
    if not source or not isinstance(report, dict):
        return None
    witness = report.get('witness') or {}
    match = re.fullmatch(r'window_(write|insert)_after_(\d+)-\d+', witness.get('id', ''))
    if not match:
        return None
    script = (report.get('plan') or {}).get('migration')
    if not isinstance(script, str):
        return None
    try:
        statements = migration_statements(script)
    except ValueError:
        return None
    boundary = int(match[2])
    if not 0 <= boundary <= len(statements):
        return None
    operation = 'old.' + match[1]
    trace = witness.get('trace') or []
    injected = next((index for index, event in enumerate(trace)
                     if event.get('action') == operation), None)
    if injected is None:
        return None
    prefix = [event for event in trace[:injected]
              if str(event.get('action', '')).startswith('migration.statement.')]
    # The probe name alone is not enough: the recorded execution must establish it.
    if len(prefix) != boundary or any(
            event.get('action') != f'migration.statement.{index}' or
            event.get('sql') != statements[index] or event.get('status') != 'pass'
            for index, event in enumerate(prefix)):
        return None
    spans, cursor = [], 0
    for statement in statements:
        start = script.find(statement, cursor)
        if start < 0:
            return None
        end = start + len(statement)
        spans.append((script.count('\n', 0, start) + 1,
                      script.count('\n', 0, end - 1) + 1))
        cursor = end
    anchor = boundary - 1 if boundary else 0
    start_line, end_line = spans[anchor]
    return {
        'kind': 'observed_migration_boundary',
        'probe_id': witness['id'],
        'operation': operation,
        'after_statement': boundary,
        'statement_count': len(statements),
        'path': source['path'],
        'sql_file_sha256': source['sha256'],
        'line': end_line if boundary else start_line,
        'statement_start_line': start_line,
        'statement_end_line': end_line,
        'sql_context': statements[anchor],
    }


def describe(location):
    position = (f"after SQL statement {location['after_statement']} of {location['statement_count']}"
                if location['after_statement'] else 'before SQL statement 1')
    return f"Observed {location['operation']} {position} (SQL line {location['line']})."
