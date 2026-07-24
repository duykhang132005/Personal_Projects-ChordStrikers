# 🎸 ChordStrikers

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Framework](https://img.shields.io/badge/framework-Flask-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

> **ChordStrikers** is an interactive, open-source web application designed for transcribing, reading, transposing, and practicing musical chord sheets without paywalls or ad clutter.

---

## ✨ Key Features

- 🎵 **Smart Bracketed Chord Parser**: Parses inline brackets like `[C]`, `[Am7]`, `[F#/A#]` into dedicated, perfectly aligned chord and lyric display layers.
- 🎹 **Real-time Transposition**: Transpose any song up or down by semitones (`-11` to `+11`) on the fly, with automated sharp (`♯`) and flat (`♭`) accidental preferences.
- 📐 **Adaptive Multi-Column Layout**: Dynamically measures monospace font widths and screen boundaries to fit song sheets onto single or multi-column layouts without line wrapping.
- 🎸 **Interactive Chord Tooltips**: Hover or tap on any chord to inspect guitar fingering patterns.
- 📜 **Auto-Scrolling**: Practice hands-free with adjustable auto-scroll speed controls.
- 🖼 **Spotify API Artwork Search**: Auto-fetches high-resolution album or artist artwork for song sheets using Spotipy.
- 🖨 **Print & Plain Text Export**: One-click printable PDF styling and raw text file downloads.
- 🎵 **YouTube Backing Track Embed**: Quick search link to practice alongside original recordings or backing tracks.

---

## 📁 Repository Structure

```text
ChordStrikers/
├── app/                    # Flask Application Package
│   ├── routes/             # Blueprint routes (main.py, creator.py)
│   ├── models.py           # SQLAlchemy database models (Song)
│   ├── parsing.py          # Legacy text parser helpers
│   ├── utils.py            # Main chord line splitter, transposition, & Spotipy logic
│   └── config.py           # App configuration settings
├── docs/                   # Developer & formatting documentation
│   └── chord_format_guide.md
├── static/                 # Static assets (CSS, JS, images, sample chord files)
│   ├── css/styles.css      # Core design system & print styles
│   ├── js/view_sheet.js    # Client-side transposition, auto-scroll, & tooltips
│   └── data/               # Song text files
├── templates/              # Jinja2 HTML templates
│   ├── home.html           # Landing page & creator intro
│   ├── explore.html        # Song library & key filter
│   ├── view_sheet.html     # Interactive chord sheet viewer
│   ├── creator.html        # Song creation form
│   └── edit_sheet.html     # Song editing form
├── tests/                  # Pytest test suite
│   ├── conftest.py         # Pytest fixtures
│   ├── test_utils.py       # Unit tests for parser and transposition
│   └── test_routes.py      # Integration tests for Flask routes
├── .env.example            # Environment variables template
├── .github/                # GitHub Actions CI & issue templates
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Testing & development dependencies
├── run.py                  # Application entrypoint
└── LICENSE                 # MIT License
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
*(Optional)* Add your Spotify Client ID & Secret to enable automatic artist and album cover fetching.

### 5. Initialize Database & Run
```bash
python run.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

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
