# This file marks the 'routes' directory as a Python package.
# You can optionally import blueprints here for convenience.

from .main import main_bp
from .creator import creator_bp

__all__ = ['main_bp', 'creator_bp']