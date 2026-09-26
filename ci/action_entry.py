"""Run Cutover's pinned action checkout against a separate consumer workspace.

The consumer supplies data files, not a copy of the Cutover engine. The existing
review gate runs from this action's source directory so a consumer package named
cutover cannot silently replace the evaluator. This packaging is a Codex extension
after Bob's original gate task.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path, PureWindowsPath


ROOT = Path(__file__).resolve().parents[1]


def workspace_path(root: Path, value: str) -> Path:
    if (not value or any(ord(char) < 32 for char in value) or
            Path(value).is_absolute() or PureWindowsPath(value).drive or
            '\\' in value or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Action paths must be nonempty relative paths inside the checkout')
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Action input or output resolves outside the checkout')
    return path


def output(name: str, value: str) -> None:
    if '\n' in value or '\r' in value:
        raise ValueError('Action output cannot contain a newline')
    target = os.environ.get('GITHUB_OUTPUT')
    if target:
        with open(target, 'a', encoding='utf-8', newline='\n') as stream:
            stream.write(f'{name}={value}\n')


def main() -> int:
    out = None
    try:
        workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
        out = workspace_path(workspace, os.environ.get('CUTOVER_OUTPUT_DIR', 'cutover-review'))
        if out.exists() and (not out.is_dir() or any(out.iterdir())):
            raise ValueError('Evidence directory must be empty; existing evidence was preserved')
        out.mkdir(parents=True, exist_ok=True)
        output('evidence-path', str(out))
    except (KeyError, OSError, ValueError) as exc:
        print(f'Cutover action could not prepare a fresh evidence directory: {exc}', file=sys.stderr)
        output('classification', 'unverified')
        return 2

    try:
        contract = workspace_path(workspace, os.environ.get('CUTOVER_CONTRACT', ''))
        plan = workspace_path(workspace, os.environ.get('CUTOVER_PLAN', ''))
        sql_value = os.environ.get('CUTOVER_MIGRATION_FILE', '')
        sql = workspace_path(workspace, sql_value) if sql_value else None
        expected_contract_hash = os.environ.get('CUTOVER_EXPECTED_CONTRACT_HASH', '')
    except ValueError as exc:
        verdict = {'classification': 'unverified', 'reason': str(exc)}
        (out / 'verdict.json').write_text(json.dumps(verdict, indent=2) + '\n', encoding='utf-8')
        summary = '## Cutover action — UNVERIFIED\n\n' + str(exc) + '\n'
        (out / 'summary.md').write_text(summary, encoding='utf-8')
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
                stream.write(summary)
        output('classification', 'unverified')
        return 2

    provenance = {
        'action_repository': os.environ.get('CUTOVER_ACTION_REPOSITORY', ''),
        'action_ref': os.environ.get('CUTOVER_ACTION_REF', ''),
        'consumer_repository': os.environ.get('GITHUB_REPOSITORY', ''),
        'consumer_checkout_sha': os.environ.get('GITHUB_SHA', ''),
        'contract': contract.relative_to(workspace).as_posix(),
        'plan': plan.relative_to(workspace).as_posix(),
        'migration_file': sql.relative_to(workspace).as_posix() if sql else None,
        'expected_contract_hash': expected_contract_hash or None,
    }
    (out / 'action.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    command = [sys.executable, str(ROOT / 'ci/review_gate.py'),
               '--contract', str(contract), '--plan', str(plan), '--output-dir', str(out)]
    if sql:
        command += ['--migration-file', str(sql)]
    if expected_contract_hash:
        command += ['--expected-contract-hash', expected_contract_hash]
    result = subprocess.run(command, cwd=ROOT, check=False,
                            capture_output=True, text=True, encoding='utf-8',
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    try:
        verdict = json.loads((out / 'verdict.json').read_text(encoding='utf-8'))
        classification = verdict['classification']
        if classification not in ('verified_pass', 'verified_block', 'unverified'):
            raise ValueError('Unexpected verdict')
    except (OSError, ValueError, KeyError, TypeError):
        classification = 'unverified'
    expected_exit = {'verified_pass': 0, 'verified_block': 1, 'unverified': 2}[classification]
    if result.returncode != expected_exit:
        classification = 'unverified'
        reason = 'Gate process exit did not agree with its recorded verdict'
        (out / 'verdict.json').write_text(json.dumps({
            'classification': classification, 'reason': reason,
            'gate_exit': result.returncode}, indent=2) + '\n', encoding='utf-8')
        with (out / 'summary.md').open('a', encoding='utf-8') as stream:
            stream.write('\n## Action could not verify the result\n\n' + reason + '\n')
    output('classification', classification)
    if (out / 'report.json').is_file():
        report = json.loads((out / 'report.json').read_text(encoding='utf-8'))
        if type(report.get('passed')) is int and type(report.get('total')) is int:
            output('coverage', f"{report['passed']}/{report['total']}")
    return {'verified_pass': 0, 'verified_block': 1, 'unverified': 2}[classification]


if __name__ == '__main__':
    sys.exit(main())
