#!/usr/bin/env python3
"""Assemble the static GitHub Pages demo into ``site/``.

Copies the vanilla demo shell, existing ChordStrikers CSS/assets, exported
song JSON, and ``index.html`` → ``404.html`` so project-Pages deep links work.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_demo import export_songs  # noqa: E402

DEFAULT_BASE_PATH = os.environ.get("DEMO_BASE_PATH", "/")
DEFAULT_OUT = ROOT / "site"
STATIC_FILES = (
    "styles.css",
    "music_bg.png",
    "favicon.ico",
)


def normalize_base_path(base_path: str) -> str:
    value = (base_path or "/").strip() or "/"
    if not value.startswith("/"):
        value = "/" + value
    if not value.endswith("/"):
        value += "/"
    return value


def _replace_base_placeholders(text: str, base_path: str) -> str:
    return text.replace("__DEMO_BASE_PATH__", base_path)


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def build_demo(*, base_path: str = DEFAULT_BASE_PATH, out_dir: Path = DEFAULT_OUT) -> Path:
    base_path = normalize_base_path(base_path)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    demo_src = ROOT / "demo"
    html = (demo_src / "index.html").read_text(encoding="utf-8")
    (out_dir / "index.html").write_text(
        _replace_base_placeholders(html, base_path), encoding="utf-8"
    )
    shutil.copyfile(out_dir / "index.html", out_dir / "404.html")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    css_dest = out_dir / "css"
    js_dest = out_dir / "js"
    css_dest.mkdir()
    js_dest.mkdir()
    shutil.copyfile(demo_src / "css" / "demo.css", css_dest / "demo.css")
    for name in ("app.js", "prepare_song.js", "view_sheet.js"):
        shutil.copyfile(demo_src / "js" / name, js_dest / name)

    static_dest = out_dir / "static"
    static_dest.mkdir()
    for name in STATIC_FILES:
        src = ROOT / "static" / name
        if src.is_file():
            shutil.copyfile(src, static_dest / name)
    img_src = ROOT / "static" / "img"
    if img_src.is_dir():
        _copy_tree(img_src, static_dest / "img")

    index = export_songs(out_dir=out_dir / "data")
    print(f"Wrote static demo to {out_dir} with base path {base_path}")
    print(
        f"Songs: {index['count']} exported, "
        f"{len(index['skipped_ids'])} skipped ({index['skipped_ids']})"
    )
    return out_dir


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-path",
        default=DEFAULT_BASE_PATH,
        help="GitHub Pages project base path (default: env DEMO_BASE_PATH or /)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    build_demo(base_path=args.base_path, out_dir=args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
