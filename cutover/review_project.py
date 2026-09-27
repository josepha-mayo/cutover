"""Review a local setup folder and retain a fresh comparison, note and passing PR kit."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import zipfile


def terminal_witness(report):
    """Display bounded recorded evidence, without inferring a cause or a repair."""
    witness = report.get('witness')
    if not witness:
        return []
    def compact(value, limit=700):
        rendered = json.dumps(value, ensure_ascii=True, separators=(',', ':'))
        return rendered if len(rendered) <= limit else rendered[:limit]+'... [see review.html for full evidence]'
    lines = ['Recorded counterexample: '+compact(witness.get('id'))]
    trace = witness.get('trace', [])
    lines.append('Sequence: '+compact([{'action':event.get('action'), 'status':event.get('status')}
                                       for event in trace], 1600))
    failed = next((event for event in trace if event.get('status') == 'fail'), None)
    if failed is not None:
        for key in ('expected', 'actual', 'error'):
            if key in failed:
                lines.append(key.capitalize()+': '+compact(failed[key]))
    failure = witness.get('failure', {})
    lines.append('Failure: '+compact(failure))
    lines.append('This is a recorded bounded rehearsal, not a production incident or single-line cause.')
    return lines


def render_pr_summary(baseline, candidate, baseline_git=None, candidate_source=None):
    """Compact PR note from reports already independently audited by the caller."""
    lines = ['# Cutover PR review: candidate '+candidate['status'].upper(), '',
             '| Executed plan | Full suite | Completed-rollout failures | Migration-window failures |',
             '| --- | --- | --- | --- |']
    for label, report in (('Original baseline', baseline), ('Candidate', candidate)):
        window = next(c for c in report['categories'] if c['id'] == 'migration_window')
        completed_total = report['total']-window['total']
        completed_failed = completed_total-(report['passed']-window['passed'])
        lines.append(f"| {label} | {report['status'].upper()} {report['passed']}/{report['total']} | "
                     f"{completed_failed}/{completed_total} | {window['total']-window['passed']}/{window['total']} |")
    lines += ['', 'Window counts describe each plan separately; different SQL sequences are not paired by step number.', '']
    witness_report = candidate if candidate['status'] == 'blocked' else baseline
    if witness_report.get('witness'):
        lines += ['## '+('Current candidate counterexample' if witness_report is candidate else 'Original counterexample retained; current candidate passed'),
                  '', '~~~text', *terminal_witness(witness_report), '~~~', '',
                  'Display is bounded; inspect the full recorded trace and SQL in [review.html](review.html).', '']
    else:
        lines += ['No blocked counterexample was retained in either executed plan.', '']
    if baseline_git or candidate_source:
        sources = {}
        if baseline_git: sources['original_sql'] = baseline_git
        if candidate_source: sources['candidate_sql'] = candidate_source
        lines += ['## SQL source identity', '', '~~~json', json.dumps(sources,ensure_ascii=True,indent=2), '~~~', '']
    lines += ['## Candidate evidence identity', '', '~~~json',
              json.dumps({key:candidate[key] for key in ('plan_hash','contract_hash','suite_hash','engine_sha256')},indent=2),
              '~~~', '', '[Full review and SQL changes](review.md) · [Offline trace viewer](review.html) · [Replayable packet](comparison.zip)', '',
              'Generated only after independent comparison audit and any requested packaging checks. '
              'Bounded sequential SQLite evidence, not whole-application verification, signed provenance or production approval. '
              'Review the supplied contract/adapters and operational rollout separately.', '']
    return '\n'.join(lines)


def git_baseline(project, ref, path=None):
    """Read a bounded committed SQL blob without fetching or changing a checkout."""
    git_directory = project
    def git(*args):
        result = subprocess.run(['git', '--literal-pathspecs', '-C', str(git_directory), *args], capture_output=True,
                                timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise ValueError('Git baseline could not be resolved; check the local commit and tracked SQL path')
        return result.stdout

    root = Path(git('rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
    git_directory = root
    commit = git('rev-parse', '--verify', '--end-of-options', ref+'^{commit}').decode('ascii').strip()
    if path is None:
        path = (project.resolve().relative_to(root)/'migration.sql').as_posix()
    if not path or path.startswith('/') or '\\' in path or any(part in ('', '.', '..') for part in path.split('/')):
        raise ValueError('Git baseline path must be a repository-relative file path')
    entries = git('ls-tree', '-z', commit, '--', path).decode('utf-8').rstrip('\0').split('\0')
    entry = entries[0].split('\t', 1)
    if (len(entries) != 1 or len(entry) != 2 or entry[1] != path or
            entry[0].split()[:2] not in (['100644', 'blob'], ['100755', 'blob'])):
        raise ValueError('Git baseline must be a tracked regular file, not a directory or symbolic link')
    blob = entry[0].split()[2]
    if int(git('cat-file', '-s', blob)) > 65536:
        raise ValueError('Git baseline SQL must be at most 64 KiB')
    raw = git('cat-file', 'blob', blob)
    raw.decode('utf-8-sig')
    return raw, {'commit': commit, 'path': path, 'blob': blob}


def review(project, output, bob_workspace=False, candidate_plan=None, baseline_migration=None,
           baseline_git_ref=None, baseline_git_path=None, expected_contract_hash=None,
           candidate_migration_file=None, candidate_git_ref=None, candidate_git_path=None):
    if sum(value is not None for value in (candidate_plan, candidate_migration_file, candidate_git_ref)) > 1:
        raise ValueError('Choose a complete candidate plan, candidate SQL file or candidate Git commit, not both')
    if expected_contract_hash is not None:
        expected_contract_hash = expected_contract_hash.lower()
        if not re.fullmatch(r'[0-9a-f]{64}', expected_contract_hash):
            raise ValueError('Expected contract hash must be 64 hexadecimal characters')
    names = ('contract.json', 'baseline.json', 'candidate.json', 'migration.sql')
    inputs = {}
    for name in names:
        source = project/name
        if source.stat().st_size > 65536:
            raise ValueError(f'{name} must be at most 64 KiB')
        inputs[name] = source.read_bytes()
    if candidate_plan is not None:
        if candidate_plan.stat().st_size > 65536:
            raise ValueError('Supplied candidate plan must be at most 64 KiB')
        inputs['supplied-candidate.json'] = candidate_plan.read_bytes()
    if candidate_migration_file is not None:
        if candidate_migration_file.stat().st_size > 65536:
            raise ValueError('Supplied candidate SQL must be at most 64 KiB')
        raw = candidate_migration_file.read_bytes()
        sql = raw.decode('utf-8-sig')
        if not sql.strip() or '\0' in sql or len(sql) > 12000:
            raise ValueError('Expected nonempty UTF-8 candidate SQL without NUL, up to 12,000 characters')
        inputs['supplied-candidate.sql'] = raw
    if baseline_migration is not None:
        if baseline_migration.stat().st_size > 65536:
            raise ValueError('Supplied baseline SQL must be at most 64 KiB')
        inputs['supplied-baseline.sql'] = baseline_migration.read_bytes()
    candidate_git = None
    if candidate_git_ref is not None:
        raw, candidate_git = git_baseline(project, candidate_git_ref, candidate_git_path)
        sql = raw.decode('utf-8-sig')
        if not sql.strip() or '\0' in sql or len(sql) > 12000:
            raise ValueError('Expected nonempty UTF-8 candidate SQL without NUL, up to 12,000 characters')
        inputs['supplied-candidate.sql'] = raw
    elif candidate_git_path is not None:
        raise ValueError('--candidate-git-path requires --candidate-git-ref')
    git_source = None
    if baseline_git_ref is not None:
        if baseline_migration is not None:
            raise ValueError('Choose a baseline SQL file or Git commit, not both')
        inputs['supplied-baseline.sql'], git_source = git_baseline(project, baseline_git_ref, baseline_git_path)
    elif baseline_git_path is not None:
        raise ValueError('--baseline-git-path requires --baseline-git-ref')
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output/'inputs'
    snapshot.mkdir()
    for name, content in inputs.items():
        (snapshot/name).write_bytes(content)
    status = {'status': 'unverified', 'input_sha256': {name: hashlib.sha256(raw).hexdigest()
              for name, raw in inputs.items()}, 'steps': []}
    status['candidate_source'] = ('supplied-candidate.json (all five plan fields)' if candidate_plan
                                  else 'candidate.json adapters and supplied-candidate.sql' if candidate_migration_file is not None or candidate_git is not None
                                  else 'candidate.json adapters and migration.sql')
    candidate_sql_source = None
    if candidate_migration_file is not None:
        source = candidate_migration_file.resolve()
        try:
            label = source.relative_to(Path.cwd().resolve()).as_posix()
            scope = 'Relative to invocation directory'
        except ValueError:
            label = source.name
            scope = 'Filename only; source is outside invocation directory'
        candidate_sql_source = {'path': label, 'path_scope': scope,
                                'snapshot': 'inputs/supplied-candidate.sql',
                                'sha256': status['input_sha256']['supplied-candidate.sql']}
        status['candidate_sql_source'] = candidate_sql_source
    elif candidate_git is not None:
        candidate_sql_source = {'path': candidate_git['path'], 'path_scope': 'Repository path at candidate commit',
                                'snapshot': 'inputs/supplied-candidate.sql',
                                'sha256': status['input_sha256']['supplied-candidate.sql'],
                                'commit': candidate_git['commit'], 'blob': candidate_git['blob']}
        status['candidate_sql_source'] = candidate_sql_source
    supplied_baseline = baseline_migration is not None or git_source is not None
    status['baseline_source'] = ('baseline.json adapters and supplied-baseline.sql' if supplied_baseline
                                else 'baseline.json (all five plan fields)')
    if git_source is not None:
        status['baseline_git'] = git_source

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
        if expected_contract_hash is not None:
            from .engine import digest
            actual = digest(json.loads(inputs['contract.json'].decode('utf-8-sig')))
            status['contract_lock'] = {'expected': expected_contract_hash, 'actual': actual,
                                     'status': 'matched' if actual == expected_contract_hash else 'changed'}
            save()
            if actual != expected_contract_hash:
                raise ValueError('Contract changed from the reviewed hash; review the contract separately before executing SQL')
        candidate_args = ['--contract', snapshot/'contract.json', '--plan',
                          snapshot/('supplied-candidate.json' if candidate_plan else 'candidate.json')]
        if candidate_plan is None:
            candidate_args += ['--migration-file', snapshot/('supplied-candidate.sql' if candidate_migration_file is not None or candidate_git is not None else 'migration.sql')]
        baseline_args = ['--baseline-plan', snapshot/'baseline.json']
        if supplied_baseline:
            baseline_args += ['--baseline-migration-file', snapshot/'supplied-baseline.sql']
        code = run('cutover', candidate_args+baseline_args+[
                   '--bundle', output/'comparison.zip', '--output', output/'candidate-report.json'], 'comparison')
        run('cutover.audit_bundle', ['--bundle', output/'comparison.zip', '--markdown', output/'review.md',
                                    '--html', output/'review.html'], 'audit')
        status['offline_review'] = 'review.html'
        if expected_contract_hash is not None:
            with (output/'review.md').open('a', encoding='utf-8') as note:
                note.write('\n## Reviewed contract lock\n\nMatched canonical SHA-256: `'+expected_contract_hash+
                           '`. Checked before SQL execution and retained in review-status.json. '
                           'Formatting and key order do not change this identity; schema, adapters, seeds and payloads do. '
                           'This is not a signature. Changes to the expected hash require separate review.\n')
        if git_source is not None or candidate_sql_source is not None:
            from .review_html import render_review
            with zipfile.ZipFile(output/'comparison.zip') as archive:
                audited_reports = [json.loads(archive.read(prefix+'report.json'))
                                   for prefix in ('baseline/', 'candidate/')]
            (output/'review.html').write_text(render_review(audited_reports, git_source, candidate_sql_source), encoding='utf-8')
            if git_source is not None:
                with (output/'review.md').open('a', encoding='utf-8') as note:
                    note.write('\n## Baseline SQL source\n\nLocal Git snapshot (not a signature):\n\n'+
                           '```json\n'+json.dumps(git_source, ensure_ascii=True, indent=2)+'\n```\n\n'+
                           'Exact bytes are retained in `inputs/supplied-baseline.sql`. '
                           'Only migration SQL comes from Git; adapters and contract are the supplied project inputs.\n')
        if candidate_sql_source is not None:
            with (output/'review.md').open('a', encoding='utf-8') as note:
                note.write('\n## Candidate SQL source\n\n'+'```json\n'+json.dumps(candidate_sql_source, ensure_ascii=True, indent=2)+'\n```\n\n'+
                           'Byte hash of the retained SQL snapshot, including any BOM and line endings. '
                           'Adapters still come from candidate.json; this is not a whole-PR verification or signature.\n')
        report = json.loads((output/'candidate-report.json').read_text(encoding='utf-8'))
        if expected_contract_hash is not None and report['contract_hash'] != expected_contract_hash:
            raise ValueError('Executed report differs from the reviewed contract hash')
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
                executed_baseline = output/'executed-baseline.json'
                executed_baseline.write_text(json.dumps(baseline['plan'], ensure_ascii=True, indent=2)+'\n',
                                             encoding='utf-8')
                kit_args += ['--ci-control', executed_baseline]
            if run('cutover', kit_args, 'pr-kit') != 0:
                raise ValueError('Passing candidate could not produce a verified PR kit')
            with zipfile.ZipFile(output/'pending-pr-kit.zip') as archive:
                kit_report = json.loads(archive.read('evidence/report.json'))
                if '--ci-control' in kit_args:
                    control_report = json.loads(archive.read('evidence/unsafe-control-report.json'))
                    for key in ('plan_hash', 'contract_hash', 'suite_hash', 'engine_sha256'):
                        if control_report[key] != baseline[key]:
                            raise ValueError('PR kit control differs from the executed baseline')
            for key in ('plan_hash', 'contract_hash', 'suite_hash', 'engine_sha256'):
                if kit_report[key] != report[key]:
                    raise ValueError('PR kit identities differ from the reviewed comparison')
            (output/'pending-pr-kit.zip').rename(output/'pr-kit.zip')
            status['pr_kit'] = 'pr-kit.zip'
        with zipfile.ZipFile(output/'comparison.zip') as archive:
            original = json.loads(archive.read('baseline/report.json'))
        (output/'pr-summary.md').write_text(render_pr_summary(original, report, git_source, candidate_sql_source), encoding='utf-8')
        status['pr_summary'] = 'pr-summary.md'
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
    candidate = parser.add_mutually_exclusive_group()
    candidate.add_argument('--candidate-plan', type=Path,
                        help='Review all fields of a saved candidate JSON instead of project candidate.json/migration.sql')
    candidate.add_argument('--candidate-migration-file', type=Path,
                        help='Snapshot actual candidate UTF-8 SQL; overrides only migration, retaining candidate.json adapters')
    candidate.add_argument('--candidate-git-ref',
                          help='Read candidate SQL from a local Git commit; no fetch or checkout changes')
    parser.add_argument('--candidate-git-path',
                        help='Repository-relative candidate SQL path; defaults to project/migration.sql')
    parser.add_argument('--expected-contract-hash',
                        help='Reviewed canonical contract SHA-256; mismatch stops before SQL and retains unverified evidence')
    baseline = parser.add_mutually_exclusive_group()
    baseline.add_argument('--baseline-migration-file', type=Path,
                        help='Snapshot actual original SQL, overriding only the baseline.json migration')
    baseline.add_argument('--baseline-git-ref',
                          help='Read original SQL from a local Git commit; no fetch or checkout changes')
    parser.add_argument('--baseline-git-path',
                        help='Repository-relative SQL path at that commit; defaults to project/migration.sql')
    args = parser.parse_args()
    try:
        code = review(args.project.resolve(), args.out.resolve(), args.bob_workspace,
                      args.candidate_plan.resolve() if args.candidate_plan else None,
                      args.baseline_migration_file.resolve() if args.baseline_migration_file else None,
                      args.baseline_git_ref, args.baseline_git_path, args.expected_contract_hash,
                      args.candidate_migration_file.resolve() if args.candidate_migration_file else None,
                      args.candidate_git_ref, args.candidate_git_path)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(f'{"PASS" if code == 0 else "BLOCKED"}: independently audited comparison and review in {args.out}')
    report = json.loads((args.out/'candidate-report.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(args.out/'comparison.zip') as archive:
        original = json.loads(archive.read('baseline/report.json'))
    print(f'Original baseline: {original["status"].upper()} {original["passed"]}/{original["total"]}')
    print(f'Current candidate: {report["status"].upper()} {report["passed"]}/{report["total"]}')
    print('Probe totals can differ with each plan\'s migration boundaries; this is bounded rehearsal evidence.')
    if code == 0 and original.get('witness'):
        print('Original failure retained in the comparison (not a failure of the current candidate):')
        for line in terminal_witness(original):
            print(line)
    for line in terminal_witness(report):
        print(line)
    print('Compact PR note: pr-summary.md. Keep the relative evidence links with its review folder.')
    print('Offline walkthrough: review.html. Open locally; it displays evidence without running SQL or using the network.')
    if args.expected_contract_hash:
        print('Reviewed contract hash matched: '+args.expected_contract_hash.lower())
    if code == 0:
        print('Passing PR kit: pr-kit.zip. Inspect its four files before copying into your repository.')
    else:
        print('No PR kit exported. Original failure and current candidate retained; edit and use a new review folder.')
        if args.bob_workspace:
            print('Local Bob handoff: bob-repair-workspace.zip. Inspect its README; export does not invoke Bob.')
    return code


if __name__ == '__main__':
    sys.exit(main())
