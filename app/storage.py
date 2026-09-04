"""Song chord-sheet file I/O.

Contract: the canonical path for a song's sheet is always
``SONG_DATA_DIR/{id}.txt``, where ``{id}`` is the integer primary key
``songs.id``. Create, edit, load, and delete must use that same path so
the database row and the text file stay linked.
"""
import os
import re

from flask import current_app

_SHEET_NAME_RE = re.compile(r'^(\d+)\.txt$')


def get_data_folder():
    """Get the data folder path, using app config if available."""
    return current_app.config.get(
        'SONG_DATA_DIR',
        os.path.join(current_app.root_path, '..', 'static', 'data')
    )


def get_song_filepath(song_id):
    """Get the absolute filepath for a song's text file."""
    return os.path.abspath(os.path.join(get_data_folder(), f'{song_id}.txt'))


def save_song_content(song_id, content):
    """Save normalized song content to file."""
    filepath = get_song_filepath(song_id)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def load_song_content(song_id):
    """Load song content from file. Returns empty string if file not found."""
    filepath = get_song_filepath(song_id)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""


def delete_song_file(song_id):
    """Delete a song's text file if it exists."""
    filepath = get_song_filepath(song_id)
    if os.path.exists(filepath):
        os.remove(filepath)


def list_sheet_ids():
    """Return sorted integer ids for canonical ``{id}.txt`` sheets.

    Non-numeric filenames in the data folder are ignored.
    """
    folder = get_data_folder()
    if not os.path.isdir(folder):
        return []
    ids = []
    for name in os.listdir(folder):
        match = _SHEET_NAME_RE.fullmatch(name)
        if match:
            ids.append(int(match.group(1)))
    return sorted(ids)


def orphan_sheet_ids(valid_ids):
    """Return sheet file ids whose stem is not in ``valid_ids``."""
    valid = {int(song_id) for song_id in valid_ids}
    return [song_id for song_id in list_sheet_ids() if song_id not in valid]


def sheet_exists(song_id):
    """Return True if ``SONG_DATA_DIR/{id}.txt`` exists."""
    return os.path.isfile(get_song_filepath(song_id))


def purge_orphan_sheets(valid_ids):
    """Delete ``{id}.txt`` files whose id is not in ``valid_ids``.

    Idempotent: missing files and an empty/missing data folder are no-ops.
    Returns the list of deleted ids.
    """
    deleted = []
    for song_id in orphan_sheet_ids(valid_ids):
        delete_song_file(song_id)
        deleted.append(song_id)
    return deleted


def orphan_db_ids(song_ids):
    """Return ids from ``song_ids`` that have no matching ``{id}.txt`` file."""
    return sorted(int(song_id) for song_id in song_ids if not sheet_exists(song_id))


def purge_orphan_song_rows(song_ids=None):
    """Delete ``Song`` rows that have no matching sheet file.

    If ``song_ids`` is omitted, every row in ``songs`` is checked.
    Idempotent. Returns the list of deleted ids.
    """
    from . import db
    from .models import Song

    if song_ids is None:
        song_ids = [row[0] for row in db.session.query(Song.id).all()]
    stale_ids = orphan_db_ids(song_ids)
    if not stale_ids:
        return []
    for song_id in stale_ids:
        song = db.session.get(Song, song_id)
        if song is not None:
            db.session.delete(song)
    db.session.commit()
    return stale_ids


def purge_unsynced_songs_and_sheets():
    """Drop orphan sheet files and Song rows that do not share an id.

    1. Delete ``{id}.txt`` files whose stem is not a ``songs.id``.
    2. Delete ``Song`` rows that have no ``{id}.txt`` file.

    Idempotent. Returns ``(deleted_file_ids, deleted_song_ids)``.
    """
    from . import db
    from .models import Song

    db_ids = [row[0] for row in db.session.query(Song.id).all()]
    deleted_files = purge_orphan_sheets(db_ids)
    deleted_songs = purge_orphan_song_rows(db_ids)
    return deleted_files, deleted_songs
