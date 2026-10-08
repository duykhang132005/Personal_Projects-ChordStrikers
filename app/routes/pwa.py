"""Progressive Web App endpoints: manifest, service worker, offline page."""
import json
import os

from flask import Blueprint, Response, current_app, render_template, url_for

pwa_bp = Blueprint('pwa', __name__)

THEME_COLOR = '#1a120c'


@pwa_bp.route('/manifest.webmanifest')
def manifest():
    data = {
        'id': '/',
        'name': 'ChordStrikers',
        'short_name': 'ChordStrikers',
        'description': 'Free chord sheets with transposing and guitar fret diagrams.',
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'background_color': THEME_COLOR,
        'theme_color': THEME_COLOR,
        'icons': [
            {
                'src': url_for('static', filename='icons/icon-192.png'),
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': url_for('static', filename='icons/icon-512.png'),
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': url_for('static', filename='icons/icon-maskable-512.png'),
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'maskable',
            },
        ],
    }
    response = Response(json.dumps(data), mimetype='application/manifest+json')
    response.headers['Cache-Control'] = 'no-cache'
    return response


@pwa_bp.route('/sw.js')
def service_worker():
    """Serve the worker from the site root so it can control every page."""
    path = os.path.join(current_app.static_folder, 'sw.js')
    with open(path, 'r', encoding='utf-8') as handle:
        source = handle.read()
    version = current_app.config.get('STATIC_ASSET_VERSION', '0')
    source = source.replace('__VERSION__', str(version))
    response = Response(source, mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@pwa_bp.route('/offline')
def offline():
    return render_template('offline.html')
