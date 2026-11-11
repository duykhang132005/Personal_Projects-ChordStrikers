import pytest
import os
import shutil
import tempfile

import flask
from flask.testing import FlaskClient
from flask_wtf.csrf import generate_csrf

from app import create_app, db
from app.models import Song
from app.storage import save_song_content


class CSRFClient(FlaskClient):
    """Test client that sends a valid CSRF token, like the real pages do.

    CSRF protection stays ON in every test. For POST, PUT, PATCH and DELETE
    this client adds the X-CSRFToken header that Flask-WTF expects, made with
    Flask-WTF's own generate_csrf() for this client's session. Set
    ``auto_csrf = False`` (see the raw_client fixture) to send requests with
    no token, as a cross-site attacker would.
    """

    auto_csrf = True

    def csrf_token(self):
        """A valid token for this client's session (what the page would embed)."""
        app = self.application
        with self.session_transaction() as sess:
            # A fresh app context: the app fixture keeps one open, and its g
            # would otherwise hand back a token cached for an older session.
            with app.app_context(), app.test_request_context():
                flask.session.update(sess)
                token = generate_csrf()
                sess.update(flask.session)
        return token

    def open(self, *args, **kwargs):
        method = (kwargs.get('method') or 'GET').upper()
        if self.auto_csrf and method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            headers = dict(kwargs.get('headers') or {})
            if 'X-CSRFToken' not in headers:
                headers['X-CSRFToken'] = self.csrf_token()
            kwargs['headers'] = headers
        return super().open(*args, **kwargs)


# Every app built in the suite (including ones tests create themselves) uses it.
flask.Flask.test_client_class = CSRFClient


def _unlink_quietly(path):
    """Remove a file; ignore Windows lock races after engine dispose."""
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def app():
    # Create a temporary database file. Close the fd immediately so SQLite
    # is the only opener; otherwise Windows cannot unlink at teardown.
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    song_dir = tempfile.mkdtemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'SONG_DATA_DIR': song_dir,
    })

    @app.before_request
    def _fresh_g_per_request():
        # In production each request gets a new app context, so g (where
        # Flask-WTF caches the page's CSRF token) starts empty. This fixture
        # keeps one app context open for the whole test, so clear g by hand.
        for name in list(vars(flask.g)):
            delattr(flask.g, name)

    with app.app_context():
        db.create_all()
        # Seed test song without forcing explicit primary key
        sample_song = Song(
            title="Test Song",
            artist="Test Artist",
            song_key="C major"
        )
        db.session.add(sample_song)
        db.session.commit()
        save_song_content(sample_song.id, "[C]Hello world")
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    _unlink_quietly(db_path)
    shutil.rmtree(song_dir, ignore_errors=True)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth_client(client):
    """Register and log in a default test user; return the client."""
    client.post('/register', data={
        'username': 'tester',
        'password': 'testpass1',
        'confirmation': 'testpass1',
    })
    return client


@pytest.fixture
def raw_client(app):
    """A client that never adds a CSRF token (a forged cross-site request)."""
    client = app.test_client()
    client.auto_csrf = False
    return client


# Every test must really run. A skip (pytest.skip, importorskip, a skipif
# mark, or a missing browser or node) is turned into a failure, so a green
# run always means 0 skipped. Expected failures (xfail) are left alone.
SKIP_IS_FAILURE = (
    'Skipped tests are not allowed in this suite. Install what is missing '
    '(see docs/MAINTAINING.md, "Browser and Node tests (required)") '
    'or remove the skip. Reason: '
)


def _skip_reason(report):
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    return str(longrepr)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.skipped and not hasattr(report, 'wasxfail'):
        report.longrepr = SKIP_IS_FAILURE + _skip_reason(report)
        report.outcome = 'failed'


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    outcome = yield
    report = outcome.get_result()
    if report.skipped:
        report.longrepr = SKIP_IS_FAILURE + _skip_reason(report)
        report.outcome = 'failed'
