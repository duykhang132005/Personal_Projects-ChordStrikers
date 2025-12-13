import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from ..models import Song
from ..utils import normalise_spacing, process_song_text, get_song_image_url
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
        custom_image_url = request.form.get('image_url', '').strip()
        content = normalise_spacing(request.form.get('sheet_content', ''))
        
        # Validate required fields (artist is now optional)
        if not title:
            flash("Title is required.", "error")
            # Create a simple object to preserve form values for error display
            class TempSong:
                def __init__(self, title, artist, song_key, image_url):
                    self.title = title
                    self.artist = artist
                    self.song_key = song_key
                    self.image_url = image_url
            
            temp_song = TempSong(title, artist if artist else None, song_key, custom_image_url if custom_image_url else None)
            return render_template(
                "creator.html",
                form_action_url=url_for('creator.create'),
                song=temp_song,
                content=content
            )
        
        # Create and save song (artist can be empty for folk songs)
        new_song = Song(
            title=title, 
            artist=artist if artist else None, 
            song_key=song_key
        )
        
        # Check if user wants to clear the image
        clear_image = request.form.get('clear_image') == '1'
        
        # Handle image URL: prioritize clear_image, then custom URL, then Spotify search
        if clear_image:
            # User explicitly wants no image
            new_song.image_url = None
        elif custom_image_url:
            # User provided a custom image URL
            new_song.image_url = custom_image_url
        elif hasattr(current_app, 'sp_client') and current_app.sp_client:
            # Auto-search Spotify if no custom URL and not clearing
            image_url = get_song_image_url(
                current_app.sp_client, 
                title, 
                artist if artist else None
            )
            if image_url:
                new_song.image_url = image_url
        
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
        # Store original values for comparison
        original_title = song.title
        original_artist = song.artist
        original_image_url = song.image_url
        
        # Update song metadata
        song.title = request.form.get('title', '').strip()
        new_artist = request.form.get('artist', '').strip()
        song.artist = new_artist if new_artist else None
        song.song_key = request.form.get('song_key', '').strip()
        custom_image_url = request.form.get('image_url', '').strip()
        content = normalise_spacing(request.form.get('sheet_content', ''))
        
        # Check if user wants to clear the image
        clear_image = request.form.get('clear_image') == '1'
        
        # Handle image URL: prioritize clear_image, then custom URL, then auto-search if needed
        if clear_image:
            # User explicitly wants no image
            song.image_url = None
        elif custom_image_url:
            # User provided a custom image URL
            song.image_url = custom_image_url
        elif hasattr(current_app, 'sp_client') and current_app.sp_client:
            # Auto-search if title/artist changed or no image exists
            title_changed = song.title != original_title
            artist_changed = song.artist != original_artist
            if title_changed or artist_changed or not original_image_url:
                image_url = get_song_image_url(
                    current_app.sp_client, 
                    song.title, 
                    song.artist if song.artist else None
                )
                song.image_url = image_url  # Can be None if not found
        else:
            # No custom URL and no Spotify client, keep existing image or set to None
            if not original_image_url:
                song.image_url = None
        
        # Validate required fields (artist is now optional)
        if not song.title:
            # Temporarily update song.image_url to preserve user input in case of error
            if custom_image_url:
                song.image_url = custom_image_url
            flash("Title is required.", "error")
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