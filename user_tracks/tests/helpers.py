import unittest
import tempfile
import shutil
import itertools

from faker import Faker

from user_tracks.user_tracks import UserTracks
from user_tracks.models import Track, TimeRange


class DBObjectTestCase(unittest.TestCase):
    """
    Utility class for setting up and asserting state of
    Track/TimeRange objects
    """

    @classmethod
    def setUpClass(cls):
        cls.faker = Faker()

    def setUp(self):
        UserTracks.db_location = tempfile.mkdtemp()
        self.ut = UserTracks(username="user", api_key="key")

    def tearDown(self):
        shutil.rmtree(UserTracks.db_location)

    def prepate_time_range_state(self, time_ranges):
        TimeRange.add_to_db(
            self.ut.cur,
            [TimeRange(*time_range) for time_range in time_ranges]
        )

    def prepate_tracks_state(self, *timestamps):
        fake_tracks = self._get_tracks(*timestamps)
        Track.add_to_db(self.ut.cur, fake_tracks)

    def _get_tracks(self, *timestamps):
        fake_tracks_data = [
            {
                "name": self.faker.pystr(max_chars=10),
                "artist": {
                    "#text": self.faker.first_name(),
                },
                "date": {
                    "uts": tm,
                }
            }
            for tm in timestamps
        ]

        fake_tracks = Track.many_from_json({
            "recenttracks": {
                "track": fake_tracks_data
            }
        })

        return fake_tracks

    def assertTimeRangesTableEquals(self, ranges):
        rows = TimeRange.all(self.ut.cur)
        self.assertListEqual(sorted(rows), sorted(ranges))

    def assertTracksTableEquals(self, timestamps):
        rows = Track.all(self.ut.cur, field="timestamp")
        flatten = itertools.chain(*rows)
        self.assertListEqual(sorted(flatten), sorted(timestamps))
