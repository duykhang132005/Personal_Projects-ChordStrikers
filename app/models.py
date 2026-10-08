from datetime import datetime, timezone

from . import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    songs = db.relationship('Song', backref='creator', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=True)  # Made optional for folk songs
    song_key = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(512), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Deleting a song (owner delete or orphan purge) also drops its favorites.
    favorites = db.relationship(
        'Favorite', backref='song', lazy=True, cascade='all, delete-orphan'
    )

    def __repr__(self):
        if self.artist:
            return f"<Song {self.title} by {self.artist}>"
        return f"<Song {self.title}>"


def _utcnow():
    return datetime.now(timezone.utc)


class Favorite(db.Model):
    """A sheet a signed-in user starred. Starred sheets are kept offline."""
    __tablename__ = 'favorites'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'song_id', name='uq_favorites_user_song'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    song_id = db.Column(
        db.Integer, db.ForeignKey('songs.id'), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    def __repr__(self):
        return f"<Favorite user={self.user_id} song={self.song_id}>"
