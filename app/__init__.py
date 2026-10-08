import os
import warnings
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from .config import Config
from .assets import compute_static_version

db = SQLAlchemy()

# Placeholder values that must not be trusted as real secrets.
_PLACEHOLDER_KEYS = {'your_random_secret_key_here', 'fallback-dev-key'}
_TRUTHY = {'1', 'true', 'yes', 'on'}


def _env_flag(name):
    return (os.environ.get(name) or '').strip().lower() in _TRUTHY


def _resolve_secret_key(test_config):
    """Return the session signing key, or refuse to start without one.

    A missing key silently falling back to a public default would let anyone
    forge login cookies, so production must set SECRET_KEY. For local
    development only, set ALLOW_INSECURE_DEV_KEY=1 (or run with FLASK_DEBUG=1).
    """
    if test_config and test_config.get('SECRET_KEY'):
        return test_config['SECRET_KEY']

    testing = bool(test_config and test_config.get('TESTING'))
    dev_ok = testing or _env_flag('ALLOW_INSECURE_DEV_KEY') or _env_flag('FLASK_DEBUG')

    key = (os.environ.get('SECRET_KEY') or '').strip()
    if key:
        if key in _PLACEHOLDER_KEYS and not dev_ok:
            warnings.warn('SECRET_KEY is still a placeholder value. Set a real random key.')
        return key

    if dev_ok:
        if not testing:
            warnings.warn('SECRET_KEY is not set. Using an insecure development key. Never do this in production.')
        return 'insecure-dev-key-not-for-production'

    raise RuntimeError(
        'SECRET_KEY is not set. Set it in the environment or in .env '
        '(generate one with: python -c "import secrets; print(secrets.token_hex(32))"). '
        'For local development only, set ALLOW_INSECURE_DEV_KEY=1 or FLASK_DEBUG=1.'
    )


def create_app(test_config=None):
    # Explicitly set template and static folders at the root level
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=os.path.join(root_dir, 'templates'),
        static_folder=os.path.join(root_dir, 'static')
    )

    app.config['SECRET_KEY'] = _resolve_secret_key(test_config)

    # Load additional config
    app.config.from_object(Config)
    if test_config is not None:
        app.config.update(test_config)

    # Version for cache-busting static files, derived from file mtimes.
    app.config.setdefault('STATIC_ASSET_VERSION', compute_static_version(app.static_folder))

    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize Extensions
    db.init_app(app)

    # Import and register blueprints
    from .routes.main import main_bp
    from .routes.creator import creator_bp
    from .routes.auth import auth_bp
    from .routes.pwa import pwa_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(creator_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(pwa_bp)
    _register_error_handlers(app)
    _register_context_processors(app)

    # Create missing SQLite tables, ensure songs.user_id, then keep songs.id in
    # sync with SONG_DATA_DIR/{id}.txt (orphan files and orphan rows). Idempotent.
    with app.app_context():
        from .models import User, Song  # noqa: F401
        from .storage import purge_unsynced_songs_and_sheets

        db.create_all()
        _ensure_songs_user_id_column()
        _ensure_users_is_admin_column()
        _ensure_admin_user()
        purge_unsynced_songs_and_sheets()

    return app


def _ensure_songs_user_id_column():
    """Idempotent SQLite migration: add songs.user_id if the table predates it."""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if 'songs' not in tables:
            return
        columns = {col['name'] for col in inspector.get_columns('songs')}
        if 'user_id' in columns:
            return
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE songs ADD COLUMN user_id INTEGER'))
    except Exception:
        # Non-SQLite or locked DB: create_all already covers fresh schemas.
        pass



def _ensure_users_is_admin_column():
    """Idempotent SQLite migration: add users.is_admin if missing."""
    try:
        inspector = inspect(db.engine)
        if 'users' not in inspector.get_table_names():
            return
        columns = {col['name'] for col in inspector.get_columns('users')}
        if 'is_admin' in columns:
            return
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0'))
    except Exception:
        pass


def _parse_bootstrap_admins():
    """Parse BOOTSTRAP_ADMINS=user:pass,user2:pass2 from the environment.

    Passwords are only used when creating a missing account. Existing users
    keep their stored password_hash forever (deploys must not reset them).
    """
    raw = (os.environ.get('BOOTSTRAP_ADMINS') or '').strip()
    if not raw:
        return []

    accounts = []
    for part in raw.split(','):
        part = part.strip()
        if not part or ':' not in part:
            continue
        username, password = part.split(':', 1)
        username = username.strip()
        password = password.strip()
        if username and password:
            accounts.append((username, password))
    return accounts


def _ensure_admin_user():
    """Create missing bootstrap admins only; never overwrite existing passwords."""
    from werkzeug.security import generate_password_hash
    from flask import current_app
    from .models import User, Song

    bootstrap_admins = _parse_bootstrap_admins()
    primary_name = (
        os.environ.get('PRIMARY_AUTHOR')
        or (bootstrap_admins[0][0] if bootstrap_admins else None)
    )
    primary_author = None

    for username, password in bootstrap_admins:
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                is_admin=True,
            )
            db.session.add(user)
            db.session.flush()
        else:
            # Keep existing hash. Still ensure admin flag for named bootstraps.
            if not user.is_admin:
                user.is_admin = True
        if primary_name and username == primary_name:
            primary_author = user

    if primary_author is None and primary_name:
        primary_author = User.query.filter_by(username=primary_name).first()

    db.session.commit()

    # Attribute unowned sheets to the primary author (skip in tests).
    if primary_author is not None and not current_app.config.get('TESTING'):
        Song.query.filter(Song.user_id.is_(None)).update(
            {Song.user_id: primary_author.id},
            synchronize_session=False,
        )
        db.session.commit()


def _register_context_processors(app):
    @app.context_processor
    def inject_globals():
        from .auth_helpers import get_current_user
        version = app.config.get('STATIC_ASSET_VERSION', '0')
        if app.debug:
            # Pick up CSS/JS edits without restarting the dev server.
            version = compute_static_version(app.static_folder)
        return {
            'current_user': get_current_user(),
            'static_v': version,
        }


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            'errors/error.html',
            code=404,
            title='Page not found',
            message=(
                "That isn’t supposed to happen… we can’t find "
                "that page. Sorry about that."
            ),
        ), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template(
            'errors/error.html',
            code=500,
            title='Something went wrong',
            message=(
                "That isn’t supposed to happen… we’ve hit an "
                "error. Sorry about that."
            ),
        ), 500
