# ChordStrikers

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Framework](https://img.shields.io/badge/framework-Flask-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

**ChordStrikers** is an interactive, open-source web application for transcribing, reading, transposing, and practicing musical chord sheets without paywalls or ad clutter.

**Demo (read-only):** [https://duykhang132005.github.io/Personal_Projects-ChordStrikers/](https://duykhang132005.github.io/Personal_Projects-ChordStrikers/)

The GitHub Pages site is a static browse/view demo (search, transpose, auto-scroll, print/download). Creating and editing songs still requires the local Flask app (`python run.py`).

---

## Key Features

- **Smart Bracketed Chord Parser**  
  Parses inline chords like `[C]`, `[Am7]`, `[F#/A#]` into aligned chord/lyric layers.

- **Real-time Transposition**  
  Shift any song by semitones (`-11` to `+11`) with automatic sharp/flat preference handling.

- **Adaptive Multi-Column Layout**  
  Dynamically measures monospace font widths and screen boundaries to fit sheets into single or multi-column layouts.

- **Interactive Chord Tooltips**  
  Hover or tap to view guitar fingering diagrams.

- **Auto-Scrolling**  
  Adjustable hands-free scrolling for practice sessions.

- **iTunes Artwork Search**  
  Fetches album cover art via the public iTunes Search API (no API key required).

- **Print & Plain Text Export**  
  One-click printable PDF styling and raw text downloads.

- **YouTube Backing Track Integration**  
  Quick search links for practicing alongside recordings or backing tracks.

---

## Repository Structure

```text
ChordStrikers/
├── app/                    # Flask application package
│   ├── routes/             # Blueprint routes (main.py, creator.py)
│   ├── storage.py          # Shared song text file I/O
│   ├── parsing.py          # Legacy text parser helpers
│   ├── utils.py            # Chord splitting, transposition, iTunes cover fetch
│   └── config.py           # App configuration
├── demo/                   # Static GitHub Pages demo source
│   ├── catalog.json        # Fallback song metadata when songs.db is absent
│   ├── index.html
│   ├── css/demo.css
│   └── js/
├── docs/                   # Developer documentation
│   └── chord_format_guide.md
├── scripts/                # Demo export + static site build
│   ├── export_demo.py
│   └── build_demo.py
├── static/                 # CSS, JS, images, sample chord files
│   ├── styles.css
│   ├── js/view_sheet.js
│   └── data/
├── templates/              # Jinja2 templates (local Flask app)
├── tests/                  # Pytest suite
├── .github/                # CI + Pages deploy workflows
├── package.json            # npm run build → static site/
├── requirements.txt
├── run.py
└── LICENSE
```

---

## Quickstart & Setup

### 1. Prerequisites
- **Python 3.10+**
- Git

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/duykhang132005/Personal_Projects-ChordStrikers.git
cd Personal_Projects-ChordStrikers

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Cover art is fetched automatically from iTunes when you leave the image URL blank. No API keys are required.

### 5. Initialize Database & Run
```bash
python run.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

Startup creates any missing SQLite tables (`songs`) automatically via SQLAlchemy `create_all` and does not wipe existing rows. Restart the app after model changes so new tables or columns that `create_all` can add are applied. Chord sheets are stored as `static/data/{song_id}.txt` (or `SONG_DATA_DIR`) and must match `songs.id`. On startup the app removes sheet files whose ids are not in the database, and deletes song rows that have no matching sheet file.

The local Flask app is unchanged: create, edit, and your `instance/songs.db` workflow stay here. The Pages demo does not replace it.

---

## GitHub Pages demo

The public site is generated from `instance/songs.db` (when present) plus matching `static/data/{id}.txt` files. If the database is missing — as it is on GitHub, because `instance/*.db` is gitignored — the build uses `demo/catalog.json` and still skips any id without a sheet file.

```bash
# Requires the Python dependencies from requirements.txt
npm run build
# or: python scripts/build_demo.py --base-path /Personal_Projects-ChordStrikers/
```

This writes a static site to `site/` (gitignored). Preview locally:

```bash
python scripts/build_demo.py --base-path /
python -m http.server --directory site 8080
```

Then open `http://127.0.0.1:8080`.

Pushes to `main` build and deploy via [`.github/workflows/pages.yml`](.github/workflows/pages.yml) (`actions/upload-pages-artifact` + `actions/deploy-pages`), using the project base path `/Personal_Projects-ChordStrikers/`. `index.html` is copied to `404.html` so deep links into the SPA still load.

**Enable Pages once:** GitHub repo → **Settings** → **Pages** → **Source** = **GitHub Actions**.

The demo is read-only: Explore (client-side filter by title/artist/key) and View sheet (transpose, sharp/flat prefer, auto-scroll, columns, chord tooltips, print/download). There is no create/edit UI on Pages.

---

## Running Automated Tests

Run the full pytest suite:

```bash
pytest
```

---

## Chord Sheet Notation Guide

Chords should be wrapped in square brackets (`[...]`) directly before or inside lyrics:

```text
Verse 1:
[C]You are my sunshine, my [F]only sun[C]shine
You make me [F]happy when skies are [C]grey
```

For complete syntax details, see [docs/chord_format_guide.md](docs/chord_format_guide.md).

---

## Roadmap

- [x] Transposition & auto-scroll hands-free reading.
- [x] Multi-column dynamic screen layout.
- [x] Interactive chord fingering tooltips.
- [x] Print / PDF and Plain Text export.

---

## Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for details on submitting pull requests and running tests.

---

## License

This project is licensed under the [MIT License](LICENSE).
