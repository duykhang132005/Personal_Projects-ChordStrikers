"""Make a consistent copy of the SQLite database and keep the newest 7.

Run from anywhere:
    python scripts/backup_db.py
    python scripts/backup_db.py --keep 7 --dest /path/to/backups

The copy uses sqlite3's online backup API, so it is safe while the app is
running and writing. Standard library only.

The database path is found the same way the app finds it: the
SQLALCHEMY_DATABASE_URI in app/config.py (or a TEST/override passed with
--db). Flask-SQLAlchemy resolves a relative sqlite:/// path inside the
Flask instance folder, which is <project>/instance, so sqlite:///songs.db
means <project>/instance/songs.db. That holds on PythonAnywhere too
(~/Personal_Projects-ChordStrikers/instance/songs.db).
"""
import argparse
import datetime
import os
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEEP = 7
PREFIX = 'songs-'
SUFFIX = '.db'
NAME_RE = re.compile(r'^songs-\d{8}-\d{6}\.db$')


def configured_uri(project_root=PROJECT_ROOT):
    """Read SQLALCHEMY_DATABASE_URI from app/config.py without importing the app."""
    config_file = Path(project_root) / 'app' / 'config.py'
    text = config_file.read_text(encoding='utf-8')
    match = re.search(r'SQLALCHEMY_DATABASE_URI\s*=\s*["\']([^"\']+)["\']', text)
    if not match:
        raise SystemExit('Could not find SQLALCHEMY_DATABASE_URI in ' + str(config_file))
    return match.group(1)


def resolve_db_path(uri, project_root=PROJECT_ROOT):
    """Turn a sqlite URI into a file path, the way Flask-SQLAlchemy does."""
    if not uri.startswith('sqlite:///'):
        raise SystemExit('Only SQLite databases can be backed up by this script: ' + uri)
    raw = uri[len('sqlite:///'):].split('?', 1)[0]
    if not raw or raw == ':memory:':
        raise SystemExit('In-memory databases cannot be backed up.')
    path = Path(raw)
    if not path.is_absolute():
        path = Path(project_root) / 'instance' / path
    return path


def backup(db_path, dest_dir, keep=DEFAULT_KEEP, now=None):
    """Copy db_path into dest_dir with a timestamped name, then prune old copies.

    Returns the path of the new backup.
    """
    db_path = Path(db_path)
    if not db_path.is_file():
        raise SystemExit('Database not found: ' + str(db_path))
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.datetime.now()).strftime('%Y%m%d-%H%M%S')
    target = dest_dir / (PREFIX + stamp + SUFFIX)
    partial = target.with_name(target.name + '.part')
    if partial.exists():
        partial.unlink()

    source = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        copy = sqlite3.connect(str(partial))
        try:
            source.backup(copy)
            check = copy.execute('PRAGMA quick_check').fetchone()[0]
        finally:
            copy.close()
    finally:
        source.close()
    if check != 'ok':
        partial.unlink()
        raise SystemExit('Backup failed its integrity check: ' + str(check))
    os.replace(partial, target)
    prune(dest_dir, keep)
    return target


def prune(dest_dir, keep=DEFAULT_KEEP):
    """Delete all but the newest `keep` backups. Other files are left alone."""
    keep = max(1, int(keep))
    copies = sorted(p for p in Path(dest_dir).iterdir() if p.is_file() and NAME_RE.match(p.name))
    removed = []
    for old in copies[:-keep]:
        old.unlink()
        removed.append(old)
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(description='Back up the ChordStrikers SQLite database.')
    parser.add_argument('--db', help='Database file (default: from app/config.py)')
    parser.add_argument('--dest', default=str(PROJECT_ROOT / 'backups'), help='Backup folder')
    parser.add_argument('--keep', type=int, default=DEFAULT_KEEP, help='How many copies to keep')
    args = parser.parse_args(argv)
    db_path = Path(args.db) if args.db else resolve_db_path(configured_uri())
    target = backup(db_path, args.dest, args.keep)
    print('Backed up', db_path, 'to', target)
    return 0


if __name__ == '__main__':
    sys.exit(main())
