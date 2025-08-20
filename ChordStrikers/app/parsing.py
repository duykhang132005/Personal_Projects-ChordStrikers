import re
from .transposition import transpose_pitch
from .utils import get_key_preference

def parse_chord(chord: str) -> dict:
    """
    Parses a chord string into components:
    - root: main pitch
    - quality: suffix like 'm7', 'maj7', 'dim'
    - bass: optional slash bass note
    """
    match = re.match(r'^([A-G][b#]?)([^/]*)/?([A-G][b#]?)?$', chord)
    if not match:
        raise ValueError(f"Invalid chord format: {chord}")
    root, quality, bass = match.groups()
    return {
        'root': root,
        'quality': quality or '',
        'bass': bass
    }

def transpose_chord(chord: str, steps: int, key: str = None) -> str:
    """Transpose full chord string by steps, respecting key signature."""
    key_pref = get_key_preference(key) if key else 'sharp'
    parts = parse_chord(chord)

    new_root = transpose_pitch(parts['root'], steps, key_pref)
    new_bass = transpose_pitch(parts['bass'], steps, key_pref) if parts['bass'] else None

    transposed = new_root + parts['quality']
    if new_bass:
        transposed += f"/{new_bass}"
    return transposed