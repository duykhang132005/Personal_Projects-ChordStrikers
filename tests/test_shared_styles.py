"""Real-browser checks for keyboard use, focus rings, motion and tap sizes.

These replace older checks that only searched the CSS, HTML and JS source
for strings. Each test drives the real pages in Chromium and reads what the
browser actually does: where focus goes, what is shown, computed styles.
Needs Playwright (see requirements-browser.txt). Required: the suite fails
without it, it never skips.
"""
import re

import pytest

from app import db  # noqa: E402
from app.models import Favorite, Song, User  # noqa: E402
from app.storage import save_song_content  # noqa: E402
# Shared real-browser fixtures (a live server, Chromium, an admin login).
from browser_fixtures import _PW, admin_state, browser, live_server  # noqa: E402,F401

pytestmark = pytest.mark.browser

DESKTOP = {'width': 1366, 'height': 900}
PHONE = {'width': 390, 'height': 844}

ACTIVE = '() => document.activeElement'
FOCUS_INFO = """() => {
    const el = document.activeElement;
    const s = getComputedStyle(el);
    return {cls: el.className, label: el.getAttribute('aria-label'), text: el.textContent.trim(),
            style: s.outlineStyle, width: parseFloat(s.outlineWidth), color: s.outlineColor};
}"""


def _page(browser, live_server, path, state=None, **context_args):
    context = browser.new_context(viewport=context_args.pop('viewport', DESKTOP),
                                  storage_state=state, service_workers='block', **context_args)
    page = context.new_page()
    page.goto(live_server['base'] + path, wait_until='load')
    return context, page


def _tab_until(page, js_test, limit=80):
    """Press Tab until js_test(document.activeElement) is true."""
    for _ in range(limit):
        page.keyboard.press('Tab')
        if page.evaluate(f'() => {{ const el = document.activeElement; return !!({js_test}); }}'):
            return
    raise AssertionError(f'Tab never reached an element matching {js_test}')


def _ring_is_visible(info):
    return (info['style'] not in ('none', 'hidden') and info['width'] >= 2
            and info['color'] not in ('transparent', 'rgba(0, 0, 0, 0)'))


def _add_song(live_server, title, content='[C]Hello [G]world'):
    app = live_server['app']
    with app.app_context():
        admin = User.query.filter_by(username='mobileadmin').first()
        song = Song(title=title, artist='Test', song_key='C', user_id=admin.id if admin else None)
        db.session.add(song)
        db.session.commit()
        save_song_content(song.id, content)
        return song.id


# ---- Home circle menu --------------------------------------------------

def test_circle_menu_is_keyboard_operable(browser, live_server):
    context, page = _page(browser, live_server, '/')
    try:
        _tab_until(page, "el.classList.contains('circle-menu-item')")
        about = page.locator('.circle-menu-item[aria-label="About"]')
        assert page.evaluate("() => document.activeElement.getAttribute('aria-label')") == 'About'
        assert about.get_attribute('aria-expanded') == 'false'
        assert page.locator('#about-card').is_hidden()

        page.keyboard.press('Enter')
        assert about.get_attribute('aria-expanded') == 'true'
        assert page.locator('#about-card').is_visible()

        page.keyboard.press('Enter')
        assert about.get_attribute('aria-expanded') == 'false'
        assert page.locator('#about-card').is_hidden()

        # Space works too, and opening one item closes the others.
        page.keyboard.press('Enter')
        page.keyboard.press('Tab')
        contact = page.locator('.circle-menu-item[aria-label="Contact"]')
        assert page.evaluate("() => document.activeElement.getAttribute('aria-label')") == 'Contact'
        scroll_before = page.evaluate('scrollY')
        page.keyboard.press(' ')
        assert contact.get_attribute('aria-expanded') == 'true'
        assert about.get_attribute('aria-expanded') == 'false'
        assert page.locator('#contact-card').is_visible() and page.locator('#about-card').is_hidden()
        assert page.evaluate('scrollY') == scroll_before  # Space did not scroll the page
    finally:
        context.close()


def test_circle_menu_focus_ring_is_visible(browser, live_server):
    context, page = _page(browser, live_server, '/')
    try:
        _tab_until(page, "el.classList.contains('circle-menu-item')")
        info = page.evaluate(FOCUS_INFO)
        assert _ring_is_visible(info), info
    finally:
        context.close()


def test_circle_menu_grows_with_transform_not_size(browser, live_server):
    context, page = _page(browser, live_server, '/')
    try:
        item = page.locator('.circle-menu-item[aria-label="Project"]')
        before = item.evaluate('el => [el.offsetWidth, el.getBoundingClientRect().width]')
        item.hover()
        page.wait_for_timeout(450)  # the 0.35s transition
        after = item.evaluate('el => [el.offsetWidth, el.getBoundingClientRect().width, getComputedStyle(el).transform]')
        assert after[0] == before[0]  # layout size unchanged, so nothing reflows
        assert after[1] > before[1] * 1.2  # but it looks bigger (scaled)
        assert after[2] != 'none'
    finally:
        context.close()


# ---- Focus rings on forms and the sheet toolbar -------------------------

def test_create_form_fields_show_a_focus_ring(browser, live_server, admin_state):
    context, page = _page(browser, live_server, '/create', state=admin_state)
    try:
        _tab_until(page, "el.id === 'title'")
        info = page.evaluate(FOCUS_INFO)
        assert _ring_is_visible(info), info
        page.keyboard.press('Tab')
        assert page.evaluate('() => document.activeElement.id') == 'artist'
        assert _ring_is_visible(page.evaluate(FOCUS_INFO))
    finally:
        context.close()


def test_sheet_toolbar_and_accidental_toggle_show_focus_rings(browser, live_server, admin_state):
    context, page = _page(browser, live_server, f"/view_sheet/{live_server['song_id']}", state=admin_state)
    try:
        _tab_until(page, "el.classList.contains('control-btn')")
        info = page.evaluate(FOCUS_INFO)
        assert _ring_is_visible(info), info
        # The sharp/flat radios are visually hidden but still reachable; the
        # ring is drawn on the label next to the focused radio.
        _tab_until(page, "el.name === 'prefer'")
        label = page.evaluate("""() => {
            const s = getComputedStyle(document.activeElement.nextElementSibling);
            return {style: s.outlineStyle, width: parseFloat(s.outlineWidth), color: s.outlineColor};
        }""")
        assert _ring_is_visible(label), label
    finally:
        context.close()


# ---- Chord picker dialog --------------------------------------------------

def _open_touch_editor(page):
    page.fill('#sheet_content', '[C]Hello world')
    if page.get_attribute('#toggle-touch-editor', 'aria-pressed') != 'true':
        page.click('#toggle-touch-editor')
    page.wait_for_selector('#touch-editor .touch-word')


def test_chord_picker_traps_focus_and_escape_returns_it(browser, live_server, admin_state):
    context, page = _page(browser, live_server, '/create', state=admin_state)
    try:
        _open_touch_editor(page)
        opener = page.locator('#touch-editor .touch-word', has_text='world')
        opener.focus()
        page.keyboard.press('Enter')
        dialog = page.locator('.chord-picker[role="dialog"]')
        assert dialog.count() == 1
        assert dialog.get_attribute('aria-modal') == 'true'
        assert dialog.get_attribute('aria-label') == 'Choose a chord'
        inside = "() => !!document.activeElement.closest('.chord-picker')"
        assert page.evaluate(inside)
        assert page.evaluate("() => document.activeElement.getAttribute('aria-label')") == 'Chord name'

        # Shift+Tab from the first control wraps to the last, Tab wraps back.
        page.keyboard.press('Shift+Tab')
        assert page.evaluate(inside)
        assert page.evaluate("() => document.activeElement.textContent") == 'Cancel'
        page.keyboard.press('Tab')
        assert page.evaluate("() => document.activeElement.getAttribute('aria-label')") == 'Chord name'
        for _ in range(5):
            page.keyboard.press('Tab')
            assert page.evaluate(inside)

        page.keyboard.press('Escape')
        assert dialog.count() == 0
        assert page.evaluate("() => document.activeElement.className") == 'touch-word'
        assert page.evaluate("() => document.activeElement.textContent") == 'world'
        assert page.input_value('#sheet_content') == '[C]Hello world'  # Escape changed nothing
    finally:
        context.close()


def test_chord_picker_places_a_chord_and_keeps_focus_in_the_editor(browser, live_server, admin_state):
    context, page = _page(browser, live_server, '/create', state=admin_state)
    try:
        _open_touch_editor(page)
        page.locator('#touch-editor .touch-word', has_text='world').click()
        page.locator('.chord-picker-grid button', has_text=re.compile('^G$')).click()
        page.locator('.chord-picker-actions button', has_text='Place chord').click()
        assert page.locator('.chord-picker').count() == 0
        assert page.input_value('#sheet_content') == '[C]Hello [G]world'
        assert page.evaluate("() => !!document.activeElement.closest('#touch-editor')")
    finally:
        context.close()


# ---- Motion ---------------------------------------------------------------

MOVING = """() => {
    const bad = [];
    for (const el of document.querySelectorAll('*')) {
        const s = getComputedStyle(el);
        const props = s.transitionProperty.split(',').map((p) => p.trim());
        const times = s.transitionDuration.split(',').map((t) => parseFloat(t));
        props.forEach((p, i) => {
            const t = times[i % times.length];
            if (t > 0 && ['all', 'width', 'height', 'font-size'].includes(p)) {
                bad.push(`${el.tagName.toLowerCase()}.${el.className}: ${p} ${t}s`);
            }
        });
    }
    return bad;
}"""

LONGEST = """() => {
    let most = 0;
    for (const el of document.querySelectorAll('*')) {
        const s = getComputedStyle(el);
        for (const v of (s.transitionDuration + ',' + s.animationDuration).split(',')) {
            most = Math.max(most, parseFloat(v) || 0);
        }
    }
    return most;
}"""

VIEW_TRANSITION = """() => {
    let nav = null;
    const walk = (rules, on) => {
        for (const r of rules) {
            if (r.constructor.name === 'CSSViewTransitionRule') { if (on) nav = r.navigation; }
            else if (r.cssRules && r.media) walk(r.cssRules, on && matchMedia(r.media.mediaText).matches);
        }
    };
    for (const sheet of document.styleSheets) {
        try { walk(sheet.cssRules, true); } catch (e) { /* cross-origin sheet */ }
    }
    return nav;
}"""


@pytest.mark.parametrize('path', ['/', '/explore', '/create', 'sheet'])
def test_nothing_animates_layout_or_uses_transition_all(browser, live_server, admin_state, path):
    if path == 'sheet':
        path = f"/view_sheet/{live_server['song_id']}"
    context, page = _page(browser, live_server, path, state=admin_state)
    try:
        assert page.evaluate(MOVING) == []
    finally:
        context.close()


def test_motion_runs_normally_without_reduced_motion(browser, live_server):
    context, page = _page(browser, live_server, '/', reduced_motion='no-preference')
    try:
        assert page.evaluate(LONGEST) >= 0.3  # e.g. the 0.35s circle menu
        assert page.evaluate(VIEW_TRANSITION) == 'auto'
    finally:
        context.close()


@pytest.mark.parametrize('path', ['/', '/explore', 'sheet'])
def test_reduced_motion_turns_off_all_motion(browser, live_server, path):
    if path == 'sheet':
        path = f"/view_sheet/{live_server['song_id']}"
    context, page = _page(browser, live_server, path, reduced_motion='reduce')
    try:
        assert page.evaluate(LONGEST) <= 0.001
        assert page.evaluate(VIEW_TRANSITION) == 'none'  # no cross-page fades either
    finally:
        context.close()


# ---- Phones ---------------------------------------------------------------

def test_phone_toolbar_controls_are_at_least_44px(browser, live_server, admin_state):
    context, page = _page(browser, live_server, f"/view_sheet/{live_server['song_id']}", state=admin_state,
                          viewport=PHONE, is_mobile=True, has_touch=True)
    try:
        boxes = page.evaluate("""() => [...document.querySelectorAll('.control-btn, .prefer-toggle label')]
            .filter((el) => el.offsetParent !== null)
            .map((el) => { const r = el.getBoundingClientRect();
                           return [el.textContent.trim() || el.getAttribute('aria-label'), r.width, r.height]; })""")
        assert len(boxes) >= 8
        small = [b for b in boxes if b[1] < 43.5 or b[2] < 43.5]
        assert small == []
    finally:
        context.close()


# ---- Names, shared classes, transposing on the page -----------------------

def test_backing_track_link_says_it_opens_a_new_tab(browser, live_server):
    context, page = _page(browser, live_server, f"/view_sheet/{live_server['song_id']}")
    try:
        link = page.get_by_role('link', name=re.compile(r'Backing Track \(opens in a new tab\)'))
        assert link.count() == 1
        assert link.get_attribute('target') == '_blank'
    finally:
        context.close()


def test_shared_classes_render_the_same_look(browser, live_server, admin_state):
    """Info boxes, hero text and checkbox rows come from shared classes."""
    context, page = _page(browser, live_server, '/')
    try:
        page.click('.circle-menu-item[aria-label="About"]')
        boxes = page.evaluate("""() => [...document.querySelectorAll('#about-card .info-box')]
            .map((el) => [getComputedStyle(el).backgroundColor, el.getAttribute('style')])""")
        assert boxes and all(b == ['rgb(233, 236, 239)', None] for b in boxes)
        hero = page.evaluate("""() => [...document.querySelectorAll('.hero-text')]
            .map((el) => [getComputedStyle(el).color, el.getAttribute('style')])""")
        assert len(hero) == 2 and all(h == ['rgb(255, 255, 255)', None] for h in hero)
    finally:
        context.close()
    context, page = _page(browser, live_server, '/create', state=admin_state)
    try:
        rows = page.evaluate("""() => [...document.querySelectorAll('label.check-row')].map((el) => {
            const box = el.querySelector('input[type=checkbox]');
            return [getComputedStyle(el).display, getComputedStyle(box).marginRight, el.getAttribute('style')];
        })""")
        assert rows == [['inline-flex', '8px', None]] * 2
    finally:
        context.close()


@pytest.mark.parametrize('prefer,expected', [('prefFlat', ['[Db]', '[Ab]']), ('prefSharp', ['[C#]', '[G#]'])])
def test_view_sheet_transpose_follows_sharp_or_flat_choice(browser, live_server, prefer, expected):
    song_id = _add_song(live_server, 'Transpose me ' + prefer, '[C]Hello [G]world')
    context, page = _page(browser, live_server, f'/view_sheet/{song_id}')
    try:
        page.click(f'label[for="{prefer}"]')  # the radios are visually hidden; users tap the label
        assert page.is_checked(f'#{prefer}')
        page.click('.transpose-btn[data-step="1"]')
        assert page.locator('.chord').all_inner_texts()[:2] == expected
        page.click('.transpose-btn[data-step="-1"]')
        assert page.locator('.chord').all_inner_texts()[:2] == ['[C]', '[G]']
    finally:
        context.close()


# ---- Delete asks first -----------------------------------------------------

@pytest.mark.parametrize('accept', [False, True])
def test_delete_song_asks_before_deleting(browser, live_server, admin_state, accept):
    song_id = _add_song(live_server, f'Delete me {accept}')
    context, page = _page(browser, live_server, f'/edit_song/{song_id}', state=admin_state)
    seen = []

    def on_dialog(dialog):
        seen.append(dialog.message)
        dialog.accept() if accept else dialog.dismiss()

    page.on('dialog', on_dialog)
    try:
        button = page.get_by_role('button', name='Delete Song')
        assert 'btn-danger' in button.get_attribute('class')
        if accept:
            with page.expect_navigation():
                button.click()
            assert page.url.endswith('/explore')
        else:
            button.click()
            page.wait_for_timeout(300)
            assert f'/edit_song/{song_id}' in page.url
        assert seen == ['Are you sure you want to delete this song? This action cannot be undone.']
        with live_server['app'].app_context():
            assert (db.session.get(Song, song_id) is None) is accept
    finally:
        context.close()


# ---- Favorite button (fetch with the page's CSRF token) -------------------

def test_favorite_button_saves_and_unsaves(browser, live_server, admin_state):
    song_id = _add_song(live_server, 'Star me')
    app = live_server['app']

    def stars():
        with app.app_context():
            admin = User.query.filter_by(username='mobileadmin').one()
            return Favorite.query.filter_by(user_id=admin.id, song_id=song_id).count()

    context, page = _page(browser, live_server, f'/view_sheet/{song_id}', state=admin_state)
    try:
        button = page.locator('#btn-favorite')
        assert button.get_attribute('aria-pressed') == 'false'
        with page.expect_response(f'**/api/favorites/{song_id}') as saved:
            button.click()
        assert saved.value.status == 200
        page.wait_for_function("() => !document.getElementById('btn-favorite').disabled")
        assert button.get_attribute('aria-pressed') == 'true'
        assert 'Added to favorites' in page.inner_text('#favorite-status')
        assert stars() == 1
        with page.expect_response(f'**/api/favorites/{song_id}') as removed:
            button.click()
        assert removed.value.status == 200
        page.wait_for_function("() => !document.getElementById('btn-favorite').disabled")
        assert button.get_attribute('aria-pressed') == 'false'
        assert stars() == 0
    finally:
        context.close()
