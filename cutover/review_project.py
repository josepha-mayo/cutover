"""Review a local setup folder and retain a fresh comparison, note and passing PR kit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def review(project, output, bob_workspace=False):
    names = ('contract.json', 'baseline.json', 'candidate.json', 'migration.sql')
    inputs = {}
    for name in names:
        source = project/name
        if source.stat().st_size > 65536:
            raise ValueError(f'{name} must be at most 64 KiB')
        inputs[name] = source.read_bytes()
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/'inputs'
    snapshot.mkdir()
    for name, content in inputs.items():
        (snapshot/name).write_bytes(content)
    status = {'status': 'unverified', 'input_sha256': {name: hashlib.sha256(raw).hexdigest()
              for name, raw in inputs.items()}, 'steps': []}

    def save():
        (output/'review-status.json').write_text(json.dumps(status, indent=2)+'\n', encoding='utf-8')

    def run(module, args, label):
        result = subprocess.run([sys.executable, '-m', module, *map(str, args)],
            capture_output=True, text=True, encoding='utf-8', timeout=600,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (output/f'{label}.log').write_text(result.stdout+result.stderr, encoding='utf-8')
        status['steps'].append({'operation': label, 'exit': result.returncode})
        save()
        if result.returncode not in (0, 1):
            raise ValueError(f'{label} was not verified; retained log: {output/f"{label}.log"}')
        return result.returncode

    save()
    try:
        candidate_args = ['--contract', snapshot/'contract.json', '--plan', snapshot/'candidate.json',
                          '--migration-file', snapshot/'migration.sql']
        code = run('cutover', candidate_args+['--baseline-plan', snapshot/'baseline.json',
                   '--bundle', output/'comparison.zip', '--output', output/'candidate-report.json'], 'comparison')
        run('cutover.audit_bundle', ['--bundle', output/'comparison.zip', '--markdown', output/'review.md'], 'audit')
        report = json.loads((output/'candidate-report.json').read_text(encoding='utf-8'))
        if code != (0 if report['status'] == 'pass' else 1):
            raise ValueError('Candidate report does not match the comparison outcome')
        if code == 1 and bob_workspace:
            from .repair_workspace import render_repair_workspace
            contract = json.loads((snapshot/'contract.json').read_text(encoding='utf-8-sig'))
            payload = render_repair_workspace(report, contract)
            with (output/'bob-repair-workspace.zip').open('xb') as destination:
                destination.write(payload)
            status['bob_workspace'] = 'bob-repair-workspace.zip'
        if code == 0:
            # Only include a negative control when the verified baseline is a data mismatch.
            with zipfile.ZipFile(output/'comparison.zip') as archive:
                baseline = json.loads(archive.read('baseline/report.json'))
            kit_args = candidate_args+['--ci-kit', output/'pending-pr-kit.zip']
            if (baseline['status'] == 'blocked' and baseline.get('witness') and
                    baseline['witness']['failure']['kind'] == 'data_mismatch'):
                kit_args += ['--ci-control', snapshot/'baseline.json']
            if run('cutover', kit_args, 'pr-kit') != 0:
                raise ValueError('Passing candidate could not produce a verified PR kit')
            with zipfile.ZipFile(output/'pending-pr-kit.zip') as archive:
                kit_report = json.loads(archive.read('evidence/report.json'))
            for key in ('plan_hash', 'contract_hash', 'suite_hash', 'engine_sha256'):
                if kit_report[key] != report[key]:
                    raise ValueError('PR kit identities differ from the reviewed comparison')
            (output/'pending-pr-kit.zip').rename(output/'pr-kit.zip')
            status['pr_kit'] = 'pr-kit.zip'
        status['status'] = report['status']
        status['candidate'] = {'passed': report['passed'], 'total': report['total']}
        save()
        return code
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        status['error'] = str(exc)
        save()
        raise


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True, help='Folder created by cutover.init_contract')
    parser.add_argument('--out', type=Path, required=True, help='New evidence folder; existing folders refused')
    parser.add_argument('--bob-workspace', action='store_true',
                        help='Export a local Bob repair workspace only when the audited candidate is blocked')
    args = parser.parse_args()
    try:
        code = review(args.project.resolve(), args.out.resolve(), args.bob_workspace)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(f'{"PASS" if code == 0 else "BLOCKED"}: independently audited comparison and review in {args.out}')
    if code == 0:
        print('Passing PR kit: pr-kit.zip. Inspect its four files before copying into your repository.')
    else:
        print('No PR kit exported. Original failure and current candidate retained; edit and use a new review folder.')
        if args.bob_workspace:
            print('Local Bob handoff: bob-repair-workspace.zip. Inspect its README; export does not invoke Bob.')
    return code


if __name__ == '__main__':
    sys.exit(main())
