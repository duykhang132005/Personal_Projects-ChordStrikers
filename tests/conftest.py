import pytest
import os
import shutil
import tempfile
from app import create_app, db
from app.models import Song
from app.storage import save_song_content


def _unlink_quietly(path):
    """Remove a file; ignore Windows lock races after engine dispose."""
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def app():
    # Create a temporary database file. Close the fd immediately so SQLite
    # is the only opener; otherwise Windows cannot unlink at teardown.
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    song_dir = tempfile.mkdtemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SONG_DATA_DIR': song_dir,
    })

    with app.app_context():
        db.create_all()
        # Seed test song without forcing explicit primary key
        sample_song = Song(
            title="Test Song",
            artist="Test Artist",
            song_key="C major"
        )
        db.session.add(sample_song)
        db.session.commit()
        save_song_content(sample_song.id, "[C]Hello world")
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    _unlink_quietly(db_path)
    shutil.rmtree(song_dir, ignore_errors=True)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
