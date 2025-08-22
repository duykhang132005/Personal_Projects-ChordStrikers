import re
from .utils import BRACKETED_CHORD_REGEX

# Matches: root note, optional quality/extensions, optional alterations, optional bass note
CHORD_BODY_REGEX = re.compile(
    r'^'                       # start
    r'([A-G][b#]?)'            # root (A–G with optional accidental)
    r'((?:m|min|maj|sus|dim|aug)?)'  # basic quality
    r'(\d*(?:add\d+)?'         # extension/add intervals (e.g., 7, 9, add9)
    r'(?:b\d+|#\d+)*)?'        # alterations (e.g., b5, #11)
    r'(?:/([A-G][b#]?\d*))?'   # optional bass note, may include octave
    r'$'                       # end
)

def strip_brackets(chord_text: str) -> str:
    """
    Remove square brackets from a chord token, if present.
    """
    chord_text = chord_text.strip()
    return chord_text[1:-1] if chord_text.startswith('[') and chord_text.endswith(']') else chord_text

def parse_chord(chord_text: str) -> tuple[str, str, str]:
    """
    Parse a chord string into (root, quality, bass).
    Returns ('', '', '') if parsing fails.
    """
    raw = strip_brackets(chord_text)
    m = CHORD_BODY_REGEX.match(raw)
    if not m:
        return '', '', ''
    root = m.group(1) or ''
    quality = (m.group(2) or '') + (m.group(3) or '')
    bass = m.group(4) or ''
    return root, quality, bass

def extract_bracketed_chords(text: str):
    """
    Return a list of all bracketed chord strings found in the given text.
    """
    return [m.group(1) for m in BRACKETED_CHORD_REGEX.finditer(text)]