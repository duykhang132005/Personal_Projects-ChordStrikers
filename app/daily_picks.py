"""Pick a featured song and runner-ups that stay the same all day.

The public library is sorted by id. Each calendar day gets a
deterministic random choice seeded from SHA-256 of the ISO date (never
Python's salted hash()). A song is not featured again during the next
6 days, a 7-day window of today plus the previous 6. If the library
has 7 or fewer songs, that window shrinks to len(pool) - 1 previous
days so one candidate always remains. Runner-ups are a separate
shuffle of the other songs for that day and may include recent
features. History is simulated from 2026-01-01, or from the requested
date if it is earlier, and the result is cached.
"""
from datetime import date, timedelta
from functools import lru_cache
import hashlib
import random

EPOCH = date(2026, 1, 1)
# Today plus the previous 6 days: a featured song is excluded for 6 days after.
FEATURE_WINDOW = 7


def _seed_int(iso_date, stream):
    """Stable integer seed for a date and RNG stream (featured or runners)."""
    payload = f'chordstrikers:{stream}:{iso_date}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(payload).digest(), 'big')


def _rng(on_date, stream):
    return random.Random(_seed_int(on_date.isoformat(), stream))


def _window_size(pool_size):
    """How many previous days' features to exclude (0 if the pool is a single song)."""
    if pool_size <= 1:
        return 0
    return min(FEATURE_WINDOW - 1, pool_size - 1)


@lru_cache(maxsize=4096)
def _featured_history(pool_ids, on_date):
    """Featured song ids from the simulation start through on_date, inclusive.

    pool_ids must be a sorted tuple. Start is EPOCH, or on_date when that
    date is earlier, so pre-epoch dates still return a pick.
    """
    start = min(EPOCH, on_date)
    window = _window_size(len(pool_ids))
    history = []
    day = start
    one_day = timedelta(days=1)
    while day <= on_date:
        banned = set(history[-window:]) if window else set()
        candidates = [song_id for song_id in pool_ids if song_id not in banned]
        chosen = _rng(day, 'featured').choice(candidates)
        history.append(chosen)
        day += one_day
    return tuple(history)


def pick_daily_songs(songs, on_date=None, runner_up_count=3):
    """Return (featured, runner_ups) from a public library list.

    The same date and library always yield the same songs for every
    visitor and process. An empty list yields (None, []). A short list
    yields as many runner-ups as remain, up to runner_up_count.
    """
    if on_date is None:
        on_date = date.today()
    pool = sorted(songs, key=lambda song: song.id)
    if not pool:
        return None, []
    by_id = {song.id: song for song in pool}
    pool_ids = tuple(song.id for song in pool)
    featured = by_id[_featured_history(pool_ids, on_date)[-1]]
    rest = [song for song in pool if song.id != featured.id]
    _rng(on_date, 'runners').shuffle(rest)
    return featured, rest[:runner_up_count]
