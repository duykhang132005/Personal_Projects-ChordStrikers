"""Real-browser smoke test: View Sheet on phone-sized screens.

Checks that the page never scrolls sideways (portrait and landscape) and
that the toolbar buttons stay centered on portrait phones.

Needs Playwright plus a Chromium build:
    pip install -r requirements-browser.txt
    python -m playwright install chromium
Without them these tests are skipped, so the normal suite stays green.
"""
import os
import shutil
import tempfile
import threading

import pytest

sync_api = pytest.importorskip('playwright.sync_api')

from werkzeug.serving import make_server  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import Song, User  # noqa: E402
from app.storage import save_song_content  # noqa: E402

pytestmark = pytest.mark.browser

PORTRAIT = [(360, 780), (390, 844), (430, 932)]
LANDSCAPE = [(844, 390), (740, 360)]

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


@pytest.fixture(scope='module')
def browser():
    try:
        playwright = sync_api.sync_playwright().start()
    except Exception as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f'Playwright could not start: {exc}')
    try:
        chromium = playwright.chromium.launch()
    except Exception as exc:  # pragma: no cover - browsers not installed
        playwright.stop()
        pytest.skip(f'Chromium is not installed for Playwright: {exc}')
    yield chromium
    chromium.close()
    playwright.stop()


@pytest.fixture(scope='module')
def admin_state(live_server, browser, tmp_path_factory):
    """Sign in once as an admin so the toolbar shows Edit and Return."""
    context = browser.new_context()
    context.request.post(live_server['base'] + '/register', form={
        'username': 'mobileadmin', 'password': 'testpass1', 'confirmation': 'testpass1',
    })
    with live_server['app'].app_context():
        user = User.query.filter_by(username='mobileadmin').first()
        user.is_admin = True
        db.session.commit()
    path = str(tmp_path_factory.mktemp('state') / 'state.json')
    context.storage_state(path=path)
    context.close()
    return path


def _open_sheet(browser, live_server, admin_state, width, height):
    context = browser.new_context(
        viewport={'width': width, 'height': height},
        is_mobile=True,
        has_touch=True,
        storage_state=admin_state,
        service_workers='block',
    )
    page = context.new_page()
    page.goto(f"{live_server['base']}/view_sheet/{live_server['song_id']}", wait_until='load')
    page.wait_for_timeout(300)  # let the font-fit pass run after load
    return context, page


OVERFLOW_JS = '() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth})'


@pytest.mark.parametrize('width,height', PORTRAIT + LANDSCAPE)
def test_view_sheet_has_no_horizontal_overflow(browser, live_server, admin_state, width, height):
    context, page = _open_sheet(browser, live_server, admin_state, width, height)
    try:
        assert page.locator('#btn-favorite').count() == 1
        sizes = page.evaluate(OVERFLOW_JS)
        assert sizes['sw'] <= sizes['iw'] + 1, f'{width}x{height}: page is {sizes["sw"]}px wide'
    finally:
        context.close()


@pytest.mark.parametrize('width,height', PORTRAIT)
def test_view_sheet_toolbar_centered_in_portrait(browser, live_server, admin_state, width, height):
    context, page = _open_sheet(browser, live_server, admin_state, width, height)
    try:
        result = page.evaluate("""() => {
            const mid = document.documentElement.clientWidth / 2;
            const center = (els) => {
                const boxes = els.map(e => e.getBoundingClientRect()).filter(b => b.width > 0);
                const left = Math.min(...boxes.map(b => b.left));
                const right = Math.max(...boxes.map(b => b.right));
                return (left + right) / 2;
            };
            // Group visible controls into visual lines (vertical centers
            // within 12px of each other) and measure each line.
            const items = [...document.querySelectorAll('.sheet-nav-btn, .sheet-tools-panel .control-box')]
                .map(el => ({el, b: el.getBoundingClientRect()}))
                .filter(item => item.b.width > 0)
                .sort((a, b) => (a.b.top + a.b.bottom) - (b.b.top + b.b.bottom));
            const lines = [];
            let lastY = null;
            items.forEach(item => {
                const y = (item.b.top + item.b.bottom) / 2;
                if (lastY === null || y - lastY > 12) lines.push([]);
                lines[lines.length - 1].push(item.el);
                lastY = y;
            });
            return {mid, centers: lines.map(center)};
        }""")
        assert result['centers'], 'no toolbar controls found'
        for c in result['centers']:
            assert abs(c - result['mid']) <= 2, f'{width}px: a toolbar line is centered at {c:.1f}, page center {result["mid"]}'
    finally:
        context.close()
