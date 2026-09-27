"""Replay a downloaded review ZIP and verify every included review artifact."""

import argparse
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from .bundle import render_bundle, render_comparison_bundle
from .engine import load_case
from .service import verify_report_against_replay
from .reporting import fenced, render_markdown

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 300 * 1024 * 1024


def members(archive, member_limit=MAX_MEMBER_BYTES, total_limit=MAX_TOTAL_BYTES):
    infos = archive.infolist()
    names = [item.filename for item in infos]
    if len(names) > 20 or len(names) != len(set(names)):
        raise ValueError('Archive has too many or duplicate members')
    if any(item.is_dir() or item.file_size > member_limit for item in infos):
        raise ValueError('Archive has an unsupported or oversized member')
    if sum(item.file_size for item in infos) > total_limit:
        raise ValueError('Archive expands beyond the audit limit')
    return {name: archive.read(name) for name in names}


def json_member(files, name):
    if name not in files:
        raise ValueError(f'Missing {name}')
    try:
        return json.loads(files[name].decode('utf-8'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'Invalid {name}: {exc}') from exc


def checked_report(files, prefix):
    report = json_member(files, prefix + 'report.json')
    plan = json_member(files, prefix + 'plan.json')
    contract = json_member(files, prefix + 'contract.json')
    case = report.get('case') if isinstance(report, dict) else None
    if case != 'custom':
        if case not in ('parcel', 'contacts') or contract != load_case(case):
            raise ValueError(f'{prefix}contract does not match its bundled case')
        verify_report_against_replay(case, plan, report)
    else:
        verify_report_against_replay(case, plan, report, contract)
    return report, contract


def audit(path):
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('Compressed archive exceeds the audit limit')
    with zipfile.ZipFile(path) as archive:
        supplied = members(archive)
    return audit_files(supplied)


def audit_bytes(payload, *, archive_limit, member_limit, total_limit):
    """Audit an in-memory packet under explicit upload limits; never extract it."""
    if not payload or len(payload) > archive_limit:
        raise ValueError('Compressed archive exceeds the hosted audit limit')
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if any(item.flag_bits & 1 or item.compress_type not in
               (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for item in archive.infolist()):
            raise ValueError('Hosted packets require unencrypted stored or deflated ZIP members')
        supplied = members(archive, member_limit, total_limit)
    reports = audit_files(supplied)
    prefix = 'candidate/' if 'comparison.json' in supplied else ''
    return reports, json_member(supplied, prefix + 'contract.json')


def audit_files(supplied):
    """Verify both replayable report fields and every packaged companion file."""
    paired = 'comparison.json' in supplied
    if paired:
        before, contract = checked_report(supplied, 'baseline/')
        after, other_contract = checked_report(supplied, 'candidate/')
        if contract != other_contract:
            raise ValueError('Baseline and candidate contracts differ')
        canonical = render_comparison_bundle(before, after, contract)
        reports = (before, after)
    else:
        report, contract = checked_report(supplied, '')
        canonical = render_bundle(report, contract)
        reports = (report,)
    with zipfile.ZipFile(io.BytesIO(canonical)) as archive:
        expected = members(archive)
    if supplied.keys() != expected.keys():
        raise ValueError('Review packet members differ from the expected format')
    for name, content in expected.items():
        if supplied[name] != content:
            raise ValueError(f'{name} differs from the verified report')
    return reports


def main():
    parser = argparse.ArgumentParser(description=(
        'Independently replay every report in a Cutover ZIP and verify its '
        'comparison, Markdown review and witness without extracting or executing it.'))
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--markdown', type=Path,
                        help='Write a verified PR review after replay; refuses existing output files')
    args = parser.parse_args()
    try:
        if args.markdown and (args.markdown.resolve() == args.bundle.resolve() or args.markdown.exists()):
            raise ValueError('Markdown output must be a new file and cannot overwrite the packet')
        reports = audit(args.bundle)
        if args.markdown:
            review = ['# Independently verified Cutover packet', '',
                      'Every retained report and packaged companion file passed independent replay and format verification. '
                      'This is bounded SQLite evidence, not production approval or authenticated authorship.', '']
            if len(reports) == 2:
                before, after = reports
                same_migration = before['plan']['migration'] == after['plan']['migration']
                old = {item['id']: item for item in before['results']}
                paired = [(old[item['id']], item) for item in after['results']
                          if (same_migration or item['category'] != 'migration_window')
                          and item['id'] in old and old[item['id']]['payload'] == item['payload']
                          and old[item['id']]['actions'] == item['actions']]
                summary = {'paired_probes': len(paired),
                           'resolved': sum(not left['passed'] and right['passed'] for left, right in paired),
                           'regressed': sum(left['passed'] and not right['passed'] for left, right in paired),
                           'window_probes_paired': same_migration,
                           'interpretation': ('Identical migration SQL permits window pairing.' if same_migration else
                               'Different SQL sequences: statement windows are evaluated separately, not paired by step number.')}
                review += ['## Review verdict', '',
                           '| Executed plan | Verdict | Full suite passed | Completed-rollout failures | Migration-window failures |',
                           '| --- | --- | --- | --- | --- |']
                for label, executed in (('Baseline', before), ('Candidate', after)):
                    window = next(category for category in executed['categories'] if category['id'] == 'migration_window')
                    complete_total = executed['total'] - window['total']
                    complete_failed = executed['failed'] - (window['total'] - window['passed'])
                    review.append(f"| {label} | {executed['status'].upper()} | {executed['passed']}/{executed['total']} | {complete_failed}/{complete_total} | {window['total'] - window['passed']}/{window['total']} |")
                review += ['',
                           'Window counts describe each plan separately. Different statement sequences create different tested boundaries; '
                           'a smaller denominator does not imply equivalent coverage. The packet retains both full reports.', '',
                           '## Measured comparison', '', fenced(json.dumps(summary, indent=2), 'json'), '',
                           '## Executed SQL changes', '',
                           'Textual differences do not establish which SQL line caused the measured change.', '']
                for key in ('migration', 'read', 'write', 'insert'):
                    if before['plan'][key] != after['plan'][key]:
                        review += [f'### {key}', '', 'Pinned baseline:', '', fenced(before['plan'][key], 'sql'), '',
                                   'Current candidate:', '', fenced(after['plan'][key], 'sql'), '']
            for index, report in enumerate(reports):
                review += [('## Pinned baseline report' if index == 0 else '## Current candidate report')
                           if len(reports) == 2 else '## Executed report', '', render_markdown(report), '']
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            with args.markdown.open('x', encoding='utf-8', newline='\n') as output:
                output.write('\n'.join(review))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError,
            zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(f'UNVERIFIED: {exc}', file=sys.stderr)
        return 2
    print('VERIFIED PACKET: ' + ' -> '.join(
        f"{item['status'].upper()} {item['passed']}/{item['total']} "
        f"plan {item['plan_hash'][:12]}" for item in reports))
    return 0 if all(item['status'] == 'pass' for item in reports) else 1


if __name__ == '__main__':
    sys.exit(main())
