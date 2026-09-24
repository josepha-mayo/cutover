import unittest

from prepare_bob_session import ROOT, session_destination


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


if __name__ == '__main__':
    unittest.main()
