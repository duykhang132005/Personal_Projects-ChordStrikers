from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session,
)
from werkzeug.security import generate_password_hash, check_password_hash

from .. import db
from ..models import User
from ..auth_helpers import login_required, get_current_user

auth_bp = Blueprint('auth', __name__)


def _safe_next_url(candidate):
    """Allow only relative same-site paths (no protocol-relative //...)."""
    if not candidate:
        return None
    candidate = candidate.strip()
    if candidate.startswith('/') and not candidate.startswith('//'):
        return candidate
    return None


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('main.home'))

    if request.method == 'GET':
        return redirect(url_for('main.home', signin=1))

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirmation = request.form.get('confirmation', '')

    if not username:
        flash('Username is required.', 'error')
        return redirect(url_for('main.home', signin=1))
    if not password:
        flash('Password is required.', 'error')
        return redirect(url_for('main.home', signin=1))
    if password != confirmation:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('main.home', signin=1))
    if User.query.filter_by(username=username).first() is not None:
        flash('Username already taken.', 'error')
        return redirect(url_for('main.home', signin=1))

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    session.clear()
    session['user_id'] = user.id
    flash(f'Welcome, {username}! Your account was created.', 'success')
    return redirect(url_for('main.home'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('main.home'))

    if request.method == 'GET':
        return redirect(url_for('main.home', signin=1))

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        flash('Invalid username and/or password.', 'error')
        return redirect(url_for('main.home', signin=1))

    session.clear()
    session['user_id'] = user.id
    flash(f'Logged in as {username}.', 'success')

    next_url = _safe_next_url(request.form.get('next') or request.args.get('next'))
    if next_url:
        return redirect(next_url)
    return redirect(url_for('main.home'))


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.home'))

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Update the logged-in user's password (never via bootstrap overwrite)."""
    user = get_current_user()
    if user is None:
        flash('Please log in to continue.', 'error')
        return redirect(url_for('main.home', signin=1))

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirmation = request.form.get('confirmation', '')

    if not current_password or not new_password:
        flash('Current and new passwords are required.', 'error')
        return redirect(url_for('main.home', account=1))
    if new_password != confirmation:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('main.home', account=1))
    if len(new_password) < 8:
        flash('New password must be at least 8 characters.', 'error')
        return redirect(url_for('main.home', account=1))
    if not check_password_hash(user.password_hash, current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('main.home', account=1))
    if check_password_hash(user.password_hash, new_password):
        flash('New password must be different from the current password.', 'error')
        return redirect(url_for('main.home', account=1))

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash('Password updated.', 'success')
    return redirect(url_for('main.home', account=1))

