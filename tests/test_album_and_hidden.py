"""Album field and owner 'Hide from Entire library' toggle."""
import os
import shutil
import sqlite3
import tempfile
from unittest import mock

import pytest

from app import create_app, db
from app.models import Song, User
from app import utils

NO_ART = mock.patch('app.routes.creator.get_song_image_url', return_value=None)


def _register(client, name):
    client.post('/register', data={'username': name, 'password': 'pw', 'confirmation': 'pw'})


def _logout(client):
    client.post('/logout')


def _create(client, **fields):
    data = {'title': 'Hidden Gem', 'artist': 'Someone', 'song_key': 'G',
            'image_url': '', 'sheet_content': '[G]la'}
    data.update(fields)
    with NO_ART:
        return client.post('/create', data=data)


def _song(app, title):
    with app.app_context():
        return Song.query.filter_by(title=title).one()


def _library_panel(html):
    return html.split('id="explore-panel-library"', 1)[1]


# --- model and migration -------------------------------------------------

def test_new_columns_default_to_visible_and_no_album(app):
    with app.app_context():
        song = Song.query.first()
        assert song.album is None and song.hidden is False


def test_startup_adds_columns_to_old_database_without_data_loss():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(80) UNIQUE NOT NULL, '
                 'password_hash VARCHAR(255) NOT NULL, is_admin BOOLEAN NOT NULL DEFAULT 0)')
    conn.execute('CREATE TABLE songs (id INTEGER PRIMARY KEY, title VARCHAR(100) NOT NULL, '
                 'artist VARCHAR(100), song_key VARCHAR(100) NOT NULL, image_url VARCHAR(512), user_id INTEGER)')
    conn.execute("INSERT INTO songs (title, song_key) VALUES ('Old Song', 'C')")
    conn.commit()
    conn.close()
    song_dir = tempfile.mkdtemp()
    with open(os.path.join(song_dir, '1.txt'), 'w') as f:
        f.write('[C]old')
    config = {'TESTING': True, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{path}',
              'SECRET_KEY': 'x', 'SONG_DATA_DIR': song_dir}
    try:
        for _ in range(2):  # second start must be a no-op
            app = create_app(config)
            with app.app_context():
                song = Song.query.filter_by(title='Old Song').one()
                assert song.album is None and song.hidden is False
                db.session.remove()
                db.engine.dispose()  # Windows cannot delete an open SQLite file
        conn = sqlite3.connect(path)
        cols = {row[1] for row in conn.execute('PRAGMA table_info(songs)')}
        conn.close()
        assert {'album', 'hidden'} <= cols
    finally:
        shutil.rmtree(song_dir, ignore_errors=True)
        try:
            os.remove(path)
        except OSError:  # pragma: no cover - a stray handle on Windows
            pass


# --- album ---------------------------------------------------------------

def test_album_is_saved_shown_and_searchable(auth_client, app):
    _create(auth_client, title='Valentine', artist='Laufey', album='Everything I Know About Love')
    assert _song(app, 'Valentine').album == 'Everything I Know About Love'
    song_id = _song(app, 'Valentine').id
    sheet = auth_client.get(f'/view_sheet/{song_id}').get_data(as_text=True)
    assert '<strong>Album:</strong> Everything I Know About Love' in sheet
    explore = auth_client.get('/explore?query=know about love').get_data(as_text=True)
    assert 'Valentine' in _library_panel(explore) and 'song-card-album' in explore


def test_album_can_be_edited_and_cleared(auth_client, app):
    _create(auth_client, title='Tune', album='First')
    song_id = _song(app, 'Tune').id
    edit = auth_client.get(f'/edit_song/{song_id}').get_data(as_text=True)
    assert 'value="First"' in edit
    with NO_ART:
        auth_client.post(f'/edit_song/{song_id}', data={'title': 'Tune', 'song_key': 'G', 'album': '',
                                                         'sheet_content': '[G]x'})
    assert _song(app, 'Tune').album is None


def test_album_is_tried_first_for_cover_art():
    calls = []

    def fake_search(term, entity, limit=1):
        calls.append((term, entity))
        return [{'artworkUrl100': 'https://is1-ssl.mzstatic.com/image/thumb/a/100x100bb.jpg'}]

    with mock.patch.object(utils, '_itunes_search', side_effect=fake_search):
        url = utils.get_song_image_url('Valentine', 'Laufey', 'Everything I Know About Love')
    assert url and calls == [('Everything I Know About Love Laufey', 'album')]


def test_without_album_lookup_is_unchanged():
    calls = []
    with mock.patch.object(utils, '_itunes_search', side_effect=lambda t, entity, limit=1: calls.append(entity) or []):
        utils.get_song_image_url('Song', 'Artist')
    assert 'album' not in calls[:2]


# --- hide from Entire library -------------------------------------------

def test_owner_sees_hidden_song_with_badge(auth_client, app):
    _create(auth_client, hidden='1')
    assert _song(app, 'Hidden Gem').hidden is True
    html = auth_client.get('/explore').get_data(as_text=True)
    library = _library_panel(html)
    assert 'Hidden Gem' in library and 'badge-hidden' in library
    mine = html.split('id="explore-panel-mine"', 1)[1].split('id="explore-panel-favorites"', 1)[0]
    assert 'Hidden Gem' in mine


def test_others_and_visitors_do_not_see_hidden_song_but_link_works(client, app):
    _register(client, 'owner')
    _create(client, hidden='1')
    song_id = _song(app, 'Hidden Gem').id
    _logout(client)
    for who in (None, 'stranger'):
        if who:
            _register(client, who)
        html = client.get('/explore').get_data(as_text=True)
        assert 'Hidden Gem' not in html
        assert 'Hidden Gem' not in client.get('/explore?query=hidden').get_data(as_text=True)
        assert client.get(f'/view_sheet/{song_id}').status_code == 200


def test_hidden_song_stays_in_other_users_favorites(client, app):
    _register(client, 'owner')
    _create(client)
    song_id = _song(app, 'Hidden Gem').id
    _logout(client)
    _register(client, 'fan')
    client.post(f'/api/favorites/{song_id}', headers={'X-Requested-With': 'fetch'})
    with app.app_context():
        song = db.session.get(Song, song_id)
        song.hidden = True
        db.session.commit()
    html = client.get('/explore').get_data(as_text=True)
    favorites = html.split('id="explore-panel-favorites"', 1)[1].split('id="explore-panel-library"', 1)[0]
    assert 'Hidden Gem' in favorites and 'Hidden Gem' not in _library_panel(html)


def test_only_owner_or_admin_can_toggle(client, app):
    _register(client, 'owner')
    _create(client)
    song_id = _song(app, 'Hidden Gem').id
    _logout(client)
    _register(client, 'stranger')
    with NO_ART:
        res = client.post(f'/edit_song/{song_id}', data={'title': 'Hidden Gem', 'song_key': 'G',
                                                         'hidden': '1', 'sheet_content': 'x'})
    assert res.status_code == 403
    assert _song(app, 'Hidden Gem').hidden is False
    with app.app_context():
        user = User.query.filter_by(username='stranger').one()
        user.is_admin = True
        db.session.commit()
    with NO_ART:
        client.post(f'/edit_song/{song_id}', data={'title': 'Hidden Gem', 'song_key': 'G',
                                                   'hidden': '1', 'sheet_content': '[G]la'})
    assert _song(app, 'Hidden Gem').hidden is True
    assert 'Hidden Gem' in _library_panel(client.get('/explore').get_data(as_text=True))  # admins see it


def test_unchecking_hidden_makes_song_public_again(auth_client, app):
    _create(auth_client, hidden='1')
    song_id = _song(app, 'Hidden Gem').id
    assert 'checked' in auth_client.get(f'/edit_song/{song_id}').get_data(as_text=True).split('id="hidden"', 1)[1][:120]
    with NO_ART:
        auth_client.post(f'/edit_song/{song_id}', data={'title': 'Hidden Gem', 'song_key': 'G',
                                                         'sheet_content': '[G]la'})
    assert _song(app, 'Hidden Gem').hidden is False


def test_library_count_excludes_hidden_for_others(client, app):
    _register(client, 'owner')
    _create(client, hidden='1')
    _logout(client)
    html = client.get('/explore').get_data(as_text=True)
    count = html.split('id="explore-tab-library"', 1)[1].split('explore-tab-count">', 1)[1].split('<', 1)[0]
    assert count == '1'  # only the seeded public song
