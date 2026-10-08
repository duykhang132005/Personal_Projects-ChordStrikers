import os
import time

import pytest

from app import create_app
from app.assets import compute_static_version


def test_manifest_is_valid_and_installable(client):
    response = client.get('/manifest.webmanifest')
    assert response.status_code == 200
    assert response.mimetype == 'application/manifest+json'
    data = response.get_json(force=True)
    assert data['display'] == 'standalone'
    assert data['start_url'] == '/'
    sizes = {icon['sizes'] for icon in data['icons']}
    assert {'192x192', '512x512'} <= sizes
    assert any(icon['purpose'] == 'maskable' for icon in data['icons'])


def test_manifest_icons_exist_on_disk(client, app):
    data = client.get('/manifest.webmanifest').get_json(force=True)
    for icon in data['icons']:
        relative = icon['src'].replace('/static/', '', 1)
        assert os.path.isfile(os.path.join(app.static_folder, relative)), icon['src']


def test_service_worker_served_from_root(client):
    response = client.get('/sw.js')
    assert response.status_code == 200
    assert 'javascript' in response.mimetype
    assert response.headers['Service-Worker-Allowed'] == '/'
    body = response.get_data(as_text=True)
    assert '__VERSION__' not in body
    assert 'addEventListener' in body


def test_offline_page_renders(client):
    response = client.get('/offline')
    assert response.status_code == 200
    assert b'offline' in response.data.lower()


def test_pages_link_manifest_and_register_worker(client):
    html = client.get('/').get_data(as_text=True)
    assert 'rel="manifest"' in html
    assert 'apple-touch-icon' in html
    assert 'serviceWorker' in html


def test_login_still_works_with_pwa_routes(client):
    client.post('/register', data={
        'username': 'pwauser',
        'password': 'testpass1',
        'confirmation': 'testpass1',
    })
    response = client.get('/')
    assert response.status_code == 200


def test_static_version_follows_file_mtime(tmp_path, monkeypatch):
    monkeypatch.delenv('STATIC_ASSET_VERSION', raising=False)
    target = tmp_path / 'styles.css'
    target.write_text('a{}')
    os.utime(target, (1_700_000_000, 1_700_000_000))
    first = compute_static_version(str(tmp_path))
    os.utime(target, (1_800_000_000, 1_800_000_000))
    second = compute_static_version(str(tmp_path))
    assert first != second


def test_static_version_ignores_song_data(tmp_path, monkeypatch):
    monkeypatch.delenv('STATIC_ASSET_VERSION', raising=False)
    (tmp_path / 'data').mkdir()
    css = tmp_path / 'styles.css'
    css.write_text('a{}')
    os.utime(css, (1_700_000_000, 1_700_000_000))
    before = compute_static_version(str(tmp_path))
    song = tmp_path / 'data' / '1.txt'
    song.write_text('[C]hi')
    os.utime(song, (1_900_000_000, 1_900_000_000))
    assert compute_static_version(str(tmp_path)) == before


def test_static_version_can_be_pinned(tmp_path, monkeypatch):
    monkeypatch.setenv('STATIC_ASSET_VERSION', 'pinned1')
    assert compute_static_version(str(tmp_path)) == 'pinned1'


def _clean_secret_env(monkeypatch):
    for name in ('SECRET_KEY', 'ALLOW_INSECURE_DEV_KEY', 'FLASK_DEBUG'):
        monkeypatch.delenv(name, raising=False)


def test_missing_secret_key_fails_loudly(monkeypatch):
    _clean_secret_env(monkeypatch)
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app()


def test_blank_secret_key_fails_loudly(monkeypatch):
    _clean_secret_env(monkeypatch)
    monkeypatch.setenv('SECRET_KEY', '   ')
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app()


def _dev_config(tmp_path):
    return {
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'dev.db').replace('\\', '/'),
        'SONG_DATA_DIR': str(tmp_path / 'songs'),
    }


def test_dev_flag_allows_insecure_key(monkeypatch, tmp_path):
    _clean_secret_env(monkeypatch)
    monkeypatch.setenv('ALLOW_INSECURE_DEV_KEY', '1')
    os.makedirs(tmp_path / 'songs', exist_ok=True)
    # The dev fallback must still warn loudly; assert it instead of leaking it.
    with pytest.warns(UserWarning, match='insecure development key'):
        app = create_app(_dev_config(tmp_path))
    assert app.config['SECRET_KEY'] == 'insecure-dev-key-not-for-production'
    with app.app_context():
        from app import db
        db.session.remove()
        db.engine.dispose()


def test_placeholder_secret_key_warns(monkeypatch, tmp_path):
    _clean_secret_env(monkeypatch)
    monkeypatch.setenv('SECRET_KEY', 'your_random_secret_key_here')
    os.makedirs(tmp_path / 'songs', exist_ok=True)
    with pytest.warns(UserWarning, match='placeholder'):
        app = create_app(_dev_config(tmp_path))
    with app.app_context():
        from app import db
        db.session.remove()
        db.engine.dispose()


def test_test_config_secret_key_wins_without_warning(monkeypatch, tmp_path, recwarn):
    _clean_secret_env(monkeypatch)
    config = dict(_dev_config(tmp_path), TESTING=True, SECRET_KEY='from-test-config')
    os.makedirs(tmp_path / 'songs', exist_ok=True)
    app = create_app(config)
    assert app.config['SECRET_KEY'] == 'from-test-config'
    assert not [w for w in recwarn if 'SECRET_KEY' in str(w.message)]
    with app.app_context():
        from app import db
        db.session.remove()
        db.engine.dispose()


def test_real_secret_key_is_used(monkeypatch, tmp_path):
    _clean_secret_env(monkeypatch)
    monkeypatch.setenv('SECRET_KEY', 'a-real-secret-value')
    os.makedirs(tmp_path / 'songs', exist_ok=True)
    app = create_app(_dev_config(tmp_path))
    assert app.config['SECRET_KEY'] == 'a-real-secret-value'
    with app.app_context():
        from app import db
        db.session.remove()
        db.engine.dispose()
