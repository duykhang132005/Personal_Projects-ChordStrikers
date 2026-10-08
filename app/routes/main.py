import os
import unicodedata
from flask import Blueprint, render_template, request, abort
from sqlalchemy.orm import joinedload
from .. import db
from ..models import Song
from ..utils import prepare_song
from ..storage import get_song_filepath
from ..auth_helpers import can_edit_song, get_current_user
from .favorites import favorite_ids_for

main_bp = Blueprint('main', __name__)

# Explore categories, in tab order: (id, label).
EXPLORE_TABS = (
    ('mine', 'Your scores'),
    ('favorites', 'Your favorites'),
    ('library', 'Entire library'),
)
EXPLORE_TAB_IDS = {tab_id for tab_id, _label in EXPLORE_TABS}


def normalize_text(text):
    """
    Normalize text for accent-insensitive comparison.
    Removes diacritical marks and converts to lowercase.
    """
    return ''.join(
        char for char in unicodedata.normalize('NFD', text)
        if unicodedata.category(char) != 'Mn'
    ).lower()


def song_matches_filters(song, query_normalized, key_normalized, author_normalized):
    """
    Check if a song matches the given search filters.
    Returns True if the song matches all provided filters.
    """
    if key_normalized:
        key_match = song.song_key and song.song_key.lower() == key_normalized
        if not key_match:
            return False

    if author_normalized:
        username = song.creator.username if song.creator else ''
        if author_normalized not in normalize_text(username):
            return False

    if query_normalized:
        title_norm = normalize_text(song.title)
        if song.artist:
            artist_norm = normalize_text(song.artist)
            return query_normalized in title_norm or query_normalized in artist_norm
        return query_normalized in title_norm

    return True


@main_bp.route('/')
def home():
    """Display the home page."""
    return render_template("home.html")


@main_bp.route('/explore')
def explore():
    """
    Display searchable song list with optional filters for query, key, and author.
    Uses accent-insensitive search for better UX.
    """
    query_raw = request.args.get('query', '').strip()
    selected_key = request.args.get('key', '').strip()
    author_raw = request.args.get('author', '').strip()

    query_normalized = normalize_text(query_raw) if query_raw else ''
    key_normalized = selected_key.lower() if selected_key else ''
    author_normalized = normalize_text(author_raw) if author_raw else ''

    all_songs = Song.query.options(joinedload(Song.creator)).all()
    filtered_songs = [
        song for song in all_songs
        if song_matches_filters(song, query_normalized, key_normalized, author_normalized)
    ]

    # id stands in for "newest": songs have no created_at column.
    sort = request.args.get('sort', '').strip()
    if sort not in ('az', 'newest'):
        sort = 'az'
    if sort == 'newest':
        songs = sorted(filtered_songs, key=lambda s: -s.id)
    else:
        songs = sorted(filtered_songs, key=lambda s: s.title.lower())

    user = get_current_user()
    favorite_ids = set(favorite_ids_for(user))
    if user is not None:
        my_songs = [song for song in songs if song.user_id == user.id]
        favorite_songs = [song for song in songs if song.id in favorite_ids]
        has_any_scores = any(song.user_id == user.id for song in all_songs)
    else:
        my_songs, favorite_songs, has_any_scores = [], [], False

    # ?tab= picks the category (bookmarks, no-JS); otherwise the page script
    # restores the last choice from localStorage. Signed-out visitors start
    # on the full library; the personal tabs ask them to sign in.
    requested_tab = request.args.get('tab', '').strip()
    if requested_tab not in EXPLORE_TAB_IDS:
        requested_tab = ''
    active_tab = requested_tab or 'library'

    return render_template(
        'explore.html',
        songs=songs,
        my_songs=my_songs,
        favorite_songs=favorite_songs,
        favorite_ids=favorite_ids,
        has_any_scores=has_any_scores,
        has_filters=bool(query_raw or selected_key or author_raw),
        tabs=EXPLORE_TABS,
        active_tab=active_tab,
        tab_from_url=bool(requested_tab),
        query=query_raw,
        selected_key=selected_key,
        author=author_raw,
        sort=sort,
    )


@main_bp.route('/view_sheet/<int:song_id>')
def view_sheet(song_id):
    """Display a song's chord sheet with processed chords and lyrics."""
    song = db.get_or_404(Song, song_id)
    filepath = get_song_filepath(song_id)

    if not os.path.isfile(filepath):
        abort(404)

    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    tuple_lines = prepare_song(raw_text, add_data_attr=True)
    processed_lines = [
        {"chord": chord, "lyric": lyric}
        for chord, lyric in tuple_lines
    ]

    author_name = song.creator.username if song.creator else None
    user = get_current_user()

    return render_template(
        'view_sheet.html',
        song=song,
        lines=processed_lines,
        author_name=author_name,
        can_edit=can_edit_song(song, user) if user is not None else False,
        is_favorite=song_id in favorite_ids_for(user),
        raw_text=raw_text,
    )
