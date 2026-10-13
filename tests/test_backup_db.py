"""Daily database backup script."""
import datetime
import importlib.util
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('backup_db', ROOT / 'scripts' / 'backup_db.py')
backup_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_db)


def make_db(path):
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT)')
    con.execute("INSERT INTO songs (title) VALUES ('Hello')")
    con.commit()
    return con


def test_path_matches_the_app():
    uri = backup_db.configured_uri()
    assert uri == 'sqlite:///songs.db'
    assert backup_db.resolve_db_path(uri) == ROOT / 'instance' / 'songs.db'
    absolute = backup_db.resolve_db_path('sqlite:////tmp/x/songs.db')
    assert absolute.as_posix().endswith('/tmp/x/songs.db')


def test_backup_is_a_readable_copy_while_open(tmp_path):
    db = tmp_path / 'songs.db'
    live = make_db(db)
    live.execute("INSERT INTO songs (title) VALUES ('Still open')")
    live.commit()
    target = backup_db.backup(db, tmp_path / 'backups', keep=7)
    live.close()
    assert backup_db.NAME_RE.match(target.name)
    copy = sqlite3.connect(target)
    rows = [r[0] for r in copy.execute('SELECT title FROM songs ORDER BY id')]
    copy.close()
    assert rows == ['Hello', 'Still open']
    assert not list((tmp_path / 'backups').glob('*.part'))


def test_keeps_only_the_newest_seven(tmp_path):
    db = tmp_path / 'songs.db'
    make_db(db).close()
    dest = tmp_path / 'backups'
    dest.mkdir()
    (dest / 'notes.txt').write_text('leave me')
    start = datetime.datetime(2026, 1, 1, 3, 0, 0)
    made = [backup_db.backup(db, dest, keep=7, now=start + datetime.timedelta(days=i)) for i in range(10)]
    left = sorted(p.name for p in dest.glob('songs-*.db'))
    assert left == sorted(p.name for p in made[-7:])
    assert (dest / 'notes.txt').exists()


def test_missing_database_is_an_error(tmp_path):
    with pytest.raises(SystemExit):
        backup_db.backup(tmp_path / 'nope.db', tmp_path / 'b')


def test_cli(tmp_path, capsys):
    db = tmp_path / 'songs.db'
    make_db(db).close()
    assert backup_db.main(['--db', str(db), '--dest', str(tmp_path / 'out'), '--keep', '2']) == 0
    assert 'Backed up' in capsys.readouterr().out
    assert len(list((tmp_path / 'out').glob('songs-*.db'))) == 1


def test_backups_folder_is_ignored():
    ignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
    assert 'backups/' in ignore.splitlines()
