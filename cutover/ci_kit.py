"""Package one verified custom rehearsal for the repository's PR review gate."""
import io
import json
import re
import zipfile

from .reporting import render_markdown
from .reporting import render_reproduction


ACTION_REF = '65984c8efd007e2d50d6beaf5afbdac500ec690b'
LEGACY_ACTION_REF = 'a5bf69f6e8f94788eade58691d292941e009f8ac'
CHECKOUT_REF = '3d3c42e5aac5ba805825da76410c181273ba90b1'


def portable_files(plan, slug, contract_hash=None):
    """Render data-only inputs and a pinned workflow for a consumer repository."""
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,40}', slug):
        raise ValueError('Portable kit slug is invalid')
    if contract_hash is not None and not re.fullmatch(r'[0-9a-f]{64}', contract_hash):
        raise ValueError('Portable kit contract hash is invalid')
    contract = f'ci/{slug}-contract.json'
    adapters = f'ci/{slug}-adapters.json'
    migration = f'ci/{slug}-migration.sql'
    workflow = (
        f'name: Cutover {slug}\n'
        'on: pull_request\n'
        'permissions:\n  contents: read\n'
        'jobs:\n  review:\n'
        '    runs-on: ubuntu-latest\n'
        '    timeout-minutes: 10\n'
        '    steps:\n'
        f'      - uses: actions/checkout@{CHECKOUT_REF}\n'
        '        with:\n          persist-credentials: false\n'
        f'      - uses: josepha-mayo/cutover@{ACTION_REF if contract_hash else LEGACY_ACTION_REF}\n'
        '        with:\n'
        f'          contract: {contract}\n'
        f'          plan: {adapters}\n'
        f'          migration-file: {migration}\n'
        + (f"          expected-contract-hash: '{contract_hash}'\n" if contract_hash else '') +
        f'          output-dir: cutover-review-{slug}\n'
        f'          artifact-name: cutover-{slug}\n'
    )
    return {
        f'.github/workflows/cutover-{slug}.yml': workflow,
        adapters: json.dumps({key: value for key, value in plan.items()
                              if key != 'migration'}, ensure_ascii=False, indent=2) + '\n',
        migration: plan['migration'],
    }


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
        '## Add this check to your own repository\n\n'
        'Inspect and copy only these four files, preserving their paths:\n\n'
        f'- `.github/workflows/cutover-{slug}.yml`\n'
        f'- `{contract_name}`\n'
        f'- `ci/{slug}-adapters.json`\n'
        f'- `ci/{slug}-migration.sql`\n\n'
        'Commit them on a branch and open a pull request. The workflow calls\n'
        f'`josepha-mayo/cutover@{ACTION_REF}`; no Cutover clone, engine copy,\n'
        'package installation or API key is needed in your repository. The\n'
        'SQL file is the migration source of truth; the adapters JSON contains\n'
        'only the candidate name and new-worker queries. Keep editing that SQL\n'
        'file to have later changes rehearsed by the same check. GitHub retains\n'
        'the independently audited verdict, report and replay packet; an unsafe\n'
        'migration or unverifiable input fails the job.\n\n'
        'The workflow locks the agreed contract hash from this replay. Changing\n'
        'the schema, old-worker adapters, seed records or payloads fails as\n'
        '`unverified`, even if the candidate passes the changed test data. JSON\n'
        'formatting and key order do not affect the lock. Review intentional\n'
        'contract changes separately before updating the pinned hash; do not\n'
        'automatically recalculate it inside a pull request. Protect workflow\n'
        'changes with repository review rules: this hash is not a signature.\n\n'
        'The downloaded contract contains the supplied synthetic seed data.\n'
        'Review all four files before committing. Do not overwrite an existing\n'
        'workflow or input with the same name. Keep the remaining evidence and\n'
        'unsafe-control files for local review; do not copy the whole archive\n'
        'into an application repository. A check runs on pull requests; make it\n'
        'required in your repository settings if your team wants to enforce it.\n\n'
        '## Alternatively: add a case inside a Cutover checkout\n\n'
        'From a checkout of the Cutover repository, verify this downloaded ZIP\n'
        'and preview the files it would add, then apply it explicitly:\n\n'
        '    python -m ci.install_kit --kit path/to/downloaded-kit.zip\n'
        '    python -m ci.install_kit --kit path/to/downloaded-kit.zip --apply\n'
        '    python -m ci.install_kit --kit path/to/downloaded-kit.zip --verify-installed\n\n'
        'The installer rejects path or slug collisions, independently replays\n'
        'the report (and unsafe control, if present), then adds only the passing\n'
        'inputs and one manifest entry. Or copy these exact two JSON files:\n'
        f'`{contract_name}` and `{plan_name}`,\n'
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
        **portable_files(report['plan'], slug, report['contract_hash']),
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
