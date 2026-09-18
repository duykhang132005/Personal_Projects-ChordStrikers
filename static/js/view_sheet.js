// ===== view_sheet.js =====

// --- Column layout handling ---
function updateColumnCount() {
  const container = document.querySelector('.song-content');
  if (!container) return;

  const lines = [...container.querySelectorAll('.line-block, .section-header')];
  if (!lines.length) return;

  const extraPadding = 5;

  // Measure longest line (chord or lyric)
  const longestLineLength = Math.max(...lines.map(line => {
    const chordLen = line.querySelector('.chord-line')?.textContent.length || 0;
    const lyricLen = line.querySelector('.lyric-line')?.textContent.length || 0;
    return Math.max(chordLen, lyricLen);
  }));

  // Measure monospace character width
  const testSpan = document.createElement('span');
  testSpan.textContent = 'M';
  testSpan.style.visibility = 'hidden';
  container.appendChild(testSpan);
  const charWidth = testSpan.getBoundingClientRect().width;
  container.removeChild(testSpan);

  const desiredColWidth = (longestLineLength + extraPadding) * charWidth;

  // Handle vertical mode
  if (container.classList.contains('vertical-mode')) {
    container.style.width = `${desiredColWidth}px`;
    container.style.marginLeft = 'auto';
    container.style.marginRight = 'auto';
    container.style.columnCount = 1;
    container.classList.add('single-column');
    container.classList.remove('multi-column');
    return;
  }

  // Determine column count based on container width
  const containerWidth = container.getBoundingClientRect().width;
  const MAX_COLS = 3;
  const colCount = Math.max(1, Math.min(MAX_COLS, Math.floor(containerWidth / desiredColWidth)));

  // NEW: Check vertical height to avoid splitting short songs
  const totalHeight = container.scrollHeight;
  const viewportHeight = window.innerHeight;
  const isTallEnough = totalHeight > viewportHeight * 0.8;

  const finalColCount = (colCount > 1 && isTallEnough) ? colCount : 1;

  container.style.columnCount = finalColCount;

  // Toggle layout classes and width
  if (finalColCount === 1) {
    container.classList.add('single-column');
    container.classList.remove('multi-column');
    container.style.width = `${desiredColWidth}px`;
    container.style.marginInline = 'auto';
  } else {
    container.classList.remove('single-column');
    container.classList.add('multi-column');
    container.style.width = '100%';
    container.style.marginInline = '';
  }
}

// Run on load and resize
window.addEventListener('load', updateColumnCount);
window.addEventListener('resize', updateColumnCount);

// --- Transposition + preference ---
let currentSteps = parseInt(window.initialSteps, 10) || 0;

const sharpNotes = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const flatNotes  = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];

function shift(note, steps, prefer) {
  let idx = sharpNotes.indexOf(note);
  if (idx === -1) idx = flatNotes.indexOf(note);
  if (idx === -1) return note;
  const toScale = prefer === 'flat' ? flatNotes : sharpNotes;
  return toScale[(idx + steps + 12) % 12];
}

function applyTransposition(steps, prefer) {
  document.querySelectorAll('.chord').forEach(el => {
    const orig = el.dataset.chord;
    if (!orig) return;

    el.textContent = orig.replace(/\[([A-G][#b]?)(.*?)(?:\/([A-G][#b]?))?\]/,
      (match, root, rest, bass) => {
        const newRoot = shift(root, steps, prefer);
        const newBass = bass ? '/' + shift(bass, steps, prefer) : '';
        return `[${newRoot}${rest || ''}${newBass}]`;
      }
    );
  });
}

function updateSteps(newSteps) {
  currentSteps = Math.max(-11, Math.min(11, newSteps));
  document.getElementById('steps').value = currentSteps;
  const preferVal = document.querySelector('.prefer-toggle input:checked')?.value || '';
  applyTransposition(currentSteps, preferVal);
}

// --- Event listeners ---
document.querySelectorAll('.transpose-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const delta = parseInt(btn.dataset.step, 10);
    updateSteps(currentSteps + delta);
  });
});

document.querySelectorAll('.prefer-toggle input').forEach(r => {
  r.addEventListener('change', () => {
    const preferVal = r.value;
    applyTransposition(currentSteps, preferVal);
  });
});

const stepsInput = document.getElementById('steps');

// Handle manual number entry on blur/change
stepsInput.addEventListener('change', e => {
  const parsed = parseInt(e.target.value.trim(), 10);
  updateSteps(isNaN(parsed) ? 0 : parsed);
});

stepsInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    const parsed = parseInt(e.target.value.trim(), 10);
    updateSteps(isNaN(parsed) ? 0 : parsed);
  }
});

document.querySelector('.transpose-reset').addEventListener('click', () => {
  updateSteps(0);
});

// --- Vertical mode toggle ---
document.getElementById('toggle-vertical').addEventListener('click', () => {
  const container = document.querySelector('.song-content');
  const btn = document.getElementById('toggle-vertical');
  const isVertical = container.classList.toggle('vertical-mode');
  btn.textContent = isVertical ? 'Switch to Multi-Column View' : 'Switch to Single Column View';
  if (!isVertical) {
  container.classList.remove('single-column');
  container.style.width = '';
  container.style.columnCount = '';
  container.style.marginLeft = '';
  container.style.marginRight = '';

  // Wait for layout to settle before recalculating
  requestAnimationFrame(() => updateColumnCount());
    } else {
    updateColumnCount();
    }
});

// --- Auto-scroll ---
(function () {
  const btn = document.getElementById('auto-scroll-toggle');
  let scrollInterval = null;
  let displaySpeed = 0;
  const MAX_DISPLAY = 4;
  const STEP_DISPLAY = 1;

  function getActualSpeed() {
    return displaySpeed / 2;
  }

  function startScroll() {
    if (scrollInterval) clearInterval(scrollInterval);
    const speed = getActualSpeed();
    if (speed > 0) {
      scrollInterval = setInterval(() => {
        window.scrollBy(0, speed);
        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight) {
          clearInterval(scrollInterval);
          scrollInterval = null;
        }
      }, 50);
    }
  }

  const downBtn = document.createElement('button');
  downBtn.textContent = '−';
  downBtn.type = 'button';
  downBtn.classList.add('control-btn');
  const upBtn = document.createElement('button');
  upBtn.textContent = '+';
  upBtn.type = 'button';
  upBtn.classList.add('control-btn');


  btn.parentNode.insertBefore(downBtn, btn);
  btn.parentNode.insertBefore(upBtn, btn.nextSibling);

  function updateDisplay() {
    btn.textContent = `Scroll Speed ${displaySpeed.toFixed(0)}x`;
  }

  downBtn.addEventListener('click', () => {
    displaySpeed = Math.max(0, displaySpeed - STEP_DISPLAY);
    updateDisplay();
    startScroll();
  });

  upBtn.addEventListener('click', () => {
    displaySpeed = Math.min(MAX_DISPLAY, displaySpeed + STEP_DISPLAY);
    updateDisplay();
    startScroll();
  });

  updateDisplay();
})();

// --- Print & Export Handlers ---
document.getElementById('btn-print-sheet')?.addEventListener('click', () => {
  window.print();
});

document.getElementById('btn-download-txt')?.addEventListener('click', () => {
  const container = document.querySelector('.song-content');
  if (!container) return;

  const title = document.querySelector('h1')?.textContent.trim() || 'song_sheet';
  const textLines = [];
  container.querySelectorAll('.line-block, .section-header').forEach(block => {
    if (block.classList.contains('section-header')) {
      textLines.push(block.textContent.trim());
    } else {
      const chord = block.querySelector('.chord-line')?.textContent.trim();
      const lyric = block.querySelector('.lyric-line')?.textContent.trim();
      if (chord) textLines.push(chord);
      if (lyric) textLines.push(lyric);
    }
  });

  const blob = new Blob([textLines.join('\n')], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title.replace(/\s+/g, '_')}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// --- Interactive Chord Fingering Tooltips (SVG fret diagrams) ---
(function() {
      const GUITAR_CHORD_DB = {
    // *(major)
    'C': 'x32010',
    'C#': 'x46664',
    'Db': 'x46664',
    'D': 'xx0232',
    'D#': 'x68886',
    'Eb': 'x68886',
    'E': '022100',
    'F': '133211',
    'F#': '244322',
    'Gb': '244322',
    'G': '320003',
    'Ab': '466544',
    'G#': '466544',
    'A': 'x02220',
    'A#': 'x13331',
    'Bb': 'x13331',
    'B': 'x24442',
    // *11
    'C11': 'x33353',
    'C#11': 'x43444',
    'Db11': 'x43444',
    'D11': 'xx0010',
    'D#11': 'x65666',
    'Eb11': 'x65666',
    'E11': 'x76777',
    'F11': 'x87888',
    'F#11': 'x98999',
    'Gb11': 'x98999',
    'G11': '353533',
    'Ab11': '464644',
    'G#11': '464644',
    'A11': '575755',
    'A#11': '686866',
    'Bb11': '686866',
    'B11': '797977',
    // *5
    'C5': 'x355xx',
    'C#5': 'x466xx',
    'Db5': 'x466xx',
    'D5': 'x577xx',
    'D#5': 'x688xx',
    'Eb5': 'x688xx',
    'E5': 'x799xx',
    'F5': '133xxx',
    'F#5': '244xxx',
    'Gb5': '244xxx',
    'G5': '355xxx',
    'Ab5': '466xxx',
    'G#5': '466xxx',
    'A5': 'x022xx',
    'A#5': '688xxx',
    'Bb5': '688xxx',
    'B5': '799xxx',
    // *6
    'C6': 'x32210',
    'C#6': 'x46666',
    'Db6': 'x46666',
    'D6': 'xx0202',
    'D#6': 'x68888',
    'Eb6': 'x68888',
    'E6': '022120',
    'F6': '1x3231',
    'F#6': '2x4342',
    'Gb6': '2x4342',
    'G6': '320000',
    'Ab6': '4x3344',
    'G#6': '4x3344',
    'A6': 'x02222',
    'A#6': '6x5566',
    'Bb6': '6x5566',
    'B6': 'x24444',
    // *7
    'C7': 'x32310',
    'C#7': 'x46464',
    'Db7': 'x46464',
    'D7': 'xx0212',
    'D#7': 'x68686',
    'Eb7': 'x68686',
    'E7': '020100',
    'F7': '131211',
    'F#7': '242322',
    'Gb7': '242322',
    'G7': '320001',
    'Ab7': '464544',
    'G#7': '464544',
    'A7': 'x02020',
    'A#7': 'x13131',
    'Bb7': 'x13131',
    'B7': 'x21202',
    // *7b9
    'C7b9': 'x35354',
    'C#7b9': 'x46465',
    'Db7b9': 'x46465',
    'D7b9': 'x57576',
    'D#7b9': 'x68687',
    'Eb7b9': 'x68687',
    'E7b9': 'x79798',
    'F7b9': '131212',
    'F#7b9': '242323',
    'Gb7b9': '242323',
    'G7b9': '321001',
    'Ab7b9': '464545',
    'G#7b9': '464545',
    'A7b9': '575656',
    'A#7b9': '686767',
    'Bb7b9': '686767',
    'B7b9': '797878',
    // *7sus4
    'C7sus4': 'x35533',
    'C#7sus4': 'x46644',
    'Db7sus4': 'x46644',
    'D7sus4': 'x57755',
    'D#7sus4': 'x68866',
    'Eb7sus4': 'x68866',
    'E7sus4': 'x79977',
    'F7sus4': '131311',
    'F#7sus4': '242422',
    'Gb7sus4': '242422',
    'G7sus4': '353533',
    'Ab7sus4': '464644',
    'G#7sus4': '464644',
    'A7sus4': '575755',
    'A#7sus4': '686866',
    'Bb7sus4': '686866',
    'B7sus4': '797977',
    // *add9
    'Cadd9': 'x32030',
    'C#add9': 'x46666',
    'Dbadd9': 'x46666',
    'Dadd9': 'x57777',
    'D#add9': 'x68888',
    'Ebadd9': 'x68888',
    'Eadd9': 'x79999',
    'Fadd9': '133213',
    'F#add9': '244324',
    'Gbadd9': '244324',
    'Gadd9': '320203',
    'Abadd9': '466546',
    'G#add9': '466546',
    'Aadd9': 'x02420',
    'A#add9': '688768',
    'Bbadd9': '688768',
    'Badd9': '799879',
    // *m
    'Cm': 'x35543',
    'C#m': 'x46654',
    'Dbm': 'x46654',
    'Dm': 'xx0231',
    'D#m': 'x68876',
    'Ebm': 'x68876',
    'Em': '022000',
    'Fm': '133111',
    'F#m': '244222',
    'Gbm': '244222',
    'Gm': '355333',
    'Abm': '466444',
    'G#m': '466444',
    'Am': 'x02210',
    'A#m': 'x13321',
    'Bbm': 'x13321',
    'Bm': 'x24432',
    // *m6
    'Cm6': 'x35243',
    'C#m6': 'x46354',
    'Dbm6': 'x46354',
    'Dm6': 'x57465',
    'D#m6': 'x68576',
    'Ebm6': 'x68576',
    'Em6': '022020',
    'Fm6': '1x0111',
    'F#m6': '2x1222',
    'Gbm6': '2x1222',
    'Gm6': '3x2333',
    'Abm6': '4x3444',
    'G#m6': '4x3444',
    'Am6': '5x4555',
    'A#m6': 'x13021',
    'Bbm6': 'x13021',
    'Bm6': '7x6777',
    // *m7
    'Cm7': 'x35343',
    'C#m7': 'x46454',
    'Dbm7': 'x46454',
    'Dm7': 'xx0211',
    'D#m7': 'x68676',
    'Ebm7': 'x68676',
    'Em7': '022030',
    'Fm7': '131111',
    'F#m7': '242222',
    'Gbm7': '242222',
    'Gm7': '353333',
    'Abm7': '464444',
    'G#m7': '464444',
    'Am7': 'x02010',
    'A#m7': 'x13121',
    'Bbm7': 'x13121',
    'Bm7': 'x20202',
    // *m7b5
    'Cm7b5': 'x3434x',
    'C#m7b5': 'x4545x',
    'Dbm7b5': 'x4545x',
    'Dm7b5': 'xx0111',
    'D#m7b5': 'x6767x',
    'Ebm7b5': 'x6767x',
    'Em7b5': 'x7878x',
    'Fm7b5': 'x8989x',
    'F#m7b5': '234232',
    'Gbm7b5': '234232',
    'Gm7b5': '345343',
    'Abm7b5': '456454',
    'G#m7b5': '456454',
    'Am7b5': '567565',
    'A#m7b5': '678676',
    'Bbm7b5': '678676',
    'Bm7b5': 'x2323x',
    // *m9
    'Cm9': 'x35345',
    'C#m9': 'x46456',
    'Dbm9': 'x46456',
    'Dm9': 'x57567',
    'D#m9': 'x68678',
    'Ebm9': 'x68678',
    'Em9': '020002',
    'Fm9': '131013',
    'F#m9': '242224',
    'Gbm9': '242224',
    'Gm9': '353335',
    'Abm9': '464446',
    'G#m9': '464446',
    'Am9': '575557',
    'A#m9': '686668',
    'Bbm9': '686668',
    'Bm9': '797779',
    // *maj7
    'Cmaj7': 'x32000',
    'C#maj7': 'x46564',
    'Dbmaj7': 'x46564',
    'Dmaj7': 'xx0222',
    'D#maj7': 'x68786',
    'Ebmaj7': 'x68786',
    'Emaj7': '021100',
    'Fmaj7': 'xx3210',
    'F#maj7': '243322',
    'Gbmaj7': '243322',
    'Gmaj7': '320002',
    'Abmaj7': '465544',
    'G#maj7': '465544',
    'Amaj7': 'x02120',
    'A#maj7': 'x13231',
    'Bbmaj7': 'x13231',
    'Bmaj7': 'x24342',
    // *sus2
    'Csus2': 'x35533',
    'C#sus2': 'x46644',
    'Dbsus2': 'x46644',
    'Dsus2': 'xx0230',
    'D#sus2': 'x68866',
    'Ebsus2': 'x68866',
    'Esus2': 'x79977',
    'Fsus2': '133113',
    'F#sus2': '244224',
    'Gbsus2': '244224',
    'Gsus2': '355335',
    'Absus2': '466446',
    'G#sus2': '466446',
    'Asus2': 'x02200',
    'A#sus2': '688668',
    'Bbsus2': '688668',
    'Bsus2': '799779',
    // *sus4
    'Csus4': 'x33011',
    'C#sus4': 'x46674',
    'Dbsus4': 'x46674',
    'Dsus4': 'xx0233',
    'D#sus4': 'x68896',
    'Ebsus4': 'x68896',
    'Esus4': '022200',
    'Fsus4': '133311',
    'F#sus4': '224422',
    'Gbsus4': '224422',
    'Gsus4': '330013',
    'Absus4': '466644',
    'G#sus4': '466644',
    'Asus4': 'x02230',
    'A#sus4': 'x13341',
    'Bbsus4': 'x13341',
    'Bsus4': 'x24452'
  };

  const FRETS_SHOWN = 4;
  const tooltip = document.createElement('div');
  tooltip.className = 'chord-tooltip d-none';
  tooltip.setAttribute('role', 'tooltip');
  document.body.appendChild(tooltip);

  function getCleanChordName(rawChord) {
    return rawChord.replace(/[\[\]]/g, '').trim().split('/')[0];
  }

  function parseShape(shape) {
    if (!shape || shape.length !== 6) return null;
    return shape.split('').map((ch) => {
      const lower = ch.toLowerCase();
      if (lower === 'x') return 'x';
      if (ch === '0') return 0;
      const n = parseInt(ch, 10);
      return Number.isFinite(n) ? n : 'x';
    });
  }

  function baseFretFor(frets) {
    const pressed = frets.filter((v) => typeof v === 'number' && v > 0);
    if (!pressed.length) return 1;
    const maxF = Math.max(...pressed);
    if (maxF <= FRETS_SHOWN) return 1;
    return Math.min(...pressed);
  }

  function escapeXml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderFretDiagram(chordName, shape) {
    const frets = parseShape(shape);
    if (!frets) {
      return `<div class="chord-diagram-fallback">No diagram for ${escapeXml(chordName)}</div>`;
    }

    const base = baseFretFor(frets);
    const padL = 18;
    const padT = 22;
    const padB = 10;
    const padR = 10;
    const stringGap = 14;
    const fretGap = 18;
    const gridW = stringGap * 5;
    const gridH = fretGap * FRETS_SHOWN;
    const width = padL + gridW + padR;
    const height = padT + gridH + padB;
    const parts = [];

    parts.push(`<svg class="chord-fret-svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">`);

    // Nut or starting fret line
    if (base === 1) {
      parts.push(`<rect x="${padL - 1}" y="${padT - 3}" width="${gridW + 2}" height="4" fill="#222" rx="1"/>`);
    } else {
      // Same baseline as mute/open markers above the grid
      parts.push(`<text x="${padL - 6}" y="${padT - 8}" text-anchor="end" class="chord-fret-num">${base}</text>`);
      parts.push(`<line x1="${padL}" y1="${padT}" x2="${padL + gridW}" y2="${padT}" stroke="#222" stroke-width="1.5"/>`);
    }

    // Fret lines
    for (let f = 1; f <= FRETS_SHOWN; f++) {
      const y = padT + f * fretGap;
      parts.push(`<line x1="${padL}" y1="${y}" x2="${padL + gridW}" y2="${y}" stroke="#444" stroke-width="1"/>`);
    }

    // Strings
    for (let s = 0; s < 6; s++) {
      const x = padL + s * stringGap;
      parts.push(`<line x1="${x}" y1="${padT}" x2="${x}" y2="${padT + gridH}" stroke="#333" stroke-width="1.25"/>`);
    }

    // Relative frets in the visible window (1..FRETS_SHOWN)
    const rel = frets.map((v) => {
      if (v === 'x' || v === 0) return v;
      return v - base + 1;
    });

    // Barre across strings fretted at/above the lowest pressed fret (e.g. F shape)
    let barreStart = -1;
    let barreEnd = -1;
    const pressedRels = rel.filter((v) => typeof v === 'number' && v > 0);
    if (pressedRels.length) {
      const barreRel = Math.min(...pressedRels);
      const candidates = [];
      rel.forEach((v, i) => {
        if (typeof v === 'number' && v >= barreRel) candidates.push(i);
      });
      if (candidates.length >= 3) {
        const start = Math.min(...candidates);
        const end = Math.max(...candidates);
        let ok = true;
        let exact = 0;
        for (let i = start; i <= end; i++) {
          const v = rel[i];
          if (!(typeof v === 'number' && v >= barreRel)) { ok = false; break; }
          if (v === barreRel) exact += 1;
        }
        if (ok && exact >= 2 && end - start >= 2) {
          barreStart = start;
          barreEnd = end;
          const y = padT + (barreRel - 0.5) * fretGap;
          const x1 = padL + start * stringGap;
          const x2 = padL + end * stringGap;
          parts.push(`<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="#111" stroke-width="9" stroke-linecap="round"/>`);
        }
      }
    }

    // Open / mute markers and finger dots
    frets.forEach((v, s) => {
      const x = padL + s * stringGap;
      if (v === 'x') {
        parts.push(`<text x="${x}" y="${padT - 8}" text-anchor="middle" class="chord-mute">×</text>`);
      } else if (v === 0) {
        parts.push(`<circle cx="${x}" cy="${padT - 10}" r="4" fill="none" stroke="#222" stroke-width="1.5"/>`);
      } else {
        const relFret = v - base + 1;
        if (relFret < 1 || relFret > FRETS_SHOWN) return;
        // Dots sitting on the barre fret are covered by the barre bar
        if (barreStart >= 0 && s >= barreStart && s <= barreEnd) {
          const barreRel = Math.min(...pressedRels);
          if (relFret === barreRel) return;
        }
        const y = padT + (relFret - 0.5) * fretGap;
        parts.push(`<circle cx="${x}" cy="${y}" r="5.5" fill="#111"/>`);
      }
    });

    parts.push('</svg>');
    return `
      <div class="chord-diagram">
        <div class="chord-diagram-name">${escapeXml(chordName)}</div>
        ${parts.join('')}
      </div>
    `;
  }

  function lookupShape(chordName) {
    if (GUITAR_CHORD_DB[chordName]) return GUITAR_CHORD_DB[chordName];
    // Try enharmonic sharp/flat swap for single-letter accidentals
    const m = chordName.match(/^([A-G])([#b]?)(.*)$/);
    if (!m) return null;
    const altAcc = m[2] === '#' ? 'b' : m[2] === 'b' ? '#' : '';
    if (!altAcc) return null;
    const map = { 'C#': 'Db', 'Db': 'C#', 'D#': 'Eb', 'Eb': 'D#', 'F#': 'Gb', 'Gb': 'F#', 'G#': 'Ab', 'Ab': 'G#', 'A#': 'Bb', 'Bb': 'A#' };
    const root = m[1] + m[2];
    const altRoot = map[root];
    if (!altRoot) return null;
    return GUITAR_CHORD_DB[altRoot + m[3]] || null;
  }

  function showTooltip(chordSpan) {
    const cleanChord = getCleanChordName(chordSpan.textContent);
    const shape = lookupShape(cleanChord);
    tooltip.innerHTML = shape
      ? renderFretDiagram(cleanChord, shape)
      : `<div class="chord-diagram"><div class="chord-diagram-name">${escapeXml(cleanChord)}</div><div class="chord-diagram-fallback">No diagram yet</div></div>`;

    tooltip.classList.remove('d-none');
    const rect = chordSpan.getBoundingClientRect();
    const tipRect = tooltip.getBoundingClientRect();
    let left = rect.left + window.scrollX + rect.width / 2 - tipRect.width / 2;
    left = Math.max(8, Math.min(left, window.scrollX + document.documentElement.clientWidth - tipRect.width - 8));
    let top = rect.top + window.scrollY - tipRect.height - 10;
    if (top < window.scrollY + 8) {
      top = rect.bottom + window.scrollY + 10;
    }
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  document.addEventListener('mouseover', (e) => {
    const chordSpan = e.target.closest('.chord');
    if (!chordSpan) return;
    showTooltip(chordSpan);
  });

  document.addEventListener('mouseout', (e) => {
    const fromChord = e.target.closest('.chord');
    if (!fromChord) return;
    const toChord = e.relatedTarget && e.relatedTarget.closest
      ? e.relatedTarget.closest('.chord')
      : null;
    if (toChord === fromChord) return;
    tooltip.classList.add('d-none');
  });

  // Tap support for touch devices
  document.addEventListener('click', (e) => {
    const chordSpan = e.target.closest('.chord');
    if (!chordSpan) {
      tooltip.classList.add('d-none');
      return;
    }
    e.preventDefault();
    showTooltip(chordSpan);
  });
})();

