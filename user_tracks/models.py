"""
Models used to store data in DB and query it later
"""


class DBObject(object):
    table_name = None

    @classmethod
    def add_to_db(cls, cursor, objects):
        if isinstance(objects, cls):
            objects = [objects]

        elif not isinstance(objects, (list, tuple)):
            raise ValueError("Objects are not iterable")

        insert_sql = cls.insert_sql()

        cursor.executemany(
            insert_sql,
            [obj.as_tuple() for obj in objects]
        )

    @classmethod
    def insert_sql(cls):
        raise NotImplementedError("Please implement insert_sql")

    @classmethod
    def create_table(cls, cursor):
        raise NotImplementedError("Please implement create_table")

    def as_tuple(self):
        """
        Seralize track into tuple format for DB insertion
        """
        raise NotImplementedError("Please implement as_tuple")

    @classmethod
    def all(cls, cursor, field=None):
        select_sql = "SELECT {} FROM {}".format(
            field if field else "*",
            cls.table_name
        )
        rows = cursor.execute(select_sql)
        return rows.fetchall()

    def is_in_db(self, cursor):
        raise NotImplementedError("Please implement is_in_db")

    @classmethod
    def count(cls, cursor):
        select_sql = "SELECT COUNT(*) FROM {}".format(cls.table_name)
        rows = cursor.execute(select_sql)
        rows_count = rows.fetchone()[0]
        return rows_count

    @classmethod
    def table_empty(cls, cursor):
        return cls.count(cursor) == 0

    @classmethod
    def latest_sql(cls):
        raise NotImplementedError("Please implement latest_sql")

    @classmethod
    def latest(cls, cursor):
        latest_sql = cls.latest_sql()
        rows = cursor.execute(latest_sql)
        row = rows.fetchone()

        if not row:
            return None

        return cls(*row)


class Track(DBObject):
    table_name = "tracks"

    def __init__(self, name, artist, timestamp):
        self.timestamp = timestamp
        self.name = name
        self.artist = artist

    def __unicode__(self):
        return u"<Track: {} at {}>".format(self.name, self.timestamp)

    def __repr__(self):
        return "<Track: {!r} at {}>".format(self.name, self.timestamp)

    def as_tuple(self):
        """
        Seralize track into tuple format for DB insertion
        """

        return (self.name, self.artist, self.timestamp, self.timestamp)

    @classmethod
    def insert_sql(cls):
        insert_sql = """
            INSERT INTO {}
            (name, artist, timestamp, date_time) VALUES
            (?, ?, ?, datetime(?, 'unixepoch'))
        """.format(cls.table_name)

        return insert_sql

    @classmethod
    def create_table(cls, cursor):
        tracks_sql = """
        CREATE TABLE IF NOT EXISTS {} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name STRING NOT NULL,
            artist STRING  NOT NULL,
            timestamp INT NOT NULL,
            date_time DATETIME NOT NULL
        )
        """.format(cls.table_name)

        cursor.execute(tracks_sql)

    @classmethod
    def from_json(cls, json_data):
        name = json_data["name"]
        artist = json_data["artist"]["#text"]
        timestamp = int(json_data["date"]["uts"])

        return cls(
            name=name,
            artist=artist,
            timestamp=timestamp
        )

    @classmethod
    def many_from_json(cls, json_data):
        if "recenttracks" not in json_data:
            raise ValueError("Could not found any recent tracks")

        tracks = json_data["recenttracks"].get("track")

        if not tracks:
            return []

        return [
            Track.from_json(track) for track in tracks if track.get("date")
        ]

    @classmethod
    def latest_sql(cls):
        latest_sql = """
            SELECT name, artist, timestamp
            FROM {}
            ORDER BY timestamp DESC
            LIMIT 1
        """.format(cls.table_name)

        return latest_sql

    def is_in_db(self, cursor):
        sql = """
            SELECT * from {} WHERE timestamp=?
        """.format(self.table_name)

        rows = cursor.execute(sql, (self.timestamp, ))
        return len(rows.fetchall()) == 1

    @classmethod
    def favourite_artists(cls, cursor, top=5):
        sql = """
            SELECT
                artist, COUNT(*)
            FROM {}
            GROUP BY artist
            ORDER BY 2 DESC
            LIMIT {}
        """.format(cls.table_name, top)

        rows = cursor.execute(sql)
        return [row[0] for row in rows]

    @classmethod
    def most_active_day_of_week(cls, cursor):
        sql = """
            SELECT
                strftime('%w', date_time),
                COUNT(*)
            FROM {}
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 1
        """.format(cls.table_name)

        days_of_week = {
            "0": "Sunday",
            "1": "Monday",
            "2": "Tuesday",
            "3": "Wednesday",
            "4": "Thursday",
            "5": "Friday",
            "6": "Saturday",
        }

        rows = cursor.execute(sql)
        most_active_day = rows.fetchone()

        if not most_active_day:
            return None

        return days_of_week[most_active_day[0]]

    @classmethod
    def average_tracks_per_day(cls, cursor):

        sql = """
            SELECT
                COUNT(DISTINCT strftime('%Y-%m-%d', date_time))
            FROM {}
        """.format(cls.table_name)

        tracks_count = cls.count(cursor)

        if not tracks_count:
            return 0

        rows = cursor.execute(sql)
        unique_days = rows.fetchone()[0]

        return tracks_count/unique_days


class TimeRange(DBObject):
    """
    Object representing time range for missing data
    """

    table_name = "time_ranges"

    def __init__(self, timestamp_from, timestamp_to):
        self.timestamp_from = timestamp_from
        self.timestamp_to = timestamp_to

    def __repr__(self):
        return "<TimeRange: {} - {}>".format(
            self.timestamp_from, self.timestamp_to)

    def as_tuple(self):
        """
        Seralize track into tuple format for DB insertion
        """

        return (self.timestamp_from, self.timestamp_to)

    @classmethod
    def insert_sql(cls):
        insert_sql = """
            INSERT INTO {}
            (timestamp_from, timestamp_to) VALUES
            (?, ?)
        """.format(cls.table_name)

        return insert_sql

    @classmethod
    def create_table(cls, cursor):
        time_range_sql = """
        CREATE TABLE IF NOT EXISTS {} (
            timestamp_from INT NOT NULL,
            timestamp_to INT NOT NULL,
            UNIQUE(timestamp_from, timestamp_to)
        )
        """.format(cls.table_name)

        cursor.execute(time_range_sql)

    def is_in_db(self, cursor):
        sql = """
            SELECT * from {} WHERE timestamp_from=? AND timestamp_to=?
        """.format(self.table_name)

        rows = cursor.execute(sql, self.as_tuple())
        return len(rows.fetchall()) == 1

    @classmethod
    def latest_sql(cls):
        latest_sql = """
            SELECT timestamp_from, timestamp_to
            FROM {}
            ORDER BY 1 DESC
            LIMIT 1
        """.format(cls.table_name)

        return latest_sql

    def remove_from_db(self, cursor):
        delete_sql = """
            DELETE FROM {}
            WHERE timestamp_from=? AND timestamp_to=?
        """.format(self.table_name)

        rows = cursor.execute(delete_sql, self.as_tuple())

        return rows.rowcount == 1
