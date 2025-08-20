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

def split_chord_lyric_line(line):
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

    return chord_line, lyric_line

def process_song_text(text):
    lines = text.split('\n')
    processed = [split_chord_lyric_line(line) for line in lines if line.strip()]
    return processed