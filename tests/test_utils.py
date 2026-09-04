import pytest
from markupsafe import Markup
from app.utils import (
    normalise_spacing,
    highlight_chords,
    split_chord_lyric_line,
    process_song_text,
    prepare_song,
    get_key_preference,
    sanitize_image_url,
    get_artist_image_url,
    get_song_image_url,
    _upscale_itunes_artwork_url,
)

ITUNES_ARTWORK_100 = (
    'https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/aa/bb/cc/source/100x100bb.jpg'
)
ITUNES_ARTWORK_600 = ITUNES_ARTWORK_100.replace('100x100bb', '600x600bb')

def test_normalise_spacing():
    raw_text = "Line 1   \n\n\nLine 2\n"
    cleaned = normalise_spacing(raw_text)
    assert "Line 1" in cleaned
    assert "Line 2" in cleaned
    assert "\n\n\n" not in cleaned

def test_highlight_chords():
    text = "Play [C] and [Am7] and [F#/A#]"
    highlighted = highlight_chords(text, add_data_attr=True)
    assert isinstance(highlighted, Markup)
    assert '<span class="chord" data-chord="[C]">[C]</span>' in highlighted
    assert '<span class="chord" data-chord="[Am7]">[Am7]</span>' in highlighted
    assert '<span class="chord" data-chord="[F#/A#]">[F#/A#]</span>' in highlighted


def test_highlight_chords_escapes_html():
    text = '<script>alert(1)</script> [C] <img src=x onerror=alert(1)>'
    highlighted = highlight_chords(text, add_data_attr=True)
    assert '<script>' not in highlighted
    assert '<img' not in highlighted
    assert '&lt;script&gt;' in highlighted
    assert '&lt;img' in highlighted
    assert '<span class="chord" data-chord="[C]">[C]</span>' in highlighted

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


def test_prepare_song_escapes_lyrics_and_section_headers():
    text = "[C]Hello <b>world</b>\nChorus: <script>xss</script>"
    lines = prepare_song(text, add_data_attr=True)

    chord_line, lyric_line = lines[0]
    assert '<span class="chord" data-chord="[C]">[C]</span>' in chord_line
    assert '<b>' not in lyric_line
    assert '&lt;b&gt;world&lt;/b&gt;' in lyric_line
    assert isinstance(lyric_line, Markup)

    header_chord, header_lyric = lines[1]
    assert header_lyric == ''
    assert '<script>' not in header_chord
    assert '&lt;script&gt;' in header_chord


def test_process_song_text_escapes_lyrics():
    lines = process_song_text("[G]Don't <img src=x onerror=alert(1)>")
    _, lyric_line = lines[0]
    assert '<img' not in lyric_line
    assert '&lt;img' in lyric_line


def test_sanitize_image_url_allows_itunes_and_spotify_hosts():
    assert sanitize_image_url(ITUNES_ARTWORK_600) == ITUNES_ARTWORK_600
    assert sanitize_image_url(
        'https://is5-ssl.mzstatic.com/image/thumb/Music/source/600x600bb.jpg'
    ) == 'https://is5-ssl.mzstatic.com/image/thumb/Music/source/600x600bb.jpg'
    assert sanitize_image_url(
        'https://i.scdn.co/image/ab67616d0000b273abc'
    ) == 'https://i.scdn.co/image/ab67616d0000b273abc'
    assert sanitize_image_url('https://mosaic.scdn.co/300/abc') == 'https://mosaic.scdn.co/300/abc'
    assert sanitize_image_url(
        'https://image-cdn-ak.spotifycdn.com/image/ab123'
    ) == 'https://image-cdn-ak.spotifycdn.com/image/ab123'


def test_sanitize_image_url_denies_unsafe():
    assert sanitize_image_url('http://is1-ssl.mzstatic.com/image/thumb/x.jpg') is None
    assert sanitize_image_url('http://i.scdn.co/image') is None
    assert sanitize_image_url('https://evil.com/x.png') is None
    assert sanitize_image_url('https://user:pass@is1-ssl.mzstatic.com/x') is None
    assert sanitize_image_url('https://is1-ssl.mzstatic.com:8443/x') is None
    assert sanitize_image_url('javascript:alert(1)') is None
    assert sanitize_image_url('https://is1-ssl.mzstatic.com.evil.com/x') is None
    assert sanitize_image_url('//is1-ssl.mzstatic.com/x') is None
    assert sanitize_image_url('https://is1-ssl.mzstatic.com/x\nhttps://evil.com') is None
    assert sanitize_image_url('') is None
    assert sanitize_image_url(None) is None


def test_sanitize_image_url_respects_custom_allowlist():
    url = 'https://cdn.example.com/a.png'
    assert sanitize_image_url(url, allowed_hosts=['cdn.example.com']) == url
    assert sanitize_image_url(url, allowed_hosts=['*.mzstatic.com']) is None


def test_upscale_itunes_artwork_url():
    assert _upscale_itunes_artwork_url(ITUNES_ARTWORK_100) == ITUNES_ARTWORK_600
    sixty = ITUNES_ARTWORK_100.replace('100x100bb', '60x60bb')
    assert _upscale_itunes_artwork_url(sixty) == ITUNES_ARTWORK_600
    unchanged = 'https://is1-ssl.mzstatic.com/image/thumb/Music/source/cover.jpg'
    assert _upscale_itunes_artwork_url(unchanged) == unchanged


def test_get_song_image_url_uses_itunes_and_upscales(monkeypatch):
    monkeypatch.setattr(
        'app.utils._itunes_search',
        lambda term, entity, limit=1: [{'artworkUrl100': ITUNES_ARTWORK_100}],
    )
    assert get_song_image_url('Hey Jude', 'The Beatles') == ITUNES_ARTWORK_600


def test_get_song_image_url_rejects_disallowed_host(monkeypatch):
    monkeypatch.setattr(
        'app.utils._itunes_search',
        lambda term, entity, limit=1: [{'artworkUrl100': 'https://evil.com/hack.png'}],
    )
    assert get_song_image_url('Song', 'Artist') is None


def test_get_song_image_url_returns_none_on_network_error(monkeypatch):
    import urllib.error

    def boom(*args, **kwargs):
        raise urllib.error.URLError('network down')

    monkeypatch.setattr('app.utils.urllib.request.urlopen', boom)
    assert get_song_image_url('Song', 'Artist') is None


def test_get_artist_image_url_searches_albums(monkeypatch):
    calls = []

    def fake_search(term, entity, limit=1):
        calls.append((term, entity))
        return [{'artworkUrl100': ITUNES_ARTWORK_100}]

    monkeypatch.setattr('app.utils._itunes_search', fake_search)
    assert get_artist_image_url('The Beatles') == ITUNES_ARTWORK_600
    assert calls == [('The Beatles', 'album')]


def test_get_song_image_url_falls_back_to_artist(monkeypatch):
    def fake_search(term, entity, limit=1):
        if entity == 'album':
            return [{'artworkUrl100': ITUNES_ARTWORK_100}]
        return []

    monkeypatch.setattr('app.utils._itunes_search', fake_search)
    assert get_song_image_url('Unknown Track', 'The Beatles') == ITUNES_ARTWORK_600
