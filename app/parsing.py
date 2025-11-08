import re
from .utils import BRACKETED_CHORD_REGEX

# Matches: root note, optional quality/extensions, optional alterations, optional bass note
CHORD_BODY_REGEX = re.compile(
    r'^'
    r'([A-G][b#]?)'                    # root (A–G with optional accidental)
    r'((?:m|min|maj|sus|dim|aug)?)'    # basic quality
    r'(\d*(?:add\d+)?(?:b\d+|#\d+)*)?'  # extension/add intervals and alterations
    r'(?:/([A-G][b#]?\d*))?'           # optional bass note with possible octave
    r'$'
)


def strip_brackets(chord_text: str) -> str:
    """Remove square brackets from a chord token, if present."""
    chord_text = chord_text.strip()
    if chord_text.startswith('[') and chord_text.endswith(']'):
        return chord_text[1:-1]
    return chord_text


def parse_chord(chord_text: str) -> tuple[str, str, str]:
    """
    Parse a chord string into (root, quality, bass).
    Returns ('', '', '') if parsing fails.
    """
    raw = strip_brackets(chord_text)
    match = CHORD_BODY_REGEX.match(raw)
    
    if not match:
        return '', '', ''
    
    root = match.group(1) or ''
    quality = (match.group(2) or '') + (match.group(3) or '')
    bass = match.group(4) or ''
    
    return root, quality, bass


def extract_bracketed_chords(text: str) -> list[str]:
    """Return a list of all bracketed chord strings found in the given text."""
    return [match.group(1) for match in BRACKETED_CHORD_REGEX.finditer(text)]