"""robots.txt and sitemap.xml for search engines."""
import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from flask import Blueprint, Response, current_app, request, url_for

from ..models import Song
from ..storage import get_song_filepath

seo_bp = Blueprint('seo', __name__)

# Pages crawlers should skip: forms, account actions and JSON endpoints.
_DISALLOW = ['/create', '/creator', '/edit_song/', '/delete_song/', '/api/',
             '/login', '/logout', '/register', '/account', '/offline', '/healthz']


def _base_url():
    """Absolute site root. SITE_URL wins; public hosts are assumed https."""
    configured = (current_app.config.get('SITE_URL') or '').rstrip('/')
    if configured:
        return configured
    host = request.host
    local = host.startswith(('localhost', '127.', '[::1]')) or host.split(':')[0] == 'localhost'
    scheme = request.scheme if local else 'https'
    return f'{scheme}://{host}'


@seo_bp.route('/robots.txt')
def robots():
    lines = ['User-agent: *', 'Allow: /']
    lines += [f'Disallow: {path}' for path in _DISALLOW]
    lines += ['', f'Sitemap: {_base_url()}/sitemap.xml', '']
    response = Response('\n'.join(lines), mimetype='text/plain')
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


def _lastmod(song_id):
    """Sheet file time, the only edit timestamp a song has."""
    try:
        stamp = os.path.getmtime(get_song_filepath(song_id))
    except OSError:
        return None
    return datetime.fromtimestamp(stamp, timezone.utc).strftime('%Y-%m-%d')


@seo_bp.route('/sitemap.xml')
def sitemap():
    base = _base_url()
    urls = [(base + url_for('main.home'), None), (base + url_for('main.explore'), None)]
    songs = Song.query.filter(Song.hidden.is_(False)).order_by(Song.id).all()
    for song in songs:
        urls.append((base + url_for('main.view_sheet', song_id=song.id), _lastmod(song.id)))
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        entry = f'<url><loc>{escape(loc)}</loc>'
        if lastmod:
            entry += f'<lastmod>{lastmod}</lastmod>'
        parts.append(entry + '</url>')
    parts.append('</urlset>')
    response = Response('\n'.join(parts) + '\n', mimetype='application/xml')
    response.headers['Cache-Control'] = 'public, max-age=900'
    return response
