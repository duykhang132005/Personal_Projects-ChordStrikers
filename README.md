# ChordStrikers

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Framework](https://img.shields.io/badge/framework-Flask-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**ChordStrikers** is a free chord sheet app for musicians. Write songs with chords inline, then read, transpose and practice them on your phone or computer, with no paywalls or ads. Vietnamese lyrics display properly, and search ignores accents, so a plain spelling still finds a Vietnamese title.

**Try it live:** [duykhang132005.pythonanywhere.com](https://duykhang132005.pythonanywhere.com)

---

## Features

### Find songs
- **Explore** with three tabs: *Your scores*, *Your favorites* and the *Entire library*.
- **Search** by song or artist, author username, or key. Accents are optional.
- **Sort** A to Z or Newest.
- Album cover art fetched automatically from iTunes (no API key needed).

### Read and play
- **Transpose** up or down by semitones, with a sharp or flat preference.
- **Simplify** turns chords like `Cmaj7` or `F#m7/C#` into easy ones (`C`, `F#m/C#`).
- **Chord diagrams**: tap or hover a chord to see a guitar fret diagram.
- **Adaptive layout** fits a sheet into one or several columns, with bigger or smaller text (A- / A+). Reset puts the transpose and text size back to the original.
- **Autoscroll** with adjustable speed.
- **Perform mode**: a big, clean view that starts autoscrolling right away and keeps the screen awake. Change the scroll speed with - and +, use Pause, Back and Ahead, or tap the sheet to pause.
- **Practice tools**: a metronome with tap tempo, and a microphone tuner.
- **Backing track** link that searches YouTube for the song.

### Keep and share
- **Offline favorites**: star a sheet (Save offline) and it opens even with bad or no signal.
- **Share links** keep your transpose, sharps/flats and simplify choices, using your phone's share menu or a copied link.
- **Print / Export PDF** and **Plain Text** download.
- Your transpose, simplify, text size and scroll speed are remembered per song on your device.

### Write
- **Classic editor**: type lyrics with chords in brackets, like `[C]You are my [F]sunshine`.
- **Touch editor** for phones: tap a word and drop a chord on it.

### Make it yours
- **Accounts**: register, sign in, change your password.
- **Color themes**: Default, Wooden and Limelight, picked in the Account card and saved on your device.

---

## Install it on your phone

ChordStrikers can be installed like an app (it is a PWA). Open the [live site](https://duykhang132005.pythonanywhere.com), then:

- **iPhone or iPad (Safari):** tap Share, then **Add to Home Screen**.
- **Android (Chrome):** open the menu, then **Install app** or **Add to Home screen**.

It then opens full screen from your home screen. Sign in and star a few sheets so they are ready offline. On iPhone, the installed app often cannot use the microphone; if the tuner is blocked, open the page in Safari instead.

---

## Run it locally

You need **Python 3.10+** and Git.

```bash
git clone https://github.com/duykhang132005/Personal_Projects-ChordStrikers.git
cd Personal_Projects-ChordStrikers

python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create your settings file and give it a secret key:

```bash
cp .env.example .env          # Windows: copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Open `.env` and replace `your_random_secret_key_here` with the key you just printed. The app will not start without a real `SECRET_KEY`. To create an admin account on a fresh database, you can also set `BOOTSTRAP_ADMINS=yourname:temporary-password` (or just use **Register** in the app).

Start the app:

```bash
python run.py
```

Open http://127.0.0.1:5000. The SQLite database (`instance/songs.db`) and its tables are created on first start.

### Run the tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

---

## Writing chord sheets

Put each chord in square brackets right before the syllable it falls on:

```text
Verse 1:
[C]You are my sunshine, my [F]only sun[C]shine
You make me [F]happy when skies are [C]grey
```

See the [chord format guide](docs/chord_format_guide.md) for the full syntax.

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit pull requests and run tests.

Hosting, deploying, backups and other maintainer notes are in [docs/MAINTAINING.md](docs/MAINTAINING.md).

## License

This project is licensed under the [MIT License](LICENSE).
