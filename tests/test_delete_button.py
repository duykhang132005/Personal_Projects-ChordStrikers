"""Edit page Delete Song button uses .btn-danger and a JS confirm."""
import re
from unittest import mock

from app.models import Song

CONFIRM = 'Are you sure you want to delete this song? This action cannot be undone.'


def _delete_button(html):
    m = re.search(r'<button[^>]*form="delete-form"[^>]*>', html)
    assert m, 'delete button missing'
    return m.group(0)


def test_edit_page_delete_button_has_no_inline_handlers(auth_client, app):
    with mock.patch('app.routes.creator.get_song_image_url', return_value=None):
        auth_client.post('/create', data={'title': 'Doomed', 'artist': 'X', 'song_key': 'C',
                                          'image_url': '', 'sheet_content': '[C]la'})
    with app.app_context():
        song_id = Song.query.filter_by(title='Doomed').first().id
    html = auth_client.get(f'/edit_song/{song_id}').get_data(as_text=True)
    btn = _delete_button(html)
    assert 'btn-danger' in btn
    assert 'onclick' not in btn and 'style=' not in btn
    assert f'data-confirm="{CONFIRM}"' in btn
    assert 'js/sheet_editor.js' in html


def test_confirm_listener_and_class_exist():
    with open('static/js/sheet_editor.js', encoding='utf-8') as f:
        js = f.read()
    assert 'data-confirm' in js and 'preventDefault' in js
    with open('static/styles.css', encoding='utf-8') as f:
        css = f.read()
    assert '.btn-danger' in css and '#dc3545' in css
