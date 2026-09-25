"""Package one verified custom rehearsal for the repository's PR review gate."""
import io
import json
import re
import zipfile

from .reporting import render_markdown


def render_ci_kit(report, contract):
    if report['case'] != 'custom' or report['status'] != 'pass':
        raise ValueError('A passing custom-contract rehearsal is required for a CI kit')
    part = re.sub(r'[^a-z0-9]+', '-', contract['project'].lower()).strip('-')[:25].strip('-')
    slug = f'release-{part or "scenario"}'
    contract_name = f'ci/{slug}-contract.json'
    plan_name = f'ci/{slug}-candidate.json'
    entry = {'case': f'Custom {slug}', 'slug': slug,
             'contract': contract_name, 'plan': plan_name}
    readme = (
        '# Cutover CI handoff kit\n\n'
        f"Fresh rehearsal: PASS {report['passed']}/{report['total']} bounded probes.\n"
        f"Plan SHA-256: {report['plan_hash']}\n"
        f"Contract SHA-256: {report['contract_hash']}\n"
        f"Engine SHA-256: {report['engine_sha256']}\n\n"
        'From a checkout of the Cutover repository, copy the two JSON files under\n'
        '`ci/` into the matching paths. Add the object in `manifest-entry.json`\n'
        'to the `ci/cases.json` array; choose a unique slug if needed. Run:\n\n'
        '    python -m ci.discover_cases\n'
        f'    python -m cutover.audit_report --contract {contract_name} '
        f'--plan {plan_name} --report evidence/report.json\n\n'
        'Commit the files and open a PR. GitHub Actions will create a separate\n'
        'review job with retained evidence for this case. This kit contains\n'
        'executed synthetic SQLite evidence, not deployment approval. Check\n'
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
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode('utf-8'))
    return output.getvalue(), slug
