from .utils import get_key_preference

PITCHES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
PITCHES_FLAT  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

ENHARMONICS = {
    'C#': 'Db', 'Db': 'C#',
    'D#': 'Eb', 'Eb': 'D#',
    'F#': 'Gb', 'Gb': 'F#',
    'G#': 'Ab', 'Ab': 'G#',
    'A#': 'Bb', 'Bb': 'A#'
}

def transpose_pitch(pitch: str, steps: int, key_pref='sharp') -> str:
    """Transpose a pitch by steps, respecting key preference."""
    if pitch in PITCHES_SHARP:
        idx = PITCHES_SHARP.index(pitch)
    elif pitch in PITCHES_FLAT:
        idx = PITCHES_FLAT.index(pitch)
    else:
        raise ValueError(f"Unknown pitch: {pitch}")

    new_idx = (idx + steps) % 12
    new_pitch = PITCHES_SHARP[new_idx] if key_pref == 'sharp' else PITCHES_FLAT[new_idx]

    if pitch in ENHARMONICS:
        if key_pref == 'flat':
            new_pitch = ENHARMONICS.get(new_pitch, new_pitch)
    return new_pitch