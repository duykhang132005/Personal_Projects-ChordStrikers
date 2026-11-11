"""Real-browser fixtures shared by the Playwright test modules.

Import the fixtures into a test module (see test_mobile_viewport.py). Each
module gets its own live server, so tests stay independent. These tests are
required: without Playwright, Chromium or WebKit the suite fails with a
message saying what to install. It never skips them.
"""
import os
import re
import shutil
import tempfile
import threading

import pytest

INSTALL_HELP = (
    'Browser tests are required and are never skipped. Install them with:\n'
    '  python -m pip install -r requirements-browser.txt\n'
    '  python -m playwright install chromium webkit\n'
    '(on Linux use: python -m playwright install --with-deps chromium webkit).\n'
    'See docs/MAINTAINING.md, "Browser and Node tests (required)".'
)

try:
    from playwright import sync_api
except ImportError as exc:  # pragma: no cover - depends on the machine
    raise ImportError(f'Playwright is not installed. {INSTALL_HELP}') from exc

from werkzeug.serving import make_server  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import Song, User  # noqa: E402
from app.storage import save_song_content  # noqa: E402


def register_in_browser(context, base, username, password, **kwargs):
    """Register through the real sign-in form fields, CSRF token included.

    Reads the token from the page's <meta name="csrf-token"> with the same
    cookies the browser context will use, as the page itself would.
    """
    html = context.request.get(base + '/?signin=1').text()
    token = re.search(r'<meta name="csrf-token" content="([^"]+)">', html).group(1)
    response = context.request.post(base + '/register', form={
        'username': username, 'password': password, 'confirmation': password,
        'csrf_token': token,
    }, **kwargs)
    assert response.status in (200, 302), response.status
    return response


LONG_SHEET = '\n'.join(
    ['[Verse 1]']
    + [
        '[C]Một dòng rất dài để thử màn hình [G]điện thoại hẹp khi xoay '
        'ngang hoặc dọc, [Am]không được tràn sang [F]bên phải nhé'
    ] * 12
    + ['[Chorus]', '[F]Short [G]line [C]here'] * 6
)


@pytest.fixture(scope='module')
def live_server():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    song_dir = tempfile.mkdtemp()
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + db_path.replace('\\', '/'),
        'SECRET_KEY': 'test-secret-key',
        'SONG_DATA_DIR': song_dir,
    })
    with app.app_context():
        db.create_all()
        song = Song(title='Bài hát rất dài', artist='Test Artist', song_key='C')
        db.session.add(song)
        db.session.commit()
        save_song_content(song.id, LONG_SHEET)
        song_id = song.id

    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        yield {'app': app, 'base': base, 'song_id': song_id}
    finally:
        server.shutdown()
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        try:
            os.unlink(db_path)
        except OSError:
            pass
        shutil.rmtree(song_dir, ignore_errors=True)


_PW = {}


@pytest.fixture(scope='module')
def browser():
    try:
        playwright = sync_api.sync_playwright().start()
    except Exception as exc:  # pragma: no cover - depends on the machine
        pytest.fail(f'Playwright could not start: {exc}\n{INSTALL_HELP}', pytrace=False)
    try:
        chromium = playwright.chromium.launch()
    except Exception as exc:  # pragma: no cover - browsers not installed
        playwright.stop()
        pytest.fail(f'Chromium is not installed for Playwright: {exc}\n{INSTALL_HELP}', pytrace=False)
    _PW['playwright'] = playwright
    yield chromium
    chromium.close()
    playwright.stop()


def launch_webkit():
    """Start WebKit (the Safari engine), or fail with install steps."""
    try:
        return _PW['playwright'].webkit.launch()
    except Exception as exc:  # pragma: no cover - WebKit not installed
        pytest.fail(f'WebKit is not installed for Playwright: {exc}\n{INSTALL_HELP}', pytrace=False)


@pytest.fixture(scope='module')
def admin_state(live_server, browser, tmp_path_factory):
    """Sign in once as an admin so the toolbar shows Edit and Return."""
    context = browser.new_context()
    register_in_browser(context, live_server['base'], 'mobileadmin', 'testpass1')
    with live_server['app'].app_context():
        user = User.query.filter_by(username='mobileadmin').first()
        user.is_admin = True
        db.session.commit()
    path = str(tmp_path_factory.mktemp('state') / 'state.json')
    context.storage_state(path=path)
    context.close()
    return path
