import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from cutover.local_starter import render_local_starter


class LocalContractSetupTests(unittest.TestCase):
    def test_explicit_seed_ids_support_supplied_schema_range_and_remain_in_audited_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            raw=b'CREATE TABLE shipments(id INTEGER PRIMARY KEY CHECK(id>=1000), loading_bay TEXT NOT NULL);'
            (root/'schema.sql').write_bytes(raw)
            base=[sys.executable,'-S','-m','cutover.init_contract','--project','ID-range dispatch',
                  '--table','shipments','--old-column','loading_bay','--new-column','dispatch_bay',
                  '--first-value','A-01','--second-value','B-02','--incoming-value','GATE-09','--schema-file','schema.sql']
            def run(args):return subprocess.run(args,cwd=root,capture_output=True,timeout=120)
            self.assertEqual(run(base+['--out','default-ids']).returncode,2)
            self.assertFalse((root/'default-ids').exists())
            created=run(base+['--first-id','1001','--second-id','1009','--out','release'])
            self.assertEqual(created.returncode,0,created.stderr)
            contract=json.loads((root/'release/contract.json').read_text(encoding='utf-8'))
            self.assertEqual(contract['seed'],[[1001,'A-01'],[1009,'B-02']])
            self.assertEqual((root/'release/schema.sql').read_bytes(),raw)
            result=run([sys.executable,'-S','-m','cutover.review_project','--project','release','--out','review'])
            self.assertEqual(result.returncode,1,result.stderr)
            audit=run([sys.executable,'-S','-m','cutover.audit_bundle','--bundle','review/pr-review.zip'])
            self.assertEqual(audit.returncode,1,audit.stderr)
            with zipfile.ZipFile(root/'review/comparison.zip') as archive:
                checked=json.loads(archive.read('candidate/contract.json'))
                report=json.loads(archive.read('candidate/report.json'))
                self.assertEqual(checked['seed'],contract['seed'])
                self.assertEqual(report['witness']['seed_id'],1001)
                ids={e['params']['id'] for probe in report['results'] for e in probe['trace'] if e.get('params')}
                self.assertTrue({1001,1009,1010}.issubset(ids))
            for first,second in [('1001','1001'),('0','1009'),('1001','1000001')]:
                rejected=run(base+['--first-id',first,'--second-id',second,'--out','invalid'])
                self.assertEqual(rejected.returncode,2)
                self.assertFalse((root/'invalid').exists())

    def test_setup_file_errors_identify_input_and_recovery_without_saving(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            base = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'File diagnostics',
                '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                '--first-value', 'A-01', '--second-value', 'B-02', '--incoming-value', 'GATE-09']
            cases = [('--schema-file', 'Schema DDL', None, 'relative paths start'),
                     ('--old-write-file', 'Old-worker write SQL', b'\xff', 'Save a UTF-8 copy'),
                     ('--new-insert-file', 'New-worker insert SQL', b'x'*65537, 'not a database dump'),
                     ('--migration-file', 'Migration SQL', b'SELECT 1;\0', 'without NUL bytes')]
            for i, (flag, label, raw, recovery) in enumerate(cases):
                source = root/('input-'+str(i)+'.sql')
                if raw is not None:
                    source.write_bytes(raw)
                output = 'release-'+str(i)
                result = subprocess.run(base+[flag, source.name, '--out', output], cwd=root,
                    capture_output=True, timeout=120)
                self.assertEqual(result.returncode, 2)
                error = result.stderr.decode('utf-8')
                self.assertIn(label+' file '+source.name, error)
                self.assertIn(recovery, error)
                self.assertFalse((root/output).exists())
                if raw is not None:
                    self.assertEqual(source.read_bytes(), raw)

    def test_supplied_new_queries_are_retained_in_both_plans_and_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            queries = {
                'read': b'\xef\xbb\xbfSELECT id,COALESCE(dispatch_bay,loading_bay) AS value FROM shipments ORDER BY id;\r\n',
                'write': b'UPDATE shipments SET dispatch_bay=:value,loading_bay=:value WHERE id=:id;\r\n',
                'insert': b'INSERT INTO shipments(id,loading_bay,dispatch_bay) VALUES(:id,:value,:value);\r\n-- supplied new inserter\r\n'}
            command = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'Supplied new worker',
                '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                '--first-value', 'A-01', '--second-value', 'B-02', '--incoming-value', 'GATE-09']
            for operation, raw in queries.items():
                (root/(operation+'.sql')).write_bytes(raw)
                command += ['--new-'+operation+'-file', operation+'.sql']
            def run(args):
                return subprocess.run(args, cwd=root, capture_output=True, timeout=120)
            created = run(command+['--out', 'release'])
            self.assertEqual(created.returncode, 0, created.stderr)
            for name in ('baseline.json', 'candidate.json'):
                plan = json.loads((root/'release'/name).read_text(encoding='utf-8'))
                for operation, raw in queries.items():
                    self.assertEqual(plan[operation], raw.decode('utf-8-sig'))
                    self.assertEqual((root/('release/new-'+operation+'.sql')).read_bytes(), raw)
                    self.assertEqual((root/(operation+'.sql')).read_bytes(), raw)
            reviewed = run([sys.executable, '-S', '-m', 'cutover.review_project', '--project', 'release', '--out', 'review'])
            self.assertEqual(reviewed.returncode, 1, reviewed.stderr)
            with zipfile.ZipFile(root/'review/comparison.zip') as archive:
                for prefix in ('baseline', 'candidate'):
                    report = json.loads(archive.read(prefix+'/report.json'))
                    for operation, raw in queries.items():
                        self.assertEqual(report['plan'][operation], raw.decode('utf-8-sig'))
                    self.assertTrue(any(e['action']=='new.write' and e.get('sql')==queries['write'].decode()
                        for p in report['results'] for e in p['trace']))
            (root/'read.sql').write_bytes(b'\xff')
            self.assertEqual(run(command+['--out', 'bad']).returncode, 2)
            self.assertFalse((root/'bad').exists())

    def test_supplied_old_queries_execute_and_invalid_query_has_no_template_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            queries = {
                'read': b'\xef\xbb\xbfSELECT id, loading_bay AS value FROM shipments WHERE id>0 ORDER BY id;\r\n',
                'write': b'UPDATE shipments SET loading_bay=:value WHERE id=:id AND loading_bay IS NOT NULL;\r\n',
                'insert': b'INSERT INTO shipments(id,loading_bay) VALUES(:id,:value);\r\n-- retained old inserter\r\n'}
            for operation, raw in queries.items():
                (root/('query-'+operation+'.sql')).write_bytes(raw)
            command = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'Supplied old worker',
                '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                '--first-value', 'A-01', '--second-value', 'B-02', '--incoming-value', 'GATE-09']
            for operation in queries:
                command += ['--old-'+operation+'-file', 'query-'+operation+'.sql']
            def run(args):
                return subprocess.run(args, cwd=root, capture_output=True, timeout=120)
            created = run(command+['--out', 'release'])
            self.assertEqual(created.returncode, 0, created.stderr)
            contract = json.loads((root/'release/contract.json').read_text(encoding='utf-8'))
            for operation, raw in queries.items():
                self.assertEqual(contract['old'][operation], raw.decode('utf-8-sig'))
                self.assertEqual((root/('release/old-'+operation+'.sql')).read_bytes(), raw)
                self.assertEqual((root/('query-'+operation+'.sql')).read_bytes(), raw)
            reviewed = run([sys.executable, '-S', '-m', 'cutover.review_project', '--project', 'release', '--out', 'review'])
            self.assertEqual(reviewed.returncode, 1, reviewed.stderr)
            with zipfile.ZipFile(root/'review/comparison.zip') as archive:
                self.assertEqual(json.loads(archive.read('candidate/contract.json'))['old'], contract['old'])
                report = json.loads(archive.read('candidate/report.json'))
                executed = [e['sql'] for p in report['results'] for e in p['trace'] if e['action']=='old.write']
                self.assertIn(contract['old']['write'], executed)
            for operation, invalid in [('read', b'SELECT id,loading_bay AS value FROM shipments WHERE id=-1'),
                    ('write', b'UPDATE shipments SET loading_bay=:value WHERE id=-1'),
                    ('insert', b'INSERT INTO shipments(id,loading_bay) VALUES(:id,NULL)')]:
                (root/('query-'+operation+'.sql')).write_bytes(invalid)
                rejected = run(command+['--out', 'bad-'+operation])
                self.assertEqual(rejected.returncode, 2, rejected.stderr)
                self.assertFalse((root/('bad-'+operation)).exists())
                (root/('query-'+operation+'.sql')).write_bytes(queries[operation])

    def test_existing_schema_is_retained_and_executed_without_importing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            raw = (b'\xef\xbb\xbfCREATE TABLE shipments (id INTEGER PRIMARY KEY, loading_bay TEXT NOT NULL, '
                   b'tenant TEXT NOT NULL DEFAULT \'synthetic-tenant\');\r\n'
                   b'CREATE INDEX shipments_loading ON shipments(loading_bay);\r\n')
            source = root/'existing-schema.sql'; source.write_bytes(raw)
            command = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'Existing dispatch schema',
                '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                '--first-value', 'A-01', '--second-value', 'B-02', '--incoming-value', 'GATE-09',
                '--schema-file', source.name, '--out', 'release']
            def run(args):
                return subprocess.run(args, cwd=root, capture_output=True, timeout=120)
            created = run(command)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual((root/'release/schema.sql').read_bytes(), raw)
            contract = json.loads((root/'release/contract.json').read_text(encoding='utf-8'))
            self.assertEqual(contract['schema'], raw.decode('utf-8-sig'))
            self.assertEqual(contract['seed'], [[1, 'A-01'], [2, 'B-02']])
            reviewed = run([sys.executable, '-S', '-m', 'cutover.review_project', '--project', 'release', '--out', 'review'])
            self.assertEqual(reviewed.returncode, 1, reviewed.stderr)
            with zipfile.ZipFile(root/'review/comparison.zip') as archive:
                self.assertEqual(json.loads(archive.read('baseline/contract.json'))['schema'], raw.decode('utf-8-sig'))
            audited = run([sys.executable, '-S', '-m', 'cutover.audit_bundle', '--bundle', 'review/comparison.zip'])
            self.assertEqual(audited.returncode, 1, audited.stderr)
            self.assertEqual(source.read_bytes(), raw)
            self.assertIn('Extra-column values are not part of the tracked write ledger',
                          (root/'release/README.md').read_text(encoding='utf-8'))
            invalid_schemas = [b'', b'SELECT 1;\0', b'\xff', b'x'*65537,
                b'CREATE TABLE shipments(id INTEGER PRIMARY KEY, loading_bay TEXT, required TEXT NOT NULL);',
                b'CREATE TABLE shipments(id INTEGER PRIMARY KEY, loading_bay TEXT); CREATE TABLE other(id INTEGER);',
                b'CREATE TABLE shipments(id INTEGER PRIMARY KEY, loading_bay TEXT, dispatch_bay TEXT);']
            for index, invalid in enumerate(invalid_schemas):
                source.write_bytes(invalid)
                rejected = command[:-1]+['rejected-'+str(index)]
                self.assertEqual(run(rejected).returncode, 2)
                self.assertFalse((root/('rejected-'+str(index))).exists())

    def test_supplied_sql_is_the_executed_original_and_invalid_inputs_create_no_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            raw = b'\xef\xbb\xbfALTER TABLE "shipments" ADD COLUMN "dispatch_bay" TEXT;\r\n-- original reader sees NULL, not a generated copy\r\n'
            source = root/'original.sql'; source.write_bytes(raw)
            args = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'Actual SQL',
                    '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                    '--first-value', 'A-01', '--second-value', 'B-02', '--incoming-value', 'GATE-09',
                    '--migration-file', 'original.sql', '--out', 'release']
            def run(command):
                return subprocess.run(command, cwd=root, capture_output=True, timeout=120)
            result = run(args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root/'release/migration.sql').read_bytes(), raw)
            for name in ('baseline.json', 'candidate.json'):
                self.assertEqual(json.loads((root/'release'/name).read_text(encoding='utf-8'))['migration'], raw.decode('utf-8-sig'))
            reviewed = run([sys.executable, '-S', '-m', 'cutover.review_project', '--project', 'release', '--out', 'review'])
            self.assertEqual(reviewed.returncode, 1, reviewed.stderr)
            with zipfile.ZipFile(root/'review/comparison.zip') as archive:
                for prefix in ('baseline/', 'candidate/'):
                    self.assertEqual(json.loads(archive.read(prefix+'report.json'))['plan']['migration'], raw.decode('utf-8-sig'))
            self.assertEqual(source.read_bytes(), raw)
            readme = (root/'release/README.md').read_text(encoding='utf-8')
            self.assertIn('No verdict is inferred', readme)
            self.assertNotIn('generated one-time backfill should block', readme)
            for invalid in (b'', b'\xff', b'x'*65537, b'x'*12001, b'SELECT 1;\0'):
                source.write_bytes(invalid)
                bad = args[:-1]+['invalid-release']
                self.assertEqual(run(bad).returncode, 2)
                self.assertFalse((root/'invalid-release').exists())

    def test_actual_extracted_private_setup_blocks_replays_and_preserves_existing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            setup = [sys.executable, '-S', '-m', 'cutover.init_contract', '--project', 'Private dispatch',
                '--table', 'shipments', '--old-column', 'loading_bay', '--new-column', 'dispatch_bay',
                '--first-value', "O'Connell", '--second-value', '東京-棚', '--incoming-value', '',
                '--out', 'my-release']
            run = subprocess.run(setup, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(run.returncode, 0, run.stderr)
            contract = json.loads((root/'my-release/contract.json').read_text(encoding='utf-8'))
            self.assertEqual(contract['seed'], [[1, "O'Connell"], [2, '東京-棚']])
            self.assertEqual(contract['payloads'][0], '')
            args = [sys.executable, '-S', '-m', 'cutover', '--contract', 'my-release/contract.json',
                    '--plan', 'my-release/baseline.json', '--bundle', 'my-release/unsafe.zip']
            run = subprocess.run(args, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(run.returncode, 1, run.stderr)
            with zipfile.ZipFile(root/'my-release/unsafe.zip') as archive:
                report = json.loads(archive.read('report.json'))
                self.assertEqual(report['witness']['payload'], '')
                self.assertEqual(report['status'], 'blocked')
            audit = subprocess.run([sys.executable, '-S', '-m', 'cutover.audit_bundle',
                '--bundle', 'my-release/unsafe.zip'], cwd=root, capture_output=True, timeout=120)
            self.assertEqual(audit.returncode, 1, audit.stderr)
            original = (root/'my-release/contract.json').read_bytes()
            again = subprocess.run(setup, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(again.returncode, 2)
            self.assertEqual((root/'my-release/contract.json').read_bytes(), original)
            invalid = setup.copy()
            invalid[invalid.index('shipments')] = 'shipments; DROP TABLE shipments'
            invalid[-1] = 'invalid-release'
            rejected = subprocess.run(invalid, cwd=root, capture_output=True, timeout=120)
            self.assertEqual(rejected.returncode, 2)
            self.assertFalse((root/'invalid-release').exists())
