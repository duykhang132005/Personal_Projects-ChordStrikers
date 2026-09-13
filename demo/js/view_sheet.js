/**
 * View-sheet interactions ported from static/js/view_sheet.js.
 * Wrapped so the static SPA can mount/unmount a sheet without leaking listeners.
 */
(function (root) {
  const sharpNotes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  const flatNotes = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];

  const GUITAR_CHORD_DB = {
    C: "x32010",
    Cm: "x35543",
    C7: "x32310",
    Cmaj7: "x32000",
    D: "xx0231",
    Dm: "xx0231",
    D7: "xx0212",
    Dmaj7: "xx0222",
    E: "022100",
    Em: "022000",
    E7: "020100",
    Emaj7: "021100",
    F: "133211",
    Fm: "133111",
    F7: "131211",
    Fmaj7: "xx3210",
    G: "320003",
    Gm: "355333",
    G7: "320001",
    Gmaj7: "320002",
    A: "x02220",
    Am: "x02210",
    A7: "x02020",
    Amaj7: "x02120",
    B: "x24442",
    Bm: "x24432",
    B7: "x21202",
    Bmaj7: "x24342",
    Bb: "x13331",
    Bbm: "x13321",
    "F#": "244322",
    "F#m": "244222",
  };

  function shift(note, steps, prefer) {
    let idx = sharpNotes.indexOf(note);
    if (idx === -1) idx = flatNotes.indexOf(note);
    if (idx === -1) return note;
    const toScale = prefer === "flat" ? flatNotes : sharpNotes;
    return toScale[(idx + steps + 12) % 12];
  }

  function applyTransposition(root, steps, prefer) {
    root.querySelectorAll(".chord").forEach((el) => {
      const orig = el.dataset.chord;
      if (!orig) return;
      el.textContent = orig.replace(
        /\[([A-G][#b]?)(.*?)(?:\/([A-G][#b]?))?\]/,
        (match, chordRoot, rest, bass) => {
          const newRoot = shift(chordRoot, steps, prefer);
          const newBass = bass ? "/" + shift(bass, steps, prefer) : "";
          return `[${newRoot}${rest || ""}${newBass}]`;
        }
      );
    });
  }

  function updateColumnCount(container) {
    if (!container) return;
    const lines = [...container.querySelectorAll(".line-block, .section-header")];
    if (!lines.length) return;

    const extraPadding = 5;
    const longestLineLength = Math.max(
      ...lines.map((line) => {
        const chordLen = line.querySelector(".chord-line")?.textContent.length || 0;
        const lyricLen = line.querySelector(".lyric-line")?.textContent.length || 0;
        return Math.max(chordLen, lyricLen, line.textContent.length);
      })
    );

    const testSpan = document.createElement("span");
    testSpan.textContent = "M";
    testSpan.style.visibility = "hidden";
    container.appendChild(testSpan);
    const charWidth = testSpan.getBoundingClientRect().width;
    container.removeChild(testSpan);

    const desiredColWidth = (longestLineLength + extraPadding) * charWidth;

    if (container.classList.contains("vertical-mode")) {
      container.style.width = `${desiredColWidth}px`;
      container.style.marginLeft = "auto";
      container.style.marginRight = "auto";
      container.style.columnCount = 1;
      container.classList.add("single-column");
      container.classList.remove("multi-column");
      return;
    }

    const containerWidth = container.getBoundingClientRect().width;
    const MAX_COLS = 3;
    const colCount = Math.max(1, Math.min(MAX_COLS, Math.floor(containerWidth / desiredColWidth)));
    const totalHeight = container.scrollHeight;
    const isTallEnough = totalHeight > window.innerHeight * 0.8;
    const finalColCount = colCount > 1 && isTallEnough ? colCount : 1;

    container.style.columnCount = finalColCount;
    if (finalColCount === 1) {
      container.classList.add("single-column");
      container.classList.remove("multi-column");
      container.style.width = `${desiredColWidth}px`;
      container.style.marginInline = "auto";
    } else {
      container.classList.remove("single-column");
      container.classList.add("multi-column");
      container.style.width = "100%";
      container.style.marginInline = "";
    }
  }

  function getCleanChordName(rawChord) {
    return rawChord.replace(/[\[\]]/g, "").trim().split("/")[0];
  }

  function initViewSheet(root) {
    const container = root.querySelector(".song-content");
    const stepsInput = root.querySelector("#steps");
    let currentSteps = 0;
    let scrollInterval = null;
    let displaySpeed = 0;
    const listeners = [];

    function on(el, event, handler) {
      if (!el) return;
      el.addEventListener(event, handler);
      listeners.push([el, event, handler]);
    }

    function preferValue() {
      return root.querySelector(".prefer-toggle input:checked")?.value || "";
    }

    function updateSteps(newSteps) {
      currentSteps = Math.max(-11, Math.min(11, newSteps));
      if (stepsInput) stepsInput.value = String(currentSteps);
      applyTransposition(root, currentSteps, preferValue());
    }

    root.querySelectorAll(".transpose-btn").forEach((btn) => {
      on(btn, "click", () => {
        const delta = parseInt(btn.dataset.step, 10);
        updateSteps(currentSteps + delta);
      });
    });

    root.querySelectorAll(".prefer-toggle input").forEach((radio) => {
      on(radio, "change", () => applyTransposition(root, currentSteps, radio.value));
    });

    on(stepsInput, "change", (e) => {
      const parsed = parseInt(e.target.value.trim(), 10);
      updateSteps(Number.isNaN(parsed) ? 0 : parsed);
    });
    on(stepsInput, "keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const parsed = parseInt(e.target.value.trim(), 10);
        updateSteps(Number.isNaN(parsed) ? 0 : parsed);
      }
    });

    on(root.querySelector(".transpose-reset"), "click", () => updateSteps(0));

    const toggleVertical = root.querySelector("#toggle-vertical");
    on(toggleVertical, "click", () => {
      if (!container) return;
      const isVertical = container.classList.toggle("vertical-mode");
      toggleVertical.textContent = isVertical
        ? "Switch to Multi-Column View"
        : "Switch to Single Column View";
      if (!isVertical) {
        container.classList.remove("single-column");
        container.style.width = "";
        container.style.columnCount = "";
        container.style.marginLeft = "";
        container.style.marginRight = "";
        requestAnimationFrame(() => updateColumnCount(container));
      } else {
        updateColumnCount(container);
      }
    });

    const scrollBtn = root.querySelector("#auto-scroll-toggle");
    if (scrollBtn && scrollBtn.parentNode) {
      const downBtn = document.createElement("button");
      downBtn.textContent = "−";
      downBtn.type = "button";
      downBtn.classList.add("control-btn");
      const upBtn = document.createElement("button");
      upBtn.textContent = "+";
      upBtn.type = "button";
      upBtn.classList.add("control-btn");
      scrollBtn.parentNode.insertBefore(downBtn, scrollBtn);
      scrollBtn.parentNode.insertBefore(upBtn, scrollBtn.nextSibling);

      const MAX_DISPLAY = 4;
      const STEP_DISPLAY = 1;

      function startScroll() {
        if (scrollInterval) clearInterval(scrollInterval);
        const speed = displaySpeed / 2;
        if (speed > 0) {
          scrollInterval = setInterval(() => {
            window.scrollBy(0, speed);
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
              clearInterval(scrollInterval);
              scrollInterval = null;
            }
          }, 50);
        }
      }

      function updateDisplay() {
        scrollBtn.textContent = `Scroll Speed ${displaySpeed.toFixed(0)}x`;
      }

      on(downBtn, "click", () => {
        displaySpeed = Math.max(0, displaySpeed - STEP_DISPLAY);
        updateDisplay();
        startScroll();
      });
      on(upBtn, "click", () => {
        displaySpeed = Math.min(MAX_DISPLAY, displaySpeed + STEP_DISPLAY);
        updateDisplay();
        startScroll();
      });
      updateDisplay();
    }

    on(root.querySelector("#btn-print-sheet"), "click", () => window.print());

    on(root.querySelector("#btn-download-txt"), "click", () => {
      if (!container) return;
      const title = root.querySelector("h1")?.textContent.trim() || "song_sheet";
      const textLines = [];
      container.querySelectorAll(".line-block, .section-header").forEach((block) => {
        if (block.classList.contains("section-header")) {
          textLines.push(block.textContent.trim());
        } else {
          const chord = block.querySelector(".chord-line")?.textContent.trim();
          const lyric = block.querySelector(".lyric-line")?.textContent.trim();
          if (chord) textLines.push(chord);
          if (lyric) textLines.push(lyric);
        }
      });
      const blob = new Blob([textLines.join("\n")], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_")}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

    let tooltip = document.querySelector(".chord-tooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.className = "chord-tooltip d-none";
      document.body.appendChild(tooltip);
    }

    function onChordOver(e) {
      const chordSpan = e.target.closest(".chord");
      if (!chordSpan || !root.contains(chordSpan)) {
        tooltip.classList.add("d-none");
        return;
      }
      const cleanChord = getCleanChordName(chordSpan.textContent);
      const tabs = GUITAR_CHORD_DB[cleanChord] || "Fingering available";
      tooltip.innerHTML = `<strong>${cleanChord}</strong><br><small style="letter-spacing: 2px;">Frets: ${tabs}</small>`;
      const rect = chordSpan.getBoundingClientRect();
      tooltip.style.left = `${rect.left + window.scrollX}px`;
      tooltip.style.top = `${rect.top + window.scrollY - 45}px`;
      tooltip.classList.remove("d-none");
    }

    function onChordOut(e) {
      if (e.target.closest(".chord")) {
        tooltip.classList.add("d-none");
      }
    }

    on(root, "mouseover", onChordOver);
    on(root, "mouseout", onChordOut);

    const onResize = () => updateColumnCount(container);
    window.addEventListener("resize", onResize);
    requestAnimationFrame(() => updateColumnCount(container));

    return function destroy() {
      listeners.forEach(([el, event, handler]) => el.removeEventListener(event, handler));
      window.removeEventListener("resize", onResize);
      if (scrollInterval) clearInterval(scrollInterval);
      tooltip.classList.add("d-none");
    };
  }

  root.initViewSheet = initViewSheet;
  root.updateColumnCount = updateColumnCount;
})(typeof globalThis !== "undefined" ? globalThis : this);
