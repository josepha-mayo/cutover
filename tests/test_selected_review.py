import unittest
from cutover.selected_replay import row_observation_summary


class SelectedReviewTests(unittest.TestCase):
    def test_missing_null_empty_and_extra_rows_remain_distinct(self):
        trace = [{'status': 'fail', 'expected': {'1': None, '2': '', '3': 'same'},
                  'actual': {'2': None, '3': 'same', '4': 'extra'}}]
        note = '\n'.join(row_observation_summary(trace))
        self.assertIn('3 mismatched row(s); 1 other recorded row(s) unchanged', note)
        self.assertIn('Expected by contract: SQL null\nReader observed: Row not returned', note)
        self.assertIn('Expected by contract: ""\nReader observed: SQL null', note)
        self.assertIn('Expected by contract: Row not returned\nReader observed: "extra"', note)

    def test_payload_markup_is_confined_and_matching_maps_do_not_invent_gap(self):
        note = '\n'.join(row_observation_summary([{'status': 'fail',
            'expected': {'1': '~~~~~~\n<script>bad</script>'}, 'actual': {'1': 'different'}}]))
        self.assertIn('~~~~~~~text', note)
        self.assertIn('"~~~~~~\\n<script>bad</script>"', note)
        self.assertEqual(row_observation_summary([{'status': 'fail', 'expected': {}, 'actual': {}}]), [])
        self.assertEqual(row_observation_summary([{'status': 'fail', 'detail': 'SQL error'}]), [])
