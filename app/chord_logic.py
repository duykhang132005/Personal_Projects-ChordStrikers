"""Transposing and chord simplifying.

The same rules live in static/js/chord_tools.js (the page has to work
offline). tests/test_sheet_tools.py checks both.
"""
import re

SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
_CHORD_RE = re.compile(r'^([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?$')
_TOKEN_RE = re.compile(r'\[[^\]]+\]')


def shift_note(note, steps, prefer='sharp'):
    if note in SHARP:
        index = SHARP.index(note)
    elif note in FLAT:
        index = FLAT.index(note)
    else:
        return note
    scale = FLAT if prefer == 'flat' else SHARP
    return scale[(index + steps) % 12]


def _split(name):
    match = _CHORD_RE.match((name or '').strip())
    if not match:
        return None
    return match.group(1), match.group(2) or '', match.group(3) or ''


def simplify_quality(quality):
    text = quality or ''
    text = re.sub(r'sus\d*', '', text)
    text = re.sub(r'add\d+', '', text)
    text = re.sub(r'[#b]\d+', '', text)

    def _keep(match):
        qual = match.group(1)
        if qual in ('m', 'min'):
            return 'm'
        if qual == 'dim':
            return 'dim'
        if qual == 'aug':
            return 'aug'
        return ''

    text = re.sub(r'(maj|min|m|dim|aug|M)?\d+', _keep, text)
    text = text.replace('min', 'm').replace('maj', '').replace('M', '')
    return text


def simplify_chord(name):
    parts = _split(name)
    if parts is None:
        return name
    root, quality, bass = parts
    quality = simplify_quality(quality)
    return root + quality + (('/' + bass) if bass else '')


def transpose_chord(name, steps, prefer='sharp'):
    parts = _split(name)
    if parts is None:
        return name
    root, quality, bass = parts
    shown = shift_note(root, steps, prefer) + quality
    if bass:
        shown += '/' + shift_note(bass, steps, prefer)
    return shown


def transform_text(text, steps=0, prefer='sharp', simplify=False):
    prefer = 'flat' if prefer == 'flat' else 'sharp'

    def _one(match):
        name = match.group(0)[1:-1]
        shown = transpose_chord(name, steps, prefer)
        if simplify:
            shown = simplify_chord(shown)
        return '[' + shown + ']'

    return _TOKEN_RE.sub(_one, text or '')
