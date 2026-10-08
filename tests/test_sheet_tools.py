"""Sort, capo, simplify, and ChordPro import."""
import shutil
import subprocess
from pathlib import Path

import pytest

from app import db
from app.chord_logic import simplify_chord, suggest_capos, transform_text, transpose_chord
from app.chordpro import parse_chordpro, to_chordpro
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

def test_chordpro_parse_and_export():
    parsed = parse_chordpro(
        "{title: Hello}\n{st: Someone}\n{key: G}\n{capo: 2}\n"
        "{soc}\n[G]Hello [D]there\n{eoc}\n{comment: skip me}\n"
    )
    assert parsed["title"] == "Hello"
    assert parsed["artist"] == "Someone"
    assert parsed["key"] == "G"
    assert parsed["capo"] == 2
    assert "[Chorus]" in parsed["content"]
    assert "skip me" not in parsed["content"]
    assert "[G]Hello [D]there" in parsed["content"]
    exported = to_chordpro(
        title=parsed["title"], artist=parsed["artist"], key=parsed["key"],
        capo=parsed["capo"], content=parsed["content"],
    )
    assert exported.startswith("{title: Hello}")
    assert "{capo: 2}" in exported

def test_chordpro_artist_beats_subtitle():
    parsed = parse_chordpro("{artist: Real}\n{subtitle: Other}\n[C]Hi")
    assert parsed["artist"] == "Real"

def test_chordpro_route(client):
    response = client.post("/api/chordpro/parse", json={
        "text": "{t: Song}\n{artist: A}\n[Am]Line",
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Song"
    assert data["content"] == "[Am]Line"
    bad = client.post("/api/chordpro/parse", json={"text": 5})
    assert bad.status_code == 400

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
    for label in ('Default', 'Stage', 'Wooden', 'Nature', 'Limelight'):
        assert label in html
    assert 'value="wooden"' in html
    assert 'value="nature"' in html
    assert 'value="limelight"' in html
    assert 'value="stage"' in html
    assert 'id="theme-toggle"' not in html


def test_theme_applies_from_head_without_the_old_button(client):
    html = client.get('/').get_data(as_text=True)
    assert 'id="theme-toggle"' not in html
    assert "localStorage.getItem('cs-theme')" in html
    assert 'data-theme' in html
    sheet = client.get('/view_sheet/1').get_data(as_text=True)
    assert 'id="theme-toggle"' not in sheet

