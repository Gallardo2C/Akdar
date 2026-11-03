from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User
from routes.auth import login_required, admin_required

employees_bp = Blueprint('employees', __name__)

@employees_bp.route('/')
@login_required
@admin_required
def index():
    role_filter = request.args.get('role', '').strip()
    search = request.args.get('search', '').strip()

    query = User.query

    if role_filter and role_filter != 'all':
        query = query.filter(User.role == role_filter)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_term)) |
            (User.username.ilike(search_term)) |
            (User.phone.ilike(search_term))
        )

    users = query.order_by(User.id.asc()).all()
    roles = ['admin', 'cashier', 'staff', 'rider']

    # Counts
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_count = User.query.filter_by(role='admin').count()
    cashier_count = User.query.filter_by(role='cashier').count()

    return render_template(
        'employees/index.html',
        users=users,
        roles=roles,
        selected_role=role_filter or 'all',
        search=search,
        total_users=total_users,
        active_users=active_users,
        admin_count=admin_count,
        cashier_count=cashier_count
    )

@employees_bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create():
    username = request.form.get('username', '').strip().lower()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'staff').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')

    if not username or not full_name or not password:
        flash('Username, Full Name, and Password are required.', 'danger')
        return redirect(url_for('employees.index'))

    existing = User.query.filter_by(username=username).first()
    if existing:
        flash(f"A user with username '{username}' already exists.", 'danger')
        return redirect(url_for('employees.index'))

    if role not in ['admin', 'cashier', 'staff', 'rider']:
        role = 'staff'

    user = User(
        username=username,
        full_name=full_name,
        role=role,
        phone=phone
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(f"Employee account '{user.full_name}' ({user.role.title()}) created successfully!", 'success')
    return redirect(url_for('employees.index'))

@employees_bp.route('/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def edit(id):
    user = User.query.get_or_404(id)
    current_user_id = session.get('user_id')

    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', user.role).strip()
    phone = request.form.get('phone', '').strip()
    is_active = request.form.get('is_active') == '1'

    if not full_name:
        flash('Full Name is required.', 'danger')
        return redirect(url_for('employees.index'))

    # Prevent current admin from demoting or deactivating self
    if user.id == current_user_id:
        if role != 'admin' or not is_active:
            flash("You cannot remove admin role or deactivate your own active session account.", 'warning')
            return redirect(url_for('employees.index'))

    user.full_name = full_name
    user.role = role
    user.phone = phone
    user.is_active = is_active

    db.session.commit()
    flash(f"User account '{user.username}' successfully updated.", 'success')
    return redirect(url_for('employees.index'))

@employees_bp.route('/<int:id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(id):
    user = User.query.get_or_404(id)
    new_password = request.form.get('new_password', '')

    if not new_password or len(new_password) < 4:
        flash('Password must be at least 4 characters long.', 'danger')
        return redirect(url_for('employees.index'))

    user.set_password(new_password)
    db.session.commit()
    flash(f"Password reset successfully for '{user.username}'.", 'success')
    return redirect(url_for('employees.index'))
