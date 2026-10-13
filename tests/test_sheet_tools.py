"""Sort, capo, simplify, and the color theme picker."""
import shutil
import subprocess
from pathlib import Path

import pytest

from app import db
from app.chord_logic import simplify_chord, suggest_capos, transform_text, transpose_chord
from app.models import Song
from app.storage import save_song_content

SIMPLIFY_CASES = [
    ('Cmaj7', 'C'),
    ('Am7', 'Am'),
    ('Dsus4', 'D'),
    ('Cadd9', 'C'),
    ('G/B', 'G/B'),
    ('F#m7/C#', 'F#m/C#'),
    ('C7', 'C'),
    ('Asus2', 'A'),
    ('Bbmaj7', 'Bb'),
    ('C#m7b5', 'C#m'),
    ('Em9', 'Em'),
    ('Cdim7', 'Cdim'),
    ('Caug7', 'Caug'),
    ('Cmin7', 'Cm'),
    ('Am', 'Am'),
    ('C7#9', 'C'),
]

@pytest.mark.parametrize("raw,expected", SIMPLIFY_CASES)
def test_simplify_chord(raw, expected):
    assert simplify_chord(raw) == expected

def test_capo_suggestion_prefers_open_shapes():
    ideas = suggest_capos(["B", "F#", "C#m"])
    assert ideas[0]["fret"] == 4
    assert ideas[0]["chords"] == ["G", "D", "Am"]
    assert ideas[0]["score"] == 0

def test_transform_text_applies_capo_and_simplify():
    shown = transform_text("[B]line [F#m7]here", steps=-4, simplify=True)
    assert shown == "[G]line [Dm]here"

def test_transpose_keeps_slash_bass():
    assert transpose_chord("G/B", 2, "sharp") == "A/C#"

def test_explore_sort_newest(client, app):
    with app.app_context():
        song = Song(title="AAAA First", artist="Z", song_key="C")
        db.session.add(song)
        db.session.commit()
        save_song_content(song.id, "[C]hi")
    newest = client.get("/explore?sort=newest").get_data(as_text=True)
    alpha = client.get("/explore?sort=az").get_data(as_text=True)
    assert newest.find("AAAA First") < newest.find("Test Song")
    assert alpha.find("AAAA First") < alpha.find("Test Song")
    fallback = client.get("/explore?sort=nope").get_data(as_text=True)
    assert "selected" in fallback.split('value="az"')[1][:80]

def test_view_sheet_has_performance_and_capo(client):
    html = client.get("/view_sheet/1").get_data(as_text=True)
    assert 'id="btn-perform"' in html
    assert 'id="capo-fret"' in html
    assert 'id="simplify-chords"' in html
    assert 'id="btn-tuner"' in html
    assert 'id="sheet-raw"' in html
    assert "No preview available. The file could not be read." in html or "Hello world" in html

def test_js_chord_tools_match_python():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, "tests/chord_tools_check.js"],
        cwd=str(root), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout

def test_account_theme_picker(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    assert 'id="theme-picker"' in html
    assert 'role="radiogroup"' in html
    assert 'aria-label="Color theme"' in html
    for label in ('Default', 'Wooden', 'Limelight'):
        assert label in html
    assert html.count('type="radio" name="color-theme"') == 3
    assert 'value="wooden"' in html
    assert 'value="limelight"' in html
    assert 'value="stage"' not in html
    assert 'value="nature"' not in html
    assert '> Stage<' not in html
    assert '> Nature<' not in html
    assert 'id="theme-toggle"' not in html


def test_theme_applies_from_head_without_the_old_button(client):
    html = client.get('/').get_data(as_text=True)
    assert 'id="theme-toggle"' not in html
    assert "localStorage.getItem('cs-theme-v2')" in html
    assert "old === 'nature'" in html
    assert 'data-theme' in html
    sheet = client.get('/view_sheet/1').get_data(as_text=True)
    assert 'id="theme-toggle"' not in sheet


def test_chordpro_is_gone(client, auth_client):
    assert client.post("/api/chordpro/parse", json={"text": "[C]hi"}).status_code == 404
    sheet = client.get("/view_sheet/1").get_data(as_text=True)
    assert 'btn-download-cho' not in sheet
    assert 'id="btn-share"' in sheet
    assert 'id="btn-download-txt"' in sheet
    creator = auth_client.get("/creator").get_data(as_text=True)
    assert 'chordpro-paste' not in creator
    assert 'toggle-touch-editor' in creator


def test_first_run_tip_is_gone(client):
    html = client.get('/').get_data(as_text=True)
    assert 'first-run-tip' not in html
    assert 'cs-tip-dismissed' not in html
    assert 'Tip: star a sheet' not in html
