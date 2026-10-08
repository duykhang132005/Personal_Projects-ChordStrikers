# This file marks the 'routes' directory as a Python package.
# You can optionally import blueprints here for convenience.

from .main import main_bp
from .creator import creator_bp
from .auth import auth_bp
from .pwa import pwa_bp
from .favorites import favorites_bp

__all__ = ['main_bp', 'creator_bp', 'auth_bp', 'pwa_bp', 'favorites_bp']
