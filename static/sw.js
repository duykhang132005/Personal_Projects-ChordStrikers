/* ChordStrikers service worker.
 * Keeps the app installable and shows a friendly page when offline.
 * HTML pages and song data are not cached, with one exception: sheets a
 * signed-in user starred ("Save offline") are copied into a separate
 * favorites cache so they still open with bad or no signal. The page tells
 * the worker which sheets those are; unstarring a sheet or signing out
 * removes the saved copy. */
const VERSION = '__VERSION__';
const CACHE_PREFIX = 'chordstrikers-';
const CACHE_NAME = CACHE_PREFIX + VERSION;
const FAVORITES_CACHE = CACHE_PREFIX + 'favorites';
const FAVORITES_MANIFEST = '/__cs-offline-favorites.json';
const OFFLINE_URL = '/offline';
const SHEET_PATH = /^\/view_sheet\/(\d+)$/;
// A starred sheet waits this long for the network before using its saved copy.
const SLOW_NETWORK_MS = 4000;
// Saved copies are refreshed after this long, or when the app version changes.
const REFRESH_AFTER_MS = 12 * 60 * 60 * 1000;
const PRECACHE = [
  OFFLINE_URL,
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function (cache) { return cache.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys
          .filter(function (key) {
            return key.indexOf(CACHE_PREFIX) === 0 && key !== CACHE_NAME && key !== FAVORITES_CACHE;
          })
          .map(function (key) { return caches.delete(key); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;

  var url = new URL(request.url);

  // CDN stylesheets, scripts and fonts: straight to the network. Only when
  // that fails, fall back to a copy saved with an offline favorite.
  if (url.origin !== self.location.origin) {
    var dest = request.destination;
    if (dest === 'style' || dest === 'script' || dest === 'font') {
      event.respondWith(
        fetch(request).catch(function () {
          return caches.match(request, { cacheName: FAVORITES_CACHE, ignoreVary: true })
            .then(function (cached) { return cached || Response.error(); });
        })
      );
    }
    return;
  }

  if (request.mode === 'navigate') {
    if (SHEET_PATH.test(url.pathname)) {
      event.respondWith(sheetNavigation(request, url));
      return;
    }
    // Other pages: always go to the network; offline page only if it fails.
    event.respondWith(
      fetch(request).catch(function () { return caches.match(OFFLINE_URL); })
    );
    return;
  }

  // Versioned static assets (CSS, JS, icons): cache first. Song text files
  // under /static/data/ are left alone so edits show up immediately.
  if (url.pathname.indexOf('/static/') === 0 && url.pathname.indexOf('/static/data/') !== 0) {
    event.respondWith(
      caches.match(request).then(function (cached) {
        if (cached) return cached;
        return fetch(request).then(function (response) {
          if (response && response.status === 200) {
            var copy = response.clone();
            caches.open(CACHE_NAME).then(function (cache) { cache.put(request, copy); });
          }
          return response;
        });
      })
    );
  }
});

// Sheet pages: network as usual, unless the user starred this sheet. Then a
// failed, very slow or broken (5xx) response falls back to the saved copy.
function sheetNavigation(request, url) {
  var offlinePage = function () { return caches.match(OFFLINE_URL); };
  return caches.open(FAVORITES_CACHE)
    .then(function (cache) { return cache.match(url.origin + url.pathname); })
    .then(function (saved) {
      if (!saved) return fetch(request).catch(offlinePage);
      var network = fetch(request);
      var slow = new Promise(function (resolve) {
        setTimeout(function () { resolve(null); }, SLOW_NETWORK_MS);
      });
      return Promise.race([network, slow])
        .then(function (response) {
          return response && response.status < 500 ? response : saved;
        })
        .catch(function () { return saved; });
    });
}

// ---- Offline favorites -------------------------------------------------

var favoritesQueue = Promise.resolve();

// Run favorites jobs one at a time so two syncs never interleave.
function enqueue(job) {
  favoritesQueue = favoritesQueue.then(job, job).catch(function () {});
  return favoritesQueue;
}

self.addEventListener('message', function (event) {
  var data = event.data || {};
  var source = event.source;
  var reply = function (message) {
    if (source && source.postMessage) source.postMessage(message);
  };
  if (data.type === 'sync-favorites' && Array.isArray(data.ids)) {
    event.waitUntil(enqueue(function () {
      return syncFavorites(data.ids).then(function (ids) {
        reply({ type: 'favorites-synced', ids: ids });
      });
    }));
  } else if (data.type === 'clear-favorites') {
    event.waitUntil(enqueue(function () {
      return caches.delete(FAVORITES_CACHE).then(function () {
        reply({ type: 'favorites-synced', ids: [] });
      });
    }));
  }
});

function sheetUrl(id) {
  return new URL('/view_sheet/' + id, self.location.origin).href;
}

function manifestUrl() {
  return new URL(FAVORITES_MANIFEST, self.location.origin).href;
}

function readManifest(cache) {
  return cache.match(manifestUrl())
    .then(function (response) { return response ? response.json() : null; })
    .catch(function () { return null; })
    .then(function (data) {
      return data && data.pages ? data : { pages: {} };
    });
}

function writeManifest(cache, manifest) {
  return cache.put(manifestUrl(), new Response(JSON.stringify(manifest), {
    headers: { 'Content-Type': 'application/json' }
  }));
}

function syncFavorites(rawIds) {
  var wanted = {};
  rawIds.forEach(function (raw) {
    var id = parseInt(raw, 10);
    if (id > 0) wanted[id] = true;
  });

  return caches.open(FAVORITES_CACHE).then(function (cache) {
    return readManifest(cache).then(function (manifest) {
      // Forget sheets that are no longer starred.
      Object.keys(manifest.pages).forEach(function (id) {
        if (!wanted[id]) delete manifest.pages[id];
      });

      // Save new stars; refresh stale copies.
      var ids = Object.keys(wanted);
      return ids.reduce(function (chain, id) {
        return chain.then(function () {
          return isFresh(cache, manifest.pages[id], id).then(function (fresh) {
            if (fresh) return;
            return savePage(cache, id)
              .then(function (entry) { manifest.pages[id] = entry; })
              .catch(function (err) {
                // Deleted sheet: drop it. Network trouble: keep the old copy.
                if (err && err.status === 404) delete manifest.pages[id];
              });
          });
        });
      }, Promise.resolve())
        .then(function () { return prune(cache, manifest); })
        .then(function () { return writeManifest(cache, manifest); })
        .then(function () { return Object.keys(manifest.pages).map(Number); });
    });
  });
}

function isFresh(cache, entry, id) {
  if (!entry || entry.version !== VERSION || Date.now() - entry.savedAt > REFRESH_AFTER_MS) {
    return Promise.resolve(false);
  }
  return cache.match(sheetUrl(id)).then(function (hit) { return !!hit; });
}

// Delete saved pages and assets that no starred sheet needs any more.
function prune(cache, manifest) {
  var keep = {};
  keep[manifestUrl()] = true;
  Object.keys(manifest.pages).forEach(function (id) {
    keep[sheetUrl(id)] = true;
    (manifest.pages[id].assets || []).forEach(function (asset) { keep[asset] = true; });
  });
  return cache.keys().then(function (requests) {
    return Promise.all(requests
      .filter(function (req) { return !keep[req.url]; })
      .map(function (req) { return cache.delete(req); }));
  });
}

function savePage(cache, id) {
  var url = sheetUrl(id);
  return fetch(url, {
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'X-CS-Offline-Save': '1' }
  }).then(function (response) {
    if (!response.ok) {
      var err = new Error('Could not save sheet ' + id);
      err.status = response.status;
      throw err;
    }
    return response.text().then(function (html) {
      return saveAssets(cache, extractAssets(html, url)).then(function (assets) {
        var page = new Response(html, {
          headers: { 'Content-Type': response.headers.get('Content-Type') || 'text/html; charset=utf-8' }
        });
        return cache.put(url, page).then(function () {
          return { title: extractTitle(html), assets: assets, savedAt: Date.now(), version: VERSION };
        });
      });
    });
  });
}

function extractTitle(html) {
  var match = /<title>([^<]*)<\/title>/i.exec(html);
  var title = match ? match[1] : '';
  title = title.replace(/&amp;/g, '&').replace(/&#39;|&#x27;/g, "'")
    .replace(/&quot;|&#34;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  return title.replace(/\s*\|\s*ChordStrikers\s*$/, '').trim();
}

// Stylesheets and scripts the sheet page loads, as absolute URLs.
function extractAssets(html, baseUrl) {
  var found = [];
  var linkTag = /<link\b[^>]*>/gi;
  var scriptTag = /<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi;
  var tag;
  while ((tag = linkTag.exec(html))) {
    if (!/\brel=["'][^"']*stylesheet/i.test(tag[0])) continue;
    var href = /\bhref=["']([^"']+)["']/i.exec(tag[0]);
    if (href) found.push(href[1]);
  }
  while ((tag = scriptTag.exec(html))) found.push(tag[1]);
  return unique(found.map(function (src) {
    try { return new URL(src.replace(/&amp;/g, '&'), baseUrl).href; } catch (e) { return null; }
  }).filter(function (href) { return href && /^https?:/.test(href); }));
}

function unique(list) {
  var seen = {};
  return list.filter(function (item) {
    if (seen[item]) return false;
    seen[item] = true;
    return true;
  });
}

// Save each asset once (they are versioned or CDN-pinned), plus the woff2
// fonts a stylesheet points at. Resolves with every URL that is cached.
function saveAssets(cache, urls) {
  var saved = [];
  return urls.reduce(function (chain, url) {
    return chain.then(function () {
      return saveAsset(cache, url).then(function (extra) {
        saved.push(url);
        return extra.reduce(function (inner, fontUrl) {
          return inner.then(function () {
            return saveAsset(cache, fontUrl)
              .then(function () { saved.push(fontUrl); })
              .catch(function () {});
          });
        }, Promise.resolve());
      }).catch(function () {});
    });
  }, Promise.resolve()).then(function () { return unique(saved); });
}

function saveAsset(cache, url) {
  return cache.match(url).then(function (hit) {
    if (hit) {
      // Already saved. Still report a stylesheet's fonts so every page that
      // needs them keeps them when another favorite is removed.
      var cssHit = hit.type !== 'opaque' && (hit.headers.get('Content-Type') || '').indexOf('text/css') !== -1;
      return cssHit ? hit.text().then(function (css) { return extractFonts(css, url); }) : [];
    }
    var sameOrigin = new URL(url).origin === self.location.origin;
    var attempt = sameOrigin
      ? fetch(url, { credentials: 'same-origin' })
      : fetch(url, { mode: 'cors', credentials: 'omit' }).catch(function () {
          return fetch(url, { mode: 'no-cors', credentials: 'omit' });
        });
    return attempt.then(function (response) {
      var opaque = response.type === 'opaque';
      if (!opaque && !response.ok) throw new Error('Asset failed: ' + url);
      var type = response.headers.get('Content-Type') || '';
      var isCss = !opaque && type.indexOf('text/css') !== -1;
      var fontsPromise = isCss
        ? response.clone().text().then(function (css) { return extractFonts(css, url); })
        : Promise.resolve([]);
      return cache.put(url, response).then(function () { return fontsPromise; });
    });
  });
}

function extractFonts(css, cssUrl) {
  var fonts = [];
  var pattern = /url\(\s*["']?([^"')]+\.woff2(?:[?#][^"')]*)?)["']?\s*\)/gi;
  var match;
  while ((match = pattern.exec(css))) {
    try { fonts.push(new URL(match[1], cssUrl).href); } catch (e) { /* skip */ }
  }
  return unique(fonts);
}
