import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from .config import Config

db = SQLAlchemy()
migrate = Migrate()  # Initialize Migrate object globally

def create_app():
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
    
    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db) # 3. Initialize Migrate with app and db

    # Import and register blueprints
    from .routes.main import main_bp
    from .routes.creator import creator_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(creator_bp)

    return app
