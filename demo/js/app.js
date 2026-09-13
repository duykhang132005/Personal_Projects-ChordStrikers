(() => {
  const app = document.getElementById("app");
  const brandHeader = document.getElementById("brand-header");
  const pageTitle = document.getElementById("page-title");

  const BASE_PATH = (window.DEMO_BASE_PATH || "/").replace(/\/?$/, "/");
  let songsIndex = null;
  let destroySheet = null;
  let circleMenuBound = false;

  function assetUrl(path) {
    return BASE_PATH + String(path).replace(/^\//, "");
  }

  function escapeHtml(text) {
    return window.ChordPrepare ? window.ChordPrepare.escapeHtml(text) : String(text ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&#34;")
      .replace(/'/g, "&#39;");
  }

  function normalizeText(text) {
    return String(text || "")
      .normalize("NFD")
      .replace(/\p{M}/gu, "")
      .toLowerCase();
  }

  function setTitle(title) {
    pageTitle.textContent = title;
  }

  function showBrand(show) {
    brandHeader.hidden = !show;
  }

  function parseRoute() {
    const hash = window.location.hash.replace(/^#/, "");
    if (hash && hash !== "/") {
      return normalizeRoute(hash);
    }
    let path = window.location.pathname || "/";
    const base = BASE_PATH.replace(/\/$/, "");
    if (base && path.startsWith(base)) {
      path = path.slice(base.length) || "/";
    }
    if (path.endsWith("index.html") || path.endsWith("404.html")) {
      path = "/";
    }
    return normalizeRoute(path);
  }

  function normalizeRoute(route) {
    let value = route.startsWith("/") ? route : `/${route}`;
    if (value.length > 1 && value.endsWith("/")) {
      value = value.slice(0, -1);
    }
    return value || "/";
  }

  function navigate(route, replace) {
    const target = `#${normalizeRoute(route)}`;
    if (replace) {
      window.history.replaceState(null, "", target);
      render();
      return;
    }
    if (window.location.hash === target) {
      render();
      return;
    }
    window.location.hash = target;
  }

  function handleLinkClick(event) {
    const link = event.target.closest("a[data-route]");
    if (!link) return;
    event.preventDefault();
    navigate(link.getAttribute("data-route"));
  }

  async function loadIndex() {
    if (songsIndex) return songsIndex;
    const response = await fetch(assetUrl("data/index.json"));
    if (!response.ok) {
      throw new Error("Could not load song list");
    }
    songsIndex = await response.json();
    return songsIndex;
  }

  async function loadSong(id) {
    const response = await fetch(assetUrl(`data/songs/${id}.json`));
    if (!response.ok) {
      const error = new Error("Song not found");
      error.status = 404;
      throw error;
    }
    return response.json();
  }

  function songMatches(song, query, key) {
    const keyNorm = key.trim().toLowerCase();
    if (keyNorm) {
      const songKey = (song.song_key || "").toLowerCase();
      if (songKey !== keyNorm) return false;
    }
    const queryNorm = normalizeText(query.trim());
    if (!queryNorm) return true;
    if (normalizeText(song.title).includes(queryNorm)) return true;
    if (song.artist && normalizeText(song.artist).includes(queryNorm)) return true;
    return false;
  }

  function bindCircleMenu() {
    if (circleMenuBound) return;
    circleMenuBound = true;
    document.addEventListener("click", (event) => {
      const item = event.target.closest(".circle-menu-item");
      if (item && app.contains(item)) {
        const isActive = item.classList.contains("active");
        document.querySelectorAll(".circle-menu-item").forEach((el) => el.classList.remove("active", "docked"));
        document.getElementById("circle-menu")?.classList.remove("docked");
        document.querySelectorAll(".circle-card").forEach((card) => card.classList.add("d-none"));
        if (!isActive) {
          item.classList.add("active");
          document.getElementById("circle-menu")?.classList.add("docked");
          document.querySelectorAll(".circle-menu-item").forEach((el) => {
            if (el !== item) el.classList.add("docked");
          });
          const card = document.getElementById(item.getAttribute("data-target"));
          if (card) card.classList.remove("d-none");
        }
        return;
      }

      const card = event.target.closest(".circle-card");
      if (card && event.target === card) {
        document.querySelectorAll(".circle-menu-item").forEach((el) => el.classList.remove("active", "docked"));
        document.getElementById("circle-menu")?.classList.remove("docked");
        document.querySelectorAll(".circle-card").forEach((c) => c.classList.add("d-none"));
      }
    });
  }

  function renderHome() {
    showBrand(false);
    setTitle("Home | ChordStrikers");
    app.innerHTML = document.getElementById("tpl-home").innerHTML;
    bindCircleMenu();
  }

  function songCardsHtml(songs, query, key) {
    const filtered = songs
      .filter((song) => songMatches(song, query, key))
      .slice()
      .sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: "base" }));

    if (!filtered.length) {
      return `<div class="col-12 text-center"><p class="fs-5">No songs found. Try a different search or check back later!</p></div>`;
    }

    return filtered
      .map((song) => {
        const keyLabel = song.song_key ? escapeHtml(song.song_key) : "—";
        const artist = song.artist
          ? `<p class="card-text song-card-text"><strong>Artist:</strong> ${escapeHtml(song.artist)}</p>`
          : "";
        const image = song.image_url
          ? `<img src="${escapeHtml(song.image_url)}" alt="${escapeHtml(song.artist || song.title)}">`
          : "";
        const bodyClass = song.image_url ? "song-card-body with-image" : "song-card-body";
        return `
          <div class="col-md-6 col-lg-4 mb-4">
            <div class="card bg-dark text-white h-100 shadow-sm song-card explore-song-card">
              ${image}
              <div class="${bodyClass}">
                <h5 class="card-title song-card-title">${escapeHtml(song.title)}</h5>
                ${artist}
                <p class="card-text song-card-text"><strong>Key:</strong> ${keyLabel}</p>
                <a href="#/view/${song.id}" data-route="/view/${song.id}" class="btn btn-outline-light mt-2" style="align-self: flex-start;">View Sheet</a>
              </div>
            </div>
          </div>`;
      })
      .join("");
  }

  function renderExplore(songs, query, key) {
    showBrand(true);
    setTitle("Explore | ChordStrikers");

    app.innerHTML = `
      <div class="container py-5 text-white">
        <p class="fs-5 text-center">Browse community-created chord sheets by song, artist, or key.</p>
        <p class="text-center demo-readonly-note">This public demo is read-only. Create and edit stay in the local Flask app (<code>python run.py</code>).</p>
        <form id="explore-form" class="my-4">
          <div class="input-group">
            <input type="text" name="query" class="form-control" placeholder="Search by song or artist" value="${escapeHtml(query)}" aria-label="Search by song or artist">
            <input type="text" name="key" class="form-control" placeholder="Key (e.g., C, F#m)" value="${escapeHtml(key)}" aria-label="Filter by key" style="max-width: 160px">
            <button class="btn btn-outline-light" type="submit" aria-label="Search"><i class="fas fa-search"></i></button>
          </div>
        </form>
        <div id="explore-results" class="row mt-5">${songCardsHtml(songs, query, key)}</div>
      </div>`;

    const form = app.querySelector("#explore-form");
    const queryInput = form.querySelector('input[name="query"]');
    const keyInput = form.querySelector('input[name="key"]');
    const results = app.querySelector("#explore-results");

    const refresh = () => {
      results.innerHTML = songCardsHtml(songs, queryInput.value, keyInput.value);
    };
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      refresh();
    });
    queryInput.addEventListener("input", refresh);
    keyInput.addEventListener("input", refresh);
  }

  function linesForSong(song) {
    if (Array.isArray(song.lines) && song.lines.length) {
      return song.lines;
    }
    if (song.raw_text && window.ChordPrepare) {
      return window.ChordPrepare.prepareSong(song.raw_text, true);
    }
    return [];
  }

  function youtubeQuery(song) {
    return encodeURIComponent(`${song.title} ${song.artist || ""} chords backing track`.trim());
  }

  function renderView(song) {
    showBrand(true);
    setTitle(`${song.title} | ChordStrikers`);
    const lines = linesForSong(song);
    const body = lines.length
      ? `<h4 class="mt-4">Chords and Lyrics</h4>
         <div class="song-content">
           ${lines
             .map((line) =>
               line.lyric === ""
                 ? `<div class="section-header">${line.chord}</div>`
                 : `<div class="line-block"><div class="chord-line">${line.chord}</div><div class="lyric-line">${line.lyric}</div></div>`
             )
             .join("")}
         </div>`
      : `<p class="text-warning">No preview available &mdash; file could not be read.</p>`;

    const artist = song.artist
      ? `<p class="mb-1"><strong>Artist:</strong> ${escapeHtml(song.artist)}</p>`
      : "";
    const keyLabel = song.song_key ? escapeHtml(song.song_key) : "&mdash;";

    app.innerHTML = `
      <div class="container py-5 text-white">
        <h1 class="mb-3">${escapeHtml(song.title)}</h1>
        ${artist}
        <p class="mb-4"><strong>Key:</strong> ${keyLabel}</p>
        <div class="d-flex align-items-center flex-wrap gap-2 mb-4 unified-controls" role="toolbar" aria-label="Sheet controls">
          <div class="d-flex align-items-center flex-wrap gap-2" role="group" aria-label="Sheet actions">
            <div class="control-box">
              <a href="#/explore" data-route="/explore" class="control-btn">
                <i class="bi bi-arrow-left" aria-hidden="true"></i> Return
              </a>
            </div>
            <div class="control-box">
              <button type="button" id="btn-print-sheet" class="control-btn">
                <i class="bi bi-printer" aria-hidden="true"></i> Print / Export PDF
              </button>
            </div>
            <div class="control-box">
              <button type="button" id="btn-download-txt" class="control-btn">
                <i class="bi bi-download" aria-hidden="true"></i> Plain Text
              </button>
            </div>
            <div class="control-box">
              <a id="btn-yt-search" href="https://www.youtube.com/results?search_query=${youtubeQuery(song)}" target="_blank" rel="noopener noreferrer" class="control-btn">
                <i class="bi bi-youtube" aria-hidden="true"></i> Backing Track
              </a>
            </div>
          </div>
          <div id="transpose-controls" class="d-flex align-items-center gap-2">
            <div class="control-box" role="group" aria-label="Transpose">
              <button type="button" class="transpose-btn control-btn" aria-label="Transpose down one semitone" data-step="-1">&larr;</button>
              <input id="steps" type="text" inputmode="numeric" pattern="^-?\\d{1,2}$" value="0" class="steps-input" aria-label="Semitone steps (−11 to +11)">
              <button type="button" class="transpose-btn control-btn" aria-label="Transpose up one semitone" data-step="1">&rarr;</button>
            </div>
            <div class="prefer-toggle control-box" role="group" aria-label="Accidental preference">
              <input type="radio" id="prefAuto" name="prefer" value="" checked>
              <label for="prefAuto" title="Automatic accidentals">A</label>
              <input type="radio" id="prefSharp" name="prefer" value="sharp">
              <label for="prefSharp" title="Prefer sharps">&#9839;</label>
              <input type="radio" id="prefFlat" name="prefer" value="flat">
              <label for="prefFlat" title="Prefer flats">&#9837;</label>
            </div>
            <div class="control-box">
              <button type="button" class="transpose-reset control-btn" aria-label="Reset transposition to 0">Reset</button>
            </div>
          </div>
          <div class="control-box">
            <button type="button" class="control-btn" id="toggle-vertical">Switch to Single Column View</button>
          </div>
          <div class="control-box">
            <div id="auto-scroll-toggle" class="scroll-status">Scroll Speed</div>
          </div>
        </div>
        ${body}
      </div>`;

    destroySheet = window.initViewSheet(app);
  }

  function renderNotFound(message) {
    showBrand(true);
    setTitle("Page not found | ChordStrikers");
    app.innerHTML = `
      <div class="container py-5">
        <div class="error-page fade-in" role="alert">
          <p class="error-code">404</p>
          <h1 class="error-title">Page not found</h1>
          <p class="error-message">${escapeHtml(message || "That isn’t supposed to happen… we can’t find that page. Sorry about that.")}</p>
          <a href="#/" data-route="/" class="error-home-btn">
            <i class="bi bi-house-door" aria-hidden="true"></i> Back to Home
          </a>
        </div>
      </div>`;
  }

  function renderError(message) {
    showBrand(true);
    setTitle("Something went wrong | ChordStrikers");
    app.innerHTML = `
      <div class="container py-5">
        <div class="error-page fade-in" role="alert">
          <p class="error-code">500</p>
          <h1 class="error-title">Something went wrong</h1>
          <p class="error-message">${escapeHtml(message)}</p>
          <a href="#/" data-route="/" class="error-home-btn">
            <i class="bi bi-house-door" aria-hidden="true"></i> Back to Home
          </a>
        </div>
      </div>`;
  }

  async function render() {
    if (destroySheet) {
      destroySheet();
      destroySheet = null;
    }
    window.scrollTo(0, 0);
    const route = parseRoute();
    try {
      if (route === "/") {
        renderHome();
        return;
      }
      if (route === "/explore") {
        const index = await loadIndex();
        renderExplore(index.songs || [], "", "");
        return;
      }
      const viewMatch = route.match(/^\/view\/(\d+)$/);
      if (viewMatch) {
        const song = await loadSong(viewMatch[1]);
        renderView(song);
        return;
      }
      renderNotFound();
    } catch (error) {
      if (error.status === 404) {
        renderNotFound("That song is not in this demo library.");
      } else {
        renderError(error.message || "The demo failed to load this page.");
      }
    }
  }

  document.addEventListener("click", handleLinkClick);
  window.addEventListener("hashchange", render);
  window.addEventListener("popstate", render);
  render();
})();
