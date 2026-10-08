"""Per-user favorite sheets.

Favorites live in the database (table ``favorites``) so they follow the
account across phone, tablet and desktop. The browser keeps a copy of each
favorited sheet in the service worker cache so it opens with no signal.
"""
from flask import Blueprint, jsonify, request

from .. import db
from ..auth_helpers import get_current_user
from ..models import Favorite, Song

favorites_bp = Blueprint('favorites', __name__)


def favorite_ids_for(user):
    """Sorted song ids the user has favorited (empty for anonymous users)."""
    if user is None:
        return []
    rows = (
        db.session.query(Favorite.song_id)
        .join(Song, Song.id == Favorite.song_id)
        .filter(Favorite.user_id == user.id)
        .order_by(Favorite.song_id)
        .all()
    )
    return [row[0] for row in rows]


def _error(message, status):
    return jsonify({'error': message}), status


def _payload(user, song_id=None, favorited=None):
    body = {'ids': favorite_ids_for(user)}
    if song_id is not None:
        body['song_id'] = song_id
        body['favorited'] = favorited
    response = jsonify(body)
    response.headers['Cache-Control'] = 'no-store'
    return response


def _is_script_request():
    """Writes must come from our own fetch() calls, not cross-site forms.

    A plain HTML form cannot set custom headers, so requiring one blocks
    simple cross-site request forgery without a token.
    """
    return request.headers.get('X-Requested-With') == 'fetch'


@favorites_bp.route('/api/favorites', methods=['GET'])
def list_favorites():
    user = get_current_user()
    if user is None:
        return _error('Sign in to use favorites.', 401)
    return _payload(user)


@favorites_bp.route('/api/favorites/<int:song_id>', methods=['POST', 'PUT', 'DELETE'])
def toggle_favorite(song_id):
    user = get_current_user()
    if user is None:
        return _error('Sign in to use favorites.', 401)
    if not _is_script_request():
        return _error('Missing X-Requested-With header.', 400)

    song = db.session.get(Song, song_id)
    if song is None:
        return _error('Song not found.', 404)

    existing = Favorite.query.filter_by(user_id=user.id, song_id=song_id).first()
    if request.method == 'DELETE':
        if existing is not None:
            db.session.delete(existing)
            db.session.commit()
        return _payload(user, song_id, False)

    if existing is None:
        db.session.add(Favorite(user_id=user.id, song_id=song_id))
        db.session.commit()
    return _payload(user, song_id, True)
