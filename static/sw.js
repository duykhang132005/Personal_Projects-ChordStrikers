/* ChordStrikers service worker.
 * Keeps the app installable and shows a friendly page when offline.
 * It never caches HTML pages, API-style responses or song data, so login
 * state and sheets always come fresh from the server. */
const VERSION = '__VERSION__';
const CACHE_PREFIX = 'chordstrikers-';
const CACHE_NAME = CACHE_PREFIX + VERSION;
const OFFLINE_URL = '/offline';
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
          .filter(function (key) { return key.indexOf(CACHE_PREFIX) === 0 && key !== CACHE_NAME; })
          .map(function (key) { return caches.delete(key); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;

  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Pages: always go to the network; show the offline page only if it fails.
  if (request.mode === 'navigate') {
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
