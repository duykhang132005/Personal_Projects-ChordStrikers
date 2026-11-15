"""Song of the day selection and home page rendering."""
from datetime import date, timedelta
from types import SimpleNamespace

from app import db
from app.daily_picks import pick_daily_songs
from app.models import Song
from app.storage import save_song_content


def _songs(*ids):
    return [SimpleNamespace(id=song_id) for song_id in ids]


def _featured_ids(songs, start, days):
    return [
        pick_daily_songs(songs, on_date=start + timedelta(days=offset))[0].id
        for offset in range(days)
    ]


def test_pick_empty_library():
    assert pick_daily_songs([]) == (None, [])


def test_pick_single_song_has_no_runner_ups():
    song = SimpleNamespace(id=7)
    for day in (date(2026, 1, 1), date(2026, 11, 12), date(2025, 6, 1)):
        featured, runner_ups = pick_daily_songs([song], on_date=day)
        assert featured is song
        assert runner_ups == []


def test_pick_three_songs_returns_what_exists():
    songs = _songs(1, 2, 3)
    featured, runner_ups = pick_daily_songs(songs, on_date=date(2026, 1, 1))
    assert featured in songs
    assert len(runner_ups) == 2
    assert featured not in runner_ups
    assert {s.id for s in [featured, *runner_ups]} == {1, 2, 3}


def test_pick_seven_songs_has_three_runner_ups_and_a_candidate():
    songs = _songs(*range(1, 8))
    start = date(2026, 1, 1)
    for offset in range(21):
        featured, runner_ups = pick_daily_songs(songs, on_date=start + timedelta(days=offset))
        assert featured.id in range(1, 8)
        assert len(runner_ups) == 3
        runner_ids = [s.id for s in runner_ups]
        assert featured.id not in runner_ids
        assert len(set(runner_ids)) == 3


def test_pick_honors_explicit_runner_up_count():
    songs = _songs(*range(1, 8))
    featured, runner_ups = pick_daily_songs(
        songs, on_date=date(2026, 1, 1), runner_up_count=5
    )
    assert len(runner_ups) == 5
    assert featured.id not in {s.id for s in runner_ups}
    assert len({s.id for s in runner_ups}) == 5


def test_pick_is_deterministic_for_a_date():
    songs = _songs(*range(1, 11))
    day = date(2026, 11, 12)
    first = pick_daily_songs(songs, on_date=day)
    second = pick_daily_songs(list(reversed(songs)), on_date=day)
    third = pick_daily_songs(songs, on_date=day)
    assert first[0].id == second[0].id == third[0].id
    assert [s.id for s in first[1]] == [s.id for s in second[1]] == [s.id for s in third[1]]


def test_pick_input_order_does_not_matter():
    day = date(2026, 3, 15)
    a = pick_daily_songs(_songs(5, 1, 9, 3, 7, 2, 8, 4, 6, 10), on_date=day)
    b = pick_daily_songs(_songs(*range(1, 11)), on_date=day)
    assert a[0].id == b[0].id
    assert [s.id for s in a[1]] == [s.id for s in b[1]]


def test_pick_changes_across_dates_and_is_not_a_rotation():
    songs = _songs(*range(1, 11))
    start = date(2026, 1, 1)
    featured_ids = _featured_ids(songs, start, 30)
    assert len(set(featured_ids)) > 2
    # Consecutive days are not a fixed +1 or -1 walk through ids.
    steps = {
        (featured_ids[i + 1] - featured_ids[i]) % 10
        for i in range(len(featured_ids) - 1)
    }
    assert steps != {1} and steps != {9}


def test_pick_three_distinct_runner_ups_exclude_featured():
    songs = _songs(*range(1, 11))
    featured, runner_ups = pick_daily_songs(songs, on_date=date(2026, 11, 12))
    ids = [featured.id, *[s.id for s in runner_ups]]
    assert len(runner_ups) == 3
    assert len(set(ids)) == 4


def test_no_featured_repeat_in_any_7_consecutive_days():
    start = date(2026, 1, 1)
    for size in (10, 29):
        songs = _songs(*range(1, size + 1))
        featured_ids = _featured_ids(songs, start, 365)
        for i in range(len(featured_ids) - 6):
            chunk = featured_ids[i:i + 7]
            assert len(set(chunk)) == 7, (size, i, chunk)


def test_recent_featured_song_can_appear_as_runner_up():
    songs = _songs(*range(1, 11))
    start = date(2026, 1, 1)
    found = False
    for offset in range(365):
        day = start + timedelta(days=offset)
        _featured, runner_ups = pick_daily_songs(songs, on_date=day)
        runner_ids = {s.id for s in runner_ups}
        for lookback in range(1, 7):
            if offset - lookback < 0:
                continue
            previous, _unused = pick_daily_songs(
                songs, on_date=day - timedelta(days=lookback)
            )
            if previous.id in runner_ids:
                found = True
                break
        if found:
            break
    assert found


def test_home_renders_song_of_the_day_and_link(client, app):
    with app.app_context():
        song = Song.query.filter_by(title='Test Song').one()
        song_id = song.id
        artist = song.artist
        key = song.song_key
    html = client.get('/').get_data(as_text=True)
    assert 'Song of the day' in html
    assert 'More to play' not in html
    assert 'Test Song' in html
    assert artist in html
    assert key in html
    assert f'href="/view_sheet/{song_id}"' in html
    assert 'daily-picks.js' not in html


def test_home_renders_runner_ups_and_script_for_signed_in_and_out(client, auth_client, app):
    with app.app_context():
        created = []
        for i in range(5):
            song = Song(title=f'Runner {i}', artist=f'Artist {i}', song_key='G')
            db.session.add(song)
            db.session.commit()
            save_song_content(song.id, '[C]Hi')
            created.append(song)
        public = Song.query.filter_by(hidden=False).all()
        featured, runners = pick_daily_songs(public)
        featured_title = featured.title
        runner_labels = []
        for song in runners:
            if song.artist:
                runner_labels.append(
                    'View sheet: %s by %s' % (song.title, song.artist)
                )
            else:
                runner_labels.append('View sheet: %s' % song.title)
    for browser in (client, auth_client):
        html = browser.get('/').get_data(as_text=True)
        assert 'Song of the day' in html
        assert 'More to play' in html
        assert html.count('daily-picks-card') == 3
        assert featured_title in html
        for label in runner_labels:
            assert 'aria-label="%s"' % label in html
        assert 'js/daily_picks.js' in html
        assert 'v=' in html.split('js/daily_picks.js', 1)[1][:40]


def test_home_hides_daily_picks_when_library_is_empty(client, app):
    with app.app_context():
        Song.query.delete()
        db.session.commit()
    html = client.get('/').get_data(as_text=True)
    assert 'Song of the day' not in html
    assert 'More to play' not in html
    assert 'daily-picks' not in html


def test_home_daily_picks_skip_hidden_songs(client, app):
    with app.app_context():
        hidden = Song(title='Hidden From Library', artist='Secret', song_key='A', hidden=True)
        db.session.add(hidden)
        db.session.commit()
        save_song_content(hidden.id, '[C]Secret')
    html = client.get('/').get_data(as_text=True)
    assert 'Hidden From Library' not in html
    assert 'Song of the day' in html
    assert 'Test Song' in html
