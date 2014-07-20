#!/usr/bin/env python

import argparse
import urllib
import datetime
import inspect
import sqlite3
import os

import requests

from models import Track, TimeRange


class ApiUsageLimitException(Exception):
    pass


class LastFmApiException(Exception):
    pass


class UserTracks(object):
    api_request_limit = 5
    last_fm_url = "http://ws.audioscrobbler.com/2.0/"
    db_location = "dbs"

    def __init__(self, username, api_key):
        self.username = username
        self.api_key = api_key
        self.request_couter = 0

        self.conn = self._get_db_connection()
        self.cur = self.conn.cursor()

        self._prepare_tables()

    def _get_db_connection(self):
        db_name = u"{}.db".format(self.username)

        if not os.path.exists(self.db_location):
            os.makedirs(self.db_location)

        path_to_db = os.path.join(self.db_location, db_name)
        conn = sqlite3.connect(path_to_db)
        conn.isolation_level = None
        return conn

    def _prepare_tables(self):

        TimeRange.create_table(self.cur)
        Track.create_table(self.cur)

    @staticmethod
    def _utc_timestamp_now():
        dt_now = datetime.datetime.utcnow()
        return int(dt_now.strftime("%s"))

    def request_tracks(self, timestamp_from, timestamp_to):
        """
        Execute API call and returns Track objects
        """

        if self.request_couter >= self.api_request_limit:
            raise ApiUsageLimitException()

        query = {
            "method": "user.getRecentTracks",
            "format": "json",
            "api_key": self.api_key,
            "user": self.username,
            "from": timestamp_from,
            "to": timestamp_to,
        }

        query_str = urllib.urlencode(query)

        url = "{}?{}".format(self.last_fm_url, query_str)
        response = requests.get(url)
        self.request_couter += 1

        if not response.ok:
            msg = "Error while requesting data: {!r}".format(response.reason)
            raise LastFmApiException(msg)

        data = response.json()

        if "error" in data:
            msg = "Error from Last.fm: {!r}".format(data.get("message", data))
            raise LastFmApiException(msg)

        tracks = Track.many_from_json(data)

        return tracks

    def next_time_range(self):
        """
        Calculates next missing range of data
        """

        if self.request_couter > 0 and TimeRange.table_empty(self.cur):
            return None

        if self.request_couter == 0:
            if Track.table_empty(self.cur):
                timestamp_from = 0
            else:
                timestamp_from = Track.latest(self.cur).timestamp

            return (timestamp_from, self._utc_timestamp_now())

        latest = TimeRange.latest(self.cur)
        return latest.timestamp_from, latest.timestamp_to

    def _update_time_ranges(self, tr_query, tr_got):
        TimeRange(*tr_query).remove_from_db(self.cur)

        short_range = tr_got[0] - tr_query[0] <= 1
        if short_range and (
                Track(None, None, timestamp=tr_query[0]).is_in_db(self.cur) or
                Track(None, None, timestamp=tr_got[0]).is_in_db(self.cur)
        ):
            return

        remaining_time_range = TimeRange(tr_query[0], tr_got[0])
        TimeRange.add_to_db(self.cur, remaining_time_range)

    def process(self):
        """
        Main execution loop.
        Once user reach limit of API requests or
        there is no more data to fetch for now it stops
        """

        while True:
            try:
                more_possible = self.update_user_tracks()
            except ApiUsageLimitException:
                break

            if not more_possible:
                break

    def update_user_tracks(self):
        """
        Executes one cycle of requesting data from API
        Once it had data updates db with tracs and
        what time ranges are still missing
        """

        time_range = self.next_time_range()
        if not time_range:
            return False

        tracks = self.request_tracks(*time_range)

        if not tracks:
            TimeRange(*time_range).remove_from_db(self.cur)
            return not TimeRange.table_empty(self.cur)

        Track.add_to_db(self.cur, tracks)

        newest_ts = tracks[0].timestamp
        oldest_ts = tracks[-1].timestamp
        new_time_range = (oldest_ts, newest_ts)
        self._update_time_ranges(time_range, new_time_range)

        return True

    def stats(self):
        """
        Produces printable stats
        """

        data = {
            "username": self.username,
            "count": Track.count(self.cur),
            "top_artists": u", ".join(Track.favourite_artists(self.cur)),
            "most_active_day_of_week": Track.most_active_day_of_week(self.cur),
            "average_tracks_per_day": Track.average_tracks_per_day(self.cur),
        }

        msg = u"""
        Stats for user '{username}':
        - listened to a total of {count} tracks.
        - top 5 favorite artists: {top_artists}.
        - listen to an average of {average_tracks_per_day} tracks a day.
        - most active day is {most_active_day_of_week}.

        All stats based on data fetched for far
        """.format(**data)

        return inspect.cleandoc(msg)


def main():
    description = """
    Last.fm user track analysis.
    Builds up history of users tracks and produces stats like:
    - Number of tracks fetched
    - Top 5 artists
    - Average number of tracks per day
    - Most active day
    """
    parser = argparse.ArgumentParser(
        description=inspect.cleandoc(description),
        epilog="Created by Karol Duleba",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('username', help="Name of Last.fm user")
    parser.add_argument('api_key', help="Last.fm api key")
    args = parser.parse_args()

    # API_KEY = "48e30b0cc7a2df581c9ac25ae35df23e"  # my
    ut = UserTracks(username=args.username, api_key=args.api_key)
    ut.process()
    stats = ut.stats()

    print stats


if __name__ == '__main__':
    main()
