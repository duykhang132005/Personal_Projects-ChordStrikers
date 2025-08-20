import re

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

def highlight_chords(text):
    return re.sub(r'(\[[^\]]+\])', r'<span class="chord">\1</span>', text)

import re

def split_chord_lyric_line(line):
    section_keywords = ['Intro', 'Verse', 'Melody', 'Prechorus', 'Chorus', 'Interlude']
    stripped_line = line.strip()
    words = stripped_line.split()
    first_word = words[0].rstrip(':') if words else ''

    if first_word.lower() in [kw.lower() for kw in section_keywords]:
        return line, ''  # Preserve section header as-is

    chord_line = ''
    lyric_line = ''
    i = 0

    while i < len(line):
        if line[i] == '[':
            end = line.find(']', i)
            if end != -1:
                chord = line[i+1:end]
                chord_line += chord
                lyric_line += ' ' * len(chord)
                i = end + 1
            else:
                chord_line += line[i]
                lyric_line += line[i]
                i += 1
        else:
            chord_line += ' '
            lyric_line += line[i]
            i += 1

    # Normalize excessive spacing in lyric line
    lyric_line = re.sub(r' {2,}', ' ', lyric_line)
    return chord_line, lyric_line

def process_song_text(text):
    highlight_chords(text)
    lines = text.split('\n')
    processed = [split_chord_lyric_line(line) for line in lines if line.strip()]
    return processed

def get_key_preference(key: str) -> str:
    """Returns 'sharp' or 'flat' based on key signature."""
    sharp_keys = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#']
    flat_keys  = ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb']
    root = key.split()[0]  # e.g. 'D major' → 'D'
    return 'sharp' if root in sharp_keys else 'flat'