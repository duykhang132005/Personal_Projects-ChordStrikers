import os
import sqlite3

import pytest
from flask import abort

from app.models import Song
from app.storage import load_song_content, get_song_filepath, save_song_content
from app import create_app, db


@pytest.fixture(autouse=True)
def disable_itunes_network(monkeypatch):
    """Keep create/edit tests off the live iTunes Search API."""
    monkeypatch.setattr('app.utils._itunes_search', lambda *args, **kwargs: [])


def test_home_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"ChordStrikers" in response.data


def test_home_links_favicon(client):
    response = client.get('/')
    html = response.data.decode()
    assert 'img/favicon.svg' in html
    assert 'favicon.ico' in html


def test_explore_route(client):
    response = client.get('/explore')
    assert response.status_code == 200
    assert b"Test Song" in response.data


def test_explore_route_filter(client):
    response = client.get('/explore?query=Test')
    assert response.status_code == 200
    assert b"Test Song" in response.data

    response_empty = client.get('/explore?query=NonExistentSong')
    assert response_empty.status_code == 200
    assert b"Test Song" not in response_empty.data


def test_creator_route(client):
    response = client.get('/creator')
    assert response.status_code == 200
    assert b"Create New Song" in response.data


def test_routes_ok_on_stamped_empty_sqlite(tmp_path):
    """Older DBs that only have alembic_version still boot via create_all."""
    db_path = tmp_path / 'songs.db'
    conn = sqlite3.connect(db_path)
    conn.execute(
        'CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)'
    )
    conn.execute(
        "INSERT INTO alembic_version (version_num) VALUES ('14637d76aaff')"
    )
    conn.commit()
    conn.close()

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SONG_DATA_DIR': str(tmp_path / 'sheets'),
    })
    try:
        client = app.test_client()

        assert client.get('/').status_code == 200
        explore = client.get('/explore')
        assert explore.status_code == 200
        assert client.get('/creator').status_code == 200

        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert 'songs' in tables
        assert 'alembic_version' in tables
        assert conn.execute('SELECT COUNT(*) FROM songs').fetchone()[0] == 0
        conn.close()
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_create_app_reconciles_orphan_files_and_song_rows(tmp_path):
    db_path = tmp_path / 'songs.db'
    sheets = tmp_path / 'sheets'
    sheets.mkdir()
    conn = sqlite3.connect(db_path)
    conn.execute(
        '''CREATE TABLE songs (
            id INTEGER PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            artist VARCHAR(100),
            song_key VARCHAR(100) NOT NULL,
            image_url VARCHAR(512)
        )'''
    )
    conn.execute(
        "INSERT INTO songs (id, title, artist, song_key) VALUES (1, 'Keep', 'A', 'C')"
    )
    conn.execute(
        "INSERT INTO songs (id, title, artist, song_key) "
        "VALUES (15, 'Leftover', 'B', 'G')"
    )
    conn.commit()
    conn.close()
    (sheets / '1.txt').write_text('[C]Keep', encoding='utf-8')
    (sheets / '99.txt').write_text('[G]Orphan file', encoding='utf-8')
    (sheets / 'notes.txt').write_text('ignore', encoding='utf-8')

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SONG_DATA_DIR': str(sheets),
    })
    try:
        with app.app_context():
            ids = {song.id for song in Song.query.all()}
            assert ids == {1}
            assert os.path.isfile(os.path.join(sheets, '1.txt'))
            assert not os.path.isfile(os.path.join(sheets, '99.txt'))
            assert os.path.isfile(os.path.join(sheets, 'notes.txt'))
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_view_sheet_toolbar_uses_unified_controls(client, app):
    with app.app_context():
        song = Song.query.filter_by(title='Test Song').first()
        song_id = song.id

    response = client.get(f'/view_sheet/{song_id}')
    assert response.status_code == 200
    html = response.data.decode()
    assert 'unified-controls' in html
    assert 'id="btn-print-sheet"' in html
    assert 'id="btn-download-txt"' in html
    assert 'id="btn-yt-search"' in html
    assert 'control-btn' in html
    assert 'btn btn-primary' not in html
    assert 'btn btn-secondary' not in html
    assert 'btn-outline-light' not in html
    assert 'btn-outline-warning' not in html


def test_view_sheet_uses_storage_and_escapes_html(client, app):
    with app.app_context():
        song = Song.query.filter_by(title="Test Song").first()
        save_song_content(
            song.id,
            "[C]Hello <img src=x onerror=alert(1)>\n<script>alert(1)</script>",
        )
        song_id = song.id
        assert get_song_filepath(song_id).startswith(app.config['SONG_DATA_DIR'])

    response = client.get(f'/view_sheet/{song_id}')
    assert response.status_code == 200
    html = response.data.decode()
    sheet_start = html.find('<div class="song-content">')
    assert sheet_start != -1
    sheet_html = html[sheet_start:html.find('<!-- Scripts -->', sheet_start)]
    assert '<div class="lyric-line">Hello &lt;img src=x onerror=alert(1)&gt;</div>' in sheet_html
    assert '<div class="lyric-line">&lt;script&gt;alert(1)&lt;/script&gt;</div>' in sheet_html
    assert '<div class="lyric-line"><script>' not in sheet_html
    assert '<div class="lyric-line"><img' not in sheet_html
    assert 'class="chord"' in sheet_html
    assert 'data-chord="[C]"' in sheet_html


def test_create_song_uses_storage_and_accepts_allowed_image_url(client, app):
    image_url = 'https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/aa/source/600x600bb.jpg'
    response = client.post('/create', data={
        'title': 'Safe Cover',
        'artist': 'Someone',
        'song_key': 'C',
        'image_url': image_url,
        'sheet_content': '[C]Hi there',
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        song = Song.query.filter_by(title='Safe Cover').first()
        assert song is not None
        assert song.image_url == image_url
        assert load_song_content(song.id) == '[C]Hi there'


def test_create_song_auto_fetches_itunes_cover_without_spotify(client, app, monkeypatch):
    artwork_100 = (
        'https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/aa/bb/cc/source/100x100bb.jpg'
    )
    artwork_600 = artwork_100.replace('100x100bb', '600x600bb')
    monkeypatch.setattr(
        'app.utils._itunes_search',
        lambda term, entity, limit=1: [{'artworkUrl100': artwork_100}],
    )
    assert not hasattr(app, 'sp_client')
    assert 'SPOTIPY_CLIENT_ID' not in app.config

    response = client.post('/create', data={
        'title': 'Auto Cover',
        'artist': 'The Beatles',
        'song_key': 'F',
        'sheet_content': '[F]Hey',
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        song = Song.query.filter_by(title='Auto Cover').first()
        assert song is not None
        assert song.image_url == artwork_600


def test_create_song_rejects_unsafe_image_url(client, app):
    response = client.post('/create', data={
        'title': 'XSS Cover',
        'artist': 'Someone',
        'song_key': 'C',
        'image_url': 'javascript:alert(1)',
        'sheet_content': '[C]Hi',
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        song = Song.query.filter_by(title='XSS Cover').first()
        assert song is not None
        assert song.image_url is None
        assert load_song_content(song.id) == '[C]Hi'


def test_delete_song_removes_storage_file(client, app):
    with app.app_context():
        song = Song(title='To Delete', artist='X', song_key='C')
        db.session.add(song)
        db.session.commit()
        save_song_content(song.id, '[G]Bye')
        song_id = song.id
        filepath = get_song_filepath(song_id)
        assert os.path.isfile(filepath)

    response = client.post(f'/delete_song/{song_id}', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(Song, song_id) is None
        assert not os.path.isfile(filepath)


def test_unknown_route_shows_friendly_404(client):
    response = client.get('/this-page-does-not-exist')
    assert response.status_code == 404
    html = response.data.decode()
    assert 'Page not found' in html
    assert 'Sorry about that' in html
    assert 'isn\u2019t supposed to happen' in html
    assert 'error-home-btn' in html
    assert 'href="/"' in html
    assert 'Traceback' not in html


def test_view_sheet_missing_file_shows_friendly_404(client, app):
    with app.app_context():
        song = Song(title='Ghost Sheet', artist='X', song_key='C')
        db.session.add(song)
        db.session.commit()
        song_id = song.id
        assert not os.path.isfile(get_song_filepath(song_id))

    response = client.get(f'/view_sheet/{song_id}')
    assert response.status_code == 404
    html = response.data.decode()
    assert 'Page not found' in html
    assert 'Sorry about that' in html
    assert 'error-home-btn' in html
    assert 'Traceback' not in html


def test_500_error_page(app):
    @app.route('/__test_abort_500__')
    def _boom():
        abort(500)

    client = app.test_client()
    response = client.get('/__test_abort_500__')
    assert response.status_code == 500
    html = response.data.decode()
    assert 'Something went wrong' in html
    assert 'Sorry about that' in html
    assert 'we\u2019ve hit an error' in html
    assert 'error-home-btn' in html
    assert 'href="/"' in html
    assert 'Traceback' not in html
