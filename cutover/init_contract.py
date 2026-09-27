"""Create local inputs for a bounded SQLite column migration with synthetic values."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def read_sql_file(path, label):
    with path.open('rb') as source:
        raw = source.read(65537)
    sql = raw.decode('utf-8-sig')
    if len(raw) > 65536 or not sql.strip() or '\0' in sql or len(sql) > 12000:
        raise ValueError(f'{label} must be nonempty UTF-8 without NUL, at most 64 KiB and 12,000 characters')
    return raw, sql


def build_contract(project, table, old_column, new_column, first, second, incoming):
    if not project.strip() or len(project) > 100:
        raise ValueError('Project name must contain 1–100 characters')
    for name in (table, old_column, new_column):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}', name):
            raise ValueError('Table and column names must be simple SQL identifiers, up to 63 characters')
    if old_column.lower() == new_column.lower() or 'id' in (old_column.lower(), new_column.lower()):
        raise ValueError('Old/new columns must differ; id is reserved')
    if any(not value or len(value) > 1000 for value in (first, second)) or len(incoming) > 1000:
        raise ValueError('Seed values must be nonempty and all values at most 1000 characters')
    payloads = list(dict.fromkeys([incoming, "O'Connell", '0', '東京-棚', '']))
    t, old, new = (f'"{name}"' for name in (table, old_column, new_column))
    contract = dict(project=project.strip(), summary=f'Rehearse {old_column} to {new_column} while old workers remain.',
        table=table, old_column=old_column, new_column=new_column,
        schema=f'CREATE TABLE {t} (id INTEGER PRIMARY KEY, {old} TEXT NOT NULL);',
        seed_sql=f'INSERT INTO {t} (id, {old}) VALUES (?, ?)', seed=[[1, first], [2, second]],
        old=dict(read=f'SELECT id, {old} AS value FROM {t} ORDER BY id',
            write=f'UPDATE {t} SET {old} = :value WHERE id = :id',
            insert=f'INSERT INTO {t} (id, {old}) VALUES (:id, :value)'), payloads=payloads)
    plan = dict(name='One-time backfill: edit and rehearse before use',
        migration=f'ALTER TABLE {t} ADD COLUMN {new} TEXT;\nUPDATE {t} SET {new} = {old};',
        read=f'SELECT id, {new} AS value FROM {t} ORDER BY id',
        write=f'UPDATE {t} SET {new} = :value WHERE id = :id',
        insert=f'INSERT INTO {t} (id, {old}, {new}) VALUES (:id, :value, :value)')
    return contract, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'table', 'old-column', 'new-column', 'first-value', 'second-value', 'incoming-value'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--out', type=Path, required=True, help='New folder; existing folders are refused')
    parser.add_argument('--migration-file', type=Path,
                        help='Snapshot UTF-8 SQL instead of generating a backfill (64 KiB, 12,000 characters, no NUL)')
    parser.add_argument('--schema-file', type=Path,
                        help='Use existing single-table SQLite DDL with synthetic seed values; validated locally before saving')
    for operation in ('read', 'write', 'insert'):
        parser.add_argument('--old-'+operation+'-file', type=Path,
                            help='Snapshot the old-worker SQL; validated with synthetic seeds and payloads before saving')
    args = parser.parse_args()
    try:
        contract, plan = build_contract(args.project, args.table, args.old_column, args.new_column,
                                       args.first_value, args.second_value, args.incoming_value)
        schema_bytes = None
        if args.schema_file is not None:
            schema_bytes, schema = read_sql_file(args.schema_file, 'Schema DDL')
            contract['schema'] = schema
        old_files = {}
        for operation in ('read', 'write', 'insert'):
            source = getattr(args, 'old_'+operation+'_file')
            if source is not None:
                raw, sql = read_sql_file(source, 'Old-worker '+operation+' SQL')
                old_files[operation] = raw
                contract['old'][operation] = sql
        migration_bytes = (plan['migration']+'\n').encode('utf-8')
        if args.migration_file is not None:
            migration_bytes, sql = read_sql_file(args.migration_file, 'Migration SQL')
            plan['migration'] = sql
            plan['name'] = ('Imported original SQL: '+args.migration_file.name)[:100]
        # Validate fixed old queries on disposable SQLite before saving any inputs.
        from .service import validate_imported_contract
        validate_imported_contract(contract)
        args.out.mkdir(parents=True, exist_ok=False)
        for name, data in [('contract.json', contract), ('baseline.json', plan), ('candidate.json', plan)]:
            (args.out/name).write_text(json.dumps(data, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')
        (args.out/'migration.sql').write_bytes(migration_bytes)
        if schema_bytes is not None:
            (args.out/'schema.sql').write_bytes(schema_bytes)
        for operation, raw in old_files.items():
            (args.out/('old-'+operation+'.sql')).write_bytes(raw)
        schema_scope = ('Your supplied schema DDL is retained byte-for-byte in schema.sql and decoded into contract.json. '
                        'The source was not edited. Exactly one named table is supported, without initial views or triggers; '
                        'id and the old column must exist, and the new column must be absent. Indexes and extra columns may remain '
                        'when the configured old queries work with your synthetic seeds and inserts. '
                        'Extra-column values are not part of the tracked write ledger. This does not export live rows or verify the whole schema.'
                        if schema_bytes is not None else
                        'The schema is a generated synthetic two-column SQLite starter. Inspect and adapt it to your fixed old-worker contract.')
        adapter_scope = ('Supplied old-worker SQL replaces only its corresponding generated query. Exact bytes are retained '
                         'in old-read.sql, old-write.sql and/or old-insert.sql; decoded SQL is fixed in contract.json. '
                         'The reader must return id/value; writes and inserts use :id and :value. All configured old queries '
                         'were validated with these synthetic seeds and payloads before saving. Queries not supplied remain generated.'
                         if old_files else 'Old-worker queries are generated templates; inspect and adapt them before use.')
        starting_sql = ('Your supplied SQL was copied byte-for-byte to migration.sql and decoded into both original plans. '
                        'The source file was not edited. No verdict is inferred from importing it.' if args.migration_file else
                        'The generated one-time backfill should block: a successful new-version smoke test does not protect old-worker writes after the copy.')
        (args.out/'README.md').write_text(f'''# Your local migration rehearsal

{schema_scope} Seed values and incoming writes are supplied synthetic examples, not database rows. No passing repair is supplied. {adapter_scope} New-worker queries remain generated templates: inspect them before use. Keep baseline.json as the original candidate; edit migration.sql and candidate.json for the repair. No SQL has been sent to the hosted demo.

After editing, run one review from the extracted runtime folder:

```text
python -m cutover.review_project --project "{args.out.as_posix()}" --out review-1
```

This snapshots the four input files, compares both plans, independently audits the packet and writes review.md and review.html. Open review.html locally to follow the recorded steps without executing SQL or using the network. A passing candidate also exports pr-kit.zip; inspect its four files before copying them into your repository. Blocked/unverified candidates do not produce a ready PR kit. Existing output folders are refused; use review-2 for the next attempt. The exit follows the candidate: 0 passing, 1 blocked, 2 unverified. The original baseline remains in the comparison.

To hand a verified blocked candidate to Bob without uploading your SQL, add `--bob-workspace` to a review command with a new output folder. Its bob-repair-workspace.zip retains the failed inputs and fixed evaluator. Extract it into a new folder and follow its README for optional local MCP/IDE setup. Export does not invoke Bob or establish Bob usage; no passing repair is supplied.

To review a saved repair, add `--candidate-plan path/to/bob-candidate.json` with a new output folder. All five fields of that saved plan are executed, including its migration; project candidate.json and migration.sql cannot override it. Both the supplied file and unchanged project inputs are retained in the review snapshot. The original baseline remains fixed.

Alternatively, run each step from the extracted runtime folder:

```text
python -m cutover --contract "{args.out.as_posix()}/contract.json" --plan "{args.out.as_posix()}/baseline.json" --bundle "{args.out.as_posix()}/unsafe.zip"
python -m cutover --contract "{args.out.as_posix()}/contract.json" --plan "{args.out.as_posix()}/candidate.json" --migration-file "{args.out.as_posix()}/migration.sql" --baseline-plan "{args.out.as_posix()}/baseline.json" --bundle "{args.out.as_posix()}/comparison.zip"
python -m cutover.audit_bundle --bundle "{args.out.as_posix()}/comparison.zip" --markdown "{args.out.as_posix()}/review.md"
```

{starting_sql} No passing repair is supplied. Keep your reviewed contract fixed during comparison. A passing rehearsal remains bounded sequential SQLite evidence, not production approval. Exported evidence contains your SQL and values; choose what to share.
''', encoding='utf-8')
    except (ValueError, OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(f'Created editable local contract and original SQL in {args.out}; no verdict produced. Rehearse before use.')


if __name__ == '__main__':
    main()
