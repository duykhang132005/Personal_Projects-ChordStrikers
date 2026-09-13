#!/usr/bin/env python3
"""Export song metadata + processed sheets for the static Pages demo.

Prefers ``instance/songs.db`` when present, otherwise ``demo/catalog.json``.
Sheet files that are missing are skipped so a partial library still builds.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils import prepare_song, sanitize_image_url  # noqa: E402

DEFAULT_DB = ROOT / "instance" / "songs.db"
DEFAULT_SHEETS = ROOT / "static" / "data"
DEFAULT_CATALOG = ROOT / "demo" / "catalog.json"
DEFAULT_OUT = ROOT / "site" / "data"


def _as_song(record) -> dict:
    if isinstance(record, sqlite3.Row):
        record = dict(record)
    return {
        "id": int(record["id"]),
        "title": record.get("title") or "",
        "artist": record.get("artist") or None,
        "song_key": record.get("song_key") or "",
        "image_url": sanitize_image_url(record.get("image_url")),
    }


def load_songs_from_db(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, title, artist, song_key, image_url FROM songs ORDER BY id"
        ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Could not read songs from {db_path}: {exc}") from exc
    finally:
        conn.close()
    return [_as_song(row) for row in rows]


def load_songs_from_catalog(catalog_path: Path) -> list[dict]:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    records = payload.get("songs", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise RuntimeError(f"Catalog {catalog_path} must be a list or {{'songs': [...]}}")
    return [_as_song(record) for record in records]


def resolve_song_records(db_path: Path, catalog_path: Path) -> tuple[list[dict], str]:
    if db_path.is_file():
        return load_songs_from_db(db_path), f"sqlite:{db_path}"
    if catalog_path.is_file():
        return load_songs_from_catalog(catalog_path), f"catalog:{catalog_path}"
    raise FileNotFoundError(
        f"No song source found. Expected {db_path} or fallback {catalog_path}."
    )


def export_songs(
    *,
    db_path: Path = DEFAULT_DB,
    sheets_dir: Path = DEFAULT_SHEETS,
    catalog_path: Path = DEFAULT_CATALOG,
    out_dir: Path = DEFAULT_OUT,
) -> dict:
    records, source = resolve_song_records(db_path, catalog_path)
    songs_dir = out_dir / "songs"
    songs_dir.mkdir(parents=True, exist_ok=True)

    exported = []
    skipped = []

    for record in records:
        song_id = record["id"]
        sheet_path = sheets_dir / f"{song_id}.txt"
        if not sheet_path.is_file():
            skipped.append(song_id)
            continue

        raw_text = sheet_path.read_text(encoding="utf-8")
        processed = prepare_song(raw_text, add_data_attr=True)
        lines = [{"chord": str(chord), "lyric": str(lyric)} for chord, lyric in processed]

        full = {
            **record,
            "raw_text": raw_text,
            "lines": lines,
        }
        (songs_dir / f"{song_id}.json").write_text(
            json.dumps(full, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        exported.append({key: record[key] for key in ("id", "title", "artist", "song_key", "image_url")})

    index = {
        "source": source,
        "count": len(exported),
        "skipped_ids": skipped,
        "songs": exported,
    }
    (out_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sheets", type=Path, default=DEFAULT_SHEETS)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    index = export_songs(
        db_path=args.db,
        sheets_dir=args.sheets,
        catalog_path=args.catalog,
        out_dir=args.out,
    )
    print(
        f"Exported {index['count']} songs from {index['source']} "
        f"(skipped {len(index['skipped_ids'])}: {index['skipped_ids']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
