from functools import wraps

from flask import session, redirect, url_for, flash

from . import db
from .models import User


def get_current_user():
    """Load the logged-in User from the session, or None."""
    user_id = session.get('user_id')
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def login_required(view):
    """CS50 Finance-style gate: require session['user_id'].

    Redirects to home with ?signin=1 so the home UI can open the sign-in card.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('user_id') is None:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('main.home', signin=1))
        return view(*args, **kwargs)
    return wrapped
