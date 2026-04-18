"""Authentication blueprint — login, logout, role guards."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from functools import wraps
from models.db import execute_query

auth_bp = Blueprint('auth', __name__)


# ------------------------------------------------------------------ #
#  Decorators
# ------------------------------------------------------------------ #

def login_required(f):
    """Ensure the user is logged in before accessing the route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def role_required(role):
    """Ensure the logged-in user has the specified role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('role') != role:
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ------------------------------------------------------------------ #
#  Routes
# ------------------------------------------------------------------ #

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Already logged in → go to dashboard
    if 'user_id' in session:
        return _redirect_to_dashboard()

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('auth/login.html')

        user = execute_query(
            "SELECT * FROM users WHERE email = %s",
            (email,), fetchone=True
        )

        if user and user['password'] == password:
            session['user_id']   = user['user_id']
            session['full_name'] = user['full_name']
            session['email']     = user['email']
            session['role']      = user['role']
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return _redirect_to_dashboard()
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #

def _redirect_to_dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher.dashboard'))
    elif role == 'student':
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))
