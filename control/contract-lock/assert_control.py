"""Check actual Action outputs and retained artifacts against prospective cases."""
import hashlib
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[2]
inputs = root / 'control/contract-lock'
case = next(case for case in json.loads((inputs / 'expected.json').read_text())
            if case['name'] == os.environ['CONTROL_NAME'])
out = root / 'control-output' / case['name']
verdict = json.loads((out / 'verdict.json').read_text())
assert verdict['classification'] == case['classification'], verdict
assert os.environ['ACTION_CLASSIFICATION'] == case['classification']
assert os.environ['ACTION_COVERAGE'] == case['coverage']
assert os.environ['ACTION_OUTCOME'] == case['outcome']
summary = (out / 'summary.md').read_text()
assert case['classification'].upper() in summary
if case['classification'] == 'unverified':
    assert verdict['cli_exit'] is None and verdict['audit_exit'] is None
    assert verdict['contract_lock']['status'] == 'changed'
    assert verdict['contract_lock']['expected'] == case['lock']
    assert 'Contract changed' in verdict['reason']
    assert not (out / 'report.json').exists()
    assert not (out / 'review.zip').exists()
else:
    report = json.loads((out / 'report.json').read_text())
    assert f"{report['passed']}/{report['total']}" == case['coverage']
    assert verdict['migration_source']['sha256'] == hashlib.sha256((inputs / case['sql']).read_bytes()).hexdigest()
    assert (out / 'review.zip').is_file()
    if case['lock']:
        assert verdict['contract_lock']['status'] == 'matched'
        assert report['contract_hash'] == case['lock']
print(json.dumps({'control': case['name'], 'classification': verdict['classification'],
                  'coverage': case['coverage'], 'prospective_expectation_met': True}))
