"""Session cookie settings, env-flag parsing, and the 1 MB body cap."""
import os

import pytest

from app import create_app, db
from app.config import MAX_CONTENT_LENGTH, env_flag, session_cookie_secure


def _app(tmp_path, **extra):
    config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'cfg.db').replace('\\', '/'),
        'SECRET_KEY': 'test-secret-key',
        'SONG_DATA_DIR': str(tmp_path / 'songs'),
    }
    config.update(extra)
    os.makedirs(config['SONG_DATA_DIR'], exist_ok=True)
    return create_app(config)


def _close(app):
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.mark.parametrize('value', ['1', 'true', 'TRUE', 'yes', 'On'])
def test_env_flag_truthy(monkeypatch, value):
    monkeypatch.setenv('SESSION_COOKIE_SECURE', value)
    assert env_flag('SESSION_COOKIE_SECURE') is True
    assert session_cookie_secure() is True


@pytest.mark.parametrize('value', [None, '', '0', 'false', 'no', 'off', 'maybe'])
def test_env_flag_falsey_and_default_off(monkeypatch, value):
    monkeypatch.delenv('SESSION_COOKIE_SECURE', raising=False)
    if value is None:
        assert env_flag('SESSION_COOKIE_SECURE') is False
        assert session_cookie_secure() is False
        return
    monkeypatch.setenv('SESSION_COOKIE_SECURE', value)
    assert env_flag('SESSION_COOKIE_SECURE') is False
    assert session_cookie_secure() is False


def test_default_cookie_and_body_limits(app):
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert app.config['SESSION_COOKIE_SECURE'] is False
    assert app.config['MAX_CONTENT_LENGTH'] == MAX_CONTENT_LENGTH == 1024 * 1024
    assert 'REMEMBER_COOKIE_SECURE' not in app.config
    assert 'REMEMBER_COOKIE_SAMESITE' not in app.config


def test_session_cookie_secure_is_read_when_the_app_starts(monkeypatch, tmp_path):
    monkeypatch.setenv('SESSION_COOKIE_SECURE', '1')
    app = _app(tmp_path)
    try:
        assert app.config['SESSION_COOKIE_SECURE'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    finally:
        _close(app)


def test_session_cookie_secure_stays_off_when_unset(monkeypatch, tmp_path):
    monkeypatch.delenv('SESSION_COOKIE_SECURE', raising=False)
    app = _app(tmp_path)
    try:
        assert app.config['SESSION_COOKIE_SECURE'] is False
    finally:
        _close(app)


def test_oversize_request_returns_413(client, app):
    assert app.config['MAX_CONTENT_LENGTH'] == 1024 * 1024
    huge = 'x' * (1024 * 1024 + 1)
    response = client.post('/register', data={
        'username': 'huge',
        'password': huge,
        'confirmation': huge,
    })
    assert response.status_code == 413
    html = response.get_data(as_text=True)
    assert 'Request too large' in html
    assert '1 MB' in html
