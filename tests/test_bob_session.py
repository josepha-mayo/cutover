import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from prepare_bob_session import ROOT, session_destination, sources


class BobSessionNamingTests(unittest.TestCase):
    def test_label_allows_a_new_session_from_the_same_commit(self):
        revision = 'abcdef1234567890'
        self.assertEqual(session_destination(revision),
                         ROOT.parent / 'cutover-bob-session-abcdef12')
        self.assertEqual(session_destination(revision, 'event-20260925'),
                         ROOT.parent / 'cutover-bob-session-abcdef12-event-20260925')

    def test_label_cannot_escape_the_session_directory_name(self):
        for label in ('', '../outside', 'event/other', 'Event', '-event', 'a' * 41):
            with self.subTest(label=label), self.assertRaises(ValueError):
                session_destination('abcdef1234567890', label)

    def test_reference_withheld_copy_can_start_both_cli_entry_points(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            for relative in sources():
                target = workspace / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            env = {**os.environ, 'PYTHONPATH': str(workspace)}
            for module in ('cutover', 'cutover.audit_report'):
                with self.subTest(module=module):
                    result = subprocess.run([sys.executable, '-m', module, '--help'],
                                            cwd=workspace, env=env, capture_output=True,
                                            text=True, encoding='utf-8', timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
