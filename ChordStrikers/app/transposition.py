from .parsing import parse_chord, strip_brackets
from .utils import get_key_preference, BRACKETED_CHORD_REGEX

# 12‑tone pitch maps
PITCHES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F',
                 'F#', 'G', 'G#', 'A', 'A#', 'B']
PITCHES_FLAT  = ['C', 'Db', 'D', 'Eb', 'E', 'F',
                 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

# Enharmonic equivalents for conversion between sharp/flat spellings
ENHARMONICS = {
    'B#': 'C', 'E#': 'F',
    'Cb': 'B', 'Fb': 'E',
    'Db': 'C#', 'Eb': 'D#',
    'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#',
    'C#': 'Db', 'D#': 'Eb',
    'F#': 'Gb', 'G#': 'Ab', 'A#': 'Bb'
}

def transpose_pitch(pitch: str, steps: int, prefer: str = 'sharp') -> str:
    """
    Transpose a pitch by a number of semitones, honouring preferred accidentals.
    Returns the pitch unchanged if it can't be matched.
    """
    if not pitch:
        return pitch

    note = pitch.strip()

    # choose working set based on preference
    notes = PITCHES_SHARP if prefer == 'sharp' else PITCHES_FLAT

    # normalise to something in our list if possible
    if note not in notes:
        if note in ENHARMONICS:
            note = ENHARMONICS[note]
        else:
            return pitch  # unknown, leave untouched

    idx = notes.index(note)
    new_idx = (idx + steps) % 12
    return notes[new_idx]

def transpose_chord(chord_text: str, steps: int, prefer: str = None) -> str:
    """
    Transpose a full chord (with or without brackets) by semitones.
    If prefer is None, deduce sharp/flat preference from the chord root.
    """
    root, quality, bass = parse_chord(chord_text)
    if not root:
        return chord_text  # unparsable, return as-is

    if prefer is None:
        prefer = get_key_preference(root)

    new_root = transpose_pitch(root, steps, prefer)
    new_bass = transpose_pitch(bass, steps, prefer) if bass else ''

    new_chord = new_root + quality + (f'/{new_bass}' if new_bass else '')

    # preserve brackets if originally present
    return f'[{new_chord}]' if chord_text.strip().startswith('[') else new_chord

def transpose_song_text(song_text: str, steps: int, prefer: str = None) -> str:
    """
    Transpose every bracketed chord in a block of song text by semitones.
    """
    def _transpose_match(match):
        chord_token = match.group(1)
        return transpose_chord(chord_token, steps, prefer)

    return BRACKETED_CHORD_REGEX.sub(lambda m: _transpose_match(m), song_text)