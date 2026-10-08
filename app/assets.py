"""Static asset helpers: automatic cache-busting version."""
import os

# Folders under static/ that never affect the page shell (song text files).
_SKIP_DIRS = {'data'}


def compute_static_version(static_folder):
    """Return a short version string from the newest static file mtime.

    Every deploy that touches CSS, JS, icons or the service worker changes
    the value, so browsers refetch assets without a manual version bump.
    Set the STATIC_ASSET_VERSION environment variable to pin a value.
    """
    pinned = (os.environ.get('STATIC_ASSET_VERSION') or '').strip()
    if pinned:
        return pinned

    newest = 0
    for folder, dirs, files in os.walk(static_folder):
        dirs[:] = [d for d in dirs if not (folder == static_folder and d in _SKIP_DIRS)]
        for name in files:
            try:
                newest = max(newest, int(os.path.getmtime(os.path.join(folder, name))))
            except OSError:
                continue
    return format(newest, 'x') if newest else '0'
