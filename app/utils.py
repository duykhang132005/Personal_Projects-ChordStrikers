import re

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
        if stripped or (cleaned and cleaned[-1]):
            cleaned.append(stripped)
    return "\n".join(cleaned)

def highlight_chords(text: str, add_data_attr: bool = False) -> str:
    """
    Wraps bracketed chords in a span for styling/click handling.

    If add_data_attr is True, also adds a `data-chord` attribute
    storing the original chord text for client‑side toggling.
    """
    if add_data_attr:
        return BRACKETED_CHORD_REGEX.sub(
            lambda m: f'<span class="chord" data-chord="{m.group(1)}">{m.group(1)}</span>',
            text
        )
    return BRACKETED_CHORD_REGEX.sub(r'<span class="chord">\1</span>', text)

def split_chord_lyric_line(line: str) -> tuple[str, str]:
    """
    Splits a line into chord and lyric layers, preserving alignment.
    Uses lyric spacing as the 'truth grid' and pads chords to match.
    Collapses multiple spaces in the lyric layer and applies the same to chords.
    """
    stripped_line = line.strip()
    words = stripped_line.split()
    first_word = words[0].rstrip(':') if words else ''

    # Section headers: highlight whole line
    if first_word.lower() in [kw.lower() for kw in SECTION_KEYWORDS]:
        return line.rstrip(), ''

    chord_parts: list[str] = []
    lyric_parts: list[str] = []
    chord_len = 0  # current rendered width of chord_parts
    j = 0          # lyric column index
    i = 0          # index into raw line
    last_space = False

    def pad_chords_to(col: int) -> None:
        nonlocal chord_len
        missing = col - chord_len
        if missing > 0:
            chord_parts.append(' ' * missing)
            chord_len += missing

    while i < len(line):
        ch = line[i]

        if ch == '[':
            end = line.find(']', i + 1)
            if end != -1:
                chord = line[i:end+1]
                pad_chords_to(j)       # position chord at current lyric column
                chord_parts.append(chord)
                chord_len += len(chord)
                i = end + 1
                continue
            # fall through if unmatched '['

        # Handle lyric-visible characters with space collapsing
        if ch == ' ':
            if last_space:
                i += 1
                continue  # collapse extra spaces
            last_space = True
        else:
            last_space = False

        lyric_parts.append(ch)
        j += 1
        i += 1

    chord_str = ''.join(chord_parts).rstrip()
    lyric_str = ''.join(lyric_parts).rstrip()
    return chord_str, lyric_str

def process_song_text(text: str, add_data_attr: bool = False) -> list[tuple[str, str]]:
    """
    Splits lines into chord/lyric pairs, highlights chords.
    """
    lines = text.split('\n')
    processed = []
    for line in lines:
        if line.strip():
            chord_line, lyric_line = split_chord_lyric_line(line)
            # avoid double-highlighting for section headers
            if not chord_line.strip().startswith('<span'):
                chord_line = highlight_chords(chord_line, add_data_attr=add_data_attr)
            processed.append((chord_line, lyric_line))
    return processed

def prepare_song(text: str, add_data_attr: bool = False) -> list[tuple[str, str]]:
    """
    Cleans and processes song text for rendering.
    """
    cleaned = normalise_spacing(text)
    return process_song_text(cleaned, add_data_attr=add_data_attr)

def get_key_preference(key: str) -> str:
    """
    Returns 'sharp' or 'flat' based on key signature.
    """
    sharp_keys = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#']
    flat_keys  = ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb']
    root = key.split()[0]  # e.g. 'D major' → 'D'
    return 'sharp' if root in sharp_keys else 'flat'
