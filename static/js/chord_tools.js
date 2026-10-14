/* Chord helpers shared by the sheet page and the editor.
 * Also loadable from Node (module.exports) so the suite can check it. */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ChordTools = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  var SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
  var FLAT = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
  var CHORD_RE = /^([A-G][#b]?)(.*?)(?:\/([A-G][#b]?))?$/;

  function shiftNote(note, steps, prefer) {
    var idx = SHARP.indexOf(note);
    if (idx === -1) idx = FLAT.indexOf(note);
    if (idx === -1) return note;
    var scale = prefer === 'flat' ? FLAT : SHARP;
    return scale[((idx + steps) % 12 + 12) % 12];
  }

  function splitChord(name) {
    var match = CHORD_RE.exec(String(name || '').trim());
    if (!match) return null;
    return { root: match[1], quality: match[2] || '', bass: match[3] || '' };
  }

  /* Drop extensions (7, maj7, sus, add9, and the rest) but keep minor,
   * dim, aug, and a slash bass note. */
  function simplifyQuality(quality) {
    var q = quality || '';
    q = q.replace(/sus\d*/g, '');
    q = q.replace(/add\d+/g, '');
    q = q.replace(/[#b]\d+/g, '');
    q = q.replace(/(maj|min|m|dim|aug|M)?\d+/g, function (_m, qual) {
      if (qual === 'm' || qual === 'min') return 'm';
      if (qual === 'dim') return 'dim';
      if (qual === 'aug') return 'aug';
      return '';
    });
    q = q.replace(/min/g, 'm').replace(/maj/g, '').replace(/M/g, '');
    return q;
  }

  function simplifyChord(name) {
    var parts = splitChord(name);
    if (!parts) return name;
    var quality = simplifyQuality(parts.quality);
    return parts.root + quality + (parts.bass ? '/' + parts.bass : '');
  }

  function transposeChord(name, steps, prefer) {
    var parts = splitChord(name);
    if (!parts) return name;
    var root = shiftNote(parts.root, steps, prefer);
    var bass = parts.bass ? '/' + shiftNote(parts.bass, steps, prefer) : '';
    return root + parts.quality + bass;
  }

  /* Rewrite every [Chord] in a sheet by the given transpose steps. */
  function transformText(text, options) {
    var opts = options || {};
    var steps = opts.steps || 0;
    var prefer = opts.prefer === 'flat' ? 'flat' : 'sharp';
    return String(text || '').replace(/\[[^\]]+\]/g, function (token) {
      var name = token.slice(1, -1);
      var shown = transposeChord(name, steps, prefer);
      if (opts.simplify) shown = simplifyChord(shown);
      return '[' + shown + ']';
    });
  }

  return {
    shiftNote: shiftNote,
    simplifyChord: simplifyChord,
    transposeChord: transposeChord,
    transformText: transformText
  };
});
