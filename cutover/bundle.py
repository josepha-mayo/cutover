"""Package one executed rehearsal and its inputs for a release review."""

import io
import json
import zipfile

from .reporting import render_markdown, render_reproduction


def bundle_files(report, contract):
    case = report['case']
    audit = ('python -m cutover.audit_report --contract contract.json --plan plan.json --report report.json'
             if case == 'custom' else
             f'python -m cutover.audit_report --case {case} --plan plan.json --report report.json')
    readme = (
        '# Cutover release review\n\n'
        f"Verdict: {report['status'].upper()} ({report['passed']}/{report['total']} probes)\n"
        f"Plan SHA-256: {report['plan_hash']}\n"
        f"Contract SHA-256: {report['contract_hash']}\n"
        f"Engine SHA-256: {report['engine_sha256']}\n\n"
        'The JSON and Markdown record one executed rehearsal. From a checkout of the\n'
        'Cutover source with the matching engine hash, rerun every replayable claim:\n\n'
        f'    {audit}\n\n'
        'Exit 0 means verified pass, 1 means verified block, and 2 means unverified.\n'
        'A passing report is bounded evidence, not deployment approval. The archive\n'
        'is not signed; creation time, runtime and host SQLite version are self-reported.\n'
    )
    files = {
        'README.md': readme,
        'contract.json': json.dumps(contract, ensure_ascii=False, indent=2) + '\n',
        'plan.json': json.dumps(report['plan'], ensure_ascii=False, indent=2) + '\n',
        'report.json': json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        'review.md': render_markdown(report),
    }
    witness = report.get('witness')
    if witness and witness['failure']['kind'] in ('data_mismatch', 'target_mismatch'):
        files['witness.py'] = render_reproduction(report, contract)
        files['README.md'] += '\nRun `python -I witness.py` to reproduce the recorded data gap.\n'
    return files


def render_bundle(report, contract):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in bundle_files(report, contract).items():
            archive.writestr(name, content.encode('utf-8'))
    return output.getvalue()


def render_comparison_bundle(before, after, contract):
    """Package two fresh reports without pretending distinct SQL boundaries pair."""
    for key in ('case', 'contract_hash', 'engine_sha256', 'suite_hash'):
        if before[key] != after[key]:
            raise ValueError(f'Cannot compare reports with different {key}')
    same_migration = before['plan']['migration'] == after['plan']['migration']
    old_by_id = {item['id']: item for item in before['results']
                 if same_migration or item['category'] != 'migration_window'}
    paired = resolved = regressed = 0
    resolved_ids = []
    regressed_ids = []
    for item in after['results']:
        if not same_migration and item['category'] == 'migration_window':
            continue
        old = old_by_id.get(item['id'])
        if not old or old['payload'] != item['payload'] or old['actions'] != item['actions']:
            continue
        paired += 1
        if not old['passed'] and item['passed']:
            resolved += 1
            resolved_ids.append(item['id'])
        if old['passed'] and not item['passed']:
            regressed += 1
            regressed_ids.append(item['id'])
    windows = []
    for report in (before, after):
        category = next(item for item in report['categories'] if item['id'] == 'migration_window')
        windows.append({'failed': category['total'] - category['passed'],
                        'total': category['total']})
    summary = {
        'schema_version': 1,
        'case': before['case'],
        'contract_hash': before['contract_hash'],
        'engine_sha256': before['engine_sha256'],
        'suite_hash': before['suite_hash'],
        'baseline_plan_hash': before['plan_hash'],
        'candidate_plan_hash': after['plan_hash'],
        'paired_probes': paired,
        'resolved_in_paired_probes': resolved,
        'regressed_in_paired_probes': regressed,
        'resolved_probe_ids': resolved_ids,
        'regressed_probe_ids': regressed_ids,
        'window_probes_paired': same_migration,
        'migration_window_failures': {'baseline': windows[0], 'candidate': windows[1]},
        'first_failed_window_probe': {
            label: next((item['id'] for item in report['results']
                         if item['category'] == 'migration_window' and not item['passed']), None)
            for label, report in (('baseline', before), ('candidate', after))
        },
        'interpretation': ('Statement-boundary probes were evaluated separately; '
                           'different SQL sequences cannot be paired by step number.'
                           if not same_migration else
                           'The same SQL sequence permits statement-boundary probe pairing.'),
    }
    readme = (
        '# Cutover before/after release review\n\n'
        'These are two independent, fresh SQL rehearsals of the same contract and evaluator.\n'
        'The `baseline/` and `candidate/` folders each contain a complete review packet.\n'
        'Run the audit command in each folder README from a checkout of Cutover with\n'
        'the matching engine hash. The auditor replays every retained claim.\n\n'
        f"Baseline: {before['status']} {before['passed']}/{before['total']} · {before['plan_hash']}\n"
        f"Candidate: {after['status']} {after['passed']}/{after['total']} · {after['plan_hash']}\n\n"
        'The comparison.json file counts paired probes only when their payload and\n'
        'action sequence match. Different migration SQL sequences have different\n'
        'statement boundaries, so their window failures are reported separately.\n'
        'A passing bounded SQLite rehearsal is not production deployment approval.\n'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('README.md', readme.encode('utf-8'))
        archive.writestr('comparison.json', (json.dumps(summary, indent=2) + '\n').encode('utf-8'))
        for label, report in (('baseline', before), ('candidate', after)):
            for name, content in bundle_files(report, contract).items():
                archive.writestr(f'{label}/{name}', content.encode('utf-8'))
    return output.getvalue()
