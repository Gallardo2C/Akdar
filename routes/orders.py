from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from sqlalchemy import func
from models import db, Order, OrderItem, Customer, Product, User, Payment, InventoryItem, InventoryLog, SystemSetting
from routes.auth import login_required

orders_bp = Blueprint('orders', __name__)

def generate_order_number():
    year = datetime.now().year
    count = Order.query.filter(Order.order_number.like(f"WDMS-{year}-%")).count() + 1
    return f"WDMS-{year}-{count:04d}"

def generate_payment_number():
    year = datetime.now().year
    count = Payment.query.count() + 1
    return f"PAY-{year}-{count:04d}"

@orders_bp.route('/')
@login_required
def index():
    status = request.args.get('status', '').strip()
    date_filter = request.args.get('date', '').strip()
    rider_id = request.args.get('rider_id', '').strip()
    search = request.args.get('search', '').strip()
    order_type = request.args.get('order_type', '').strip()

    query = Order.query

    if order_type and order_type != 'all':
        query = query.filter(Order.order_type == order_type)

    if status and status != 'all':
        if status == 'Completed':
            query = query.filter(Order.delivery_status.in_(['Delivered', 'Completed']))
        else:
            query = query.filter(Order.delivery_status == status)

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Order.delivery_date == filter_date)
        except ValueError:
            pass

    if rider_id:
        query = query.filter(Order.assigned_staff_id == int(rider_id))

    if search:
        search_filter = f"%{search}%"
        query = query.outerjoin(Customer).filter(
            (Order.order_number.ilike(search_filter)) |
            (Customer.name.ilike(search_filter)) |
            (Order.walk_in_customer_name.ilike(search_filter)) |
            (Order.barangay.ilike(search_filter)) |
            (Order.contact_number.ilike(search_filter))
        )

    orders = query.order_by(Order.created_at.desc()).all()
    riders = User.query.filter(User.role.in_(['rider', 'staff', 'admin']), User.is_active == True).all()

    # Counts for quick filter tabs
    all_count = Order.query.count()
    walkin_count = Order.query.filter_by(order_type='Walk-in').count()
    delivery_count = Order.query.filter(Order.order_type != 'Walk-in').count()
    pending_count = Order.query.filter_by(delivery_status='Pending').count()
    dispatched_count = Order.query.filter_by(delivery_status='Dispatched').count()
    delivered_count = Order.query.filter(Order.delivery_status.in_(['Delivered', 'Completed'])).count()
    cancelled_count = Order.query.filter_by(delivery_status='Cancelled').count()

    return render_template(
        'orders/index.html',
        orders=orders,
        selected_status=status or 'all',
        selected_type=order_type or 'all',
        selected_date=date_filter,
        selected_rider=rider_id,
        search=search,
        riders=riders,
        all_count=all_count,
        walkin_count=walkin_count,
        delivery_count=delivery_count,
        pending_count=pending_count,
        dispatched_count=dispatched_count,
        delivered_count=delivered_count,
        cancelled_count=cancelled_count
    )

@orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    customers = Customer.query.filter(Customer.is_active == True, Customer.customer_type != 'Walk-in').order_by(Customer.name.asc()).all()
    products = Product.query.filter_by(is_active=True).all()
    riders = User.query.filter(User.role.in_(['rider', 'staff', 'admin']), User.is_active == True).all()
    barangays = current_app.config.get('MINGLANILLA_BARANGAYS', [])

    preselected_customer_id = request.args.get('customer_id', type=int)

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        customer = db.session.get(Customer, customer_id)
        if not customer:
            flash('Invalid customer selected for delivery order.', 'danger')
            return redirect(url_for('orders.create'))

        delivery_date_str = request.form.get('delivery_date')
        try:
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date() if delivery_date_str else date.today()
        except ValueError:
            delivery_date = date.today()

        delivery_time_slot = request.form.get('delivery_time_slot', 'Morning (8:00 AM - 12:00 NN)')
        delivery_address = request.form.get('delivery_address', customer.full_address).strip()
        barangay = request.form.get('barangay', customer.barangay).strip()
        contact_number = request.form.get('contact_number', customer.contact_number).strip()
        delivery_notes = request.form.get('delivery_notes', '').strip()
        assigned_staff_id = request.form.get('assigned_staff_id', type=int) or None

        # Parse line items from form
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        if not product_ids:
            flash('Please select at least one product for this delivery order.', 'warning')
            return redirect(url_for('orders.create', customer_id=customer_id))

        total_amount = 0.0
        total_containers = 0
        items_to_add = []

        for p_id_str, q_str in zip(product_ids, quantities):
            if not p_id_str or not q_str:
                continue
            p_id = int(p_id_str)
            qty = int(q_str)
            if qty <= 0:
                continue
            
            prod = db.session.get(Product, p_id)
            if prod:
                subtotal = prod.unit_price * qty
                total_amount += subtotal
                if prod.category in ['Refill', 'New Container']:
                    total_containers += qty

                items_to_add.append(OrderItem(
                    product_id=prod.id,
                    product_name=prod.name,
                    quantity=qty,
                    unit_price=prod.unit_price,
                    subtotal=subtotal
                ))

        if not items_to_add:
            flash('Please specify valid product quantities.', 'warning')
            return redirect(url_for('orders.create', customer_id=customer_id))

        order = Order(
            order_number=generate_order_number(),
            customer_id=customer.id,
            order_type='Delivery',
            delivery_address=delivery_address,
            barangay=barangay,
            contact_number=contact_number,
            order_date=datetime.utcnow(),
            delivery_date=delivery_date,
            delivery_time_slot=delivery_time_slot,
            delivery_notes=delivery_notes,
            assigned_staff_id=assigned_staff_id,
            created_by=session.get('user_id'),
            delivery_status='Pending',
            payment_status='Unpaid',
            total_amount=total_amount,
            amount_paid=0.0,
            containers_delivered=total_containers,
            empty_containers_returned=0
        )

        db.session.add(order)
        db.session.flush()

        for item in items_to_add:
            item.order_id = order.id
            db.session.add(item)

        db.session.commit()
        flash(f'Delivery Order #{order.order_number} successfully created for {customer.name}!', 'success')
        return redirect(url_for('orders.view', id=order.id))

    return render_template(
        'orders/create.html',
        customers=customers,
        products=products,
        riders=riders,
        barangays=barangays,
        preselected_customer_id=preselected_customer_id,
        today_date=date.today().strftime('%Y-%m-%d')
    )

@orders_bp.route('/<int:id>')
@login_required
def view(id):
    order = Order.query.get_or_404(id)
    riders = User.query.filter(User.role.in_(['rider', 'staff', 'admin']), User.is_active == True).all()
    return render_template('orders/view.html', order=order, riders=riders)

@orders_bp.route('/<int:id>/status', methods=['POST'])
@login_required
def update_status(id):
    order = Order.query.get_or_404(id)
    new_status = request.form.get('delivery_status')
    current_user_id = session.get('user_id')

    if new_status == 'Dispatched':
        rider_id = request.form.get('assigned_staff_id', type=int)
        if rider_id:
            order.assigned_staff_id = rider_id
        order.delivery_status = 'Dispatched'
        
        # Deduct filled containers from inventory stock
        inv_round = InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
        inv_slim = InventoryItem.query.filter_by(item_code='INV-SLM-5GAL').first()

        for item in order.items:
            if item.product and item.product.container_type == 'Round' and inv_round:
                inv_round.filled_stock = max(0, inv_round.filled_stock - item.quantity)
                log = InventoryLog(
                    item_id=inv_round.id,
                    action_type='Dispatched Delivery',
                    quantity_change=-item.quantity,
                    notes=f'Dispatched for Order #{order.order_number}',
                    performed_by=current_user_id
                )
                db.session.add(log)
            elif item.product and item.product.container_type == 'Slim' and inv_slim:
                inv_slim.filled_stock = max(0, inv_slim.filled_stock - item.quantity)
                log = InventoryLog(
                    item_id=inv_slim.id,
                    action_type='Dispatched Delivery',
                    quantity_change=-item.quantity,
                    notes=f'Dispatched for Order #{order.order_number}',
                    performed_by=current_user_id
                )
                db.session.add(log)

        db.session.commit()
        flash(f'Order #{order.order_number} marked as Out for Delivery / Dispatched.', 'info')

    elif new_status == 'Delivered':
        empties_returned = int(request.form.get('empty_containers_returned', 0) or 0)
        payment_option = request.form.get('payment_option', 'cash_full')  # 'cash_full', 'credit', 'partial'
        payment_method = request.form.get('payment_method', 'Cash on Delivery')
        amount_collected = float(request.form.get('amount_collected', 0.0) or 0.0)
        payment_reference = request.form.get('payment_reference', '').strip()

        order.delivery_status = 'Delivered'
        order.delivered_at = datetime.utcnow()
        order.empty_containers_returned = empties_returned

        # Update customer gallon balance
        gallon_delta = order.containers_delivered - empties_returned
        order.customer.gallons_on_hand = max(0, order.customer.gallons_on_hand + gallon_delta)

        # Inventory container tracking:
        inv_round = InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
        inv_slim = InventoryItem.query.filter_by(item_code='INV-SLM-5GAL').first()

        if inv_round:
            inv_round.empty_stock += empties_returned
            inv_round.loaned_stock = max(0, inv_round.loaned_stock + gallon_delta)
            log_empty = InventoryLog(
                item_id=inv_round.id,
                action_type='Empties Returned',
                quantity_change=empties_returned,
                notes=f'Returned empties from delivery #{order.order_number}',
                performed_by=current_user_id
            )
            db.session.add(log_empty)

        # Handle Payment Recording
        if payment_option == 'cash_full':
            order.payment_status = 'Paid'
            order.amount_paid = order.total_amount

            pay = Payment(
                payment_number=generate_payment_number(),
                customer_id=order.customer_id,
                order_id=order.id,
                amount=order.total_amount,
                payment_method=payment_method,
                payment_date=datetime.utcnow(),
                reference_no=payment_reference,
                notes=f'Payment for Order #{order.order_number}',
                received_by=current_user_id
            )
            db.session.add(pay)

        elif payment_option == 'partial':
            order.amount_paid = amount_collected
            remaining_balance = max(0.0, order.total_amount - amount_collected)

            if amount_collected > 0:
                pay = Payment(
                    payment_number=generate_payment_number(),
                    customer_id=order.customer_id,
                    order_id=order.id,
                    amount=amount_collected,
                    payment_method=payment_method,
                    payment_date=datetime.utcnow(),
                    reference_no=payment_reference,
                    notes=f'Partial payment for Order #{order.order_number}',
                    received_by=current_user_id
                )
                db.session.add(pay)

            if remaining_balance > 0:
                order.payment_status = 'Partial'
                order.customer.outstanding_balance += remaining_balance
            else:
                order.payment_status = 'Paid'

        elif payment_option == 'credit':
            order.payment_status = 'Unpaid'
            order.amount_paid = 0.0
            order.customer.outstanding_balance += order.total_amount

        db.session.commit()
        flash(f'Order #{order.order_number} marked as Delivered! Container count & payment updated.', 'success')

    elif new_status == 'Cancelled':
        order.delivery_status = 'Cancelled'
        db.session.commit()
        flash(f'Order #{order.order_number} has been cancelled.', 'warning')

    return redirect(url_for('orders.view', id=order.id))

@orders_bp.route('/<int:id>/receipt')
@login_required
def receipt(id):
    order = Order.query.get_or_404(id)
    if order.order_type == 'Walk-in':
        return redirect(url_for('pos.receipt', id=order.id))
    
    station_name = SystemSetting.get_setting('station_name', current_app.config.get('STATION_NAME', 'Water Refilling System'))
    station_address = SystemSetting.get_setting('station_address', current_app.config.get('STATION_ADDRESS', ''))
    station_contact = SystemSetting.get_setting('station_contact', current_app.config.get('STATION_CONTACT', ''))
    receipt_header = SystemSetting.get_setting('receipt_header', 'WATER REFILLING SYSTEM')

    return render_template(
        'orders/receipt.html',
        order=order,
        station_name=station_name,
        station_address=station_address,
        station_contact=station_contact,
        receipt_header=receipt_header
    )
