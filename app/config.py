from dotenv import load_dotenv
import os

# Load .env from the project folder (the directory that contains app/),
# so it works even if the process was started somewhere else (for example
# a PythonAnywhere WSGI file). Existing environment variables win.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(_PROJECT_ROOT, '.env'))

_TRUTHY = {'1', 'true', 'yes', 'on'}
# 1 MB. Create and edit send a text chord sheet, not a file upload; the
# largest sheet in static/data is well under this cap.
MAX_CONTENT_LENGTH = 1024 * 1024


def env_flag(name, default=False):
    """Parse a boolean environment variable.

    Truthy values are 1, true, yes, and on (any case). Unset, empty, and
    any other value are false, unless default is True.
    """
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in _TRUTHY


def session_cookie_secure():
    """Read SESSION_COOKIE_SECURE at app-creation time (default off)."""
    return env_flag('SESSION_COOKIE_SECURE', default=False)


class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///songs.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CSRF tokens stay valid for the whole session instead of one hour, so
    # a sheet left open (or opened from the offline cache) can still save.
    # Tokens are still tied to the session and signed with SECRET_KEY.
    WTF_CSRF_TIME_LIMIT = None

    # Hosts allowed for song cover <img src> URLs. Entries may be exact
    # hostnames or a single leading wildcard (e.g. *.mzstatic.com).
    # mzstatic.com is Apple/iTunes artwork; Spotify CDN hosts remain so
    # previously stored or manually pasted covers still work.
    IMAGE_URL_ALLOWED_HOSTS = (
        '*.mzstatic.com',
        'i.scdn.co',
        '*.scdn.co',
        '*.spotifycdn.com',
    )

    SESSION_COOKIE_SAMESITE = 'Lax'
    # Default off so local http:// development still receives the cookie.
    # create_app overwrites this from the environment at startup.
    SESSION_COOKIE_SECURE = False
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
