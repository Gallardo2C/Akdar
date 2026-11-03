from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Product, InventoryItem
from routes.auth import login_required, staff_required

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
@login_required
def index():
    query = Product.query
    
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    if category and category != 'all':
        query = query.filter(Product.category == category)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_filter)) |
            (Product.code.ilike(search_filter))
        )

    if status == 'active':
        query = query.filter(Product.is_active == True)
    elif status == 'inactive':
        query = query.filter(Product.is_active == False)

    products = query.order_by(Product.name.asc()).all()
    categories = ['Refill', 'New Container', 'Bottled Water', 'Supply']

    # Total counts
    total_count = Product.query.count()
    active_count = Product.query.filter_by(is_active=True).count()

    return render_template(
        'products/index.html',
        products=products,
        categories=categories,
        selected_category=category or 'all',
        selected_status=status or 'all',
        search=search,
        total_count=total_count,
        active_count=active_count
    )

@products_bp.route('/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Refill').strip()
        unit_price = float(request.form.get('unit_price', 0.0) or 0.0)
        container_type = request.form.get('container_type', 'Round').strip()
        is_refill = request.form.get('is_refill') == '1'
        is_active = request.form.get('is_active') == '1'

        if not code or not name or unit_price < 0:
            flash('Please provide a valid product code, name, and non-negative unit price.', 'danger')
            return redirect(url_for('products.index'))

        # Check unique code
        existing = Product.query.filter_by(code=code).first()
        if existing:
            flash(f"A product with code '{code}' already exists.", 'danger')
            return redirect(url_for('products.index'))

        product = Product(
            code=code,
            name=name,
            category=category,
            unit_price=unit_price,
            container_type=container_type,
            is_refill=is_refill,
            is_active=is_active
        )
        db.session.add(product)
        db.session.commit()

        flash(f"Product '{product.name}' ({product.code}) successfully created!", 'success')
        return redirect(url_for('products.index'))

    return redirect(url_for('products.index'))

@products_bp.route('/<int:id>/edit', methods=['POST'])
@login_required
@staff_required
def edit(id):
    product = Product.query.get_or_404(id)
    
    name = request.form.get('name', '').strip()
    category = request.form.get('category', product.category).strip()
    unit_price = float(request.form.get('unit_price', product.unit_price) or product.unit_price)
    container_type = request.form.get('container_type', product.container_type).strip()
    is_refill = request.form.get('is_refill') == '1'
    is_active = request.form.get('is_active') == '1'

    if not name or unit_price < 0:
        flash('Invalid product name or unit price.', 'danger')
        return redirect(url_for('products.index'))

    product.name = name
    product.category = category
    product.unit_price = unit_price
    product.container_type = container_type
    product.is_refill = is_refill
    product.is_active = is_active

    db.session.commit()
    flash(f"Product '{product.name}' successfully updated!", 'success')
    return redirect(url_for('products.index'))

@products_bp.route('/<int:id>/toggle-status', methods=['POST'])
@login_required
@staff_required
def toggle_status(id):
    product = Product.query.get_or_404(id)
    product.is_active = not product.is_active
    db.session.commit()
    status_str = "activated" if product.is_active else "deactivated"
    flash(f"Product '{product.name}' is now {status_str}.", 'info')
    return redirect(url_for('products.index'))
