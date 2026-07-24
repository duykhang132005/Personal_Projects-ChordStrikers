# 🎵 ChordStrikers Notation & Formatting Guide

`ChordStrikers` processes text-based chord sheets and converts them into beautifully aligned, transposable, multi-column chord sheets.

---

## 1. Chord Syntax

Chords should be enclosed in square brackets (`[...]`).

### Supported Chord Types
- **Basic Major / Minor**: `[C]`, `[Am]`, `[D]`
- **Sharps & Flats**: `[F#]`, `[Bb]`, `[G#m]`
- **7ths & Extended Chords**: `[G7]`, `[Cmaj7]`, `[Am7]`, `[Cadd9]`, `[Dsus4]`
- **Slash (Bass) Chords**: `[C/E]`, `[G/B]`, `[F#/A#]`
- **Diminished & Augmented**: `[Edim]`, `[Aaug]`, `[Bm7b5]`

### Example
```text
[C]You are my sunshine, my [F]only sun[C]shine
You make me [F]happy when skies are [C]grey
```

---

## 2. Section Keywords

Headers for song sections will automatically be highlighted and given distinct section styling.

### Recognized Keywords
- `Intro`
- `Verse` / `Verse 1` / `Verse 2`
- `Prechorus` / `Pre-chorus` / `Pre Chorus`
- `Chorus`
- `Bridge`
- `Melody`
- `Interlude`
- `Outro`

### Example
```text
Chorus:
[C]Singing ayo, [G]technology
[Am]Walk into the club, [F]what do I see
```

---

## 3. How Alignment Works

- The parser reads your song text line by line.
- When brackets `[Chord]` are detected inline with lyrics, the engine computes exact character positions.
- The lyrics form the baseline width, while chords are padded and elevated to an aligned chord layer above the lyrics.
- In **Sheet View**, clicking transpose (`+1` / `-1` / Sharp/Flat preference) instantly recalculates and updates all root and bass notes across the song.

---

## 4. Tips for Best Results
- Use standard monospace spacing when drafting sheets.
- Keep section headers on their own separate lines ending with a colon (e.g. `Verse 1:`).
- Place bracketed chords directly in front of the syllable where the chord change occurs.
