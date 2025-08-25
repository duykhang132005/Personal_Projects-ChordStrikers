import os
import unicodedata
from flask import Blueprint, render_template, request, current_app, abort
from ..models import Song
from ..utils import prepare_song

main_bp = Blueprint('main', __name__)

# Home page
@main_bp.route('/')
def home():
    return render_template("home.html")

# Accent-insensitive normalization helper
def normalize_text(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()

# Explore page — optimized for accent-insensitive search and scalability
@main_bp.route('/explore')
def explore():
    query_raw = request.args.get('query', '').strip()
    selected_key = request.args.get('key', '').strip()

    # Normalize query for accent-insensitive matching
    query_normalized = normalize_text(query_raw) if query_raw else ''
    key_normalized = selected_key.lower() if selected_key else ''

    # Load all songs once — consider caching or indexing for large datasets
    all_songs = Song.query.all()

    # Filter in Python for accent-insensitive match
    filtered_songs = []
    for song in all_songs:
        title_norm = normalize_text(song.title)
        artist_norm = normalize_text(song.artist)
        key_match = key_normalized == song.song_key.lower() if song.song_key else False

        if query_normalized:
            if query_normalized in title_norm or query_normalized in artist_norm:
                if selected_key:
                    if key_match:
                        filtered_songs.append(song)
                else:
                    filtered_songs.append(song)
        elif selected_key:
            if key_match:
                filtered_songs.append(song)
        else:
            filtered_songs.append(song)

    # Sort alphabetically by title
    songs = sorted(filtered_songs, key=lambda s: s.title.lower())

    return render_template(
        'explore.html',
        songs=songs,
        query=query_raw,
        selected_key=selected_key
    )

# View individual chord sheet
@main_bp.route('/view_sheet/<int:song_id>')
def view_sheet(song_id):
    song = Song.query.get_or_404(song_id)

    # Locate chord sheet file
    data_dir = current_app.config.get(
        'SONG_DATA_DIR',
        os.path.join(current_app.root_path, '..', 'static', 'data')
    )
    filepath = os.path.abspath(os.path.join(data_dir, f'{song_id}.txt'))

    if not os.path.isfile(filepath):
        abort(404, description=f"Chord sheet not found for {song.title}")

    # Read and process chord sheet
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
