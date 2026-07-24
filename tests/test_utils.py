import pytest
from app.utils import (
    normalise_spacing,
    highlight_chords,
    split_chord_lyric_line,
    process_song_text,
    get_key_preference
)

def test_normalise_spacing():
    raw_text = "Line 1   \n\n\nLine 2\n"
    cleaned = normalise_spacing(raw_text)
    assert "Line 1" in cleaned
    assert "Line 2" in cleaned
    assert "\n\n\n" not in cleaned

def test_highlight_chords():
    text = "Play [C] and [Am7] and [F#/A#]"
    highlighted = highlight_chords(text, add_data_attr=True)
    assert '<span class="chord" data-chord="[C]">[C]</span>' in highlighted
    assert '<span class="chord" data-chord="[Am7]">[Am7]</span>' in highlighted
    assert '<span class="chord" data-chord="[F#/A#]">[F#/A#]</span>' in highlighted

def test_split_chord_lyric_line_lyrics_and_chords():
    line = "[C]Hello [G]world"
    chord_layer, lyric_layer = split_chord_lyric_line(line)
    assert "[C]" in chord_layer
    assert "[G]" in chord_layer
    assert lyric_layer.strip() == "Hello world"

def test_split_chord_lyric_line_section_header():
    line = "Chorus:"
    chord_layer, lyric_layer = split_chord_lyric_line(line)
    assert chord_layer == "Chorus:"
    assert lyric_layer == ""

def test_get_key_preference():
    assert get_key_preference("G major") == "sharp"
    assert get_key_preference("F major") == "flat"
    assert get_key_preference("Bb major") == "flat"
    assert get_key_preference("D major") == "sharp"
