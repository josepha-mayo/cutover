"""Independently replay an exported Cutover report from checked-in inputs."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .service import verify_report_against_replay

MAX_REPORT_BYTES = 128 * 1024 * 1024


def read_json(parser, path, label, limit):
    try:
        if path.stat().st_size > limit:
            parser.error(f'{label} JSON exceeds {limit // 1024} KiB')
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        parser.error(f'Cannot read {label} JSON: {exc}')


def main():
    parser = argparse.ArgumentParser(
        description='Replay an exported report from its contract and candidate; do not trust its stated verdict.')
    parser.add_argument('--report', required=True, type=Path, help='Exported Cutover JSON evidence')
    parser.add_argument('--plan', required=True, type=Path, help='The candidate JSON used for that evidence')
    parser.add_argument('--contract', type=Path, help='Imported SQLite contract JSON, if used')
    parser.add_argument('--case', choices=('parcel', 'contacts'), default='parcel',
                        help='Bundled case when --contract is absent')
    args = parser.parse_args()
    if args.contract and args.case != 'parcel':
        parser.error('--case selects a bundled example and cannot be combined with --contract')

    # Many failing probes or long SQL can still produce a large bounded report
    # even after redundant passing row maps are removed. The auditor must not
    # reject evidence solely because the supported contract is large.
    report = read_json(parser, args.report, 'Report', MAX_REPORT_BYTES)
    plan = read_json(parser, args.plan, 'Plan', 64 * 1024)
    contract = read_json(parser, args.contract, 'Contract', 64 * 1024) if args.contract else None
    case = 'custom' if contract is not None else args.case
    try:
        verify_report_against_replay(case, plan, report, contract)
    except (ValueError, subprocess.TimeoutExpired) as exc:
        print(f'UNVERIFIED: {exc}', file=sys.stderr)
        return 2
    print(f"VERIFIED {report['status'].upper()}: {report['passed']}/{report['total']} probes; "
          f"plan {report['plan_hash'][:12]}; contract {report['contract_hash'][:12]}")
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
