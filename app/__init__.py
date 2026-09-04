import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

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

    app.register_blueprint(main_bp)
    app.register_blueprint(creator_bp)
    _register_error_handlers(app)

    # Create missing SQLite tables, then keep songs.id in sync with
    # SONG_DATA_DIR/{id}.txt (orphan files and orphan rows). Idempotent.
    with app.app_context():
        from .models import Song  # noqa: F401
        from .storage import purge_unsynced_songs_and_sheets

        db.create_all()
        purge_unsynced_songs_and_sheets()

    return app


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            'errors/error.html',
            code=404,
            title='Page not found',
            message=(
                "That isn\u2019t supposed to happen\u2026 we can\u2019t find "
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
                "That isn\u2019t supposed to happen\u2026 we\u2019ve hit an "
                "error. Sorry about that."
            ),
        ), 500
