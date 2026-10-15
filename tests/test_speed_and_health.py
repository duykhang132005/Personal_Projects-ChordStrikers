"""gzip, health check, and the self-hosted chord font."""
import gzip
from unittest import mock

from sqlalchemy import text
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


def test_healthz_reports_missing_songs_table(client, app):
    with app.app_context():
        db.session.execute(text('DROP TABLE songs'))
        db.session.commit()
    response = client.get('/healthz')
    assert response.status_code == 503
    assert response.get_json() == {'status': 'error', 'db': 'error'}
    assert response.headers['Cache-Control'] == 'no-store'
    assert 'songs' not in response.get_data(as_text=True)


def test_view_transitions_css_and_reduced_motion(client):
    css = client.get('/static/styles.css').get_data(as_text=True)
    assert '@view-transition' in css and 'navigation: auto' in css
    assert '::view-transition-old(root)' in css
    assert 'prefers-reduced-motion: reduce' in css
    assert 'navigation: none' in css
    assert 'view-transition-name: site-nav' in css
    # Chord sheet must never be a shared element (would animate sheet open).
    assert 'view-transition-name: song' not in css
    assert 'view-transition-name: sheet' not in css


def test_no_white_flash_head_order(client):
    """Theme and a dark canvas are set inline before any stylesheet loads."""
    html = client.get('/').get_data(as_text=True)
    head = html.split('</head>', 1)[0]
    first_css = head.index('rel="stylesheet"')
    assert head.index("setAttribute('data-theme'") < first_css
    assert head.index('html { background: #3a2f63; }') < first_css
    assert 'html[data-theme="wooden"] { background: #3a2412; }' in head
    assert 'html[data-theme="limelight"] { background: #0e2418; }' in head
    assert head.index('name="theme-color"') < head.index('<script>')


def test_speculation_rules_only_safe_pages(client):
    import json
    html = client.get('/').get_data(as_text=True)
    rules = json.loads(html.split('<script type="speculationrules">', 1)[1].split('</script>', 1)[0])
    patterns = [r['href_matches'] for r in rules['prerender'][0]['where']['or']]
    assert patterns == ['/', '/explore', '/create', '/view_sheet/*']
    assert rules['prerender'][0]['eagerness'] == 'moderate'
    for unsafe in ('logout', 'edit', 'delete', 'api', 'favorites'):
        assert not any(unsafe in p for p in patterns)
