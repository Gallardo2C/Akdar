from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from models import db, Customer, Order, Payment
from routes.auth import login_required

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/')
@login_required
def index():
    query = Customer.query.filter_by(is_active=True)
    
    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Customer.name.ilike(search_filter)) |
            (Customer.contact_number.ilike(search_filter)) |
            (Customer.purok_street.ilike(search_filter)) |
            (Customer.barangay.ilike(search_filter))
        )
        
    # Barangay filter
    barangay = request.args.get('barangay', '').strip()
    if barangay:
        query = query.filter(Customer.barangay == barangay)
        
    # Customer type filter
    customer_type = request.args.get('type', '').strip()
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)
    else:
        # Hide the system generic walk-in profile unless explicitly searched
        if not search:
            query = query.filter(Customer.customer_type != 'Walk-in')
        
    # Balance filter
    has_debt = request.args.get('has_debt', '')
    if has_debt == '1':
        query = query.filter(Customer.outstanding_balance > 0)

    customers = query.order_by(Customer.name.asc()).all()
    barangays = current_app.config.get('MINGLANILLA_BARANGAYS', [])

    total_registered = Customer.query.filter(Customer.is_active == True, Customer.customer_type != 'Walk-in').count()
    with_balance_count = Customer.query.filter(Customer.outstanding_balance > 0).count()

    return render_template(
        'customers/index.html',
        customers=customers,
        search=search,
        selected_barangay=barangay,
        selected_type=customer_type,
        has_debt=has_debt,
        barangays=barangays,
        total_registered=total_registered,
        with_balance_count=with_balance_count
    )

@customers_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    barangays = current_app.config.get('MINGLANILLA_BARANGAYS', [])
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        customer_type = request.form.get('customer_type', 'Household')
        contact_number = request.form.get('contact_number', '').strip()
        barangay = request.form.get('barangay', '').strip()
        purok_street = request.form.get('purok_street', '').strip()
        landmark_notes = request.form.get('landmark_notes', '').strip()
        initial_gallons = int(request.form.get('initial_gallons', 0) or 0)
        initial_balance = float(request.form.get('initial_balance', 0.0) or 0.0)

        if not name or not contact_number or not barangay or not purok_street:
            flash('Please fill in all required customer fields.', 'danger')
            return render_template('customers/form.html', barangays=barangays, customer=None)

        customer = Customer(
            name=name,
            customer_type=customer_type,
            contact_number=contact_number,
            barangay=barangay,
            purok_street=purok_street,
            landmark_notes=landmark_notes,
            gallons_on_hand=initial_gallons,
            outstanding_balance=initial_balance
        )
        db.session.add(customer)
        db.session.commit()

        flash(f'Customer "{customer.name}" registered successfully.', 'success')
        return redirect(url_for('customers.view', id=customer.id))

    return render_template('customers/form.html', barangays=barangays, customer=None)

@customers_bp.route('/<int:id>')
@login_required
def view(id):
    customer = Customer.query.get_or_404(id)
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    payments = Payment.query.filter_by(customer_id=customer.id).order_by(Payment.payment_date.desc()).all()
    
    # Calculate stats for this customer
    completed_orders = [o for o in orders if o.delivery_status in ['Delivered', 'Completed']]
    total_spent = sum(o.total_amount for o in completed_orders)
    total_orders_count = len(orders)
    total_gallons_received = sum(o.containers_delivered for o in completed_orders)
    total_gallons_returned = sum(o.empty_containers_returned for o in completed_orders)

    return render_template(
        'customers/view.html',
        customer=customer,
        orders=orders,
        payments=payments,
        total_spent=total_spent,
        total_orders_count=total_orders_count,
        total_gallons_received=total_gallons_received,
        total_gallons_returned=total_gallons_returned
    )

@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = Customer.query.get_or_404(id)
    barangays = current_app.config.get('MINGLANILLA_BARANGAYS', [])

    if request.method == 'POST':
        customer.name = request.form.get('name', '').strip()
        customer.customer_type = request.form.get('customer_type', 'Household')
        customer.contact_number = request.form.get('contact_number', '').strip()
        customer.barangay = request.form.get('barangay', '').strip()
        customer.purok_street = request.form.get('purok_street', '').strip()
        customer.landmark_notes = request.form.get('landmark_notes', '').strip()
        
        # Admin can adjust containers or balance directly if reconciling
        if session.get('user_role') == 'admin':
            customer.gallons_on_hand = int(request.form.get('gallons_on_hand', customer.gallons_on_hand) or 0)
            customer.outstanding_balance = float(request.form.get('outstanding_balance', customer.outstanding_balance) or 0.0)

        db.session.commit()
        flash(f'Customer "{customer.name}" profile updated.', 'success')
        return redirect(url_for('customers.view', id=customer.id))

    return render_template('customers/form.html', barangays=barangays, customer=customer)

@customers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    customer = Customer.query.get_or_404(id)
    customer.is_active = False
    db.session.commit()
    flash(f'Customer "{customer.name}" has been deactivated.', 'info')
    return redirect(url_for('customers.index'))
