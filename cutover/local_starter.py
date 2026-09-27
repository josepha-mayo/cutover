"""A standard-library-only local rehearsal starter; no user inputs or credentials."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def render_local_starter():
    names = ['LICENSE', 'cutover/__init__.py', 'cutover/__main__.py',
        'cutover/engine.py', 'cutover/service.py', 'cutover/worker.py',
        'cutover/reporting.py', 'cutover/bundle.py', 'cutover/audit_report.py',
        'cutover/audit_bundle.py', 'cutover/selected_replay.py', 'cutover/ci_kit.py', 'cutover/init_contract.py', 'cutover/review_project.py',
        'cutover/repair_workspace.py', 'configure_bob.py', 'mcp_server.py', 'requirements-mcp.txt']
    for case in ('parcel', 'contacts', 'warehouse'):
        for plan in ('contract', 'rename', 'backfill', 'late_bridge', 'bridge'):
            name = f'examples/{case}/{plan}.json'
            if (ROOT/name).is_file():
                names.append(name)
    files = {name: (ROOT/name).read_bytes().replace(b'\r\n', b'\n') for name in names}
    files['SOURCE_INVENTORY.json'] = (json.dumps({name: hashlib.sha256(data).hexdigest()
        for name, data in files.items()}, indent=2) + '\n').encode()
    files['README.md'] = b'''# Cutover local rehearsal starter

Extract into a new folder and inspect the source. Python 3.10+ is the only
requirement for these CLI commands: no pip install, API key, Bob account or
Cutover clone is needed. The commands below execute disposable local SQLite.
They do not contact the hosted demo. Exported packets contain your SQL and values;
decide what to share. SOURCE_INVENTORY.json records bundled file hashes, not
publisher authenticity.

## Try the missing test

```text
python -m cutover --contract examples/warehouse/contract.json --plan examples/warehouse/late_bridge.json --bundle unsafe.zip
python -m cutover --contract examples/warehouse/contract.json --plan examples/warehouse/bridge.json --baseline-plan examples/warehouse/late_bridge.json --bundle comparison.zip
python -m cutover.audit_bundle --bundle comparison.zip --markdown review.md
```

The first command blocks (exit 1). The second passes its candidate (exit 0).
The last command independently verifies both plans and writes a PR note; exit 1
preserves the blocked baseline, while exit 2 means unverified. These bundled
plans are prewritten reference examples, not IBM Bob output. No saved Bob
candidate, passing claim or credentials are included in this starter.

## Bring your own migration

For a simple two-column rename, create editable inputs locally without writing
JSON by hand. This generates an unsafe backfill, not a passing repair:

```text
python -m cutover.init_contract --project "Dispatch release" --table shipments --old-column loading_bay --new-column dispatch_bay --first-value A-01 --second-value B-02 --incoming-value GATE-09 --out my-release
python -m cutover --contract my-release/contract.json --plan my-release/baseline.json --bundle my-release/unsafe.zip
```

The second command should block. Edit my-release/migration.sql and the candidate
queries, then run one local review command:

```text
python -m cutover.review_project --project my-release --out review-1
```

It snapshots the four actual inputs, freshly compares the original and candidate,
independently audits the packet, writes review.md and retains logs. A passing
candidate also exports pr-kit.zip with the reviewed contract lock; a blocked or
unverified candidate does not produce a ready PR kit. Existing review folders
are refused. Inspect kit files before copying them into your repository.

Read my-release/README.md for the individual repair and comparison commands. Inspect and adapt the synthetic schema to your real old
queries before relying on it. Existing output folders are refused.

For a blocked candidate, optionally create its Bob handoff entirely locally:

```text
python -m cutover.review_project --project my-release --out review-for-bob --bob-workspace
```

The verified blocked review includes bob-repair-workspace.zip with the exact
failed inputs, fixed evaluator, task and local MCP setup. Extract into a new
folder and follow its README. Optional IDE integration requires the pinned MCP
SDK and your Bob account; ordinary CLI review still needs only Python. Exporting
does not invoke Bob, establish IDE acceptance or supply a passing repair. A
passing or unverified candidate does not export a repair workspace.

Bring a saved repair plan back without copying its SQL into separate files:

```text
python -m cutover.review_project --project my-release --candidate-plan bob-workspace/work/bob-candidate.json --out review-after-bob
```

This explicitly reviews all five fields of the supplied JSON, including its
migration. Project candidate.json and migration.sql are retained as inputs but
do not override that candidate. The supplied file is snapshotted byte for byte;
the project and original failure stay unchanged. No Bob authorship is inferred.

If the original migration lives in a checked-in SQL file, add
`--baseline-migration-file migrations/original.sql`. Its bytes are snapshotted
and only the baseline migration is overridden; the fixed old contract and
baseline adapters stay unchanged. The optional unsafe control in a passing PR
kit uses that exact executed baseline, with matching evidence identities.

For more complex contracts, copy a sample contract and plan into new files. Set your schema, synthetic seed
records, test payloads and fixed old read/write/insert queries in the contract.
Set the new read/write/insert adapters in each plan. The reader must return all
records as id and value; update/insert use named :id and :value inputs.

```text
python -m cutover --contract contract.json --plan candidate.json --migration-file migrations/repaired.sql --baseline-plan baseline.json --baseline-migration-file migrations/original.sql --bundle private-comparison.zip
python -m cutover.audit_bundle --bundle private-comparison.zip --markdown private-review.md
```

Both actual SQL files override only their respective migration. The comparison
keeps different statement boundaries separate, names regressions and freshly
replays the first new regression. A pass is bounded sequential SQLite evidence,
not production approval or support for other database engines.

After a candidate passes, export a pinned PR gate locally:

```text
python -m cutover --contract contract.json --plan candidate.json --migration-file migrations/repaired.sql --ci-kit pr-kit.zip
```

Inspect the kit README and its four listed files before copying them into your
repository. Keep your reviewed contract lock. For optional Bob repair integration,
use the full Cutover checkout or a blocked rehearsal's local Bob workspace:
https://github.com/josepha-mayo/cutover
'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()
