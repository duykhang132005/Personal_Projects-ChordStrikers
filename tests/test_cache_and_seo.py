"""Static Cache-Control rules, robots.txt and sitemap.xml."""
import re
import xml.etree.ElementTree as ET

from app import db
from app.models import Song
from app.storage import save_song_content

IMMUTABLE = 'public, max-age=31536000, immutable'


def _static_v(client):
    html = client.get('/').get_data(as_text=True)
    return re.search(r'styles\.css\?v=([^"&]+)', html).group(1)


# --- Cache-Control ---------------------------------------------------------

def test_versioned_static_is_immutable(client):
    v = _static_v(client)
    for path in ('/static/styles.css', '/static/vendor/vendor.min.css', '/static/js/view_sheet.js'):
        response = client.get(f'{path}?v={v}')
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == IMMUTABLE, path


def test_fonts_are_immutable_without_version(client):
    response = client.get('/static/fonts/roboto-mono-latin.woff2')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == IMMUTABLE


def test_unversioned_static_gets_modest_cache(client):
    response = client.get('/static/styles.css')
    assert response.headers['Cache-Control'] == 'public, max-age=3600'


def test_sheet_text_is_not_long_cached(client):
    response = client.get('/static/data/1.txt')
    assert response.headers['Cache-Control'] == 'no-cache'


def test_other_responses_keep_their_own_headers(client):
    sw = client.get('/sw.js')
    assert sw.headers['Cache-Control'] == 'no-cache'
    assert sw.headers['Service-Worker-Allowed'] == '/'
    assert client.get('/healthz').headers['Cache-Control'] == 'no-store'
    assert 'immutable' not in client.get('/api/favorites').headers.get('Cache-Control', '')
    assert 'immutable' not in client.get('/').headers.get('Cache-Control', '')
    assert 'immutable' not in client.get('/static/missing-file.css?v=1').headers.get('Cache-Control', '')


def test_every_template_static_reference_is_versioned(client, app):
    """Pages served to users only point at ?v= URLs (fonts excepted)."""
    pages = ['/', '/explore', '/view_sheet/1', '/offline']
    for page in pages:
        html = client.get(page).get_data(as_text=True)
        for ref in re.findall(r'(?:href|src)="(/static/[^"]+)"', html):
            if ref.startswith('/static/fonts/') or ref.startswith('/static/data/'):
                continue
            assert '?v=' in ref, f'{page}: {ref}'


# --- robots.txt --------------------------------------------------------------

def test_robots_txt(client):
    response = client.get('/robots.txt', base_url='https://example.org')
    assert response.status_code == 200 and response.mimetype == 'text/plain'
    body = response.get_data(as_text=True)
    assert 'User-agent: *' in body and 'Allow: /' in body
    for path in ('/create', '/creator', '/edit_song/', '/api/', '/login', '/logout', '/account'):
        assert f'Disallow: {path}\n' in body
    assert 'Sitemap: https://example.org/sitemap.xml' in body
    assert response.headers['Cache-Control'] == 'public, max-age=3600'


def test_robots_public_host_is_https(client):
    body = client.get('/robots.txt', base_url='http://chords.example.com').get_data(as_text=True)
    assert 'Sitemap: https://chords.example.com/sitemap.xml' in body


# --- sitemap.xml -------------------------------------------------------------

def _locs(response):
    root = ET.fromstring(response.get_data())
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    return {u.find('s:loc', ns).text: u.find('s:lastmod', ns) for u in root.findall('s:url', ns)}


def test_sitemap_lists_public_pages_and_skips_hidden(client, app):
    with app.app_context():
        hidden = Song(title='Secret', song_key='C', hidden=True)
        db.session.add(hidden)
        db.session.commit()
        save_song_content(hidden.id, '[C]x')
        hidden_id = hidden.id
    response = client.get('/sitemap.xml', base_url='https://example.org')
    assert response.status_code == 200 and response.mimetype == 'application/xml'
    assert response.headers['Cache-Control'] == 'public, max-age=900'
    locs = _locs(response)
    assert 'https://example.org/' in locs and 'https://example.org/explore' in locs
    assert 'https://example.org/view_sheet/1' in locs
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', locs['https://example.org/view_sheet/1'].text)
    assert f'https://example.org/view_sheet/{hidden_id}' not in locs


def test_service_worker_ignores_robots_and_sitemap(client):
    source = client.get('/sw.js').get_data(as_text=True)
    assert 'robots' not in source and 'sitemap' not in source
