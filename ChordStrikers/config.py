import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Core settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')  # Replace in production
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(basedir, 'songs.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File storage
    DATA_FOLDER = os.path.join('static', 'data')