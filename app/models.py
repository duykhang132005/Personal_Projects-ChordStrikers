from . import db

class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=True)  # Made optional for folk songs
    song_key = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(512), nullable=True)

    def __repr__(self):
        if self.artist:
            return f"<Song {self.title} by {self.artist}>"
        return f"<Song {self.title}>"