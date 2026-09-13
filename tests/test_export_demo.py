import json
import sqlite3
from pathlib import Path

from app.utils import prepare_song, sanitize_image_url
from scripts.export_demo import export_songs, load_songs_from_catalog


def _write_db(path: Path, rows):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            artist VARCHAR(100),
            song_key VARCHAR(100) NOT NULL,
            image_url VARCHAR(512)
        )
        """
    )
    conn.executemany(
        "INSERT INTO songs (id, title, artist, song_key, image_url) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_export_from_db_skips_missing_sheets(tmp_path):
    db_path = tmp_path / "songs.db"
    sheets = tmp_path / "sheets"
    sheets.mkdir()
    out = tmp_path / "data"
    _write_db(
        db_path,
        [
            (1, "Has Sheet", "Artist", "C", "https://i.scdn.co/image/abc"),
            (2, "Missing Sheet", "Artist", "G", "https://i.scdn.co/image/def"),
        ],
    )
    (sheets / "1.txt").write_text("[C]Hello world\n", encoding="utf-8")

    index = export_songs(db_path=db_path, sheets_dir=sheets, out_dir=out)

    assert index["count"] == 1
    assert index["skipped_ids"] == [2]
    assert index["songs"][0]["title"] == "Has Sheet"
    assert index["songs"][0]["image_url"] == "https://i.scdn.co/image/abc"

    song = json.loads((out / "songs" / "1.json").read_text(encoding="utf-8"))
    expected = [{"chord": str(c), "lyric": str(l)} for c, l in prepare_song("[C]Hello world\n", add_data_attr=True)]
    assert song["lines"] == expected
    assert 'data-chord="[C]"' in song["lines"][0]["chord"]


def test_export_falls_back_to_catalog(tmp_path):
    sheets = tmp_path / "sheets"
    sheets.mkdir()
    (sheets / "9.txt").write_text("Chorus:\n[G]Hi\n", encoding="utf-8")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "songs": [
                    {
                        "id": 9,
                        "title": "Catalog Song",
                        "artist": "Someone",
                        "song_key": "G",
                        "image_url": "javascript:alert(1)",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    index = export_songs(
        db_path=tmp_path / "missing.db",
        sheets_dir=sheets,
        catalog_path=catalog,
        out_dir=tmp_path / "data",
    )

    assert index["count"] == 1
    assert index["source"].startswith("catalog:")
    assert index["songs"][0]["image_url"] is None
    assert sanitize_image_url("javascript:alert(1)") is None


def test_committed_catalog_is_valid():
    catalog = Path("demo/catalog.json")
    songs = load_songs_from_catalog(catalog)
    assert len(songs) >= 1
    assert all("id" in song and "title" in song for song in songs)
