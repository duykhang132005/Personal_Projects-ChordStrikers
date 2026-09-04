import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///songs.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Keep the credentials as configuration attributes
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')

    # Hosts allowed for song cover <img src> URLs. Entries may be exact
    # hostnames or a single leading wildcard (e.g. *.scdn.co).
    IMAGE_URL_ALLOWED_HOSTS = (
        'i.scdn.co',
        '*.scdn.co',
        '*.spotifycdn.com',
    )