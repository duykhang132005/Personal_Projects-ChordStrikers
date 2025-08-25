import os
from flask import Blueprint, render_template, request, current_app, abort
from ..models import Song
from ..utils import prepare_song

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template("home.html")

@main_bp.route('/explore')
def explore():
    query = request.args.get('query', '').strip()
    selected_key = request.args.get('key', '').strip()

    songs_query = Song.query

    if query:
        search = f"%{query}%"
        songs_query = songs_query.filter(
            (Song.title.ilike(search)) | (Song.artist.ilike(search))
        )

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

    data_dir = current_app.config.get(
        'SONG_DATA_DIR',
        os.path.join(current_app.root_path, '..', 'static', 'data')
    )
    filepath = os.path.abspath(os.path.join(data_dir, f'{song_id}.txt'))

    if not os.path.isfile(filepath):
        abort(404, description=f"Chord sheet not found for {song.title}")

    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # No server-side transposition — just prep the base lines
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
