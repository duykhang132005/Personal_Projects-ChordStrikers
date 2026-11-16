"""Content-Security-Policy-Report-Only, /csp-report, offline JS, parsing.py."""
import logging
from pathlib import Path

import pytest

from app.csp import build_csp_policy


ROOT = Path(__file__).resolve().parents[1]


def test_csp_header_on_html_and_worker_routes(client):
    policy_keys = (
        "default-src 'self'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "style-src 'self'",
        "img-src 'self' data: https:",
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        "connect-src 'self'",
        "manifest-src 'self'",
        "worker-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
        'report-uri /csp-report',
        'report-to csp-endpoint',
    )
    for path in ('/', '/explore', '/offline', '/sw.js', '/healthz'):
        response = client.get(path)
        assert response.status_code == 200, path
        header = response.headers.get('Content-Security-Policy-Report-Only', '')
        assert header, path
        for directive in policy_keys:
            assert directive in header, (path, directive)
        assert 'Content-Security-Policy' not in response.headers or (
            'Content-Security-Policy-Report-Only' in response.headers
            and response.headers.get('Content-Security-Policy') is None
        )
        assert response.headers.get('Reporting-Endpoints') == 'csp-endpoint="/csp-report"'


def test_csp_header_matches_builder(client):
    header = client.get('/').headers['Content-Security-Policy-Report-Only']
    assert header == build_csp_policy('/csp-report')


def test_csp_report_only_can_be_turned_off(tmp_path, monkeypatch):
    monkeypatch.setenv('CSP_REPORT_ONLY', '0')
    from app import create_app, db

    song_dir = tmp_path / 'songs'
    song_dir.mkdir()
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'csp.db').replace('\\', '/'),
        'SECRET_KEY': 'test-secret-key',
        'SONG_DATA_DIR': str(song_dir),
    })
    try:
        assert app.config['CSP_REPORT_ONLY'] is False
        with app.test_client() as client:
            response = client.get('/healthz')
            assert 'Content-Security-Policy-Report-Only' not in response.headers
            assert 'Reporting-Endpoints' not in response.headers
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_csp_report_returns_204_for_both_content_types(raw_client, caplog):
    payload = (
        b'{"csp-report":{"effective-directive":"style-src-attr",'
        b'"blocked-uri":"inline","document-uri":"http://example.test/"}}'
    )
    with caplog.at_level(logging.INFO):
        response = raw_client.post(
            '/csp-report',
            data=payload,
            content_type='application/csp-report',
        )
    assert response.status_code == 204
    assert response.data == b''
    assert 'CSP report directive=style-src-attr' in caplog.text
    assert 'blocked=inline' in caplog.text

    reports = (
        b'[{"type":"csp-violation","body":{"effectiveDirective":"script-src-elem",'
        b'"blockedURL":"https://evil.example/x.js","documentURL":"http://example.test/explore"}}]'
    )
    with caplog.at_level(logging.INFO):
        response = raw_client.post(
            '/csp-report',
            data=reports,
            content_type='application/reports+json',
        )
    assert response.status_code == 204
    assert 'CSP report directive=script-src-elem' in caplog.text
    assert 'blocked=https://evil.example/x.js' in caplog.text


def test_csp_report_is_csrf_exempt(raw_client):
    response = raw_client.post(
        '/csp-report',
        data=b'{"csp-report":{"violated-directive":"style-src"}}',
        content_type='application/csp-report',
    )
    assert response.status_code == 204


def test_csp_report_rejects_oversize_body(raw_client, app):
    limit = int(app.config['CSP_REPORT_MAX_BYTES'])
    huge = b'{"csp-report":{"blocked-uri":"' + (b'x' * (limit + 1)) + b'"}}'
    assert len(huge) > limit
    response = raw_client.post(
        '/csp-report',
        data=huge,
        content_type='application/csp-report',
    )
    assert response.status_code == 413
    # Not the HTML 413 page used for oversized form posts.
    assert b'Request too large' not in response.data
    assert b'<!DOCTYPE' not in response.data


def test_csp_report_invalid_json_still_204(raw_client):
    response = raw_client.post(
        '/csp-report',
        data=b'not-json',
        content_type='application/csp-report',
    )
    assert response.status_code == 204


def test_offline_page_has_no_inline_handlers_and_uses_precached_js(client, app):
    html = client.get('/offline').get_data(as_text=True)
    lower = html.lower()
    assert 'onclick=' not in lower
    assert 'onload=' not in lower
    assert 'onerror=' not in lower
    assert '<style' not in lower
    assert '<script>' not in lower
    assert 'src="/static/js/offline.js"' in html
    assert 'href="/static/css/offline.css"' in html
    assert '?v=' not in html
    assert 'id="offline-retry"' in html

    js_path = Path(app.static_folder) / 'js' / 'offline.js'
    css_path = Path(app.static_folder) / 'css' / 'offline.css'
    assert js_path.is_file()
    assert css_path.is_file()
    js = js_path.read_text(encoding='utf-8')
    assert 'addEventListener' in js
    assert 'window.location.reload' in js
    assert 'onclick' not in js

    sw = client.get('/sw.js').get_data(as_text=True)
    assert "'/static/js/offline.js'" in sw or '"/static/js/offline.js"' in sw
    assert "'/static/css/offline.css'" in sw or '"/static/css/offline.css"' in sw
    # Version placeholder is still replaced; cache name still follows STATIC_ASSET_VERSION.
    assert '__VERSION__' not in sw
    assert 'CACHE_NAME' in sw


def test_parsing_py_is_removed():
    assert not (ROOT / 'app' / 'parsing.py').exists()
    assert not (ROOT / 'app' / 'parsing.pyc').exists()
    leftover = list((ROOT / 'app').glob('**/parsing.py'))
    assert leftover == []
    for path in (ROOT / 'docs' / 'MAINTAINING.md', ROOT / 'README.md'):
        if path.is_file():
            text = path.read_text(encoding='utf-8')
            assert 'parsing.py' not in text, path
    # Keep the real transpose helpers.
    assert (ROOT / 'app' / 'chord_logic.py').is_file()
