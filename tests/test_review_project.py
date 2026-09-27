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
            self.assertFalse((root/'review-1/pr-kit.zip').exists())
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
