"""A downloaded, independently replayed kit can enter CI without manual JSON edits."""
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from ci.discover_cases import discover
from ci.install_kit import install_kit


ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'evidence/ci_kit_red_green/cutover-my-release-ci-kit.zip'


class InstallKitTests(unittest.TestCase):
    def test_dry_run_then_apply_verified_browser_kit(self):
        with tempfile.TemporaryDirectory(prefix='cutover-kit-') as directory:
            target = Path(directory)
            baseline = [item for item in json.loads((ROOT / 'ci/cases.json').read_text(encoding='utf-8'))
                        if item['slug'] != 'release-my-release']
            for source in ['ci/cases.json', *(item[key] for item in baseline
                                               for key in ('contract', 'plan'))]:
                destination = target / source
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / source, destination)
            (target / 'ci/cases.json').write_text(json.dumps(baseline), encoding='utf-8')
            before = (target / 'ci/cases.json').read_bytes()
            dry = install_kit(KIT, target)
            self.assertEqual(dry['action'], 'dry_run')
            self.assertEqual(dry['coverage'], '124/124')
            self.assertTrue(dry['unsafe_control_verified'])
            self.assertEqual((target / 'ci/cases.json').read_bytes(), before)
            self.assertFalse((target / 'ci/release-my-release-contract.json').exists())

            applied = install_kit(KIT, target, apply=True)
            self.assertEqual(applied['action'], 'applied')
            cases = discover(target)['include']
            self.assertEqual(len(cases), len(baseline) + 1)
            self.assertEqual(cases[-1]['slug'], 'release-my-release')
            self.assertTrue((target / cases[-1]['contract']).is_file())
            self.assertTrue((target / cases[-1]['plan']).is_file())
            self.assertFalse((target / 'ci/cases.cutover-tmp.json').exists())

    def test_kit_rejects_paths_outside_checked_in_ci_inputs(self):
        with tempfile.TemporaryDirectory(prefix='cutover-kit-bad-') as directory:
            target = Path(directory)
            baseline = json.loads((ROOT / 'ci/cases.json').read_text(encoding='utf-8'))[:1]
            for source in (baseline[0]['contract'], baseline[0]['plan']):
                destination = target / source
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / source, destination)
            (target / 'ci/cases.json').write_text(json.dumps(baseline), encoding='utf-8')
            malicious = target / 'bad.zip'
            with zipfile.ZipFile(malicious, 'w') as archive:
                archive.writestr('manifest-entry.json', json.dumps({
                    'case': 'Custom Test', 'slug': 'bad',
                    'contract': '../../outside.json', 'plan': 'ci/bad-candidate.json',
                }))
            with self.assertRaisesRegex(ValueError, 'paths, label or slug'):
                install_kit(malicious, target, apply=True)
            self.assertFalse((target / 'outside.json').exists())
            self.assertEqual(json.loads((target / 'ci/cases.json').read_text(encoding='utf-8')), baseline)


if __name__ == '__main__':
    unittest.main()
