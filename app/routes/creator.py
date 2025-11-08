import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from ..models import Song
from ..utils import normalise_spacing, process_song_text
from .. import db

creator_bp = Blueprint('creator', __name__)


def get_data_folder():
    """Get the data folder path, using app config if available."""
    return current_app.config.get(
        'SONG_DATA_DIR',
        os.path.join(current_app.root_path, '..', 'static', 'data')
    )


def get_song_filepath(song_id):
    """Get the absolute filepath for a song's text file."""
    return os.path.abspath(os.path.join(get_data_folder(), f"{song_id}.txt"))


def save_song_content(song_id, content):
    """Save normalized song content to file."""
    filepath = get_song_filepath(song_id)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def load_song_content(song_id):
    """Load song content from file. Returns empty string if file not found."""
    filepath = get_song_filepath(song_id)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""


def delete_song_file(song_id):
    """Delete a song's text file if it exists."""
    filepath = get_song_filepath(song_id)
    if os.path.exists(filepath):
        os.remove(filepath)


@creator_bp.route('/creator')
def creator():
    """Display list of all songs."""
    songs = Song.query.all()
    return render_template("creator.html", songs=songs)


@creator_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new song."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        artist = request.form.get('artist', '').strip()
        song_key = request.form.get('song_key', '').strip()
        content = normalise_spacing(request.form.get('sheet_content', ''))
        
        # Validate required fields
        if not title or not artist:
            flash("Title and artist are required.", "error")
            return render_template(
                "creator.html",
                form_action_url=url_for('creator.create'),
                title=title,
                artist=artist,
                song_key=song_key,
                content=content
            )
        
        # Create and save song
        new_song = Song(title=title, artist=artist, song_key=song_key)
        db.session.add(new_song)
        db.session.commit()
        
        # Save content to file
        save_song_content(new_song.id, content)
        
        flash(f"Song '{title}' created successfully!", "success")
        return redirect(url_for('main.explore'))
    
    return render_template("creator.html", form_action_url=url_for('creator.create'))


@creator_bp.route('/edit_song/<int:song_id>', methods=['GET', 'POST'])
def edit_song(song_id):
    """Edit an existing song."""
    song = Song.query.get_or_404(song_id)
    
    if request.method == 'POST':
        # Update song metadata
        song.title = request.form.get('title', '').strip()
        song.artist = request.form.get('artist', '').strip()
        song.song_key = request.form.get('song_key', '').strip()
        content = normalise_spacing(request.form.get('sheet_content', ''))
        
        # Validate required fields
        if not song.title or not song.artist:
            flash("Title and artist are required.", "error")
            return render_template(
                "edit_sheet.html",
                song=song,
                content=content,
                lines=process_song_text(content),
                form_action_url=url_for('creator.edit_song', song_id=song_id)
            )
        
        # Save changes
        save_song_content(song_id, content)
        db.session.commit()
        
        flash(f"Song '{song.title}' updated successfully!", "success")
        return redirect(url_for('main.explore'))
    
    # GET request - load existing content
    content = load_song_content(song_id)
    lines = process_song_text(content) if content else []
    
    return render_template(
        "edit_sheet.html",
        song=song,
        content=content,
        lines=lines,
        form_action_url=url_for('creator.edit_song', song_id=song_id)
    )


@creator_bp.route('/delete_song/<int:song_id>', methods=['POST'])
def delete_song(song_id):
    """Delete a song and its associated file."""
    song = Song.query.get_or_404(song_id)
    song_title = song.title  # Store for flash message
    
    # Delete file and database record
    delete_song_file(song_id)
    db.session.delete(song)
    db.session.commit()
    
    flash(f"Song '{song_title}' deleted successfully.", "success")
    return redirect(url_for('main.explore'))