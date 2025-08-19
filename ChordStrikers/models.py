from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=True)
    sheet_path = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<Song {self.title} by {self.artist}>"

    @property
    def filename(self):
        """Returns just the filename from the sheet path."""
        return self.sheet_path.split('/')[-1]

    @property
    def display_name(self):
        """Returns a clean display name for UI."""
        return f"{self.title} – {self.artist}" if self.artist else self.title