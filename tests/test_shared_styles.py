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
