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
  let pickerReturn = null;

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
    box.setAttribute('aria-modal', 'true');
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
      closePicker(false);
      replaceLine(lineIndex, next);
      refocus(returnIndex);
    });
    if (existing) {
      addAction('Remove', function () {
        const line = area.value.split('\n')[lineIndex] || '';
        closePicker(false);
        replaceLine(lineIndex, line.replace('[' + existing + ']', ''));
        refocus(returnIndex);
      });
    }
    addAction('Cancel', function () { closePicker(true); });
    box.appendChild(actions);
    // Keep Tab inside the picker while it is open; Escape closes it.
    box.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        e.preventDefault();
        e.stopPropagation();
        closePicker(true);
        return;
      }
      if (e.key !== 'Tab') return;
      const focusable = Array.prototype.filter.call(
        box.querySelectorAll('button, input'),
        function (el) { return !el.disabled; }
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      } else if (!box.contains(document.activeElement)) {
        e.preventDefault();
        first.focus();
      }
    });
    // Place and Remove re-render the line, so remember the trigger by position.
    const returnIndex = Array.prototype.indexOf.call(mount.querySelectorAll('.touch-chord, .touch-word'), anchor);
    anchor.insertAdjacentElement('afterend', box);
    picking = box;
    pickerReturn = anchor;
    input.focus();
  }

  // Close the picker. With returnFocus, focus goes back to the word or chord that opened it.
  function closePicker(returnFocus) {
    const back = pickerReturn;
    if (picking) picking.remove();
    picking = null;
    pickerReturn = null;
    if (returnFocus && back && back.isConnected) back.focus();
  }

  // After a re-render, focus the button that now sits where the trigger was.
  function refocus(index) {
    const buttons = mount.querySelectorAll('.touch-chord, .touch-word');
    if (!buttons.length || index < 0) return;
    buttons[Math.min(index, buttons.length - 1)].focus();
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

  area.addEventListener('input', function () { if (!mount.hidden) render(); });
  setMode(wantedMode());
})();

/* Confirm before destructive submits (e.g. Delete Song). No inline handlers. */
document.addEventListener('click', function (e) {
  const btn = e.target.closest && e.target.closest('button[data-confirm]');
  if (btn && !window.confirm(btn.dataset.confirm)) e.preventDefault();
});
