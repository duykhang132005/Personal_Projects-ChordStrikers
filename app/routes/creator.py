from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..models import Song
from ..utils import normalise_spacing, process_song_text, get_song_image_url, sanitize_image_url
from ..storage import save_song_content, load_song_content, delete_song_file
from .. import db

creator_bp = Blueprint('creator', __name__)


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
        
        # Handle image URL: prioritize clear_image, then custom URL, then iTunes search
        if clear_image:
            # User explicitly wants no image
            new_song.image_url = None
        else:
            sanitized_custom = sanitize_image_url(custom_image_url) if custom_image_url else None
            if custom_image_url and not sanitized_custom:
                flash(
                    "Cover image URL was not allowed. Use an https URL from a permitted image host.",
                    "error",
                )
            if sanitized_custom:
                new_song.image_url = sanitized_custom
            else:
                image_url = get_song_image_url(title, artist if artist else None)
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
            sanitized_custom = sanitize_image_url(custom_image_url)
            if sanitized_custom:
                song.image_url = sanitized_custom
            else:
                flash(
                    "Cover image URL was not allowed. Use an https URL from a permitted image host.",
                    "error",
                )
        else:
            # Auto-search iTunes if title/artist changed or no image exists
            title_changed = song.title != original_title
            artist_changed = song.artist != original_artist
            if title_changed or artist_changed or not original_image_url:
                song.image_url = get_song_image_url(
                    song.title,
                    song.artist if song.artist else None
                )
        
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