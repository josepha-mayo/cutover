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
        'cutover/audit_bundle.py', 'cutover/review_html.py', 'cutover/selected_replay.py', 'cutover/ci_kit.py', 'cutover/init_contract.py', 'cutover/review_project.py',
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

If you already have migration SQL, add `--migration-file path/to/original.sql`
to the setup command. It copies the exact UTF-8 file (up to 64 KiB) into the
new project and both original plans, leaving the source untouched. SQL is also
limited to 12,000 characters without NUL bytes, matching the review command. Importing
does not establish a verdict. The generated schema and old/new queries are
still a two-column starter: inspect and adapt them to your actual contract.

To retain existing SQLite DDL instead of the generated table, also add
`--schema-file path/to/schema.sql`. It snapshots that UTF-8 file and executes
its decoded schema in disposable local SQLite before saving the project.
The schema must have exactly the named table, id and the old column, without
the new column or initial views/triggers. Indexes and extra columns can remain
if the generated old reader/updater/inserter work with your synthetic seeds;
required extra columns without usable defaults are refused. No live database
rows are imported. Extra-column values are not tracked by the write ledger.
Inspect the generated adapters; this is not whole-schema/application verification.

To retain existing old-worker queries, add any of `--old-read-file old-read.sql`,
`--old-write-file old-write.sql`, `--old-insert-file old-insert.sql` to setup.
The reader returns id/value; writes and inserts use :id/:value parameters.
Each supplied UTF-8 file replaces only that old query, retains its exact bytes
in the project, and puts decoded SQL into the fixed contract. All old queries
must work with the synthetic seeds/payloads before the folder is saved; invalid
queries are refused rather than replaced by defaults. Unsupplied old queries
remain generated templates. Inspect every adapter before use.
No queries are inferred from application source and no production rows are copied.

Supply the new-worker queries with `--new-read-file new-read.sql`,
`--new-write-file new-write.sql`, `--new-insert-file new-insert.sql` as needed.
These replace corresponding generated new queries in both initial plans and
retain their exact source bytes in the project. Setup validates input shape,
not new-query execution: the later rehearsal executes them with the migration.
Missing flags leave that query generated; no passing claim or repair is inferred.
The new reader must return id/value from the new column without reading the old
column. A fallback such as COALESCE(new, old) remains blocked as an adapter-contract
failure even when values match. New writes/inserts must store the payload directly
in the new column; explicit dual-writes are supported.

```text
python -m cutover.review_project --project my-release --out review-1
```

It snapshots the four actual inputs, freshly compares the original and candidate,
independently audits the packet, writes review.md and review.html, and retains logs.
The terminal also shows a bounded recorded counterexample for a blocked candidate:
operation sequence, expected data and observed data. Long values are shortened only
for display; the packet and walkthrough retain the full evidence.
After a passing repair, it still shows the original blocked verdict and its
counterexample, clearly separated from the current passing candidate. Probe totals
can differ because migration boundary probes depend on each plan.
Open review.html locally to inspect verdicts, exact SQL and each recorded replay step. It needs no
network access or server and does not execute SQL or reverify itself. The page is
unsigned; share only when its included SQL/values are appropriate for the reviewer.
For an existing packet: `python -m cutover.audit_bundle --bundle comparison.zip --html review.html`.
For later attempts on a reviewed contract, add
`--expected-contract-hash REVIEWED_SHA256` to review_project. Take that hash from
the original reviewed report's contract_hash, rather than recomputing it from
changed inputs. A mismatch retains unverified input/hash evidence and stops
before SQL, comparison or kit export. Formatting and key order are ignored;
schema, queries, seed values and payloads are covered. Intentional lock changes
need separate review; this is not a signature.
A passing
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

For a PR, read the original SQL from a locally available Git commit instead:

```text
python -m cutover.review_project --project my-release --baseline-git-ref origin/main --baseline-git-path db/relocation.sql --out review-pr
```

Requires Git and a project inside the repository. The ref resolves to an exact
commit; the note/status retain the commit, path and blob identity and the original
SQL bytes are snapshotted. No fetch, branch switch or checkout change occurs.
Without an explicit path, it reads my-release/migration.sql at that commit.
Only baseline migration SQL comes from Git; contract and adapters stay the supplied
project inputs. Missing refs/files, symlinks and files over 64 KiB are refused.
This is not a signature or a full application diff. Use either a Git ref or a
baseline SQL file, not both, and a new output folder for each attempt.

To review the actual candidate SQL elsewhere in your repository, add
`--candidate-migration-file db/relocation.sql`. Its exact UTF-8 bytes (including
BOM/line endings) are retained in inputs/supplied-candidate.sql and override only
the candidate migration. Unspecified candidate adapters still come from project candidate.json;
the copied project migration.sql remains retained but cannot override this file.
SQL must be nonempty, at most 64 KiB and 12,000 characters, without NUL. Choose
either this SQL file or --candidate-plan, not both. The comparison and passing kit
execute the same retained SQL snapshot; the source file is never edited.


To review changed worker queries directly from files, add any of
`--candidate-read-file new-read.sql`, `--candidate-write-file new-write.sql`,
`--candidate-insert-file new-insert.sql` to a review command with a new output
folder. These replace only named candidate adapters. Other adapters remain in
candidate.json; the original baseline and fixed old-worker contract do not change.
Files use the same UTF-8/64 KiB/12,000-character bounds as setup, retain their
exact bytes in inputs/supplied-candidate-<operation>.sql and are decoded into
inputs/supplied-candidate.json for execution. Source byte hashes appear in the
note/status; they are unsigned labels, not authenticated provenance. Query-file
flags can accompany a candidate migration file or Git source; a complete
--candidate-plan cannot be combined with them. The comparison and passing kit
use the same retained candidate queries.

```text
python -m cutover.review_project --project my-release --candidate-migration-file migration.sql --candidate-read-file new-read.sql --candidate-write-file new-write.sql --candidate-insert-file new-insert.sql --out review-repair
```

To review an exact committed candidate instead of the working file:

```text
python -m cutover.review_project --project my-release --baseline-git-ref origin/main --baseline-git-path db/relocation.sql --candidate-git-ref HEAD --candidate-git-path db/relocation.sql --out review-commits
```

Both SQL sources are retained from their resolved local commits, even if the
working file later changes. Candidate commit, repository path, blob and SQL byte
SHA-256 appear in the note/status and offline review. Only migration SQL comes
from Git; this does not test the whole application at either commit. Candidate
Git SQL uses the same UTF-8/size bounds as a supplied candidate SQL file. Choose
one candidate source: --candidate-plan, --candidate-migration-file or
--candidate-git-ref. --candidate-git-path requires --candidate-git-ref.

Every verified review also writes pr-summary.md: compact verdict, current or
retained-original counterexample, candidate identities and supplied source
provenance. Use it as the PR note; keep its relative links with the evidence folder
or replace them with your artifact links. Full SQL/trace evidence remains in
review.md, review.html and comparison.zip. Unverified attempts get no PR summary.

pr-review.zip is the portable handoff: extract it into a new folder to preserve
the summary links, offline viewer, full review, source snapshots, comparison and
any generated kit/workspace. Its README gives the independent comparison replay
command. Its SHA256SUMS.json is an unsigned byte inventory, not authentication of
outer notes or Git provenance. Execution logs stay in the original folder.

To verify the whole handoff without unpacking or uploading it:

    python -m cutover.audit_bundle --bundle pr-review.zip --markdown freshly-audited.md --html freshly-audited.html

This checks its unsigned byte inventory, independently replays the inner
comparison, and writes fresh evidence-only notes and a viewer. Packaged outer
notes, HTML, optional kits and Git labels remain unverified; no scripts are
extracted or executed. Exit1 preserves any verified block, including an original
failure before a passing repair. Exit2 means unverified. Use new output filenames.


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
