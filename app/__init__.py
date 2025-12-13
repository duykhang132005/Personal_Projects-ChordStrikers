import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy

from .config import Config

db = SQLAlchemy()
migrate = Migrate() # 2. Initialize Migrate object globally

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
    
    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db) # 3. Initialize Migrate with app and db

    # --- SPOTIPY CLIENT INITIALIZATION ---
    client_id = app.config.get('SPOTIPY_CLIENT_ID')
    client_secret = app.config.get('SPOTIPY_CLIENT_SECRET')
    
    app.sp_client = None # Default to None
    
    if client_id and client_secret:
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            # Initialize Spotipy and store it on the app instance
            app.sp_client = spotipy.Spotify(auth_manager=auth_manager)
            app.logger.info("Spotipy client initialized successfully.")
        except Exception:
            app.logger.error("Spotipy initialization failed. Images will not be fetched.")
    else:
        app.logger.warning("SPOTIPY_CLIENT_ID or SECRET not found. Artist images disabled.")

    # Import and register blueprints
    from .routes.main import main_bp
    from .routes.creator import creator_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(creator_bp)

    return app