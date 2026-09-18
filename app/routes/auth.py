from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session,
)
from werkzeug.security import generate_password_hash, check_password_hash

from .. import db
from ..models import User

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
