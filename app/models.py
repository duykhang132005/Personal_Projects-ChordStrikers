from . import db

class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    song_key = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Song {self.title} by {self.artist}>"