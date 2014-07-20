from mock import patch, Mock

from user_tracks.user_tracks import (
    UserTracks, ApiUsageLimitException, LastFmApiException,
)
from user_tracks.models import Track, TimeRange
from user_tracks.tests.helpers import DBObjectTestCase


class TestBuildingNextRangeToCheck(DBObjectTestCase):

    @patch.object(UserTracks, "_utc_timestamp_now")
    def test_first_request_ever(self, utc_now):
        # Just to say that db is empty
        self.assertTrue(Track.table_empty(self.ut.cur))
        self.assertTrue(TimeRange.table_empty(self.ut.cur))

        self.ut.request_couter = 0
        utc_now.return_value = 100

        next_range = self.ut.next_time_range()

        self.assertEquals(next_range, (0, 100))

    def test_further_request_in_fist_session_one_entry(self):
        self.prepate_time_range_state([(0, 95)])
        self.prepate_tracks_state(100, 96)
        self.ut.request_couter = 1

        next_range = self.ut.next_time_range()

        self.assertEquals(next_range, (0, 95))

    @patch.object(UserTracks, "_utc_timestamp_now")
    def test_fist_request_in_next_session(self, utc_now):
        self.prepate_time_range_state([(90, 95), (0, 80)])
        self.prepate_tracks_state(100, 96, 89, 81)
        self.ut.request_couter = 0
        utc_now.return_value = 110

        next_range = self.ut.next_time_range()

        self.assertEquals(next_range, (100, 110))

    def test_further_request_in_next_session(self):
        self.prepate_time_range_state([(90, 95), (0, 80)])
        self.prepate_tracks_state(110, 101, 100, 96, 89, 81)
        self.ut.request_couter = 1

        next_range = self.ut.next_time_range()

        self.assertEquals(next_range, (90, 95))


class TestRequestFlow(DBObjectTestCase):

    @patch.object(UserTracks, "request_tracks")
    @patch.object(UserTracks, "_utc_timestamp_now")
    def test_request_flow(self, utc_now, request_tracks):
        """
        This test is reather unusual:
        - it's lengthy
        - has multiple section
        - etc..

        However pourpose of it is to show/test whole process
        """
        #### 1nd call within 1 session

        utc_now.return_value = 100
        request_tracks.return_value = self._get_tracks(100, 95, 90)
        self.ut.request_couter = 0

        self.ut.update_user_tracks()

        request_tracks.assert_called_once_with(0, 100)
        self.assertTimeRangesTableEquals([(0, 90)])
        self.assertTracksTableEquals([100, 95, 90])

        #### 2nd call within 1 session

        request_tracks.reset_mock()
        self.ut.request_couter = 1
        request_tracks.return_value = self._get_tracks(89, 85, 80)

        self.ut.update_user_tracks()

        request_tracks.assert_called_once_with(0, 90)
        self.assertTimeRangesTableEquals([(0, 80)])
        self.assertTracksTableEquals([100, 95, 90, 89, 85, 80])

        #### 3rd call within 1 session

        request_tracks.reset_mock()
        self.ut.request_couter = 2
        request_tracks.return_value = self._get_tracks(79, 75, 70)

        self.ut.update_user_tracks()

        request_tracks.assert_called_once_with(0, 80)
        self.assertTimeRangesTableEquals([(0, 70)])
        self.assertTracksTableEquals([100, 95, 90, 89, 85, 80, 79, 75, 70])

        #### 1st call within new a session

        request_tracks.reset_mock()
        utc_now.return_value = 150
        self.ut.request_couter = 0
        request_tracks.return_value = self._get_tracks(140, 120, 110)

        self.ut.update_user_tracks()

        request_tracks.assert_called_once_with(100, 150)
        self.assertTimeRangesTableEquals([(100, 110), (0, 70)])
        self.assertTracksTableEquals(
            [140, 120, 110, 100, 95, 90, 89, 85, 80, 79, 75, 70])

        #### 2nd call within new a session

        request_tracks.reset_mock()
        self.ut.request_couter = 1
        request_tracks.return_value = self._get_tracks(109, 105)

        self.ut.update_user_tracks()

        request_tracks.assert_called_once_with(100, 110)
        self.assertTimeRangesTableEquals([(100, 105), (0, 70)])
        self.assertTracksTableEquals(
            [140, 120, 110, 109, 105, 100, 95, 90, 89, 85, 80, 79, 75, 70])

        #### 3rd call within new a session

        request_tracks.reset_mock()
        self.ut.request_couter = 2
        request_tracks.return_value = self._get_tracks(104, 102, 101)

        self.ut.update_user_tracks()

        request_tracks.assert_called_once_with(100, 105)
        self.assertTimeRangesTableEquals([(0, 70)])
        self.assertTracksTableEquals(
            [140, 120, 110, 109, 105, 104, 102, 101,
             100, 95, 90, 89, 85, 80, 79, 75, 70]
        )

        #### Last call to fetch remaining tracks - nothing more found

        request_tracks.reset_mock()
        self.ut.request_couter = 3
        request_tracks.return_value = []

        self.ut.update_user_tracks()

        request_tracks.assert_called_once_with(0, 70)
        self.assertTimeRangesTableEquals([])  # no more data
        self.assertTracksTableEquals(
            [140, 120, 110, 109, 105, 104, 102, 101,
             100, 95, 90, 89, 85, 80, 79, 75, 70]
        )

        #### Last call to fetch remaining tracks - nothing more found

        request_tracks.reset_mock()
        self.ut.request_couter = 3
        request_tracks.return_value = []

        self.ut.update_user_tracks()


class TestFetchingTracks(DBObjectTestCase):

    @patch("user_tracks.user_tracks.requests.get")
    @patch.object(Track, "many_from_json")
    def test_request_limit(self, many_from_json, get_req):
        with self.assertRaises(ApiUsageLimitException):
            for x in xrange(UserTracks.api_request_limit + 10):
                self.ut.request_tracks(0, 1)

        self.assertEquals(
            self.ut.request_couter, UserTracks.api_request_limit)
        self.assertEquals(get_req.call_count, UserTracks.api_request_limit)

    @patch("user_tracks.user_tracks.requests.get")
    @patch.object(Track, "many_from_json")
    def test_correct_api_url(self, many_from_json, get_req):
        self.ut.request_tracks(123, 321)

        url = get_req.call_args[0][0]
        self.assertIn("from=123", url)
        self.assertIn("to=321", url)
        self.assertIn("format=json", url)
        self.assertIn("api_key=key", url)
        self.assertIn("method=user.getRecentTracks", url)

    @patch("user_tracks.user_tracks.requests.get")
    def test_500_causing_exception(self, get_req):
        get_req.return_value = Mock(ok=False, reason="500 :(")

        with self.assertRaises(LastFmApiException):
            self.ut.request_tracks(123, 321)

    @patch("user_tracks.user_tracks.requests.get")
    def test_problem_with_request(self, get_req):
        response = Mock(ok=True)
        response.json.return_value = {
            "error": 1,
            "message": "Some error from Last.fm",
        }
        get_req.return_value = response

        with self.assertRaises(LastFmApiException):
            self.ut.request_tracks(123, 321)

    @patch("user_tracks.user_tracks.requests.get")
    @patch.object(Track, "many_from_json")
    def test_json_to_track(self, many_from_json, get_req):
        response = Mock(ok=True)
        response.json.return_value = "Some json data"
        get_req.return_value = response
        many_from_json.return_value = "List of tracks"

        tracks = self.ut.request_tracks(123, 321)

        many_from_json.assert_called_once_with("Some json data")
        self.assertEquals(tracks, "List of tracks")
