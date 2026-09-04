import os
import inspect

from app import storage
from app.routes import main as main_routes
from app.routes import creator as creator_routes
from app.storage import (
    get_song_filepath,
    save_song_content,
    load_song_content,
    delete_song_file,
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
