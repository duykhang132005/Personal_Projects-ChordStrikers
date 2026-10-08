/* Phone-first chord editor. The classic textarea stays in the form. */
(function () {
  const area = document.getElementById('sheet_content');
  const mount = document.getElementById('touch-editor');
  const toggle = document.getElementById('toggle-touch-editor');
  if (!area || !mount || !toggle) return;

  const ROOTS = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'];
  const QUALITIES = ['', 'm', '7', 'm7', 'maj7', 'sus4', 'sus2', 'add9'];
  const MODE_KEY = 'cs-editor-mode';
  let picking = null;

  function wantedMode() {
    try {
      const saved = localStorage.getItem(MODE_KEY);
      if (saved === 'touch' || saved === 'classic') return saved;
    } catch (e) { /* ignore */ }
    const coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    return coarse && window.innerWidth < 768 ? 'touch' : 'classic';
  }

  function parseLine(line) {
    const parts = [];
    const re = /\[([^\]]+)\]/g;
    let last = 0;
    let match;
    while ((match = re.exec(line))) {
      if (match.index > last) parts.push({ type: 'text', value: line.slice(last, match.index) });
      parts.push({ type: 'chord', value: match[1] });
      last = match.index + match[0].length;
    }
    if (last < line.length || !parts.length) parts.push({ type: 'text', value: line.slice(last) });
    return parts;
  }

  function render() {
    mount.innerHTML = '';
    const lines = area.value.split('\n');
    lines.forEach(function (line, lineIndex) {
      const row = document.createElement('div');
      row.className = 'touch-line';
      parseLine(line).forEach(function (part) {
        if (part.type === 'chord') {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'touch-chord';
          btn.textContent = part.value;
          btn.addEventListener('click', function () { openPicker(lineIndex, part.value, btn); });
          row.appendChild(btn);
          return;
        }
        const words = part.value.split(/(\s+)/);
        words.forEach(function (word) {
          if (!word) return;
          if (/^\s+$/.test(word)) {
            row.appendChild(document.createTextNode(word));
            return;
          }
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'touch-word';
          btn.textContent = word;
          btn.addEventListener('click', function () { openPicker(lineIndex, '', btn, word); });
          row.appendChild(btn);
        });
      });
      if (!line.trim()) {
        const empty = document.createElement('button');
        empty.type = 'button';
        empty.className = 'touch-word';
        empty.textContent = 'Empty line (tap to add a chord)';
        empty.addEventListener('click', function () { openPicker(lineIndex, '', empty, ''); });
        row.appendChild(empty);
      }
      mount.appendChild(row);
    });
    const preview = document.createElement('pre');
    preview.className = 'touch-preview';
    preview.textContent = area.value;
    mount.appendChild(preview);
  }

  function replaceLine(lineIndex, next) {
    const lines = area.value.split('\n');
    lines[lineIndex] = next;
    area.value = lines.join('\n');
    render();
  }

  function openPicker(lineIndex, existing, anchor, word) {
    closePicker();
    const box = document.createElement('div');
    box.className = 'chord-picker';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Choose a chord');
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-control';
    input.value = existing || 'C';
    input.setAttribute('aria-label', 'Chord name');
    box.appendChild(input);
    const grid = document.createElement('div');
    grid.className = 'chord-picker-grid';
    ROOTS.forEach(function (root) {
      QUALITIES.forEach(function (quality) {
        const name = root + quality;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'control-btn';
        btn.textContent = name;
        btn.addEventListener('click', function () { input.value = name; });
        grid.appendChild(btn);
      });
    });
    box.appendChild(grid);
    const actions = document.createElement('div');
    actions.className = 'chord-picker-actions';
    function addAction(label, fn) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm btn-outline-light';
      btn.textContent = label;
      btn.addEventListener('click', fn);
      actions.appendChild(btn);
    }
    addAction('Place chord', function () {
      const name = input.value.trim();
      if (!name) return;
      const line = area.value.split('\n')[lineIndex] || '';
      let next = line;
      if (existing && anchor.classList.contains('touch-chord')) {
        next = line.replace('[' + existing + ']', '[' + name + ']');
      } else if (word) {
        next = line.replace(word, '[' + name + ']' + word);
      } else {
        next = (line ? line + ' ' : '') + '[' + name + ']';
      }
      closePicker();
      replaceLine(lineIndex, next);
    });
    if (existing) {
      addAction('Remove', function () {
        const line = area.value.split('\n')[lineIndex] || '';
        closePicker();
        replaceLine(lineIndex, line.replace('[' + existing + ']', ''));
      });
    }
    addAction('Cancel', closePicker);
    box.appendChild(actions);
    anchor.insertAdjacentElement('afterend', box);
    picking = box;
    input.focus();
  }

  function closePicker() {
    if (picking) picking.remove();
    picking = null;
  }

  function setMode(mode) {
    const touch = mode === 'touch';
    mount.hidden = !touch;
    area.hidden = touch;
    toggle.textContent = touch ? 'Classic editor' : 'Touch editor';
    toggle.setAttribute('aria-pressed', touch ? 'true' : 'false');
    try { localStorage.setItem(MODE_KEY, mode); } catch (e) { /* ignore */ }
    if (touch) render();
  }

  toggle.addEventListener('click', function () {
    setMode(area.hidden ? 'classic' : 'touch');
  });

  const pasteBtn = document.getElementById('btn-paste-chordpro');
  const pasteArea = document.getElementById('chordpro-paste');
  if (pasteBtn && pasteArea) {
    pasteBtn.addEventListener('click', function () {
      const text = pasteArea.value;
      if (!text.trim()) return;
      fetch('/api/chordpro/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ text: text })
      })
        .then(function (response) { if (!response.ok) throw new Error('parse failed'); return response.json(); })
        .then(function (data) {
          if (data.content) area.value = data.content;
          const title = document.getElementById('title');
          const artist = document.getElementById('artist');
          const key = document.getElementById('song_key');
          if (title && data.title && !title.value) title.value = data.title;
          if (artist && data.artist && !artist.value) artist.value = data.artist;
          if (key && data.key && !key.value) key.value = data.key;
          pasteArea.value = '';
          if (!mount.hidden) render();
        })
        .catch(function () {
          pasteArea.setAttribute('aria-invalid', 'true');
        });
    });
  }

  area.addEventListener('input', function () { if (!mount.hidden) render(); });
  setMode(wantedMode());
})();
