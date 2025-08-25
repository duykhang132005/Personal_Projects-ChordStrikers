import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..models import Song
from ..utils import normalise_spacing, process_song_text
from .. import db

creator_bp = Blueprint('creator', __name__)

DATA_FOLDER = os.path.join('static', 'data')

@creator_bp.route('/creator')
def creator():
    songs = Song.query.all()
    return render_template("creator.html", songs=songs)

@creator_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        artist = request.form['artist']
        song_key = request.form['song_key']
        content = normalise_spacing(request.form['sheet_content'])

        new_song = Song(title=title, artist=artist, song_key=song_key)
        db.session.add(new_song)
        db.session.commit()

        filepath = os.path.join(DATA_FOLDER, f"{new_song.id}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return redirect(url_for('main.explore'))

    return render_template("creator.html", form_action_url=url_for('creator.create'))

@creator_bp.route('/edit_song/<int:song_id>', methods=['GET', 'POST'])
def edit_song(song_id):
    song = Song.query.get_or_404(song_id)
    filepath = os.path.join(DATA_FOLDER, f"{song.id}.txt")

    if request.method == 'POST':
        song.title = request.form['title']
        song.artist = request.form['artist']
        song.song_key = request.form['song_key']
        content = normalise_spacing(request.form['sheet_content'])

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        db.session.commit()
        return redirect(url_for('main.explore'))

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = process_song_text(content)
    except FileNotFoundError:
        content = ""
        lines = []

    return render_template("edit_sheet.html",
                        song=song,
                        content=content,
                        lines=lines,
                        form_action_url=url_for('creator.edit_song', song_id=song.id))

@creator_bp.route('/delete_song/<int:song_id>', methods=['POST'])
def delete_song(song_id):
    song = Song.query.get_or_404(song_id)

    # Delete associated .txt file
    filepath = os.path.join(DATA_FOLDER, f"{song_id}.txt")
    if os.path.exists(filepath):
        os.remove(filepath)

    # Delete from database
    db.session.delete(song)
    db.session.commit()

    flash("Song deleted successfully.")
    return redirect(url_for('main.explore'))