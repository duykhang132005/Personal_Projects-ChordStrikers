from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///songs.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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
