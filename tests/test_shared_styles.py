from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_home_info_boxes_use_shared_class():
    html = _read("templates/home.html")
    assert "background: #e9ecef" not in html
    assert "info-box" in html
    assert "div.info-box" in _read("static/styles.css")


def test_creator_checkboxes_use_shared_classes():
    html = _read("templates/creator.html")
    assert "display: inline-flex" not in html
    assert "margin-right: 0.5rem" not in html
    assert 'style="margin-top: 0.5rem;"' not in html
    assert html.count('class="check-row"') == 2
    css = _read("static/styles.css")
    assert "label.check-row" in css
    assert ".check-row-wrap" in css


def test_home_hero_text_uses_shared_class():
    html = _read("templates/home.html")
    assert "color: white" not in html
    assert 'style="color: white;"' not in html
    assert html.count("hero-text") >= 2
    css = _read("static/styles.css")
    assert ".hero-text" in css
    assert "color: white" in css


def _css_block(css, selector):
    start = css.index(selector)
    return css[start:css.index("}", start)]


def test_home_circle_menu_items_are_keyboard_buttons():
    html = _read("templates/home.html")
    assert html.count('class="circle-menu-item') == 6
    assert html.count('role="button" tabindex="0" aria-expanded="false"') == 6
    for label in ("About", "Contact", "Project", "Library", "Account", "Sign In"):
        assert 'aria-label="%s"' % label in html
    index = _read("templates/index.html")
    assert "addEventListener('keydown'" in index
    assert "e.key === 'Enter'" in index and "e.key === ' '" in index
    assert "aria-expanded" in index
    css = _read("static/styles.css")
    assert ".circle-menu-item:focus-visible {" in css


def test_home_circle_menu_renders_buttons(client):
    html = client.get("/").get_data(as_text=True)
    assert html.count('role="button" tabindex="0"') == 5
    assert 'aria-controls="signin-card"' in html


def test_chord_picker_dialog_is_accessible():
    js = _read("static/js/sheet_editor.js")
    assert "setAttribute('aria-modal', 'true')" in js
    assert "setAttribute('aria-label', 'Choose a chord')" in js
    assert "e.key === 'Escape'" in js
    assert "e.key !== 'Tab'" in js
    assert "back.focus()" in js


def test_circle_menu_animates_transform_not_size():
    css = _read("static/styles.css")
    block = _css_block(css, ".circle-menu-item {")
    assert "width 0.35s" not in block and "height 0.35s" not in block
    assert "font-size 0.35s" not in block
    assert "transform 0.35s" in block
    assert "transition: all" not in css


def test_focus_rings_are_visible():
    css = _read("static/styles.css")
    for sel in (".chord-input:focus,", ".form-input:focus,"):
        assert "outline: none" not in _css_block(css, sel)
    assert ".chord-input:focus-visible" in css
    assert ".form-input:focus-visible" in css
    assert '.prefer-toggle input[type="radio"]:focus-visible+label' in css
    assert "display: none" not in _css_block(css, '.prefer-toggle input[type="radio"] {')


def test_phone_controls_are_44px():
    css = _read("static/styles.css")
    start = css.index("@media (max-width: 768px), (pointer: coarse)")
    block = css[start:start + 400]
    assert ".control-btn" in block and ".prefer-toggle label" in block
    assert "min-height: 44px" in block and "min-width: 44px" in block


def test_reduced_motion_covers_all_motion():
    css = _read("static/styles.css")
    start = css.index("@media (prefers-reduced-motion: reduce)")
    block = css[start:start + 1200]
    assert "transition-duration: 0.01ms !important" in block
    assert "animation-duration: 0.01ms !important" in block


def test_backing_track_link_says_new_tab():
    html = _read("templates/view_sheet.html")
    assert "(opens in a new tab)" in html
