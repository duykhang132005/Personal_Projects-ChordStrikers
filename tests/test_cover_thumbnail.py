"""View Sheet cover art thumbnail."""
from app import db
import os

from app.models import Song
from app.storage import get_song_filepath


def _add(app, **fields):
    with app.app_context():
        song = Song(title='Thumb Song', artist='A', song_key='C', **fields)
        db.session.add(song)
        db.session.commit()
        path = get_song_filepath(song.id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('[C]la')
        return song.id


def test_thumbnail_rendered_when_url_present(app, client):
    sid = _add(app, image_url='https://example.com/art.jpg', album='Great Album')
    html = client.get(f'/view_sheet/{sid}').get_data(as_text=True)
    assert 'class="sheet-cover"' in html
    assert 'src="https://example.com/art.jpg"' in html
    assert 'alt="Great Album cover art"' in html
    assert 'loading="lazy"' in html and 'decoding="async"' in html
    assert 'width="64" height="64"' in html


def test_thumbnail_alt_falls_back_to_title(app, client):
    sid = _add(app, image_url='https://example.com/art.jpg')
    html = client.get(f'/view_sheet/{sid}').get_data(as_text=True)
    assert 'alt="Thumb Song cover art"' in html


def test_no_thumbnail_without_url(app, client):
    sid = _add(app, image_url=None)
    html = client.get(f'/view_sheet/{sid}').get_data(as_text=True)
    assert '<img class="sheet-cover"' not in html
