"""A kit must not vouch for altered consumer workflow or source files."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ci.install_kit import _read_kit
from cutover.ci_kit import render_ci_kit


ROOT = Path(__file__).resolve().parents[1]


class PortableKitIntegrityTests(unittest.TestCase):
    def test_portable_files_are_verified_and_old_kits_still_work(self):
        original = ROOT / 'evidence/ci_kit_red_green/cutover-my-release-ci-kit.zip'
        entry, _, _, report, _ = _read_kit(original)
        with zipfile.ZipFile(original) as archive:
            contract = json.loads(archive.read(entry['contract']))
        packet, slug = render_ci_kit(report, contract)
        with zipfile.ZipFile(io.BytesIO(packet)) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        portable = [f'.github/workflows/cutover-{slug}.yml',
                    f'ci/{slug}-migration.sql', f'ci/{slug}-adapters.json']
        lock_line = f"          expected-contract-hash: '{report['contract_hash']}'\n".encode()
        self.assertIn(lock_line, files[portable[0]])
        _read_kit(ROOT / 'evidence/ci_browser_action_control/cutover-dispatch-action-kit.zip')
        with tempfile.TemporaryDirectory(prefix='cutover-kit-integrity-') as directory:
            kit = Path(directory) / 'kit.zip'
            kit.write_bytes(packet)
            self.assertEqual(_read_kit(kit)[0], entry)
            for changed_workflow in (files[portable[0]].replace(lock_line, b''),
                                     files[portable[0]].replace(report['contract_hash'].encode(), b'0' * 64)):
                with zipfile.ZipFile(kit, 'w') as archive:
                    for name, content in files.items():
                        archive.writestr(name, changed_workflow if name == portable[0] else content)
                with self.assertRaisesRegex(ValueError, 'portable file differs'):
                    _read_kit(kit)
            for changed in portable:
                with self.subTest(changed=changed), zipfile.ZipFile(kit, 'w') as archive:
                    for name, content in files.items():
                        archive.writestr(name, content + b'\n# changed' if name == changed else content)
                with self.assertRaisesRegex(ValueError, 'portable file differs'):
                    _read_kit(kit)
            with zipfile.ZipFile(kit, 'w') as archive:
                for name, content in files.items():
                    if name != portable[1]:
                        archive.writestr(name, content)
            with self.assertRaisesRegex(ValueError, 'portable workflow inputs are incomplete'):
                _read_kit(kit)


if __name__ == '__main__':
    unittest.main()
