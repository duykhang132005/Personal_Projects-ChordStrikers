import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from .config import Config

db = SQLAlchemy()

def create_app(test_config=None):
    # Explicitly set template and static folders at the root level
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=os.path.join(root_dir, 'templates'),
        static_folder=os.path.join(root_dir, 'static')
    )

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-dev-key')

    # Load additional config
    app.config.from_object(Config)
    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize Extensions
    db.init_app(app)

    # Import and register blueprints
    from .routes.main import main_bp
    from .routes.creator import creator_bp
    from .routes.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(creator_bp)
    app.register_blueprint(auth_bp)
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


def _ensure_admin_user():
    """Ensure bootstrap admin accounts exist with full access."""
    from werkzeug.security import generate_password_hash
    from .models import User, Song

    bootstrap_admins = (
        ('admin', 'admin123'),
        ('duykhang132005', 'Kh1325knd01#'),
    )

    primary_author = None
    for username, password in bootstrap_admins:
        password_hash = generate_password_hash(password)
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(
                username=username,
                password_hash=password_hash,
                is_admin=True,
            )
            db.session.add(user)
            db.session.flush()
        else:
            user.password_hash = password_hash
            user.is_admin = True
        if username == 'duykhang132005':
            primary_author = user

    db.session.commit()

    # Attribute unowned sheets to the primary author (skip in tests).
    from flask import current_app
    if primary_author is not None and not current_app.config.get('TESTING'):
        Song.query.filter(Song.user_id.is_(None)).update(
            {Song.user_id: primary_author.id},
            synchronize_session=False,
        )
        db.session.commit()

def _register_context_processors(app):
    @app.context_processor
    def inject_current_user():
        from .auth_helpers import get_current_user
        return {'current_user': get_current_user()}


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
