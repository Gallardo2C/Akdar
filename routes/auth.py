from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models import db, User

auth_bp = Blueprint('auth', __name__)

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('user_role') != 'admin':
            flash('Access restricted to System Administrators only.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def cashier_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('user_role') not in ['cashier', 'admin', 'staff']:
            flash('Access restricted to Cashiers and Station Staff.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('user_role') not in ['admin', 'staff']:
            flash('Access restricted to Staff and Administrators.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('user_role') == 'cashier':
            return redirect(url_for('pos.index'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_name'] = user.full_name
            session['user_role'] = user.role
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            
            # Direct cashiers straight to POS for optimal in-store speed
            if user.role == 'cashier':
                return redirect(url_for('pos.index'))
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = db.session.get(User, session['user_id'])
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')

        if full_name:
            user.full_name = full_name
            session['user_name'] = full_name
        user.phone = phone

        if new_password:
            if not current_password or not user.check_password(current_password):
                flash('Current password incorrect. Cannot change password.', 'danger')
                return render_template('auth/profile.html', user=user)
            user.set_password(new_password)
            flash('Password updated successfully.', 'success')

        db.session.commit()
        flash('Profile details updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', user=user)
