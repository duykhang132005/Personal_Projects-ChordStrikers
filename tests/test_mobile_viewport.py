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


_PW = {}


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
    _PW['playwright'] = playwright
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


def test_perform_starts_autoscroll_and_exit_restores(browser, live_server, admin_state):
    context, page = _open_sheet(browser, live_server, admin_state, 390, 844)
    try:
        state = "[csScroll.getSpeed(), csScroll.isRunning()]"
        assert page.evaluate(state) == [0, False]
        page.click('#btn-perform')
        assert page.evaluate(state) == [1, True]
        page.click('#perform-pause')
        assert page.evaluate(state) == [1, False]
        page.click('#perform-pause')
        assert page.evaluate(state) == [1, True]
        page.click('#perform-exit')
        assert page.evaluate(state) == [0, False]

        page.evaluate("csScroll.setSpeed(3); csScroll.pause()")
        page.click('#btn-perform')
        assert page.evaluate(state) == [3, True]
        page.click('#perform-exit')
        assert page.evaluate(state) == [3, False]
    finally:
        context.close()


@pytest.mark.parametrize('width,height', [(390, 844), (1366, 900)])
def test_perform_speed_controls(browser, live_server, admin_state, width, height):
    context, page = _open_sheet(browser, live_server, admin_state, width, height)
    try:
        page.click('#btn-perform')
        assert page.locator('#perform-speed').inner_text() == '1x'
        page.click('#perform-faster')
        page.click('#perform-faster')
        assert page.locator('#perform-speed').inner_text() == '3x'
        assert page.evaluate("[csScroll.getSpeed(), csScroll.isRunning()]") == [3, True]
        page.click('#perform-slower')
        assert page.evaluate("csScroll.getSpeed()") == 2
        for _ in range(5):
            page.click('#perform-slower')
        assert page.evaluate("csScroll.getSpeed()") == 1
        page.focus('#perform-faster')
        page.keyboard.press('Enter')
        assert page.evaluate("csScroll.getSpeed()") == 2
        size = page.evaluate(OVERFLOW_JS)
        assert size['sw'] <= size['iw']
        for sel in ('#perform-slower', '#perform-faster', '#perform-pause', '#perform-exit'):
            box = page.locator(sel).bounding_box()
            assert box['height'] >= 40 and box['width'] >= 40
            assert box['x'] >= 0 and box['x'] + box['width'] <= width + 1
        page.click('#perform-exit')
        assert page.evaluate("csScroll.getSpeed()") == 2
        saved = page.evaluate("JSON.parse(localStorage.getItem('cs-song-' + document.getElementById('sheet-root').dataset.songId))")
        assert saved['scrollSpeed'] == 2
    finally:
        context.close()


def test_reset_restores_text_size(browser, live_server, admin_state):
    context, page = _open_sheet(browser, live_server, admin_state, 1366, 900)
    try:
        font = "parseFloat(getComputedStyle(document.querySelector('.song-content')).fontSize)"
        page.wait_for_function("document.fonts.status === 'loaded'")
        page.wait_for_timeout(200)
        start = page.evaluate(font)
        page.click('#btn-font-up')
        page.click('#btn-font-up')
        page.click('.transpose-btn[data-step="1"]')
        assert page.evaluate(font) > start
        page.click('.transpose-reset')
        page.wait_for_timeout(150)
        assert abs(page.evaluate(font) - start) < 0.2
        assert page.input_value('#steps') == '0'
        saved = page.evaluate("JSON.parse(localStorage.getItem('cs-song-' + document.getElementById('sheet-root').dataset.songId))")
        assert saved['fontScale'] == 1 and saved['steps'] == 0
    finally:
        context.close()


@pytest.mark.parametrize('width,height', PORTRAIT + LANDSCAPE + [(768, 1024), (1366, 900)])
def test_site_nav_fits_and_hides_in_perform(browser, live_server, admin_state, width, height):
    context, page = _open_sheet(browser, live_server, admin_state, width, height)
    try:
        toggle = page.locator('.site-nav-toggle')
        if toggle.is_visible():
            toggle.click()
            assert toggle.get_attribute('aria-expanded') == 'true'
        links = page.locator('.site-nav-list a')
        assert links.count() == 3
        assert links.nth(2).is_visible()
        size = page.evaluate(OVERFLOW_JS)
        assert size['sw'] <= size['iw']
        nav = page.locator('.site-nav-toggle' if toggle.is_visible() else '.site-nav-list').bounding_box()
        title = page.locator('h1 .highlight').bounding_box()
        overlap = not (nav['x'] >= title['x'] + title['width'] or nav['x'] + nav['width'] <= title['x']
                       or nav['y'] >= title['y'] + title['height'] or nav['y'] + nav['height'] <= title['y'])
        assert not overlap
        if toggle.is_visible():
            page.keyboard.press('Escape')
        page.click('#btn-perform')
        assert not page.locator('.site-nav').is_visible()
        page.click('#perform-exit')
    finally:
        context.close()


_SEARCH_SHAPE = """() => {
    const group = document.querySelector('.input-group');
    const g = getComputedStyle(group);
    const kids = [...group.children].map((el) => {
        const s = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return {radius: [s.borderTopLeftRadius, s.borderTopRightRadius,
                         s.borderBottomLeftRadius, s.borderBottomRightRadius],
                left: r.left, width: r.width, top: r.top};
    });
    return {groupRadius: parseFloat(g.borderTopLeftRadius), overflow: g.overflow,
            groupWidth: group.getBoundingClientRect().width, kids};
}"""


@pytest.mark.parametrize('theme', ['', 'wooden', 'limelight'])
@pytest.mark.parametrize('width', [360, 390])
def test_explore_search_is_one_rounded_card_on_phones(browser, live_server, theme, width):
    context = browser.new_context(viewport={'width': width, 'height': 780}, is_mobile=True)
    page = context.new_page()
    page.goto(live_server['base'] + '/explore')
    page.evaluate("(t) => localStorage.setItem('cs-theme-v2', t)", theme)
    page.goto(live_server['base'] + '/explore', wait_until='load')
    shape = page.evaluate(_SEARCH_SHAPE)
    context.close()
    assert shape['groupRadius'] >= 8 and shape['overflow'] == 'hidden'
    tops = [k['top'] for k in shape['kids']]
    assert tops == sorted(tops) and len(set(tops)) == len(tops)  # stacked
    for kid in shape['kids']:
        assert kid['radius'] == ['0px'] * 4  # uniform; the card clips the corners
        assert abs(kid['width'] - (shape['groupWidth'] - 2)) < 2


def test_explore_search_desktop_is_unchanged(browser, live_server):
    context = browser.new_context(viewport={'width': 1366, 'height': 900})
    page = context.new_page()
    page.goto(live_server['base'] + '/explore', wait_until='load')
    shape = page.evaluate(_SEARCH_SHAPE)
    context.close()
    assert shape['groupRadius'] == 0 and shape['overflow'] != 'hidden'
    assert len({round(k['top']) for k in shape['kids']}) == 1  # one row
    assert shape['kids'][0]['radius'][0] != '0px'  # Bootstrap rounded ends


@pytest.fixture(scope='module')
def ipad_webkit(browser):
    """WebKit (Safari engine) with iPad landscape descriptors, if installed."""
    playwright = _PW['playwright']
    try:
        webkit = playwright.webkit.launch()
    except Exception as exc:  # pragma: no cover - WebKit not installed
        pytest.skip(f'WebKit is not installed for Playwright: {exc}')
    yield webkit, playwright.devices
    webkit.close()


IPADS = ['iPad (gen 7) landscape', 'iPad Pro 11 landscape', 'iPad Mini landscape']


@pytest.mark.parametrize('device', IPADS)
def test_ipad_landscape_perform_scrolls_and_bar_fits(ipad_webkit, live_server, admin_state, device):
    webkit, devices = ipad_webkit
    context = webkit.new_context(**devices[device], storage_state=admin_state)
    page = context.new_page()
    page.goto(f"{live_server['base']}/view_sheet/{live_server['song_id']}", wait_until='load')
    assert page.evaluate('document.documentElement.scrollWidth - innerWidth') <= 0
    page.evaluate("document.querySelector('.song-content').style.minHeight = '4000px'")
    page.click('#btn-perform')
    # Speed 1 is a sub-pixel step; Safari ignored it before the fix.
    assert page.inner_text('#perform-speed') == '1x'
    start = page.evaluate('scrollY')
    page.wait_for_timeout(1500)
    assert page.evaluate('scrollY') - start >= 5
    page.click('#perform-faster')  # Back used to cover + in WebKit
    assert page.inner_text('#perform-speed') == '2x'
    page.click('#perform-slower')
    assert page.inner_text('#perform-speed') == '1x'
    page.evaluate("scrollTo({top: document.documentElement.scrollHeight - innerHeight - 40, behavior: 'instant'})")
    page.wait_for_function('innerHeight + scrollY >= document.documentElement.scrollHeight - 2', timeout=15000)
    context.close()


@pytest.mark.parametrize('device', IPADS)
def test_ipad_landscape_nav_does_not_cover_home_title(ipad_webkit, live_server, device):
    webkit, devices = ipad_webkit
    context = webkit.new_context(**devices[device])
    page = context.new_page()
    page.goto(live_server['base'] + '/', wait_until='load')
    overlap = page.evaluate("""() => {
        const n = document.querySelector('.site-nav').getBoundingClientRect();
        const h = document.querySelector('h1');
        const r = document.createRange(); r.selectNodeContents(h);
        const t = r.getBoundingClientRect();
        return t.right > n.left && t.left < n.right && t.bottom > n.top && t.top < n.bottom;
    }""")
    context.close()
    assert not overlap


@pytest.mark.parametrize('engine', ['chromium', 'webkit'])
def test_menu_create_then_submit_saves_song(browser, live_server, admin_state, engine):
    """Regression: menu Create -> submit returned 405 (form posted to /creator)."""
    if engine == 'webkit':
        try:
            launched = _PW['playwright'].webkit.launch()
        except Exception as exc:  # pragma: no cover - WebKit not installed
            pytest.skip(f'WebKit is not installed for Playwright: {exc}')
    else:
        launched = browser
    context = launched.new_context(viewport={'width': 1366, 'height': 900}, storage_state=admin_state)
    page = context.new_page()
    page.goto(live_server['base'] + '/explore', wait_until='load')
    page.click('.site-nav-list a:has-text("Create")')
    page.fill('[name=title]', 'Menu create ' + engine)
    with page.expect_navigation() as nav:
        page.evaluate("document.querySelector('form[method=POST]').requestSubmit()")
    status = nav.value.status if nav.value else None
    url = page.url
    context.close()
    if engine == 'webkit':
        launched.close()
    assert status == 200 and '/creator' not in url and '/create' not in url


def test_chromium_nav_with_view_transitions(browser, live_server, admin_state):
    """Cross-document View Transitions must not break Chromium navigations."""
    context = browser.new_context(viewport={'width': 390, 'height': 780}, storage_state=admin_state)
    page = context.new_page()
    page.goto(live_server['base'] + '/', wait_until='load')
    page.click('.site-nav-toggle')
    page.click('.site-nav-list a:has-text("Explore")')
    page.wait_for_url('**/explore**')
    page.click('.site-nav-toggle')
    page.click('.site-nav-list a:has-text("Create")')
    page.wait_for_url('**/create**')
    page.goto(f"{live_server['base']}/view_sheet/{live_server['song_id']}", wait_until='load')
    page.click('#btn-perform')
    start = page.evaluate('scrollY')
    page.wait_for_timeout(1500)
    assert page.evaluate('scrollY') - start >= 5
    page.click('#perform-exit')
    context.close()


@pytest.mark.parametrize('engine', ['chromium', 'webkit'])
@pytest.mark.parametrize('theme,expected', [('', 'rgb(58, 47, 99)'), ('wooden', 'rgb(58, 36, 18)'), ('limelight', 'rgb(14, 36, 24)')])
def test_page_canvas_is_never_white(browser, live_server, engine, theme, expected):
    """Before styles.css and the background image load, html is already dark."""
    if engine == 'webkit':
        try:
            launched = _PW['playwright'].webkit.launch()
        except Exception as exc:  # pragma: no cover - WebKit not installed
            pytest.skip(f'WebKit is not installed for Playwright: {exc}')
    else:
        launched = browser
    context = launched.new_context(viewport={'width': 390, 'height': 780})
    page = context.new_page()
    page.goto(live_server['base'] + '/explore')
    page.evaluate("(t) => localStorage.setItem('cs-theme-v2', t)", theme)
    page.route('**/*.css*', lambda route: route.abort())  # worst case: no stylesheet at all
    page.route('**/*.webp*', lambda route: route.abort())
    page.goto(live_server['base'] + '/explore', wait_until='domcontentloaded')
    canvas = page.evaluate('getComputedStyle(document.documentElement).backgroundColor')
    context.close()
    if engine == 'webkit':
        launched.close()
    assert canvas == expected
