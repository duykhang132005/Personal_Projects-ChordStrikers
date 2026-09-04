import re
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


def get_artist_image_url(sp_client, artist_name):
    """
    Searches Spotify for an artist and returns the URL of their largest image.
    
    Args:
        sp_client: The initialized Spotipy client object.
        artist_name: The name of the artist to search for.
        
    Returns:
        The URL (string) of the artist's largest image, or None if not found 
        or an error occurs.
    """
    if not sp_client or not artist_name:
        return None
        
    try:
        # Search Spotify for the artist, limiting to 1 result of type 'artist'.
        results = sp_client.search(q=artist_name, type='artist', limit=1)
        
        # Check if any artists were found in the results.
        if results and results['artists']['items']:
            artist_data = results['artists']['items'][0]
            
            # Spotify returns images in various sizes, widest/largest first.
            if artist_data['images']:
                # Grab the URL of the largest image.
                image_url = artist_data['images'][0]['url']
                return sanitize_image_url(image_url)
            
    except Exception as e:
        # Log error if we have access to Flask app context
        try:
            from flask import current_app
            current_app.logger.error(f"Error fetching Spotify image for {artist_name}: {e}")
        except RuntimeError:
            # Not in Flask app context, just pass silently
            pass
        
    return None


def get_song_image_url(sp_client, song_title, artist_name=None):
    """
    Searches Spotify for a song and returns the URL of the album/track image.
    Falls back to artist image if song not found.
    Parallelizes tracking and artist search for better performance.
    
    Args:
        sp_client: The initialized Spotipy client object.
        song_title: The name of the song to search for.
        artist_name: Optional artist name for fallback and better search results.
        
    Returns:
        The URL (string) of the song's album image, or artist image if song not found,
        or None if neither is found.
    """
    if not sp_client or not song_title:
        # If no song title, try artist only
        if artist_name:
            return get_artist_image_url(sp_client, artist_name)
        return None
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def search_track():
        try:
            # First, try to find the song/track
            # Construct search query: combine song title and artist name together
            if artist_name:
                # Strategy 1: Combined query (most accurate)
                search_query = f"{song_title} {artist_name}"
            else:
                search_query = song_title
            
            results = sp_client.search(q=search_query, type='track', limit=1)
            
            # Check if any tracks were found
            if results and results['tracks']['items']:
                track_data = results['tracks']['items'][0]
                
                # Try to get album image first (usually better quality)
                if 'album' in track_data and track_data['album']['images']:
                    image_url = track_data['album']['images'][0]['url']
                    return sanitize_image_url(image_url)
                
                # Fallback: try artist image from track
                if 'artists' in track_data and track_data['artists']:
                    artist_id = track_data['artists'][0]['id']
                    artist_data = sp_client.artist(artist_id)
                    if artist_data.get('images'):
                        return sanitize_image_url(artist_data['images'][0]['url'])
            return None
        except Exception as e:
            # Log error if we have access to Flask app context
            try:
                from flask import current_app
                current_app.logger.error(f"Error fetching Spotify image for song '{song_title}': {e}")
            except RuntimeError:
                pass
            return None

    def search_artist_fallback():
        if artist_name:
            return get_artist_image_url(sp_client, artist_name)
        return None

    # Execute searches in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_track = executor.submit(search_track)
        future_artist = executor.submit(search_artist_fallback)
        
        # Wait for track result first
        track_image = future_track.result()
        if track_image:
            return sanitize_image_url(track_image)

        # If track not found or failed, return artist result
        return sanitize_image_url(future_artist.result())
