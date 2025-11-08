import os
import unicodedata
from flask import Blueprint, render_template, request, current_app, abort
from ..models import Song
from ..utils import prepare_song

main_bp = Blueprint('main', __name__)


def normalize_text(text):
    """
    Normalize text for accent-insensitive comparison.
    Removes diacritical marks and converts to lowercase.
    """
    return ''.join(
        char for char in unicodedata.normalize('NFD', text)
        if unicodedata.category(char) != 'Mn'
    ).lower()


def get_song_filepath(song_id):
    """Get the absolute filepath for a song's text file."""
    data_dir = current_app.config.get(
        'SONG_DATA_DIR',
        os.path.join(current_app.root_path, '..', 'static', 'data')
    )
    return os.path.abspath(os.path.join(data_dir, f'{song_id}.txt'))


def song_matches_filters(song, query_normalized, key_normalized):
    """
    Check if a song matches the given search filters.
    Returns True if the song matches all provided filters.
    """
    # Check key filter
    if key_normalized:
        key_match = song.song_key and song.song_key.lower() == key_normalized
        if not key_match:
            return False
    
    # Check query filter
    if query_normalized:
        title_norm = normalize_text(song.title)
        artist_norm = normalize_text(song.artist)
        return query_normalized in title_norm or query_normalized in artist_norm
    
    return True


@main_bp.route('/')
def home():
    """Display the home page."""
    return render_template("home.html")


@main_bp.route('/explore')
def explore():
    """
    Display searchable song list with optional filters for query and key.
    Uses accent-insensitive search for better UX.
    """
    query_raw = request.args.get('query', '').strip()
    selected_key = request.args.get('key', '').strip()
    
    # Normalize inputs for comparison
    query_normalized = normalize_text(query_raw) if query_raw else ''
    key_normalized = selected_key.lower() if selected_key else ''
    
    # Filter songs based on search criteria
    all_songs = Song.query.all()
    filtered_songs = [
        song for song in all_songs
        if song_matches_filters(song, query_normalized, key_normalized)
    ]
    
    # Sort alphabetically by title
    songs = sorted(filtered_songs, key=lambda s: s.title.lower())
    
    return render_template(
        'explore.html',
        songs=songs,
        query=query_raw,
        selected_key=selected_key
    )


@main_bp.route('/view_sheet/<int:song_id>')
def view_sheet(song_id):
    """Display a song's chord sheet with processed chords and lyrics."""
    song = Song.query.get_or_404(song_id)
    filepath = get_song_filepath(song_id)
    
    # Verify file exists
    if not os.path.isfile(filepath):
        abort(404, description=f"Chord sheet not found for '{song.title}'")
    
    # Load and process the chord sheet
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    tuple_lines = prepare_song(raw_text, add_data_attr=True)
    processed_lines = [
        {"chord": chord, "lyric": lyric}
        for chord, lyric in tuple_lines
    ]
    
    return render_template(
        'view_sheet.html',
        song=song,
        lines=processed_lines
    )