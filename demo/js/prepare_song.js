/**
 * Client-side port of app/utils.py prepare_song / highlight_chords.
 * Used at runtime when a song JSON has raw_text but no precomputed lines.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.ChordPrepare = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const BRACKETED_CHORD_REGEX =
    /(\[[A-G][#b]?(?:m|min|maj|sus|dim|aug|m7b5)?(?:\d+|add\d+)?(?:[#b]\d+)*(?:\/[A-G][#b]?)?\])/g;

  const SECTION_KEYWORDS = new Set(
    [
      "Intro",
      "Verse",
      "Melody",
      "Prechorus",
      "Pre-chorus",
      "Pre Chorus",
      "Chorus",
      "Interlude",
      "Outro",
      "Bridge",
    ].map((kw) => kw.toLowerCase())
  );

  const SHARP_KEYS = new Set(["C", "G", "D", "A", "E", "B", "F#", "C#"]);
  const FLAT_KEYS = new Set(["F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"]);

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&#34;")
      .replace(/'/g, "&#39;");
  }

  function normaliseSpacing(text) {
    const lines = String(text).split(/\r?\n/);
    const cleaned = [];
    for (const line of lines) {
      const stripped = line.replace(/[ \t]+$/g, "");
      if (stripped || (cleaned.length && cleaned[cleaned.length - 1])) {
        cleaned.push(stripped);
      }
    }
    return cleaned.join("\n");
  }

  function wrapChordSpan(chord, addDataAttr) {
    const escaped = escapeHtml(chord);
    if (addDataAttr) {
      return `<span class="chord" data-chord="${escaped}">${escaped}</span>`;
    }
    return `<span class="chord">${escaped}</span>`;
  }

  function highlightChords(text, addDataAttr) {
    const pieces = [];
    let pos = 0;
    const re = new RegExp(BRACKETED_CHORD_REGEX.source, "g");
    let match;
    while ((match = re.exec(text)) !== null) {
      pieces.push(escapeHtml(text.slice(pos, match.index)));
      pieces.push(wrapChordSpan(match[1], addDataAttr));
      pos = match.index + match[0].length;
    }
    pieces.push(escapeHtml(text.slice(pos)));
    return pieces.join("");
  }

  function splitChordLyricLine(line) {
    const strippedLine = line.trim();
    const words = strippedLine.split(/\s+/).filter(Boolean);
    if (words.length) {
      const firstWord = words[0].replace(/:+$/, "");
      if (SECTION_KEYWORDS.has(firstWord.toLowerCase())) {
        return [line.replace(/[ \t]+$/g, ""), ""];
      }
    }

    const chordParts = [];
    const lyricParts = [];
    let chordLen = 0;
    let lyricCol = 0;
    let i = 0;
    let lastWasSpace = false;

    function padChordsTo(targetCol) {
      const gap = targetCol - chordLen;
      if (gap > 0) {
        chordParts.push(" ".repeat(gap));
        chordLen += gap;
      }
    }

    while (i < line.length) {
      const char = line[i];
      if (char === "[") {
        const end = line.indexOf("]", i + 1);
        if (end !== -1) {
          const chord = line.slice(i, end + 1);
          padChordsTo(lyricCol);
          chordParts.push(chord);
          chordLen += chord.length;
          i = end + 1;
          continue;
        }
      }

      if (char === " ") {
        if (lastWasSpace) {
          i += 1;
          continue;
        }
        lastWasSpace = true;
      } else {
        lastWasSpace = false;
      }

      lyricParts.push(char);
      lyricCol += 1;
      i += 1;
    }

    return [chordParts.join("").replace(/[ \t]+$/g, ""), lyricParts.join("").replace(/[ \t]+$/g, "")];
  }

  function processSongText(text, addDataAttr) {
    const processed = [];
    for (const line of String(text).split("\n")) {
      if (!line.trim()) continue;
      let [chordLine, lyricLine] = splitChordLyricLine(line);
      if (!chordLine.trim().startsWith("<span")) {
        chordLine = highlightChords(chordLine, addDataAttr);
      }
      processed.push({ chord: chordLine, lyric: escapeHtml(lyricLine) });
    }
    return processed;
  }

  function prepareSong(text, addDataAttr) {
    return processSongText(normaliseSpacing(text), addDataAttr);
  }

  function getKeyPreference(key) {
    const root = String(key || "").split(/\s+/)[0];
    if (SHARP_KEYS.has(root)) return "sharp";
    if (FLAT_KEYS.has(root)) return "flat";
    return "sharp";
  }

  return {
    BRACKETED_CHORD_REGEX,
    escapeHtml,
    normaliseSpacing,
    highlightChords,
    splitChordLyricLine,
    processSongText,
    prepareSong,
    getKeyPreference,
  };
});
