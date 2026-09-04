import os
from flask import current_app


def get_data_folder():
    """Get the data folder path, using app config if available."""
    return current_app.config.get(
        'SONG_DATA_DIR',
        os.path.join(current_app.root_path, '..', 'static', 'data')
    )


def get_song_filepath(song_id):
    """Get the absolute filepath for a song's text file."""
    return os.path.abspath(os.path.join(get_data_folder(), f'{song_id}.txt'))


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
