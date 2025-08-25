import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config

db = SQLAlchemy()

def create_app():
    # Explicitly set template and static folders at the root level
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=os.path.join(root_dir, 'templates'),
        static_folder=os.path.join(root_dir, 'static')
    )

    app.config.from_object(Config)
    db.init_app(app)

    # Import and register blueprints
    from .routes.main import main_bp
    from .routes.creator import creator_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(creator_bp)

    # Create tables if they don't exist
    with app.app_context():
        from .models import Song
        if not db.inspect(db.engine).has_table("songs"):
            db.create_all()

    return app