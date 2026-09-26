import hashlib
import json
import os
from pathlib import Path

name = os.environ['CONTROL_NAME']
base = Path('control/witness-source')
expected = next(case for case in json.loads((base / 'expected.json').read_text()) if case['name'] == name)
out = Path('control-output') / name
verdict = json.loads((out / 'verdict.json').read_text())
report = json.loads((out / 'report.json').read_text())
assert os.environ['ACTION_CLASSIFICATION'] == expected['classification'] == verdict['classification']
assert os.environ['ACTION_COVERAGE'] == expected['coverage'] == f"{report['passed']}/{report['total']}"
assert os.environ['ACTION_OUTCOME'] == expected['outcome']
assert verdict['contract_lock']['status'] == 'matched'
assert verdict['contract_lock']['expected'] == expected['lock'] == report['contract_hash']
summary = (out / 'summary.md').read_text()
sql = base / name / 'migration.sql'
assert verdict['migration_source']['sha256'] == hashlib.sha256(sql.read_bytes()).hexdigest()
if expected['line'] is not None:
    source = verdict['witness_source']
    assert source['line'] == 8 == expected['line']
    assert source['after_statement'] == 2 and source['statement_count'] == 5
    assert source['operation'] == 'old.write'
    assert source['probe_id'] == report['witness']['id'] == 'window_write_after_2-0'
    assert source['path'] == sql.as_posix()
    assert source['sql_file_sha256'] == verdict['migration_source']['sha256']
    assert sql.read_text().splitlines()[source['line'] - 1] == 'SET fulfillment_bin = pick_bin;'
    assert 'Observed old.write after SQL statement 2 of 5 (SQL line 8).' in summary
    assert 'not a claim that this SQL line alone caused the defect.' in summary
else:
    assert 'witness_source' not in verdict
    assert 'Replay location:' not in summary
for required in ('report.json', 'review.md', 'review.zip', 'summary.md', 'verdict.json', 'effective-plan.json', 'action.json'):
    assert (out / required).is_file()
print(f"Verified prospective {name}: {expected['classification']} {expected['coverage']}; source line {expected['line']}")
