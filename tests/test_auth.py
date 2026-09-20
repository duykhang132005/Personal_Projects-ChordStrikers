import pytest

from werkzeug.security import check_password_hash



from app import db

from app.models import User, Song

from app.storage import load_song_content





def register(client, username='alice', password='secret123'):

    return client.post('/register', data={

        'username': username,

        'password': password,

        'confirmation': password,

    }, follow_redirects=False)





def login(client, username='alice', password='secret123'):

    return client.post('/login', data={

        'username': username,

        'password': password,

    }, follow_redirects=False)





def test_register_login_logout(client, app):

    response = register(client)

    assert response.status_code == 302

    assert response.headers['Location'].endswith('/')



    with app.app_context():

        user = User.query.filter_by(username='alice').first()

        assert user is not None

        assert check_password_hash(user.password_hash, 'secret123')

        user_id = user.id



    with client.session_transaction() as sess:

        assert sess.get('user_id') == user_id



    home = client.get('/')

    assert home.status_code == 200

    assert b'Account' in home.data

    assert b'alice' in home.data



    logout = client.post('/logout', follow_redirects=False)

    assert logout.status_code == 302

    with client.session_transaction() as sess:

        assert sess.get('user_id') is None



    # Login again

    response = login(client)

    assert response.status_code == 302

    with client.session_transaction() as sess:

        assert sess.get('user_id') is not None





def test_register_duplicate_username(client):

    assert register(client).status_code == 302

    client.get('/logout')

    response = register(client, username='alice', password='otherpass')

    assert response.status_code == 302

    assert 'signin=1' in response.headers['Location']





def test_login_rejects_bad_password(client):

    register(client)

    client.get('/logout')

    response = login(client, password='wrong')

    assert response.status_code == 302

    assert 'signin=1' in response.headers['Location']

    with client.session_transaction() as sess:

        assert sess.get('user_id') is None





def test_create_requires_login(client):

    response = client.get('/create', follow_redirects=False)

    assert response.status_code == 302

    loc = response.headers['Location']

    assert 'signin=1' in loc

    assert loc.endswith('/') or '/?' in loc or loc.endswith('/?signin=1') or 'signin=1' in loc



    response = client.post('/create', data={

        'title': 'Nope',

        'artist': 'X',

        'song_key': 'C',

        'sheet_content': '[C]Hi',

    }, follow_redirects=False)

    assert response.status_code == 302

    assert 'signin=1' in response.headers['Location']





def test_logged_in_create_sets_user_id(client, app):

    register(client, username='bob', password='pw12345')

    with app.app_context():

        user = User.query.filter_by(username='bob').one()

        user_id = user.id



    response = client.post('/create', data={

        'title': 'Owned Song',

        'artist': 'Bob',

        'song_key': 'G',

        'sheet_content': '[G]Hello',

    }, follow_redirects=True)

    assert response.status_code == 200



    with app.app_context():

        song = Song.query.filter_by(title='Owned Song').one()

        assert song.user_id == user_id

        assert load_song_content(song.id) == '[G]Hello'





def test_edit_delete_forbidden_for_other_owner(client, app):

    register(client, username='owner', password='pw12345')

    client.post('/create', data={

        'title': 'Private',

        'artist': 'O',

        'song_key': 'C',

        'sheet_content': '[C]Mine',

    })

    with app.app_context():

        song_id = Song.query.filter_by(title='Private').one().id



    client.post('/logout')

    register(client, username='intruder', password='pw12345')



    response = client.get(f'/edit_song/{song_id}')

    assert response.status_code == 403



    response = client.post(f'/delete_song/{song_id}')

    assert response.status_code == 403



    with app.app_context():

        assert db.session.get(Song, song_id) is not None





def test_legacy_song_without_owner_not_editable_by_regular_user(client, app):

    """Songs with user_id NULL are not editable by non-admin users."""

    with app.app_context():

        song = Song.query.filter_by(title='Test Song').one()

        assert song.user_id is None

        song_id = song.id



    register(client, username='editor', password='pw12345')

    response = client.get(f'/edit_song/{song_id}')

    assert response.status_code == 403





def test_explore_author_filter_and_view_hides_edit(client, app):

    register(client, username='author1', password='pw12345')

    client.post('/create', data={

        'title': 'AuthorFilterSong',

        'artist': 'Band',

        'song_key': 'C',

        'sheet_content': '[C]Hi',

    })

    client.post('/logout')

    register(client, username='viewer1', password='pw12345')



    explore = client.get('/explore?author=author1')

    assert explore.status_code == 200

    assert b'AuthorFilterSong' in explore.data

    assert b'authored by' in explore.data.lower() or b'Authored by' in explore.data



    with app.app_context():

        song_id = Song.query.filter_by(title='AuthorFilterSong').one().id

    view = client.get(f'/view_sheet/{song_id}')

    assert view.status_code == 200

    assert b'Authored by:' in view.data

    assert b'author1' in view.data

    # Edit button should be hidden for non-owner

    assert b'> Edit' not in view.data and b'>Edit' not in view.data



def test_admin_can_edit_other_owner(client, app):
    register(client, username='owner2', password='pw12345')
    client.post('/create', data={
        'title': 'OwnedByOther',
        'artist': 'O',
        'song_key': 'C',
        'sheet_content': '[C]Mine',
    })
    with app.app_context():
        from werkzeug.security import generate_password_hash
        from app.models import User
        song_id = Song.query.filter_by(title='OwnedByOther').one().id
        admin = User.query.filter_by(username='admin').first()
        if admin is None:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True,
            )
            db.session.add(admin)
        else:
            admin.is_admin = True
            admin.password_hash = generate_password_hash('admin123')
        db.session.commit()

    client.post('/logout')
    login(client, username='admin', password='admin123')
    response = client.get(f'/edit_song/{song_id}')
    assert response.status_code == 200



def test_change_password(auth_client, app):

    bad = auth_client.post('/change-password', data={

        'current_password': 'wrong',

        'new_password': 'newpass12',

        'confirmation': 'newpass12',

    }, follow_redirects=False)

    assert bad.status_code == 302

    assert 'account=1' in bad.headers['Location']



    ok = auth_client.post('/change-password', data={

        'current_password': 'testpass1',

        'new_password': 'newpass12',

        'confirmation': 'newpass12',

    }, follow_redirects=False)

    assert ok.status_code == 302

    assert 'account=1' in ok.headers['Location']



    with app.app_context():

        from app.models import User

        user = User.query.filter_by(username='tester').first()

        assert user is not None

        assert check_password_hash(user.password_hash, 'newpass12')



    # Old password no longer works

    auth_client.post('/logout')

    refused = login(auth_client, username='tester', password='testpass1')

    assert refused.status_code == 302

    assert 'signin=1' in refused.headers['Location']

    again = login(auth_client, username='tester', password='newpass12')

    assert again.status_code == 302

    assert 'signin=1' not in (again.headers.get('Location') or '')

