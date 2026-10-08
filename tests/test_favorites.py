"""Favorites API, offline-favorites service worker rules and Explore tabs."""
import re
import sqlite3

from app import create_app, db
from app.models import Favorite, Song, User
from app.storage import save_song_content

XHR = {'X-Requested-With': 'fetch'}


def _login(client, username='favuser'):
    client.post('/register', data={
        'username': username,
        'password': 'testpass1',
        'confirmation': 'testpass1',
    })
    return client


def _song_id(app, title='Test Song'):
    with app.app_context():
        return Song.query.filter_by(title=title).first().id


def _add_song(app, title, user_id=None):
    with app.app_context():
        song = Song(title=title, artist='Someone', song_key='G', user_id=user_id)
        db.session.add(song)
        db.session.commit()
        save_song_content(song.id, '[G]' + title)
        return song.id


def _user_id(app, username):
    with app.app_context():
        return User.query.filter_by(username=username).first().id


# ---- API ----------------------------------------------------------------

def test_favorites_require_login(client, app):
    song_id = _song_id(app)
    assert client.get('/api/favorites').status_code == 401
    assert client.post(f'/api/favorites/{song_id}', headers=XHR).status_code == 401
    assert client.delete(f'/api/favorites/{song_id}', headers=XHR).status_code == 401


def test_add_list_and_remove_favorite(client, app):
    _login(client)
    song_id = _song_id(app)

    response = client.post(f'/api/favorites/{song_id}', headers=XHR)
    assert response.status_code == 200
    assert response.get_json() == {'ids': [song_id], 'song_id': song_id, 'favorited': True}
    assert response.headers['Cache-Control'] == 'no-store'

    # Adding twice is harmless (unique per user and song).
    client.post(f'/api/favorites/{song_id}', headers=XHR)
    assert client.get('/api/favorites').get_json() == {'ids': [song_id]}
    with app.app_context():
        assert Favorite.query.count() == 1

    response = client.delete(f'/api/favorites/{song_id}', headers=XHR)
    assert response.get_json()['favorited'] is False
    assert client.get('/api/favorites').get_json() == {'ids': []}

    # Removing again is also harmless.
    assert client.delete(f'/api/favorites/{song_id}', headers=XHR).status_code == 200


def test_favorite_write_needs_script_header(client, app):
    """A cross-site HTML form cannot add the header, so it cannot star."""
    _login(client)
    song_id = _song_id(app)
    assert client.post(f'/api/favorites/{song_id}').status_code == 400
    assert client.get('/api/favorites').get_json() == {'ids': []}


def test_favorite_unknown_song_is_404(client):
    _login(client)
    assert client.post('/api/favorites/9999', headers=XHR).status_code == 404


def test_favorites_are_per_user(app):
    song_id = _song_id(app)
    first = _login(app.test_client(), 'alice')
    second = _login(app.test_client(), 'bob')
    first.post(f'/api/favorites/{song_id}', headers=XHR)
    assert first.get('/api/favorites').get_json() == {'ids': [song_id]}
    assert second.get('/api/favorites').get_json() == {'ids': []}


def test_deleting_song_removes_its_favorites(client, app):
    _login(client)
    owner_id = _user_id(app, 'favuser')
    song_id = _add_song(app, 'Mine To Delete', user_id=owner_id)
    client.post(f'/api/favorites/{song_id}', headers=XHR)

    response = client.post(f'/delete_song/{song_id}')
    assert response.status_code == 302
    with app.app_context():
        assert Favorite.query.filter_by(song_id=song_id).count() == 0
    assert client.get('/api/favorites').get_json() == {'ids': []}


# ---- View Sheet button ----------------------------------------------------

def test_view_sheet_favorite_button_state(client, app):
    song_id = _song_id(app)

    html = client.get(f'/view_sheet/{song_id}').get_data(as_text=True)
    assert 'id="btn-favorite"' not in html
    assert 'Save offline' in html
    assert 'signin=1' in html

    _login(client)
    html = client.get(f'/view_sheet/{song_id}').get_data(as_text=True)
    assert 'id="btn-favorite"' in html
    assert 'aria-pressed="false"' in html

    client.post(f'/api/favorites/{song_id}', headers=XHR)
    html = client.get(f'/view_sheet/{song_id}').get_data(as_text=True)
    assert 'aria-pressed="true"' in html
    assert 'Saved offline' in html


def test_offline_save_fetch_does_not_consume_flashes(client, app):
    song_id = _song_id(app)
    _login(client)  # registering leaves a "Welcome" flash pending
    saved = client.get(f'/view_sheet/{song_id}', headers={'X-CS-Offline-Save': '1'})
    assert 'Welcome' not in saved.get_data(as_text=True)
    assert 'Welcome' in client.get('/').get_data(as_text=True)


def test_login_form_keeps_next(client):
    html = client.get('/?signin=1&next=/explore?tab=favorites').get_data(as_text=True)
    assert 'name="next"' in html


# ---- Service worker rules -------------------------------------------------

def test_service_worker_keeps_favorites_cache_on_upgrade(client):
    body = client.get('/sw.js').get_data(as_text=True)
    assert "FAVORITES_CACHE = CACHE_PREFIX + 'favorites'" in body
    assert 'key !== FAVORITES_CACHE' in body
    assert "'sync-favorites'" in body and "'clear-favorites'" in body
    # Song text files are still never cached by the static rule.
    assert "'/static/data/'" in body


def test_offline_page_lists_saved_sheets(client):
    html = client.get('/offline').get_data(as_text=True)
    assert 'chordstrikers-favorites' in html
    assert 'saved-list' in html


def test_pages_expose_sign_in_state_for_sync(client):
    assert 'data-signed-in="0"' in client.get('/').get_data(as_text=True)
    _login(client)
    assert 'data-signed-in="1"' in client.get('/').get_data(as_text=True)


# ---- Explore tabs -----------------------------------------------------------

def test_explore_tabs_markup_signed_out(client):
    html = client.get('/explore').get_data(as_text=True)
    assert 'role="tablist"' in html
    for tab in ('mine', 'favorites', 'library'):
        assert f'id="explore-tab-{tab}"' in html
        assert f'id="explore-panel-{tab}"' in html
    assert 'Your scores' in html and 'Your favorites' in html and 'Entire library' in html
    # Signed out defaults to the library and asks to sign in elsewhere.
    assert 'id="explore-tab-library" data-tab="library"' in html
    assert len(re.findall(r'aria-selected="true"\s+tabindex="0"', html)) == 1
    library_tab = html.split('id="explore-tab-library"')[1].split('</button>')[0]
    assert 'aria-selected="true"' in library_tab
    assert 'Sign in to see the scores you have written.' in html
    assert 'Sign in to star sheets' in html


def test_explore_tabs_empty_states_signed_in(client):
    _login(client)
    html = client.get('/explore').get_data(as_text=True)
    assert 'You have not created any scores yet.' in html
    assert '/create' in html
    assert 'No favorites yet.' in html


def test_explore_tabs_list_my_scores_and_favorites(client, app):
    _login(client)
    owner_id = _user_id(app, 'favuser')
    mine_id = _add_song(app, 'Zebra Mine', user_id=owner_id)
    other_id = _song_id(app)
    client.post(f'/api/favorites/{other_id}', headers=XHR)

    html = client.get('/explore?tab=mine').get_data(as_text=True)
    mine_panel = html.split('id="explore-panel-mine"')[1].split('id="explore-panel-favorites"')[0]
    fav_panel = html.split('id="explore-panel-favorites"')[1].split('id="explore-panel-library"')[0]
    library_panel = html.split('id="explore-panel-library"')[1]

    assert 'Zebra Mine' in mine_panel and 'Test Song' not in mine_panel
    assert 'Test Song' in fav_panel and 'Zebra Mine' not in fav_panel
    assert 'Test Song' in library_panel and 'Zebra Mine' in library_panel
    assert f'/view_sheet/{mine_id}' in mine_panel
    # ?tab= selects the panel on the server; the others start hidden.
    assert 'data-from-url="1"' in html
    assert 'aria-labelledby="explore-tab-mine" tabindex="0">' in html
    assert 'aria-labelledby="explore-tab-library" tabindex="0" hidden>' in html


def test_explore_search_with_no_match_in_my_scores(client, app):
    _login(client)
    _add_song(app, 'Only Mine', user_id=_user_id(app, 'favuser'))
    html = client.get('/explore?tab=mine&query=nothing-matches').get_data(as_text=True)
    assert 'None of your scores match this search.' in html


def test_explore_ignores_unknown_tab(client):
    html = client.get('/explore?tab=bogus').get_data(as_text=True)
    library_tab = html.split('id="explore-tab-library"')[1].split('</button>')[0]
    assert 'aria-selected="true"' in library_tab
    assert 'data-from-url="0"' in html


# ---- Existing databases ---------------------------------------------------

def test_older_database_gets_favorites_table(tmp_path):
    """create_app adds the favorites table to a pre-favorites songs.db."""
    db_path = tmp_path / 'songs.db'
    sheets = tmp_path / 'sheets'
    sheets.mkdir()
    conn = sqlite3.connect(db_path)
    conn.execute(
        'CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE, '
        'password_hash VARCHAR(255) NOT NULL, is_admin BOOLEAN NOT NULL DEFAULT 0)'
    )
    conn.execute(
        'CREATE TABLE songs (id INTEGER PRIMARY KEY, title VARCHAR(100) NOT NULL, '
        'artist VARCHAR(100), song_key VARCHAR(100) NOT NULL, image_url VARCHAR(512), '
        'user_id INTEGER)'
    )
    conn.execute("INSERT INTO songs (id, title, song_key) VALUES (1, 'Keep Me', 'C')")
    conn.commit()
    conn.close()
    (sheets / '1.txt').write_text('[C]Keep', encoding='utf-8')

    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'SONG_DATA_DIR': str(sheets),
    })
    try:
        conn = sqlite3.connect(db_path)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'favorites' in tables
        assert conn.execute('SELECT COUNT(*) FROM songs').fetchone()[0] == 1
        conn.close()
        client = _login(app.test_client(), 'olddb')
        assert client.post('/api/favorites/1', headers=XHR).get_json()['ids'] == [1]
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
