"""Create an auditable Bob repair workspace without bundled passing plans.

The generated sibling directory is never overwritten. Bob's candidate is later
replayed in the source project, which retains the full fixed evaluator.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = ('parcel', 'contacts')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    files = [
        Path('.bob/custom_modes.yaml'),
        Path('LICENSE'),
        Path('configure_bob.py'),
        Path('mcp_server.py'),
        Path('requirements-mcp.txt'),
        Path('cutover/__init__.py'),
        Path('cutover/__main__.py'),
        Path('cutover/engine.py'),
        Path('cutover/reporting.py'),
        Path('cutover/service.py'),
        Path('cutover/worker.py'),
    ]
    for case in CASES:
        files.extend(Path('examples') / case / f'{name}.json'
                     for name in ('contract', 'rename', 'backfill', 'late_bridge'))
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', required=True, type=Path,
                        help='Absolute path to the Python interpreter with requirements-mcp.txt installed')
    args = parser.parse_args()
    interpreter = args.python.resolve()
    if not interpreter.is_file():
        parser.error('The requested Python interpreter does not exist.')
    try:
        subprocess.run([str(interpreter), '-c', 'import mcp'], check=True,
                       capture_output=True, timeout=45)
    except subprocess.TimeoutExpired:
        parser.error('That interpreter did not finish an MCP import within 45 seconds.')
    except subprocess.CalledProcessError:
        parser.error('That interpreter cannot import the installed MCP SDK.')

    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        parser.error('Commit or set aside source changes before freezing a Bob session.')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    destination = ROOT.parent / f'cutover-bob-session-{revision[:8]}'
    if destination.exists():
        parser.error(f'Session already exists: {destination}. Reuse it or make a new source commit.')

    required = sources()
    missing = [str(relative) for relative in required if not (ROOT / relative).is_file()]
    if missing:
        parser.error(f'Required source is missing: {", ".join(missing)}')
    committed = {}
    for relative in required:
        name = relative.as_posix()
        try:
            committed[name] = subprocess.check_output(
                ['git', 'show', f'{revision}:{name}'], cwd=ROOT)
        except subprocess.CalledProcessError:
            parser.error(f'Required file is absent from source commit: {name}')

    copied = {}
    for relative in required:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(committed[relative.as_posix()])
        copied[relative.as_posix()] = digest(target)

    task = f'''# Cutover repair task for IBM Bob

This workspace was copied from source commit `{revision}`. Passing reference
plans, presentation materials and prior repair notes are intentionally absent.
The fixed evaluator is identical to the source project's `cutover/engine.py`.

Use the `Cutover release engineer` mode and the `cutover` MCP server. Call
`inspect_release` and `diagnose_reference` with `reference=late_bridge` for
Parcel. The late bridge passes completed-rollout checks but fails when old
workers write between migration statements. Explain one concrete failing
replay. Propose your own migration and new-version SQL adapter, then call
`rehearse_candidate` until you have an honestly reported result. Keep any
failed attempts. The new reader must read the target column without accessing
the old column; new updates and inserts must put their values in the target
on a trigger-free snapshot. Explicit dual-writes are valid. The
target column must preserve every acknowledged value. Touching it only in a
no-op expression while returning old-column data is not a repair.
Save your final five-field plan to `work/bob-candidate.json`
and your reasoning to `work/bob-repair.md`. Do not change the fixed contract,
evaluator, seed data, schedules or oracle. State the untested boundaries.

After the Bob session, the source project will independently replay the saved
candidate and retain the actual Bob task summary and screenshots. This is a
reference-withheld exercise, not proof of a general or production-safe repair.
'''
    (destination / 'TASK.md').write_text(task, encoding='utf-8')
    (destination / 'work').mkdir(exist_ok=True)
    manifest = {
        'source_revision': revision,
        'purpose': 'Reference-withheld Bob repair session; no passing plan or presentation files copied.',
        'copied_sha256': copied,
        'withheld': [f'examples/{case}/bridge.json' for case in CASES],
        'evaluator_sha256': copied['cutover/engine.py'],
    }
    (destination / 'SESSION_MANIFEST.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    subprocess.run([str(interpreter), str(destination / 'configure_bob.py'),
                    '--python', str(interpreter)], cwd=destination, check=True)
    assert not any((destination / 'examples' / case / 'bridge.json').exists() for case in CASES)
    # Windows can check out CRLF working files from LF Git blobs. The session
    # inventory is defined by committed bytes, not working-tree line endings.
    assert digest(destination / 'cutover/engine.py') == hashlib.sha256(committed['cutover/engine.py']).hexdigest()
    print(f'Bob session ready: {destination}')
    print(f'Source commit: {revision}; evaluator SHA-256: {manifest["evaluator_sha256"]}')


if __name__ == '__main__':
    main()
