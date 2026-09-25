"""Package one verified custom rehearsal for the repository's PR review gate."""
import io
import json
import re
import zipfile

from .reporting import render_markdown
from .reporting import render_reproduction


def render_ci_kit(report, contract, control=None):
    if report['case'] != 'custom' or report['status'] != 'pass':
        raise ValueError('A passing custom-contract rehearsal is required for a CI kit')
    part = re.sub(r'[^a-z0-9]+', '-', contract['project'].lower()).strip('-')[:25].strip('-')
    slug = f'release-{part or "scenario"}'
    contract_name = f'ci/{slug}-contract.json'
    plan_name = f'ci/{slug}-candidate.json'
    control_name = f'ci/{slug}-unsafe-control.json'
    entry = {'case': f'Custom {slug}', 'slug': slug,
             'contract': contract_name, 'plan': plan_name}
    readme = (
        '# Cutover CI handoff kit\n\n'
        f"Fresh rehearsal: PASS {report['passed']}/{report['total']} bounded probes.\n"
        f"Plan SHA-256: {report['plan_hash']}\n"
        f"Contract SHA-256: {report['contract_hash']}\n"
        f"Engine SHA-256: {report['engine_sha256']}\n\n"
        'From a checkout of the Cutover repository, verify this downloaded ZIP\n'
        'and preview the files it would add, then apply it explicitly:\n\n'
        '    python -m ci.install_kit --kit path/to/downloaded-kit.zip\n'
        '    python -m ci.install_kit --kit path/to/downloaded-kit.zip --apply\n\n'
        'The installer rejects path or slug collisions, independently replays\n'
        'the report (and unsafe control, if present), then adds only the passing\n'
        'inputs and one manifest entry. Or copy the two JSON files under `ci/`\n'
        'and append `manifest-entry.json` to `ci/cases.json` manually. Run:\n\n'
        '    python -m ci.discover_cases\n'
        f'    python -m cutover.audit_report --contract {contract_name} '
        f'--plan {plan_name} --report evidence/report.json\n\n'
        'Commit the files and open a PR. GitHub Actions will create a separate\n'
        'review job with retained evidence for this case. This kit contains\n'
        'freshly executed and independently replayed synthetic SQLite evidence,\n'
        'not deployment approval. Check\n'
        'the source SQL, privacy, dialect and operational rollback plan yourself.\n'
        'The archive is not signed; its self-reported timestamps are not proof\n'
        'of origin or IBM Bob authorship.\n'
    )
    files = {
        'README.md': readme,
        contract_name: json.dumps(contract, ensure_ascii=False, indent=2) + '\n',
        plan_name: json.dumps(report['plan'], ensure_ascii=False, indent=2) + '\n',
        'manifest-entry.json': json.dumps(entry, ensure_ascii=False, indent=2) + '\n',
        'evidence/report.json': json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        'evidence/review.md': render_markdown(report),
    }
    if control is not None:
        if (control['case'] != 'custom' or control['status'] != 'blocked' or
                control['contract_hash'] != report['contract_hash'] or
                control['engine_sha256'] != report['engine_sha256'] or
                control['suite_hash'] != report['suite_hash'] or
                control['witness']['failure']['kind'] not in ('data_mismatch', 'target_mismatch')):
            raise ValueError('CI kit control must be a comparable verified data-mismatch block')
        files[control_name] = json.dumps(control['plan'], ensure_ascii=False, indent=2) + '\n'
        files['evidence/unsafe-control-report.json'] = json.dumps(control, ensure_ascii=False, indent=2) + '\n'
        files['evidence/unsafe-control-review.md'] = render_markdown(control)
        files['evidence/unsafe-control-witness.py'] = render_reproduction(control, contract)
        readme += (
            '\n## Prove this gate can go red\n\n'
            f"The same contract also blocked the unsafe control at {control['passed']}/{control['total']} probes. "
            'Its first failing write is retained in `evidence/unsafe-control-report.json` and '
            '`evidence/unsafe-control-witness.py`. From the repository checkout, run:\n\n'
            f'    python ci/review_gate.py --contract {contract_name} --plan {control_name} '
            '--output-dir work/ci-negative-control\n'
            '    # Expected exit 1 and classification verified_block.\n'
            f'    python ci/review_gate.py --contract {contract_name} --plan {plan_name} '
            '--output-dir work/ci-positive-control\n'
            '    # Expected exit 0 and classification verified_pass.\n\n'
            'The unsafe control is not in `manifest-entry.json`: do not add it to a normal green PR.\n'
        )
        files['README.md'] = readme
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode('utf-8'))
    return output.getvalue(), slug
