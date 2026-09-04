import pytest
import os
import shutil
import tempfile
from app import create_app, db
from app.models import Song
from app.storage import save_song_content

@pytest.fixture
def app():
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    song_dir = tempfile.mkdtemp()
    
    app = create_app()
    app.config.update({
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

    os.close(db_fd)
    os.unlink(db_path)
    shutil.rmtree(song_dir, ignore_errors=True)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
