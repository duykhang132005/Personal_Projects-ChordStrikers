import os

class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///songs.db"  # Flask will resolve this inside 'instance/'
    SQLALCHEMY_TRACK_MODIFICATIONS = False