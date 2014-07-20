import unittest
import sqlite3

from user_tracks.models import TimeRange


class TestTimeRange(unittest.TestCase):

    def setUp(self):
        conn = sqlite3.connect(":memory:")
        self.cur = conn.cursor()
        TimeRange.create_table(self.cur)

    def test_add_single(self):
        time_range = TimeRange(timestamp_from=10, timestamp_to=20)

        TimeRange.add_to_db(self.cur, time_range)

        time_ranges = TimeRange.all(self.cur)
        expected = [(10, 20)]
        self.assertEqual(time_ranges, expected)

    def test_add_multiple(self):
        time_range_a = TimeRange(timestamp_from=10, timestamp_to=20)
        time_range_b = TimeRange(timestamp_from=20, timestamp_to=30)

        TimeRange.add_to_db(self.cur, [time_range_a, time_range_b])

        time_ranges = TimeRange.all(self.cur)
        expected = [(10, 20), (20, 30)]
        self.assertEqual(time_ranges, expected)

    def test_is_in_db(self):
        time_range = TimeRange(timestamp_from=10, timestamp_to=20)
        TimeRange.add_to_db(self.cur, time_range)

        is_in_db = time_range.is_in_db(self.cur)

        self.assertTrue(is_in_db, "TimeRange missing from DB")

    def test_is_no_in_db(self):
        time_range = TimeRange(timestamp_from=10, timestamp_to=20)

        is_in_db = time_range.is_in_db(self.cur)

        self.assertFalse(is_in_db, "TimeRange should not be from DB")

    def test_latest(self):
        time_ranges = [
            TimeRange(timestamp_from=20, timestamp_to=30),
            TimeRange(timestamp_from=10, timestamp_to=20),
        ]
        TimeRange.add_to_db(self.cur, time_ranges)

        latest = TimeRange.latest(self.cur)

        self.assertEquals(latest.as_tuple(), (20, 30))

    def test_latest_empty_db(self):
        latest = TimeRange.latest(self.cur)

        self.assertEquals(latest, None)

    def test_remove(self):
        time_range = TimeRange(timestamp_from=20, timestamp_to=30)
        TimeRange.add_to_db(self.cur, time_range)

        time_range.remove_from_db(self.cur)

        self.assertFalse(time_range.is_in_db(self.cur))

    def test_remove_non_existing(self):
        time_range = TimeRange(timestamp_from=20, timestamp_to=30)

        time_range.remove_from_db(self.cur)

        self.assertFalse(time_range.is_in_db(self.cur))

    def test_table_empty_true(self):
        is_empty = TimeRange.table_empty(self.cur)

        self.assertTrue(is_empty)

    def test_table_empty_false(self):
        time_range = TimeRange(timestamp_from=20, timestamp_to=30)
        TimeRange.add_to_db(self.cur, time_range)

        is_empty = TimeRange.table_empty(self.cur)

        self.assertFalse(is_empty)
