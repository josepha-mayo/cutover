"""Verify a downloaded Cutover CI kit and add its passing case to this checkout."""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

from ci.discover_cases import FIELDS, LABEL, SLUG, discover
from cutover.reporting import render_reproduction
from cutover.service import verify_report_against_replay


ROOT = Path(__file__).resolve().parents[1]
MAX_ZIP_BYTES = 2_000_000
MAX_EXPANDED_BYTES = 10_000_000


def _json(archive: zipfile.ZipFile, name: str):
    return json.loads(archive.read(name).decode('utf-8'))


def _read_kit(path: Path):
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError('CI kit must be an existing ZIP of at most 2 MB')
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) > 20:
            raise ValueError('CI kit contains duplicate or excess entries')
        if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED_BYTES:
            raise ValueError('CI kit expands beyond the 10 MB limit')
        entry = _json(archive, 'manifest-entry.json')
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ValueError('CI kit manifest entry has invalid fields')
        slug = entry['slug']
        if (not isinstance(slug, str) or not SLUG.fullmatch(slug) or
                not isinstance(entry['case'], str) or not LABEL.fullmatch(entry['case']) or
                entry['contract'] != f'ci/{slug}-contract.json' or
                entry['plan'] != f'ci/{slug}-candidate.json'):
            raise ValueError('CI kit paths, label or slug are invalid')
        required = {'README.md', 'manifest-entry.json', entry['contract'], entry['plan'],
                    'evidence/report.json', 'evidence/review.md'}
        if not required.issubset(names):
            raise ValueError('CI kit is missing a required file')
        contract_bytes = archive.read(entry['contract'])
        plan_bytes = archive.read(entry['plan'])
        contract = json.loads(contract_bytes)
        plan = json.loads(plan_bytes)
        report = _json(archive, 'evidence/report.json')
        if not isinstance(report, dict):
            raise ValueError('CI kit report must be a JSON object')
        if report.get('case') != 'custom' or report.get('status') != 'pass':
            raise ValueError('CI kit must contain a passing custom rehearsal')
        verify_report_against_replay('custom', plan, report, contract)
        from cutover.reporting import render_markdown
        if archive.read('evidence/review.md') != render_markdown(report).encode('utf-8'):
            raise ValueError('CI kit review differs from its replayed report')
        control_name = f'ci/{slug}-unsafe-control.json'
        control_files = {control_name, 'evidence/unsafe-control-report.json',
                         'evidence/unsafe-control-review.md', 'evidence/unsafe-control-witness.py'}
        has_control = bool(control_files.intersection(names))
        if has_control:
            if not control_files.issubset(names):
                raise ValueError('CI kit unsafe control is incomplete')
            control_plan = _json(archive, control_name)
            control = _json(archive, 'evidence/unsafe-control-report.json')
            if not isinstance(control, dict):
                raise ValueError('CI kit unsafe report must be a JSON object')
            witness = control.get('witness')
            failure = witness.get('failure') if isinstance(witness, dict) else None
            if (control.get('case') != 'custom' or control.get('status') != 'blocked' or
                    control.get('contract_hash') != report['contract_hash'] or
                    control.get('engine_sha256') != report['engine_sha256'] or
                    control.get('suite_hash') != report['suite_hash'] or
                    (failure.get('kind') if isinstance(failure, dict) else None)
                    not in ('data_mismatch', 'target_mismatch')):
                raise ValueError('CI kit unsafe control is not a comparable data-mismatch block')
            verify_report_against_replay('custom', control_plan, control, contract)
            if archive.read('evidence/unsafe-control-review.md') != render_markdown(control).encode('utf-8'):
                raise ValueError('CI kit unsafe review differs from its replayed report')
            if archive.read('evidence/unsafe-control-witness.py') != render_reproduction(control, contract).encode('utf-8'):
                raise ValueError('CI kit standalone witness differs from the replayed failure')
        return entry, contract_bytes, plan_bytes, report, has_control


def install_kit(path: Path, root: Path = ROOT, apply: bool = False) -> dict:
    """Default to a no-write preflight; --apply installs only verified passing inputs."""
    root = root.resolve()
    manifest = root / 'ci/cases.json'
    if not manifest.is_file():
        raise ValueError('Target checkout has no ci/cases.json')
    existing = discover(root)['include']
    if len(existing) >= 8:
        raise ValueError('CI manifest already has the maximum eight cases')
    entry, contract_bytes, plan_bytes, report, has_control = _read_kit(path)
    if entry['slug'] in {item['slug'] for item in existing}:
        raise ValueError(f"CI case slug already exists: {entry['slug']}")
    targets = [root / entry['contract'], root / entry['plan']]
    if ((root / 'ci').is_symlink() or any(target.is_symlink() for target in targets) or
            any(target.exists() or not target.resolve().is_relative_to(root) for target in targets)):
        raise ValueError('CI kit would overwrite a file or escape the checkout')
    result = {'action': 'applied' if apply else 'dry_run', 'slug': entry['slug'],
              'coverage': f"{report['passed']}/{report['total']}",
              'plan_hash': report['plan_hash'], 'contract_hash': report['contract_hash'],
              'unsafe_control_verified': has_control,
              'files': [entry['contract'], entry['plan'], 'ci/cases.json']}
    if not apply:
        return result
    # Inputs are new paths; the manifest is replaced last. Restore the original
    # manifest and remove only these newly created files if any write fails.
    original_manifest = manifest.read_bytes()
    temp_manifest = manifest.with_name('cases.cutover-tmp.json')
    if temp_manifest.exists():
        raise ValueError('Refusing to overwrite an existing temporary manifest')
    created = []
    try:
        for target, content in zip(targets, (contract_bytes, plan_bytes)):
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                created.append(target)
                stream.write(content)
        # Re-run discovery on the assembled manifest before replacing the
        # checkout's manifest, including every previously registered case.
        proposed = json.dumps([*existing, entry], ensure_ascii=False, indent=2) + '\n'
        temp_manifest.write_text(proposed, encoding='utf-8')
        discover(root, 'ci/cases.cutover-tmp.json')
        os.replace(temp_manifest, manifest)
    except Exception:
        if temp_manifest.exists():
            temp_manifest.unlink()
        for target in created:
            target.unlink()
        if manifest.read_bytes() != original_manifest:
            manifest.write_bytes(original_manifest)
        raise
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kit', required=True, type=Path, help='Downloaded Cutover CI kit ZIP')
    parser.add_argument('--apply', action='store_true', help='Write the passing case and manifest entry')
    args = parser.parse_args()
    try:
        print(json.dumps(install_kit(args.kit, apply=args.apply), indent=2))
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f'CI kit rejected: {exc}', file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == '__main__':
    main()
