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

// --- Interactive Chord Fingering Tooltips ---
(function() {
  const GUITAR_CHORD_DB = {
    'C': 'x32010', 'Cm': 'x35543', 'C7': 'x32310', 'Cmaj7': 'x32000',
    'D': 'xx0231', 'Dm': 'xx0231', 'D7': 'xx0212', 'Dmaj7': 'xx0222',
    'E': '022100', 'Em': '022000', 'E7': '020100', 'Emaj7': '021100',
    'F': '133211', 'Fm': '133111', 'F7': '131211', 'Fmaj7': 'xx3210',
    'G': '320003', 'Gm': '355333', 'G7': '320001', 'Gmaj7': '320002',
    'A': 'x02220', 'Am': 'x02210', 'A7': 'x02020', 'Amaj7': 'x02120',
    'B': 'x24442', 'Bm': 'x24432', 'B7': 'x21202', 'Bmaj7': 'x24342',
    'Bb': 'x13331', 'Bbm': 'x13321', 'F#': '244322', 'F#m': '244222'
  };

  const tooltip = document.createElement('div');
  tooltip.className = 'chord-tooltip d-none';
  document.body.appendChild(tooltip);

  function getCleanChordName(rawChord) {
    return rawChord.replace(/[\[\]]/g, '').trim().split('/')[0];
  }

  document.addEventListener('mouseover', (e) => {
    const chordSpan = e.target.closest('.chord');
    if (!chordSpan) {
      tooltip.classList.add('d-none');
      return;
    }

    const cleanChord = getCleanChordName(chordSpan.textContent);
    const tabs = GUITAR_CHORD_DB[cleanChord] || 'Fingering available';

    tooltip.innerHTML = `<strong>${cleanChord}</strong><br><small style="letter-spacing: 2px;">Frets: ${tabs}</small>`;
    
    const rect = chordSpan.getBoundingClientRect();
    tooltip.style.left = `${rect.left + window.scrollX}px`;
    tooltip.style.top = `${rect.top + window.scrollY - 45}px`;
    tooltip.classList.remove('d-none');
  });

  document.addEventListener('mouseout', (e) => {
    if (e.target.closest('.chord')) {
      tooltip.classList.add('d-none');
    }
  });
})();

