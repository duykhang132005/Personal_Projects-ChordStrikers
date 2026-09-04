# ChordStrikers

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Framework](https://img.shields.io/badge/framework-Flask-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

**ChordStrikers** is an interactive, open-source web application for transcribing, reading, transposing, and practicing musical chord sheets without paywalls or ad clutter.

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
├── docs/                   # Developer documentation
│   └── chord_format_guide.md
├── static/                 # CSS, JS, images, sample chord files
│   ├── css/styles.css
│   ├── js/view_sheet.js
│   └── data/
├── templates/              # Jinja2 templates
│   ├── home.html
│   ├── explore.html
│   ├── view_sheet.html
│   ├── creator.html
│   └── edit_sheet.html
├── tests/                  # Pytest suite
│   ├── conftest.py
│   ├── test_utils.py
│   └── test_routes.py
├── .env.example
├── .github/                # CI workflows and issue templates
├── requirements.txt
├── requirements-dev.txt
├── run.py
└── LICENSE
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- **Python 3.10+**
- Git

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/duykhang132005/ChordStrikers.git
cd ChordStrikers

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

Startup creates any missing SQLite tables (`songs`) automatically and does not wipe existing rows. If Explore or Creator 500s with `no such table: songs` on an older checkout, restart the app so that create runs (or `flask db upgrade` if you manage schema only via Alembic).

---

## 🧪 Running Automated Tests

Run the full pytest suite:

```bash
pytest
```

---

## 📘 Chord Sheet Notation Guide

Chords should be wrapped in square brackets (`[...]`) directly before or inside lyrics:

```text
Verse 1:
[C]You are my sunshine, my [F]only sun[C]shine
You make me [F]happy when skies are [C]grey
```

For complete syntax details, see [docs/chord_format_guide.md](file:///c:/Users/khang/Desktop/Personal_Projects/ChordStrikers/docs/chord_format_guide.md).

---

## 🗺 Roadmap

- [x] Transposition & auto-scroll hands-free reading.
- [x] Multi-column dynamic screen layout.
- [x] Interactive chord fingering tooltips.
- [x] Print / PDF and Plain Text export.
- [ ] Ukulele & Mandolin alternate chord diagram modes.
- [ ] User accounts and personal playlist / favorite collections.
- [ ] Offline PWA support for live musical performances.

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](file:///c:/Users/khang/Desktop/Personal_Projects/ChordStrikers/CONTRIBUTING.md) for details on submitting pull requests and running tests.

---

## 📄 License

This project is licensed under the [MIT License](file:///c:/Users/khang/Desktop/Personal_Projects/ChordStrikers/LICENSE).
