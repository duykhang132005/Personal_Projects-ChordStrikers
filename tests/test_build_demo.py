from scripts.build_demo import build_demo, normalize_base_path


def test_normalize_base_path():
    assert normalize_base_path("Personal_Projects-ChordStrikers") == "/Personal_Projects-ChordStrikers/"
    assert normalize_base_path("/Personal_Projects-ChordStrikers/") == "/Personal_Projects-ChordStrikers/"
    assert normalize_base_path("") == "/"


def test_build_demo_writes_spa_shell(tmp_path):
    out = tmp_path / "site"
    build_demo(base_path="/Personal_Projects-ChordStrikers/", out_dir=out)

    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="/Personal_Projects-ChordStrikers/"' in index
    assert 'window.DEMO_BASE_PATH = "/Personal_Projects-ChordStrikers/"' in index
    assert (out / "404.html").read_text(encoding="utf-8") == index
    assert (out / ".nojekyll").is_file()
    assert (out / "static" / "styles.css").is_file()
    assert (out / "data" / "index.json").is_file()
    assert (out / "js" / "view_sheet.js").is_file()
