"""CSRF protection: forged requests without the page's token are refused.

The usual ``client`` fixture adds a valid token like a real page does.
``raw_client`` sends nothing, like a form on another site would.
"""
import re
from html.parser import HTMLParser

import pytest

from app import db
from app.models import Favorite, Song, User
from app.storage import save_song_content

XHR = {'X-Requested-With': 'fetch'}


def _meta_token(html):
    match = re.search(r'<meta name="csrf-token" content="([^"]+)">', html)
    assert match, 'page has no csrf-token meta tag'
    return match.group(1)


def _sign_up(client, username='victim'):
    # Uses the real page: read the token the sign-in card embeds, then post it.
    html = client.get('/?signin=1').get_data(as_text=True)
    token = _form_tokens(html)['/register']
    response = client.post('/register', data={
        'username': username, 'password': 'secret123', 'confirmation': 'secret123',
        'csrf_token': token,
    })
    assert response.status_code == 302
    return client


class _Forms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.forms.append({'action': attrs.get('action', ''),
                               'method': (attrs.get('method') or 'get').lower(), 'token': None})
        elif tag == 'input' and self.forms and attrs.get('name') == 'csrf_token':
            self.forms[-1]['token'] = attrs.get('value')


def _forms(html):
    parser = _Forms()
    parser.feed(html)
    return parser.forms


def _form_tokens(html):
    return {f['action']: f['token'] for f in _forms(html) if f['method'] == 'post'}


def _own_song(app, username, title='Mine'):
    with app.app_context():
        user = User.query.filter_by(username=username).one()
        song = Song(title=title, artist='A', song_key='C', user_id=user.id)
        db.session.add(song)
        db.session.commit()
        save_song_content(song.id, '[C]la')
        return song.id


# ---- Forged requests are refused ----------------------------------------

def test_register_and_login_without_token_are_refused(raw_client, app):
    response = raw_client.post('/register', data={
        'username': 'mallory', 'password': 'secret123', 'confirmation': 'secret123'})
    assert response.status_code == 400
    assert 'Form expired' in response.get_data(as_text=True)
    with app.app_context():
        assert User.query.filter_by(username='mallory').count() == 0
    response = raw_client.post('/login', data={'username': 'x', 'password': 'y'})
    assert response.status_code == 400


def test_forged_create_delete_and_password_change_do_nothing(client, raw_client, app):
    _sign_up(client)
    song_id = _own_song(app, 'victim')
    # Same signed-in browser, but the request carries no token.
    with client.session_transaction() as sess:
        cookie_session = dict(sess)
    with raw_client.session_transaction() as sess:
        sess.update(cookie_session)

    assert raw_client.post(f'/delete_song/{song_id}').status_code == 400
    assert raw_client.post('/create', data={
        'title': 'Spam', 'song_key': 'C', 'sheet_content': '[C]x'}).status_code == 400
    assert raw_client.post(f'/edit_song/{song_id}', data={
        'title': 'Defaced', 'song_key': 'C', 'sheet_content': '[C]x'}).status_code == 400
    assert raw_client.post('/change-password', data={
        'current_password': 'secret123', 'new_password': 'hijacked99',
        'confirmation': 'hijacked99'}).status_code == 400
    assert raw_client.post('/logout').status_code == 400

    with app.app_context():
        song = db.session.get(Song, song_id)
        assert song is not None and song.title == 'Mine'
        assert Song.query.filter_by(title='Spam').count() == 0
    with raw_client.session_transaction() as sess:
        assert sess.get('user_id') is not None
    # The real password still works.
    client.post('/logout')
    assert client.post('/login', data={'username': 'victim', 'password': 'secret123'}).headers['Location'] == '/'


def test_token_from_another_session_is_refused(app, raw_client):
    other = app.test_client()
    other_token = _meta_token(other.get('/').get_data(as_text=True))
    raw_client.get('/')
    response = raw_client.post('/register', data={
        'username': 'mallory', 'password': 'secret123', 'confirmation': 'secret123',
        'csrf_token': other_token})
    assert response.status_code == 400


def test_tampered_token_is_refused(raw_client):
    token = _meta_token(raw_client.get('/').get_data(as_text=True))
    # Change one character of the signed payload (not the base64 padding bits).
    bad = token[:5] + ('A' if token[5] != 'A' else 'B') + token[6:]
    response = raw_client.post('/login', data={
        'username': 'x', 'password': 'y', 'csrf_token': bad})
    assert response.status_code == 400


def test_favorites_api_needs_token_header(client, raw_client, app):
    _sign_up(client)
    song_id = _own_song(app, 'victim')
    with client.session_transaction() as sess:
        cookie_session = dict(sess)
    with raw_client.session_transaction() as sess:
        sess.update(cookie_session)

    refused = raw_client.post(f'/api/favorites/{song_id}', headers=XHR)
    assert refused.status_code == 400
    assert refused.is_json and 'token' in refused.get_json()['error']
    assert raw_client.delete(f'/api/favorites/{song_id}', headers=XHR).status_code == 400
    with app.app_context():
        assert Favorite.query.count() == 0
    # Reading is still fine without a token.
    assert raw_client.get('/api/favorites').get_json() == {'ids': []}


# ---- Real tokens from the page are accepted -----------------------------

def test_page_token_lets_the_real_forms_work(raw_client, app):
    _sign_up(raw_client, 'realuser')
    with raw_client.session_transaction() as sess:
        assert sess.get('user_id') is not None

    create_html = raw_client.get('/create').get_data(as_text=True)
    token = _form_tokens(create_html)['/create']
    response = raw_client.post('/create', data={
        'title': 'Real Song', 'song_key': 'C', 'sheet_content': '[C]hi', 'csrf_token': token})
    assert response.status_code == 302
    with app.app_context():
        song_id = Song.query.filter_by(title='Real Song').one().id

    sheet = raw_client.get(f'/view_sheet/{song_id}').get_data(as_text=True)
    header_token = _meta_token(sheet)
    starred = raw_client.post(f'/api/favorites/{song_id}',
                              headers=dict(XHR, **{'X-CSRFToken': header_token}))
    assert starred.status_code == 200 and starred.get_json()['ids'] == [song_id]

    edit_html = raw_client.get(f'/edit_song/{song_id}').get_data(as_text=True)
    delete_token = _form_tokens(edit_html)[f'/delete_song/{song_id}']
    assert raw_client.post(f'/delete_song/{song_id}', data={'csrf_token': delete_token}).status_code == 302
    with app.app_context():
        assert db.session.get(Song, song_id) is None

    home = raw_client.get('/').get_data(as_text=True)
    logout_token = _form_tokens(home)['/logout']
    assert raw_client.post('/logout', data={'csrf_token': logout_token}).status_code == 302
    with raw_client.session_transaction() as sess:
        assert sess.get('user_id') is None


@pytest.mark.parametrize('path,signed_in', [
    ('/', False), ('/?signin=1', False), ('/', True), ('/create', True), ('/edit_song/{id}', True),
])
def test_every_post_form_carries_a_token(client, app, path, signed_in):
    if signed_in:
        _sign_up(client, 'formcheck')
        path = path.format(id=_own_song(app, 'formcheck'))
    html = client.get(path).get_data(as_text=True)
    post_forms = [f for f in _forms(html) if f['method'] == 'post']
    assert post_forms, path
    for form in post_forms:
        assert form['token'], f'{path}: form to {form["action"]} has no csrf_token'
