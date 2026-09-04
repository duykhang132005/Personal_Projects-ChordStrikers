import os

from app.models import Song
from app.storage import load_song_content, get_song_filepath, save_song_content
from app import db


def test_home_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"ChordStrikers" in response.data


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
    image_url = 'https://i.scdn.co/image/ab67616d0000b273abc'
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
