"""Package one executed rehearsal and its inputs for a release review."""

import io
import json
import zipfile

from .reporting import render_markdown, render_reproduction


def render_bundle(report, contract):
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
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode('utf-8'))
    return output.getvalue()
