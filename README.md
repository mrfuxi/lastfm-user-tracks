# Last.fm user track analysis

## Description

 Program that retrieves data from the Last.fm service API and provides the user with information on their listening habits.

## How to run it

You can start it either by executing module with `python` command

```bash
python user_tracks user_name api_key
```

Or by starting app it self:

```bash
./user_tracks/user_tracks.py user_name api_key
```

It can be run for multiple users in any order.

For more details please run app with `--help`:

```bash
python user_tracks --help
```

*Note:* Please see **Requirements** section to install necessary libraries

## How to run tests

Application has number of tests that can be executed with helper script:

```bash
./runtests.py
```

*Note:* Please see **Requirements** section to install necessary libraries

## Requirements

To run app you need external library. To install it please run standard `pip`command:

```bash
pip install -r requirements.txt
```

Tests depends on some more requirements, listed in `test_requirements.txt` and can be installed in similar way:

```bash
pip install -r test_requirements.txt
```

## To remove history of tracks

This has to happen manually by removing either whole `dbs` folder (that will be created after first run) or specific file in this folder (named after user name).

## Assumptions

When writing this small app I had some assumptions:
* User has it's own API key for Last.fm service
* Application can write to directory from where was executed (to store the state between runs)
* API call to "user.getRecentTracks" always returns tracks from newest to oldest
* Application will not try to recover from most of exceptions (ie. when network error will occur it will fail fast and laud). It can be rerun to start from where it left off
* Currently running track will not be included in history (it will get in with of of next runs)
* State of app is preserved using SQLite db

## Final note

Tested on Ubuntu with Python 2.7.5 and virtualenv

## Example of output

```
Stats for user 'mrfuxi':
- listened to a total of 554 tracks.
- top 5 favorite artists: Chris Rea, Dire Straits, Evanescence, Formacja Nieżywych Schabuff, The Doors.
- listen to an average of 22 tracks a day.
- most active day is Saturday.
```
