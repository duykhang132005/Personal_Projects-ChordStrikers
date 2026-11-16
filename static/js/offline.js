/* Offline fallback page: apply the saved theme, reload on "Try again",
 * and list starred sheets the service worker saved on this device.
 * Loaded without a ?v= query so the service worker PRECACHE path matches. */
(function () {
    /* cs-theme-v2 is the live choice: "wooden" or "limelight".
       Limelight is the green background (formerly stored as nature).
       Old cs-theme "limelight" was the dark spotlight and is dropped,
       along with "stage". Both become Default. */
    var allowed = { wooden: 1, limelight: 1 };
    var theme = '';
    try {
        var saved = localStorage.getItem('cs-theme-v2');
        if (saved === null) {
            var old = localStorage.getItem('cs-theme') || '';
            if (old === 'nature') theme = 'limelight';
            else if (old === 'wooden') theme = 'wooden';
            localStorage.setItem('cs-theme-v2', theme);
        } else if (allowed[saved]) {
            theme = saved;
        }
    } catch (e) { theme = ''; }
    if (theme) document.documentElement.setAttribute('data-theme', theme);

    function listSavedSheets() {
        if (!window.caches) return;
        caches.open('chordstrikers-favorites')
            .then(function (cache) { return cache.match('/__cs-offline-favorites.json'); })
            .then(function (response) { return response ? response.json() : null; })
            .then(function (manifest) {
                var pages = manifest && manifest.pages ? manifest.pages : {};
                var ids = Object.keys(pages);
                if (!ids.length) return;
                ids.sort(function (a, b) {
                    return String(pages[a].title || '').localeCompare(String(pages[b].title || ''));
                });
                var list = document.getElementById('saved-list');
                if (!list) return;
                ids.forEach(function (id) {
                    var link = document.createElement('a');
                    link.href = '/view_sheet/' + id;
                    link.textContent = pages[id].title || ('Sheet ' + id);
                    var item = document.createElement('li');
                    item.appendChild(link);
                    list.appendChild(item);
                });
                var section = document.getElementById('saved-sheets');
                if (section) section.hidden = false;
            })
            .catch(function () {});
    }

    function wire() {
        var retry = document.getElementById('offline-retry');
        if (retry) {
            retry.addEventListener('click', function () {
                window.location.reload();
            });
        }
        listSavedSheets();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wire);
    } else {
        wire();
    }
})();
