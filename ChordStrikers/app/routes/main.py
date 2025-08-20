import os
from flask import Blueprint, render_template, request, current_app
from ..models import Song
from ..utils import process_song_text

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template("home.html")

@main_bp.route('/explore')
def explore():
    query = request.args.get('query', '').strip()
    selected_key = request.args.get('key', '').strip()

    # Start with all songs
    songs_query = Song.query

    # Filter by title or artist
    if query:
        search = f"%{query}%"
        songs_query = songs_query.filter(
            (Song.title.ilike(search)) | (Song.artist.ilike(search))
        )

    # Filter by key
    if selected_key:
        songs_query = songs_query.filter(Song.song_key.ilike(selected_key))

    songs = songs_query.order_by(Song.title.asc()).all()

    return render_template(
        'explore.html',
        songs=songs,
        query=query,
        selected_key=selected_key
    )

@main_bp.route('/view_sheet/<int:song_id>')
def view_sheet(song_id):
    song = Song.query.get_or_404(song_id)
    filepath = os.path.join(current_app.root_path, '..', 'static', 'data', f'{song_id}.txt')
    filepath = os.path.abspath(filepath)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_text = f.read()
            processed_lines = process_song_text(raw_text)

    except FileNotFoundError:
        processed_lines = "[Chord sheet not found. Tried reading at " + filepath

    return render_template('view_sheet.html', song=song, lines=processed_lines)
