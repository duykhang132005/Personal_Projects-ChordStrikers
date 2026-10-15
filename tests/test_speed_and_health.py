"""gzip, health check, and the self-hosted chord font."""
import gzip
from unittest import mock

from sqlalchemy.exc import OperationalError

from app import db


def test_html_is_gzipped_when_asked(client):
    response = client.get('/explore', headers={'Accept-Encoding': 'gzip'})
    assert response.status_code == 200
    assert response.headers.get('Content-Encoding') == 'gzip'
    assert 'Accept-Encoding' in response.headers.get('Vary', '')
    assert b'ChordStrikers' in gzip.decompress(response.data)


def test_no_gzip_without_accept_encoding(client):
    response = client.get('/explore')
    assert response.headers.get('Content-Encoding') is None


def test_service_worker_headers_survive_compression(client):
    response = client.get('/sw.js', headers={'Accept-Encoding': 'gzip'})
    assert response.status_code == 200
    assert response.headers['Service-Worker-Allowed'] == '/'
    assert response.headers['Cache-Control'] == 'no-cache'
    assert response.mimetype == 'application/javascript'
    body = gzip.decompress(response.data) if response.headers.get('Content-Encoding') == 'gzip' else response.data
    assert b'__VERSION__' not in body and b'CACHE_PREFIX' in body


def test_healthz_ok(client):
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'ok', 'db': 'ok'}
    assert response.headers['Cache-Control'] == 'no-store'


def test_healthz_reports_db_failure(client, app):
    with mock.patch.object(db.session, 'execute', side_effect=OperationalError('SELECT 1', {}, Exception('down'))):
        response = client.get('/healthz')
    assert response.status_code == 503
    assert response.get_json() == {'status': 'error', 'db': 'error'}
    assert 'down' not in response.get_data(as_text=True)


def test_service_worker_leaves_healthz_alone(client):
    source = client.get('/sw.js').get_data(as_text=True)
    assert 'healthz' not in source


def test_chord_font_is_self_hosted_and_preloaded(client):
    html = client.get('/view_sheet/1').get_data(as_text=True)
    assert 'fonts.googleapis.com' not in html
    for name in ('roboto-mono-latin.woff2', 'roboto-mono-vietnamese.woff2'):
        assert f'href="/static/fonts/{name}" as="font" type="font/woff2" crossorigin' in html
        font = client.get(f'/static/fonts/{name}')
        assert font.status_code == 200 and font.data[:4] == b'wOF2'
    css = client.get('/static/styles.css').get_data(as_text=True)
    assert "url('fonts/roboto-mono-latin.woff2')" in css


def test_scroll_speed_buttons_are_in_the_markup(client):
    """Rendering them server-side keeps the toolbar from jumping (layout shift)."""
    html = client.get('/view_sheet/1').get_data(as_text=True)
    assert 'id="scroll-slower"' in html and 'id="scroll-faster"' in html
