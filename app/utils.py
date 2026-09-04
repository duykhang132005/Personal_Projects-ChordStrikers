import json
import re
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlparse

from markupsafe import Markup, escape

# Central regex for bracketed chords, used by both highlighting and parsing
BRACKETED_CHORD_REGEX = re.compile(
    r'(\['                                # opening bracket
    r'[A-G][#b]?'                         # root note (A–G, optional sharp/flat)
    r'(?:m|min|maj|sus|dim|aug|m7b5)?'    # optional chord quality
    r'(?:\d+|add\d+)?'                    # optional extension (7, 9, 13, add9, etc.)
    r'(?:[#b]\d+)*'                       # optional alterations (b5, #11, etc.)
    r'(?:/[A-G][#b]?)?'                   # optional slash bass note
    r'\])'                                # closing bracket
)

SECTION_KEYWORDS = [
    'Intro', 'Verse', 'Melody', 'Prechorus', 'Pre-chorus', 'Pre Chorus',
    'Chorus', 'Interlude', 'Outro', 'Bridge'
]

# Normalize section keywords to lowercase for faster lookups
_SECTION_KEYWORDS_LOWER = {kw.lower() for kw in SECTION_KEYWORDS}


def normalise_spacing(text: str) -> str:
    """
    Cleans up spacing in chord sheets:
    - Removes trailing whitespace
    - Collapses multiple blank lines
    - Ensures consistent line endings
    """
    lines = text.splitlines()
    cleaned = []
    
    for line in lines:
        stripped = line.rstrip()
        # Add line if it has content, or if it's blank but previous line had content
        if stripped or (cleaned and cleaned[-1]):
            cleaned.append(stripped)
    
    return "\n".join(cleaned)


def _wrap_chord_span(chord: str, add_data_attr: bool) -> Markup:
    """Return a safe <span class="chord"> wrapper around an escaped token."""
    escaped_chord = escape(chord)
    if add_data_attr:
        return Markup('<span class="chord" data-chord="{}">{}</span>').format(
            escaped_chord, escaped_chord
        )
    return Markup('<span class="chord">{}</span>').format(escaped_chord)


def highlight_chords(text: str, add_data_attr: bool = False) -> Markup:
    """
    Wraps bracketed chords in a span for styling/click handling.

    HTML-escapes both chord tokens and surrounding text so the result is
    safe to mark as trusted HTML. If add_data_attr is True, also adds a
    `data-chord` attribute storing the original chord text for client-side
    toggling.
    """
    pieces = []
    pos = 0
    for match in BRACKETED_CHORD_REGEX.finditer(text):
        pieces.append(escape(text[pos:match.start()]))
        pieces.append(_wrap_chord_span(match.group(1), add_data_attr))
        pos = match.end()
    pieces.append(escape(text[pos:]))
    return Markup('').join(pieces)


def split_chord_lyric_line(line: str) -> tuple[str, str]:
    """
    Splits a line into chord and lyric layers, preserving alignment.
    Uses lyric spacing as the 'truth grid' and pads chords to match.
    Collapses multiple spaces in the lyric layer and applies the same to chords.
    """
    stripped_line = line.strip()
    words = stripped_line.split()
    
    # Check if line is a section header
    if words:
        first_word = words[0].rstrip(':')
        if first_word.lower() in _SECTION_KEYWORDS_LOWER:
            return line.rstrip(), ''
    
    chord_parts = []
    lyric_parts = []
    chord_len = 0  # current rendered width of chord_parts
    lyric_col = 0  # lyric column index
    i = 0          # index into raw line
    last_was_space = False
    
    def pad_chords_to(target_col: int) -> None:
        nonlocal chord_len
        gap = target_col - chord_len
        if gap > 0:
            chord_parts.append(' ' * gap)
            chord_len += gap
    
    while i < len(line):
        char = line[i]
        
        # Handle bracketed chords
        if char == '[':
            end = line.find(']', i + 1)
            if end != -1:
                chord = line[i:end + 1]
                pad_chords_to(lyric_col)  # position chord at current lyric column
                chord_parts.append(chord)
                chord_len += len(chord)
                i = end + 1
                continue
        
        # Handle spaces with collapsing
        if char == ' ':
            if last_was_space:
                i += 1
                continue  # collapse consecutive spaces
            last_was_space = True
        else:
            last_was_space = False
        
        lyric_parts.append(char)
        lyric_col += 1
        i += 1
    
    chord_str = ''.join(chord_parts).rstrip()
    lyric_str = ''.join(lyric_parts).rstrip()
    
    return chord_str, lyric_str


def process_song_text(text: str, add_data_attr: bool = False) -> list[tuple[str, str]]:
    """Splits lines into chord/lyric pairs, highlights chords."""
    lines = text.split('\n')
    processed = []
    
    for line in lines:
        if line.strip():
            chord_line, lyric_line = split_chord_lyric_line(line)
            # Avoid double-highlighting for section headers
            if not chord_line.strip().startswith('<span'):
                chord_line = highlight_chords(chord_line, add_data_attr=add_data_attr)
            processed.append((chord_line, escape(lyric_line)))
    
    return processed


def prepare_song(text: str, add_data_attr: bool = False) -> list[tuple[str, str]]:
    """Cleans and processes song text for rendering."""
    cleaned = normalise_spacing(text)
    return process_song_text(cleaned, add_data_attr=add_data_attr)


def get_key_preference(key: str) -> str:
    """Returns 'sharp' or 'flat' based on key signature."""
    SHARP_KEYS = {'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#'}
    FLAT_KEYS = {'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb'}
    
    root = key.split()[0]  # e.g. 'D major' → 'D'
    
    if root in SHARP_KEYS:
        return 'sharp'
    elif root in FLAT_KEYS:
        return 'flat'
    else:
        return 'sharp'  # default to sharp for unknown keys


DEFAULT_IMAGE_URL_ALLOWED_HOSTS = (
    '*.mzstatic.com',
    'i.scdn.co',
    '*.scdn.co',
    '*.spotifycdn.com',
)


def _get_allowed_image_hosts(allowed_hosts=None):
    """Resolve the cover-image host allowlist from argument, app config, or defaults."""
    if allowed_hosts is not None:
        return allowed_hosts
    try:
        from flask import current_app, has_app_context
        if has_app_context():
            configured = current_app.config.get('IMAGE_URL_ALLOWED_HOSTS')
            if configured:
                return configured
    except Exception:
        pass
    return DEFAULT_IMAGE_URL_ALLOWED_HOSTS


def _hostname_allowed(hostname: str, allowed_hosts) -> bool:
    """Return True if hostname matches an exact or *.suffix allowlist entry."""
    host = hostname.lower().rstrip('.')
    if not host:
        return False
    for raw in allowed_hosts:
        if not raw:
            continue
        pattern = str(raw).lower().strip().rstrip('.')
        if pattern.startswith('*.'):
            suffix = pattern[2:].lstrip('.')
            if suffix and (host == suffix or host.endswith('.' + suffix)):
                return True
        elif host == pattern:
            return True
    return False


def sanitize_image_url(url, allowed_hosts=None):
    """
    Return url if it is a safe https image URL on an allowed host, else None.

    Rejects non-https schemes, credentials/userinfo, explicit ports, and
    hosts outside IMAGE_URL_ALLOWED_HOSTS (or allowed_hosts if provided).
    """
    if not url or not isinstance(url, str):
        return None

    candidate = url.strip()
    if not candidate or any(ch.isspace() for ch in candidate):
        return None
    if len(candidate) > 512:
        return None

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    if parsed.scheme != 'https':
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    if parsed.port is not None:
        return None
    if not parsed.hostname:
        return None
    if not _hostname_allowed(parsed.hostname, _get_allowed_image_hosts(allowed_hosts)):
        return None

    return candidate


ITUNES_SEARCH_URL = 'https://itunes.apple.com/search'
ITUNES_ARTWORK_SIZE = 600


def _log_cover_fetch_error(message):
    try:
        from flask import current_app
        current_app.logger.error(message)
    except RuntimeError:
        pass


def _upscale_itunes_artwork_url(url: str) -> str:
    """
    Prefer a larger square thumbnail when Apple's documented size token is present.

    The Search API returns artworkUrl100 URLs containing `100x100bb` (and
    artworkUrl60 uses `60x60bb`). Those tokens can be replaced with `600x600bb`
    on mzstatic.com; other URL shapes are left unchanged.
    """
    if not url:
        return url
    if '100x100bb' in url:
        return url.replace('100x100bb', f'{ITUNES_ARTWORK_SIZE}x{ITUNES_ARTWORK_SIZE}bb', 1)
    if '60x60bb' in url:
        return url.replace('60x60bb', f'{ITUNES_ARTWORK_SIZE}x{ITUNES_ARTWORK_SIZE}bb', 1)
    return url


def _normalize_itunes_artwork_url(url: str):
    """Upgrade http→https, upscale the thumbnail token, then sanitize."""
    if not url or not isinstance(url, str):
        return None
    candidate = url.strip()
    if candidate.startswith('http://'):
        candidate = 'https://' + candidate[len('http://'):]
    return sanitize_image_url(_upscale_itunes_artwork_url(candidate))


def _itunes_search(term, entity, limit=1):
    """Return iTunes Search API result dicts, or an empty list on failure."""
    if not term or not str(term).strip():
        return []

    params = urllib.parse.urlencode({
        'term': str(term).strip(),
        'media': 'music',
        'entity': entity,
        'limit': str(limit),
    })
    request = urllib.request.Request(
        f'{ITUNES_SEARCH_URL}?{params}',
        headers={'User-Agent': 'ChordStrikers/1.0'},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError) as exc:
        _log_cover_fetch_error(f"Error searching iTunes for {term!r}: {exc}")
        return []

    results = payload.get('results') if isinstance(payload, dict) else None
    return results if isinstance(results, list) else []


def _artwork_url_from_itunes_results(results):
    for item in results or []:
        if not isinstance(item, dict):
            continue
        raw = item.get('artworkUrl100') or item.get('artworkUrl60')
        sanitized = _normalize_itunes_artwork_url(raw) if raw else None
        if sanitized:
            return sanitized
    return None


def get_artist_image_url(artist_name):
    """
    Search iTunes for an artist and return album artwork (musicArtist has none).

    Returns a sanitized https image URL, or None if not found or an error occurs.
    """
    if not artist_name:
        return None
    try:
        results = _itunes_search(artist_name, entity='album')
        return _artwork_url_from_itunes_results(results)
    except Exception as exc:
        _log_cover_fetch_error(f"Error fetching iTunes image for {artist_name}: {exc}")
        return None


def get_song_image_url(song_title, artist_name=None):
    """
    Search iTunes for a song and return album/track artwork.

    Tries title+artist, then title-only, then artist album artwork.
    Returns a sanitized https image URL, or None if not found or an error occurs.
    """
    if not song_title:
        if artist_name:
            return get_artist_image_url(artist_name)
        return None

    try:
        if artist_name:
            combined = _artwork_url_from_itunes_results(
                _itunes_search(f'{song_title} {artist_name}', entity='song')
            )
            if combined:
                return combined

        title_only = _artwork_url_from_itunes_results(
            _itunes_search(song_title, entity='song')
        )
        if title_only:
            return title_only

        if artist_name:
            return get_artist_image_url(artist_name)
    except Exception as exc:
        _log_cover_fetch_error(f"Error fetching iTunes image for song {song_title!r}: {exc}")

    return None
