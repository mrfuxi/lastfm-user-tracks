import unittest
import sqlite3

from user_tracks.models import Track


class TestTrack(unittest.TestCase):

    def setUp(self):
        conn = sqlite3.connect(":memory:")
        self.cur = conn.cursor()
        Track.create_table(self.cur)

    def test_add_single_track(self):
        track = Track(name="name", artist="artist", timestamp=10)

        Track.add_to_db(self.cur, track)

        tracks = Track.all(self.cur)
        expected = [(1, u'name', u'artist', 10, u'1970-01-01 00:00:10')]
        self.assertEqual(tracks, expected)

    def test_add_multiple_tracks(self):
        track_a = Track(name="name1", artist="artist1", timestamp=10)
        track_b = Track(name="name2", artist="artist2", timestamp=20)

        Track.add_to_db(self.cur, [track_a, track_b])

        tracks = Track.all(self.cur)
        expected = [
            (1, u'name1', u'artist1', 10, u'1970-01-01 00:00:10'),
            (2, u'name2', u'artist2', 20, u'1970-01-01 00:00:20'),
        ]
        self.assertEqual(tracks, expected)

    def test_track_is_in_db(self):
        track = Track(name="name", artist="artist", timestamp=10)
        Track.add_to_db(self.cur, track)

        is_in_db = track.is_in_db(self.cur)

        self.assertTrue(is_in_db, "Track missing from DB")

    def test_track_is_no_in_db(self):
        track = Track(name="name", artist="artist", timestamp=10)

        is_in_db = track.is_in_db(self.cur)

        self.assertFalse(is_in_db, "Track should not be from DB")

    def test_track_is_no_in_db_modified_timestamp(self):
        track = Track(name="name", artist="artist", timestamp=10)
        Track.add_to_db(self.cur, track)
        track.timestamp = 20

        is_in_db = track.is_in_db(self.cur)

        self.assertFalse(is_in_db, "Track should not be from DB")

    def test_build_from_json(self):
        json_data = {
            "name": "track name",
            "artist": {
                "#text": "artist name",
            },
            "date": {
                "uts": 11,
            }
        }

        track = Track.from_json(json_data)

        self.assertEquals(track.name, "track name")
        self.assertEquals(track.artist, "artist name")
        self.assertEquals(track.timestamp, 11)

    def test_build_multiple_from_json(self):
        track_data = [
            {
                "name": "track name 1",
                "artist": {
                    "#text": "artist name 1",
                },
                "date": {
                    "uts": 1,
                }
            },
            {
                "name": "track name 2",
                "artist": {
                    "#text": "artist name 2",
                },
                "date": {
                    "uts": 2,
                }
            },
        ]

        json_data = {
            "recenttracks": {
                "track": track_data
            }
        }

        track = Track.many_from_json(json_data)

        self.assertEquals(len(track), 2)

        self.assertEquals(track[0].name, "track name 1")
        self.assertEquals(track[0].artist, "artist name 1")
        self.assertEquals(track[0].timestamp, 1)

        self.assertEquals(track[1].name, "track name 2")
        self.assertEquals(track[1].artist, "artist name 2")
        self.assertEquals(track[1].timestamp, 2)

    def test_favourite_artists(self):
        tracks = []
        tracks += [Track(name="name", artist="artist a", timestamp=11)] * 6
        tracks += [Track(name="name", artist="artist b", timestamp=11)] * 5
        tracks += [Track(name="name", artist="artist c", timestamp=11)] * 4
        tracks += [Track(name="name", artist="artist d", timestamp=11)] * 3
        tracks += [Track(name="name", artist="artist e", timestamp=11)] * 2
        tracks += [Track(name="name", artist="artist f", timestamp=11)] * 1
        Track.add_to_db(self.cur, tracks)
        expected_artists = [
            "artist a", "artist b", "artist c", "artist d", "artist e",
        ]

        artists = Track.favourite_artists(self.cur)

        self.assertListEqual(artists, expected_artists)

    def test_favourite_artists_empty_db(self):

        artists = Track.favourite_artists(self.cur)

        self.assertListEqual(artists, [])

    def test_most_active_day(self):
        tracks = []
        # Thursday
        tracks += [Track(name="name", artist="artist a", timestamp=1)]
        # Friday
        tracks += [Track(name="name", artist="artist b", timestamp=86400)] * 5
        Track.add_to_db(self.cur, tracks)

        day_of_week = Track.most_active_day_of_week(self.cur)

        self.assertEquals(day_of_week, "Friday")

    def test_most_active_day_empty_db(self):
        day_of_week = Track.most_active_day_of_week(self.cur)
        self.assertEquals(day_of_week, None)

    def test_average_tracks_per_day(self):
        tracks = []
        tracks += [Track(name="name", artist="artist a", timestamp=1)] * 10
        tracks += [Track(name="name", artist="artist b", timestamp=86400)] * 5
        Track.add_to_db(self.cur, tracks)

        average = Track.average_tracks_per_day(self.cur)

        self.assertEquals(average, 7)

    def test_average_tracks_per_day_empty_db(self):
        average = Track.average_tracks_per_day(self.cur)

        self.assertEquals(average, 0)

    def test_latest(self):
        tracks = [
            Track(name="name1", artist="artist1", timestamp=10),
            Track(name="name2", artist="artist2", timestamp=20),
        ]
        Track.add_to_db(self.cur, tracks)

        latest = Track.latest(self.cur)

        self.assertEquals(latest.as_tuple(), ("name2", "artist2", 20, 20))

    def test_latest_empty_db(self):
        latest = Track.latest(self.cur)

        self.assertEquals(latest, None)

    def test_table_empty_true(self):
        is_empty = Track.table_empty(self.cur)

        self.assertTrue(is_empty)

    def test_table_empty_false(self):
        track = Track(name="name1", artist="artist1", timestamp=10)
        Track.add_to_db(self.cur, track)

        is_empty = Track.table_empty(self.cur)

        self.assertFalse(is_empty)
