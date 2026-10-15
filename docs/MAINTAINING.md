# Maintaining ChordStrikers

Notes for whoever hosts and updates the app. Visitors and contributors can start with the [README](../README.md).

## Project layout

```text
app/                    Flask application package
  routes/               Blueprints: main, creator, auth, pwa, favorites
  chord_logic.py        Transpose and simplify (server side)
  storage.py            Song text file I/O
  parsing.py            Legacy text parser helpers
  utils.py              Chord splitting, iTunes cover fetch, artwork sizes
  config.py             App configuration
docs/                   Chord format guide and this file
scripts/
  backup_db.py          Daily SQLite backup (stdlib only)
  build_vendor_css.js   Rebuilds static/vendor/vendor.min.css
static/                 styles.css, js/, vendor/, icons, sw.js, data/ (sheets)
templates/              Jinja2 templates
tests/                  Pytest suite (test_mobile_viewport.py needs Playwright)
run.py                  Development entry point
requirements.txt        Runtime dependencies
requirements-dev.txt    Adds pytest and coverage
requirements-browser.txt  Adds Playwright for the optional browser checks
```

## Data and startup

Startup creates any missing SQLite tables (`songs`, `users`, `favorites`) automatically via SQLAlchemy `create_all` and does not wipe existing rows. Restart the app after model changes so new tables or columns that `create_all` can add are applied. Chord sheets are stored as `static/data/{song_id}.txt` (or `SONG_DATA_DIR`) and must match `songs.id`. On startup the app removes sheet files whose ids are not in the database, and deletes song rows that have no matching sheet file.

## Accounts

`instance/*.db` stays gitignored so production user hashes are not overwritten by `git pull`.

On startup, ChordStrikers may create **missing** bootstrap admins from `BOOTSTRAP_ADMINS` in `.env`. It **never** changes an existing user's password hash.

### First deploy / empty database
1. On the host, set in `.env` (not committed):
   `BOOTSTRAP_ADMINS=admin:YOUR_TEMP_PASSWORD,duykhang132005:YOUR_TEMP_PASSWORD`
   `PRIMARY_AUTHOR=duykhang132005`
2. Start the app once so those users are created.
3. Log in and change passwords in the app (or clear `BOOTSTRAP_ADMINS` afterward).
4. You can remove or empty `BOOTSTRAP_ADMINS` after the accounts exist; later deploys will leave hashes alone.

### Later updates (`git pull` on the host)
1. Pull/reset tracked code from `main` as usual.
2. Leave `instance/*.db` alone (ignored). That is your live accounts.
3. Do **not** put real passwords back into source code.
4. New people: use **Register** in the app, or temporarily add `newuser:tempPass` to `BOOTSTRAP_ADMINS`, restart once, then remove that entry and have them change the password.
5. Promote an existing user to admin in the DB/admin UI if you have one; bootstrap only sets `is_admin` for names listed when creating **or** if the user already exists and is not admin yet (still without touching their password).

### Local development
Copy `.env.example` to `.env`, set `BOOTSTRAP_ADMINS` for a fresh local DB only. Your local `instance/songs.db` remains private.

## Deploying on PythonAnywhere

The live site runs from `~/Personal_Projects-ChordStrikers`. A normal update is:

1. Open a Bash console, `cd ~/Personal_Projects-ChordStrikers`, then `git pull`.
2. If `requirements.txt` changed, run `pip install -r requirements.txt` inside the site's virtualenv.
3. Press **Reload** on the Web tab.

New tables and columns are created on startup, so there is no migration step.

### After this update: install Flask-Compress

`requirements.txt` now includes `Flask-Compress==1.25` (gzip for HTML and JSON). The app will not start without it, so install it before pressing Reload:

1. Bash console: `cd ~/Personal_Projects-ChordStrikers && git pull`
2. `workon <your-virtualenv>` (or `source <virtualenv path>/bin/activate`; the path is on the Web tab), then `pip install -r requirements.txt`
3. Press **Reload** on the Web tab.
4. Check `https://duykhang132005.pythonanywhere.com/healthz` shows `{"db": "ok", "status": "ok"}`.

Static files are served by Flask (Flask-Compress skips them) unless you add a **Static files** mapping on the Web tab (URL `/static/`, directory `/home/YOUR_PA_USERNAME/Personal_Projects-ChordStrikers/static`), in which case PythonAnywhere's own web server serves them, which may compress them. Unconfirmed whether PythonAnywhere gzips app responses by itself; with Flask-Compress it does not matter.

### Health check

`GET /healthz` returns `{"status": "ok", "db": "ok"}` with 200 when a trivial `SELECT 1` works, or `{"status": "error", "db": "error"}` with 503 when it does not. No login, no version or error details, `Cache-Control: no-store`, and the service worker never touches it. Point an uptime monitor at `https://duykhang132005.pythonanywhere.com/healthz`.

### Chord font

Roboto Mono (Apache License 2.0) is self-hosted in `static/fonts/` (latin and Vietnamese subsets of the variable font, weights 400 to 700) and preloaded in `templates/index.html`, so sheets render with it on first paint and offline. If you replace the files, keep the `@font-face` URLs in `static/styles.css` and the preload links in sync.

### SECRET_KEY is required

The app will not start without a `SECRET_KEY`, because a public default would let anyone forge login cookies. Set it in the host environment or in `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

For local development only, you can instead set `ALLOW_INSECURE_DEV_KEY=1` (or run with `FLASK_DEBUG=1`) to use a throwaway key. Tests supply their own key.

On PythonAnywhere, add `SECRET_KEY` to the `.env` file in the project folder (or the WSGI file), then press Reload.

### Static file versions

CSS and JS links carry a `?v=` value computed from the newest file modification time under `static/` (song text files in `static/data/` are ignored). There is nothing to bump by hand. Set `STATIC_ASSET_VERSION` in the environment to pin a value.

### Service worker and offline favorites

ChordStrikers ships a web app manifest, icons and a small service worker (`static/sw.js`), so it can be installed. Installing needs HTTPS, which PythonAnywhere provides.

The service worker caches versioned CSS, JS and icons, plus an offline page. Pages, logins and song sheets come from the server, with one exception: signed-in users can tap **Save offline** (the star) on a sheet. Starred sheets are stored per account in the `favorites` table, listed under **Your favorites** on Explore, and copied to the device together with the styles and fonts they need, so they open with bad or no signal. Unstarring removes the copy, and signing out clears all saved copies.

## Daily database backup

`scripts/backup_db.py` copies `instance/songs.db` into `backups/` (gitignored, outside `static/`) as `songs-YYYYMMDD-HHMMSS.db` and keeps only the newest 7. It uses the SQLite backup API, so it is safe while the site is running. It needs nothing beyond the Python standard library.

Run it by hand:

```bash
python scripts/backup_db.py
```

On PythonAnywhere, open the **Tasks** tab and add a daily Scheduled Task:

- Time (UTC): `08:00` (about 4 AM New York time; pick any quiet hour).
- Command (replace `YOUR_PA_USERNAME`, and use your real virtualenv path from the **Web** tab, "Virtualenv" field, with `/bin/python` added):

```bash
/home/YOUR_PA_USERNAME/Personal_Projects-ChordStrikers/venv/bin/python /home/YOUR_PA_USERNAME/Personal_Projects-ChordStrikers/scripts/backup_db.py
```

If the virtualenv lives under `~/.virtualenvs/NAME`, the first part becomes `/home/YOUR_PA_USERNAME/.virtualenvs/NAME/bin/python`. Since the script is stdlib only, `python3` also works. After the first run, check the task log and look for a new file in `~/Personal_Projects-ChordStrikers/backups/`.

Not confirmed: whether the free PythonAnywhere plan still allows a daily Scheduled Task (historically one daily task, and free tasks may expire unless renewed from the Tasks tab). Check the Tasks tab on your account. If tasks are not available, run the command by hand from a Bash console now and then, or download a backup from the Files tab.

To restore, stop the web app (or accept a short blip), copy a backup over `instance/songs.db`, and press Reload.

## Trimmed Bootstrap and icon CSS

`static/vendor/vendor.min.css` holds Bootstrap 5.3.3, Bootstrap Icons and Font Awesome, trimmed to the classes the app uses (about 29 KB instead of about 430 KB). If you add a Bootstrap class or icon that is not used anywhere yet, rebuild it on your PC (Node needed only for this):

```bash
npm install --no-save purgecss@6 clean-css@5
node scripts/build_vendor_css.js
```

## Optional browser tests

Real-browser checks (View Sheet on phone-sized screens: no sideways scrolling, centered toolbar, Perform autoscroll) use Playwright and are skipped when it is not installed:

```bash
pip install -r requirements-browser.txt
python -m playwright install chromium
python -m pytest -m browser
```
