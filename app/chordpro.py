"""ChordPro in and out.

Sheets in this app are already inline ``[C]lyric`` lines, which is the
ChordPro lyric line. Directives such as ``{title: ...}`` are extra.
"""
import re

from .utils import normalise_spacing

_DIRECTIVE_RE = re.compile(r'^\{([A-Za-z0-9_-]+)\s*:\s*(.*)\}$')
_BARE_RE = re.compile(r'^\{([A-Za-z0-9_-]+)\}$')
_COMMENT_KEYS = {'comment', 'c', 'comment_italic', 'ci', 'comment_box', 'cb'}
_CHORUS_START = {'soc', 'start_of_chorus'}
_CHORUS_END = {'eoc', 'end_of_chorus'}


def parse_chordpro(text):
    """Return title, artist, key, capo and sheet text in app format."""
    meta = {'title': '', 'artist': '', 'key': '', 'capo': None}
    body = []
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if line.startswith('{') and line.endswith('}'):
            bare = _BARE_RE.match(line)
            if bare:
                key = bare.group(1).lower()
                if key in _CHORUS_START:
                    body.append('[Chorus]')
                continue
            match = _DIRECTIVE_RE.match(line)
            if match:
                key = match.group(1).lower()
                value = match.group(2).strip()
                if key in ('title', 't') and value:
                    meta['title'] = value
                elif key == 'artist' and value:
                    meta['artist'] = value
                elif key in ('subtitle', 'st') and value and not meta['artist']:
                    meta['artist'] = value
                elif key == 'key' and value:
                    meta['key'] = value
                elif key == 'capo' and value:
                    try:
                        meta['capo'] = max(0, min(12, int(value)))
                    except ValueError:
                        pass
                elif key in _CHORUS_START:
                    body.append('[Chorus]')
                elif key in _CHORUS_END or key in _COMMENT_KEYS:
                    continue
                continue
        body.append(raw_line.rstrip())
    return {
        'title': meta['title'],
        'artist': meta['artist'],
        'key': meta['key'],
        'capo': meta['capo'],
        'content': normalise_spacing('\n'.join(body)),
    }


def to_chordpro(title='', artist='', key='', content='', capo=None):
    """Build a ChordPro document from an app sheet."""
    lines = []
    if title:
        lines.append('{title: %s}' % title)
    if artist:
        lines.append('{artist: %s}' % artist)
    if key:
        lines.append('{key: %s}' % key)
    if capo:
        lines.append('{capo: %s}' % int(capo))
    if lines:
        lines.append('')
    lines.append(content or '')
    return '\n'.join(lines)
