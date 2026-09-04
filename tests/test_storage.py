import os
import inspect

from app import db, storage
from app.models import Song
from app.routes import main as main_routes
from app.routes import creator as creator_routes
from app.storage import (
    get_song_filepath,
    save_song_content,
    load_song_content,
    delete_song_file,
    list_sheet_ids,
    orphan_sheet_ids,
    purge_orphan_sheets,
    orphan_db_ids,
    purge_orphan_song_rows,
    purge_unsynced_songs_and_sheets,
)


def test_storage_roundtrip(app):
    with app.app_context():
        save_song_content(99, '[C]Hello')
        filepath = get_song_filepath(99)
        assert os.path.isfile(filepath)
        assert os.path.abspath(app.config['SONG_DATA_DIR']) in filepath
        assert load_song_content(99) == '[C]Hello'
        delete_song_file(99)
        assert load_song_content(99) == ''
        assert not os.path.isfile(filepath)


def test_load_song_content_missing_file(app):
    with app.app_context():
        assert load_song_content(12345) == ''


def test_list_sheet_ids_ignores_non_numeric_names(app):
    with app.app_context():
        save_song_content(1, '[C]One')
        save_song_content(12, '[G]Twelve')
        data_dir = app.config['SONG_DATA_DIR']
        with open(os.path.join(data_dir, 'notes.txt'), 'w', encoding='utf-8') as f:
            f.write('not a sheet')
        with open(os.path.join(data_dir, 'readme.md'), 'w', encoding='utf-8') as f:
            f.write('# notes')
        assert list_sheet_ids() == [1, 12]


def test_purge_orphan_sheets_deletes_only_unknown_ids(app):
    with app.app_context():
        save_song_content(1, '[C]Keep')
        save_song_content(2, '[G]Keep too')
        save_song_content(99, '[D]Orphan')
        data_dir = app.config['SONG_DATA_DIR']
        notes_path = os.path.join(data_dir, 'notes.txt')
        with open(notes_path, 'w', encoding='utf-8') as f:
            f.write('leave me')

        assert orphan_sheet_ids({1, 2}) == [99]
        deleted = purge_orphan_sheets({1, 2})
        assert deleted == [99]
        assert load_song_content(1) == '[C]Keep'
        assert load_song_content(2) == '[G]Keep too'
        assert load_song_content(99) == ''
        assert not os.path.isfile(get_song_filepath(99))
        assert os.path.isfile(notes_path)
        assert purge_orphan_sheets({1, 2}) == []


def test_purge_orphan_song_rows_deletes_songs_without_sheets(app):
    with app.app_context():
        keep = Song.query.filter_by(title='Test Song').first()
        save_song_content(keep.id, '[C]Keep')
        leftover = Song(title='Leftover', artist='Test', song_key='C')
        db.session.add(leftover)
        db.session.commit()
        leftover_id = leftover.id
        keep_id = keep.id
        assert leftover_id not in list_sheet_ids()
        assert orphan_db_ids([keep_id, leftover_id]) == [leftover_id]

        deleted = purge_orphan_song_rows()
        assert leftover_id in deleted
        assert keep_id not in deleted
        assert db.session.get(Song, leftover_id) is None
        assert db.session.get(Song, keep_id) is not None
        assert os.path.isfile(get_song_filepath(keep_id))
        assert purge_orphan_song_rows() == []


def test_purge_unsynced_songs_and_sheets_is_bidirectional(app):
    with app.app_context():
        keep = Song.query.filter_by(title='Test Song').first()
        save_song_content(keep.id, '[C]Keep')
        leftover = Song(title='No File', artist='X', song_key='G')
        db.session.add(leftover)
        db.session.commit()
        leftover_id = leftover.id
        keep_id = keep.id
        save_song_content(99, '[D]Orphan file')

        deleted_files, deleted_songs = purge_unsynced_songs_and_sheets()
        assert 99 in deleted_files
        assert leftover_id in deleted_songs
        assert keep_id not in deleted_songs
        assert not os.path.isfile(get_song_filepath(99))
        assert os.path.isfile(get_song_filepath(keep_id))
        assert db.session.get(Song, leftover_id) is None
        assert db.session.get(Song, keep_id) is not None
        assert purge_unsynced_songs_and_sheets() == ([], [])


def test_routes_use_shared_storage_helpers():
    assert main_routes.get_song_filepath is storage.get_song_filepath
    assert creator_routes.save_song_content is storage.save_song_content
    assert creator_routes.load_song_content is storage.load_song_content
    assert creator_routes.delete_song_file is storage.delete_song_file
    assert 'def get_song_filepath' not in inspect.getsource(main_routes)
    assert 'def get_song_filepath' not in inspect.getsource(creator_routes)
    assert 'def save_song_content' not in inspect.getsource(creator_routes)
    assert 'def load_song_content' not in inspect.getsource(creator_routes)
    assert 'def delete_song_file' not in inspect.getsource(creator_routes)
