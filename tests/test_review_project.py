import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from cutover.local_starter import render_local_starter
from cutover.review_project import git_baseline


class LocalProjectReviewTests(unittest.TestCase):
    def test_actual_candidate_sql_overrides_stale_copy_and_binds_passing_kit(self):
        from cutover.init_contract import build_contract
        from cutover.review_project import review
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); project=root/'release';project.mkdir()
            contract, plan=build_contract('Actual PR SQL','shipments','loading_bay','dispatch_bay','A-01','B-02','GATE-09')
            reference=json.loads(Path('examples/warehouse/bridge.json').read_text(encoding='utf-8'))
            repaired=reference['migration'].replace('stock_items','shipments').replace('pick_bin','loading_bay').replace('fulfillment_bin','dispatch_bay')
            for name,data in [('contract.json',contract),('baseline.json',plan),('candidate.json',plan)]:
                (project/name).write_text(json.dumps(data),encoding='utf-8')
            (project/'migration.sql').write_text(repaired,encoding='utf-8')
            source=root/'actual-pr.sql';raw=b'\xef\xbb\xbf'+plan['migration'].replace('\n','\r\n').encode()
            source.write_bytes(raw)
            self.assertEqual(review(project,root/'unsafe',candidate_migration_file=source),1)
            report=json.loads((root/'unsafe/candidate-report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['plan']['migration'],raw.decode('utf-8-sig'))
            self.assertEqual((root/'unsafe/inputs/supplied-candidate.sql').read_bytes(),raw)
            self.assertEqual(source.read_bytes(),raw)
            import hashlib
            source_status=json.loads((root/'unsafe/review-status.json').read_text(encoding='utf-8'))['candidate_sql_source']
            self.assertEqual(source_status['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(source_status['path'],source.name)
            for artifact in ('review.md','review.html'):
                note=(root/'unsafe'/artifact).read_text(encoding='utf-8')
                self.assertIn(source_status['sha256'],note)
                self.assertIn(source.name,note)
                self.assertNotIn(str(root),note)
            self.assertFalse((root/'unsafe/pr-kit.zip').exists())
            raw=b'\xef\xbb\xbf'+repaired.replace('\n','\r\n').encode();source.write_bytes(raw)
            self.assertEqual(review(project,root/'repaired',candidate_migration_file=source),0)
            with zipfile.ZipFile(root/'repaired/pr-kit.zip') as archive:
                self.assertEqual(json.loads(archive.read('evidence/report.json'))['plan']['migration'],raw.decode('utf-8-sig'))
            self.assertEqual(source.read_bytes(),raw)
            for index,invalid in enumerate((b'',b'\xff',b'x'*12001,b'SELECT 1;\0')):
                source.write_bytes(invalid);output=root/f'invalid-{index}'
                with self.assertRaises((ValueError,UnicodeError)):
                    review(project,output,candidate_migration_file=source)
                self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError,'not both'):
                review(project,root/'conflict',candidate_plan=project/'candidate.json',candidate_migration_file=source)
            self.assertFalse((root/'conflict').exists())

    def test_terminal_counterexample_preserves_missing_null_and_escapes_untrusted_values(self):
        from cutover.review_project import terminal_witness
        report = {'witness': {'id':'window-1', 'trace':[
            {'action':'old.write','status':'ok'},
            {'action':'new.read','status':'fail','expected':{'1':"O\'Connell",'2':None},'actual':{},
             'error':'line\n\x1b[31m'}], 'failure':{'kind':'data_mismatch','message':'read differs'}}}
        output='\n'.join(terminal_witness(report))
        self.assertIn('"old.write","status":"ok"', output)
        self.assertIn('Expected: {"1":"O\'Connell","2":null}', output)
        self.assertIn('Actual: {}', output)
        self.assertIn('Error: "line\\n\\u001b[31m"', output)
        self.assertNotIn('\x1b', output)
        report['witness']['trace'][1]['expected']={'1':'x'*10000}
        self.assertLess(len('\n'.join(terminal_witness(report))),2500)
        self.assertIn('see review.html for full evidence','\n'.join(terminal_witness(report)))
        self.assertEqual(terminal_witness({'witness':None}),[])

    def test_reviewed_contract_lock_ignores_formatting_but_stops_changed_seed_before_sql(self):
        from unittest.mock import patch
        from cutover.engine import digest
        from cutover.init_contract import build_contract
        from cutover.review_project import review
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); project=root/'release'; project.mkdir()
            contract, plan = build_contract('Locked local review','shipments','loading_bay','dispatch_bay','A-01','B-02','GATE-09')
            expected = digest(contract)
            (project/'contract.json').write_text(json.dumps(dict(reversed(list(contract.items()))),indent=4),encoding='utf-8')
            for name in ('baseline.json','candidate.json'):
                (project/name).write_text(json.dumps(plan),encoding='utf-8')
            (project/'migration.sql').write_text(plan['migration'],encoding='utf-8')
            self.assertEqual(review(project,root/'matched',expected_contract_hash=expected.upper()),1)
            status=json.loads((root/'matched/review-status.json').read_text(encoding='utf-8'))
            self.assertEqual(status['contract_lock'],{'expected':expected,'actual':expected,'status':'matched'})
            self.assertEqual(status['status'],'blocked')
            contract['seed'][0][1]='Changed seed'
            (project/'contract.json').write_text(json.dumps(contract),encoding='utf-8')
            with patch('cutover.review_project.subprocess.run') as execute:
                with self.assertRaisesRegex(ValueError,'Contract changed'):
                    review(project,root/'changed',expected_contract_hash=expected)
                execute.assert_not_called()
            status=json.loads((root/'changed/review-status.json').read_text(encoding='utf-8'))
            self.assertEqual(status['status'],'unverified')
            self.assertEqual(status['steps'],[])
            self.assertEqual(status['contract_lock']['actual'],digest(contract))
            self.assertNotEqual(status['contract_lock']['actual'],expected)
            self.assertTrue((root/'changed/inputs/contract.json').exists())
            self.assertFalse((root/'changed/comparison.zip').exists())
            self.assertFalse((root/'changed/pr-kit.zip').exists())
            with self.assertRaisesRegex(ValueError,'64 hexadecimal'):
                review(project,root/'invalid',expected_contract_hash='not-a-hash')
            self.assertFalse((root/'invalid').exists())

    def test_git_baseline_reads_exact_committed_blob_and_refuses_missing_or_oversized_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.STDOUT)
            git('init')
            raw = b'\xef\xbb\xbfSELECT 1;\r\n'
            (root/'.gitattributes').write_text('* -text\n', encoding='utf-8')
            (root/'original.sql').write_bytes(raw)
            (root/'release').mkdir()
            (root/'release/migration.sql').write_bytes(raw)
            (root/'old plan.sql').write_bytes(raw)
            (root/'large.sql').write_bytes(b'x'*65537)
            git('add', '.')
            blob = git('hash-object', 'original.sql').decode().strip()
            git('update-index', '--add', '--cacheinfo', f'120000,{blob},link.sql')
            git('-c', 'user.name=Cutover test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'Original SQL')
            commit = git('rev-parse', 'HEAD').decode().strip()
            (root/'original.sql').write_bytes(b'SELECT 2;')
            observed, source = git_baseline(root, 'HEAD', 'original.sql')
            self.assertEqual(observed, raw)
            self.assertEqual(source['commit'], commit)
            self.assertEqual(source['path'], 'original.sql')
            self.assertEqual((root/'original.sql').read_bytes(), b'SELECT 2;')
            self.assertEqual(git_baseline(root/'release', 'HEAD')[0], raw)
            self.assertEqual(git_baseline(root/'release', 'HEAD', 'old plan.sql')[0], raw)
            for ref, path in [('missing-ref', 'original.sql'), ('HEAD', 'missing.sql'),
                              ('HEAD', '../original.sql'), ('HEAD', 'large.sql'), ('HEAD', '*'),
                              ('HEAD', 'release'), ('HEAD', 'link.sql')]:
                with self.subTest(ref=ref, path=path), self.assertRaises(ValueError):
                    git_baseline(root, ref, path)
    def test_blocked_repair_and_malformed_attempts_keep_separate_evidence_and_gate_only_the_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with zipfile.ZipFile(io.BytesIO(render_local_starter())) as archive:
                archive.extractall(root)
            def run(module, args):
                return subprocess.run([sys.executable, '-S', '-m', module, *args], cwd=root,
                                      capture_output=True, timeout=120)
            setup = run('cutover.init_contract', ['--project', 'Private dispatch', '--table', 'shipments',
                '--old-column', 'loading_bay', '--new-column', 'dispatch_bay', '--first-value', "O'Connell",
                '--second-value', '東京-棚', '--incoming-value', 'GATE-09', '--out', 'my-release'])
            self.assertEqual(setup.returncode, 0, setup.stderr)
            blocked = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-1', '--bob-workspace'])
            self.assertEqual(blocked.returncode, 1, blocked.stderr)
            self.assertIn(b'Recorded counterexample:', blocked.stdout)
            self.assertIn(b'Expected:', blocked.stdout)
            self.assertIn(b'Actual:', blocked.stdout)
            self.assertFalse((root/'review-1/pr-kit.zip').exists())
            self.assertTrue((root/'review-1/review.html').exists())
            workspace = root/'bob-handoff'
            with zipfile.ZipFile(root/'review-1/bob-repair-workspace.zip') as archive:
                archive.extractall(workspace)
                baseline = json.loads(archive.read('baseline-report.json'))
                self.assertEqual(baseline['passed'], 55)
                self.assertEqual(json.loads(archive.read('contract.json')),
                                 json.loads((root/'my-release/contract.json').read_text(encoding='utf-8')))
                self.assertEqual(json.loads(archive.read('baseline-plan.json')), baseline['plan'])
                self.assertNotIn('.bob/mcp.json', archive.namelist())
            checked = subprocess.run([sys.executable, '-S', 'verify_workspace.py',
                                      '--candidate', 'baseline-plan.json'], cwd=workspace,
                                     capture_output=True, timeout=30)
            self.assertEqual(checked.returncode, 1, checked.stderr)
            before = (root/'review-1/comparison.zip').read_bytes()
            # Separate supplied reference SQL is a test repair, not generated Bob output.
            reference = json.loads((root/'examples/warehouse/bridge.json').read_text(encoding='utf-8'))
            sql = reference['migration'].replace('stock_items', 'shipments').replace('pick_bin', 'loading_bay').replace('fulfillment_bin', 'dispatch_bay')
            sql = sql.replace('\n', '\r\n')
            unchanged_sql = (root/'my-release/migration.sql').read_bytes()
            candidate = json.loads((root/'my-release/candidate.json').read_text(encoding='utf-8'))
            candidate['migration'] = sql
            supplied = json.dumps(candidate, ensure_ascii=True, indent=2).encode('utf-8')
            (root/'saved-candidate.json').write_bytes(supplied)
            repaired = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-2',
                           '--bob-workspace', '--candidate-plan', 'saved-candidate.json'])
            self.assertEqual(repaired.returncode, 0, repaired.stderr)
            self.assertIn(b'Original baseline: BLOCKED 55/125', repaired.stdout)
            self.assertIn(b'Current candidate: PASS 155/155', repaired.stdout)
            self.assertIn(b'not a failure of the current candidate', repaired.stdout)
            self.assertIn(b'Recorded counterexample:', repaired.stdout)
            self.assertFalse((root/'review-2/bob-repair-workspace.zip').exists())
            note = (root/'review-2/review.md').read_text(encoding='utf-8')
            self.assertIn('| Baseline | BLOCKED | 55/125', note)
            self.assertIn('| Candidate | PASS | 155/155', note)
            with zipfile.ZipFile(root/'review-2/pr-kit.zip') as archive:
                report = json.loads(archive.read('evidence/report.json'))
                self.assertEqual(report['plan']['migration'], sql)
                self.assertEqual(report['status'], 'pass')
                self.assertIn('evidence/unsafe-control-report.json', archive.namelist())
                workflow = next(name for name in archive.namelist() if name.startswith('.github/'))
                self.assertIn(report['contract_hash'], archive.read(workflow).decode())
            self.assertEqual((root/'review-1/comparison.zip').read_bytes(), before)
            self.assertEqual((root/'review-2/inputs/migration.sql').read_bytes(), unchanged_sql)
            self.assertEqual((root/'my-release/migration.sql').read_bytes(), unchanged_sql)
            self.assertEqual((root/'review-2/inputs/supplied-candidate.json').read_bytes(), supplied)
            # Actual original SQL must override a stale passing baseline JSON,
            # and the kit control must bind that executed baseline.
            (root/'my-release/baseline.json').write_bytes(supplied)
            original_sql = b'\xef\xbb\xbf' + unchanged_sql
            (root/'original.sql').write_bytes(original_sql)
            source_review = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-source',
                '--candidate-plan', 'saved-candidate.json', '--baseline-migration-file', 'original.sql'])
            self.assertEqual(source_review.returncode, 0, source_review.stderr)
            self.assertEqual((root/'review-source/inputs/supplied-baseline.sql').read_bytes(), original_sql)
            with zipfile.ZipFile(root/'review-source/comparison.zip') as archive:
                executed = json.loads(archive.read('baseline/report.json'))
            self.assertEqual(executed['passed'], 55)
            self.assertEqual(executed['plan']['migration'], unchanged_sql.decode('utf-8'))
            with zipfile.ZipFile(root/'review-source/pr-kit.zip') as archive:
                control = json.loads(archive.read('evidence/unsafe-control-report.json'))
            for key in ('plan_hash', 'contract_hash', 'suite_hash', 'engine_sha256'):
                self.assertEqual(control[key], executed[key])
            # Resolve the original from Git even after that working-tree file changes.
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.STDOUT)
            git('init')
            (root/'.gitattributes').write_text('original.sql -text\n', encoding='utf-8')
            git('add', '.gitattributes', 'original.sql')
            git('-c', 'user.name=Cutover test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'Reviewed original')
            commit = git('rev-parse', 'HEAD').decode().strip()
            (root/'original.sql').write_bytes(b'SELECT 999;')
            git_review = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-git',
                '--candidate-plan', 'saved-candidate.json', '--baseline-git-ref', commit,
                '--baseline-git-path', 'original.sql'])
            self.assertEqual(git_review.returncode, 0, git_review.stderr)
            self.assertEqual((root/'review-git/inputs/supplied-baseline.sql').read_bytes(), original_sql)
            source_status = json.loads((root/'review-git/review-status.json').read_text())
            self.assertEqual(source_status['baseline_git']['commit'], commit)
            self.assertIn(commit, (root/'review-git/review.md').read_text(encoding='utf-8'))
            offline = (root/'review-git/review.html').read_text(encoding='utf-8')
            for value in source_status['baseline_git'].values():
                self.assertIn(value, offline)
            self.assertIn('does not verify the whole application', offline)
            with zipfile.ZipFile(root/'review-git/comparison.zip') as archive:
                git_report = json.loads(archive.read('baseline/report.json'))
            self.assertEqual(git_report['plan_hash'], executed['plan_hash'])
            with zipfile.ZipFile(root/'review-git/pr-kit.zip') as archive:
                git_control = json.loads(archive.read('evidence/unsafe-control-report.json'))
            self.assertEqual(git_control['plan_hash'], executed['plan_hash'])
            self.assertEqual((root/'original.sql').read_bytes(), b'SELECT 999;')
            repeat = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-2'])
            self.assertEqual(repeat.returncode, 2)
            (root/'my-release/candidate.json').write_text('{broken', encoding='utf-8')
            malformed = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-3', '--bob-workspace'])
            self.assertEqual(malformed.returncode, 2)
            status = json.loads((root/'review-3/review-status.json').read_text(encoding='utf-8'))
            self.assertEqual(status['status'], 'unverified')
            self.assertFalse((root/'review-3/pr-kit.zip').exists())
            self.assertFalse((root/'review-3/bob-repair-workspace.zip').exists())
            (root/'saved-candidate.json').write_text('{broken', encoding='utf-8')
            malformed_saved = run('cutover.review_project', ['--project', 'my-release', '--out', 'review-4',
                                   '--candidate-plan', 'saved-candidate.json'])
            self.assertEqual(malformed_saved.returncode, 2)
            self.assertFalse((root/'review-4/pr-kit.zip').exists())
