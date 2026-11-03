from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from sqlalchemy import func
from models import db, Order, OrderItem, Customer, Product, User, Payment, InventoryItem, InventoryLog, SystemSetting
from routes.auth import login_required, cashier_required

pos_bp = Blueprint('pos', __name__)

def generate_pos_reference():
    year = datetime.now().year
    count = Order.query.filter(Order.order_number.like(f"POS-{year}-%")).count() + 1
    return f"POS-{year}-{count:04d}"

def generate_payment_number():
    year = datetime.now().year
    count = Payment.query.count() + 1
    return f"PAY-{year}-{count:04d}"

@pos_bp.route('/')
@login_required
@cashier_required
def index():
    # Active products by category
    products = Product.query.filter_by(is_active=True).all()
    categories = sorted(list(set(p.category for p in products)))
    
    # Active customers for selector
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name.asc()).all()
    default_walkin = Customer.query.filter_by(customer_type='Walk-in').first()

    # Inventory statuses
    inv_round = InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
    inv_slim = InventoryItem.query.filter_by(item_code='INV-SLM-5GAL').first()

    # Cashier stats for today
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    current_user_id = session.get('user_id')

    today_sales_cashier = db.session.query(func.coalesce(func.sum(Payment.amount), 0.0))\
        .filter(Payment.received_by == current_user_id, Payment.payment_date >= today_start, Payment.payment_date <= today_end)\
        .scalar()

    today_txns_cashier = Order.query.filter(Order.created_by == current_user_id, Order.order_date >= today_start, Order.order_date <= today_end).count()

    # Station settings
    station_name = SystemSetting.get_setting('station_name', current_app.config.get('STATION_NAME', 'Water Refilling System'))
    receipt_header = SystemSetting.get_setting('receipt_header', 'WATER REFILLING SYSTEM')

    return render_template(
        'pos/index.html',
        products=products,
        categories=categories,
        customers=customers,
        default_walkin=default_walkin,
        inv_round=inv_round,
        inv_slim=inv_slim,
        today_sales_cashier=today_sales_cashier,
        today_txns_cashier=today_txns_cashier,
        station_name=station_name,
        receipt_header=receipt_header,
        current_date=date.today().strftime('%b %d, %Y')
    )

@pos_bp.route('/checkout', methods=['POST'])
@login_required
@cashier_required
def checkout():
    try:
        current_user_id = session.get('user_id')
        
        # Form inputs
        customer_id = request.form.get('customer_id', type=int)
        walk_in_name = request.form.get('walk_in_name', '').strip()
        payment_method = request.form.get('payment_method', 'Cash').strip()
        amount_received = float(request.form.get('amount_received', 0.0) or 0.0)
        discount_type = request.form.get('discount_type', 'none')
        discount_value = float(request.form.get('discount_value', 0.0) or 0.0)
        notes = request.form.get('notes', '').strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.form.get('is_ajax') == '1'

        # Line items
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        bottle_exchanges = request.form.getlist('bottle_exchange[]') # 1 if bottle returned, 0 if not

        if not product_ids:
            msg = 'Cannot process sale: Cart is empty. Please select products.'
            if is_ajax:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'warning')
            return redirect(url_for('pos.index'))

        # Resolve Customer
        customer = None
        if customer_id:
            customer = db.session.get(Customer, customer_id)
        if not customer:
            customer = Customer.query.filter_by(customer_type='Walk-in').first()
            if not customer:
                customer = Customer(
                    name="Walk-in Customer",
                    customer_type="Walk-in",
                    contact_number="In-Store",
                    barangay="Station Walk-in",
                    purok_street="Store Counter"
                )
                db.session.add(customer)
                db.session.flush()

        # Build items and calculate subtotal
        subtotal = 0.0
        total_containers_delivered = 0
        total_empties_returned = 0
        items_to_create = []

        inv_round = InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
        inv_slim = InventoryItem.query.filter_by(item_code='INV-SLM-5GAL').first()
        cap_round = InventoryItem.query.filter_by(item_code='CAP-RND-BLUE').first()
        cap_slim = InventoryItem.query.filter_by(item_code='CAP-SLM-WHITE').first()
        seal_item = InventoryItem.query.filter_by(item_code='SEAL-HEAT-SHRINK').first()

        for idx, (p_id_str, q_str) in enumerate(zip(product_ids, quantities)):
            if not p_id_str or not q_str:
                continue
            p_id = int(p_id_str)
            qty = int(q_str)
            if qty <= 0:
                continue

            prod = db.session.get(Product, p_id)
            if not prod or not prod.is_active:
                continue

            line_subtotal = round(prod.unit_price * qty, 2)
            subtotal += line_subtotal

            # Check bottle exchange
            b_exchange = True
            if idx < len(bottle_exchanges):
                b_exchange = (bottle_exchanges[idx] in ['1', 'true', 'True', True])

            if prod.category in ['Refill', 'New Container']:
                total_containers_delivered += qty
                if prod.is_refill and b_exchange:
                    total_empties_returned += qty

            item_obj = OrderItem(
                product_id=prod.id,
                product_name=prod.name,
                quantity=qty,
                unit_price=prod.unit_price,
                subtotal=line_subtotal
            )
            items_to_create.append((item_obj, prod, qty, b_exchange))

        if not items_to_create:
            msg = 'No valid items in transaction cart.'
            if is_ajax:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'warning')
            return redirect(url_for('pos.index'))

        # Calculate discount
        discount_applied = 0.0
        if discount_type == 'pwd_senior':
            discount_applied = round(subtotal * 0.20, 2)
        elif discount_type == 'promo_5':
            discount_applied = round(subtotal * 0.05, 2)
        elif discount_type == 'promo_10':
            discount_applied = round(subtotal * 0.10, 2)
        elif discount_type == 'custom':
            discount_applied = min(subtotal, round(discount_value, 2))

        total_amount = max(0.0, round(subtotal - discount_applied, 2))

        # Payment Validation
        if payment_method == 'Cash':
            if amount_received < total_amount:
                msg = f"Insufficient cash tendered. Total is ₱{total_amount:,.2f}, received ₱{amount_received:,.2f}."
                if is_ajax:
                    return jsonify({'success': False, 'message': msg}), 400
                flash(msg, 'danger')
                return redirect(url_for('pos.index'))
            change_given = round(amount_received - total_amount, 2)
        else:
            # GCash, Card, Bank Transfer: exact amount received
            amount_received = total_amount
            change_given = 0.0

        # Create Order Transaction Record
        pos_ref = generate_pos_reference()
        customer_display_name = walk_in_name if walk_in_name else customer.name

        order = Order(
            order_number=pos_ref,
            customer_id=customer.id,
            order_type='Walk-in',
            delivery_address='Store Counter (Walk-in)',
            barangay=customer.barangay if customer.customer_type != 'Walk-in' else 'Station Walk-in',
            contact_number=customer.contact_number if customer.customer_type != 'Walk-in' else 'In-Store',
            order_date=datetime.utcnow(),
            delivery_date=date.today(),
            delivery_time_slot='Immediate In-Store',
            delivery_notes=notes or f'In-store walk-in sale ({payment_method})',
            assigned_staff_id=current_user_id,
            created_by=current_user_id,
            delivery_status='Completed',
            payment_status='Paid',
            total_amount=total_amount,
            amount_paid=total_amount,
            discount=discount_applied,
            amount_received=amount_received,
            change_given=change_given,
            walk_in_customer_name=customer_display_name,
            containers_delivered=total_containers_delivered,
            empty_containers_returned=total_empties_returned,
            delivered_at=datetime.utcnow()
        )

        db.session.add(order)
        db.session.flush()

        # Add Order Items and Update Inventory
        for item_obj, prod, qty, b_exchange in items_to_create:
            item_obj.order_id = order.id
            db.session.add(item_obj)

            # Auto-deduct inventory
            if prod.container_type == 'Round' and inv_round:
                inv_round.filled_stock = max(0, inv_round.filled_stock - qty)
                if prod.is_refill and b_exchange:
                    inv_round.empty_stock += qty
                
                log = InventoryLog(
                    item_id=inv_round.id,
                    action_type='POS Walk-in Sale',
                    quantity_change=-qty,
                    notes=f"POS Sale #{order.order_number} ({prod.name} x{qty})",
                    performed_by=current_user_id
                )
                db.session.add(log)

                # Deduct caps and seals for refill production balance
                if prod.is_refill:
                    if cap_round:
                        cap_round.quantity_on_hand = max(0, cap_round.quantity_on_hand - qty)
                    if seal_item:
                        seal_item.quantity_on_hand = max(0, seal_item.quantity_on_hand - qty)

            elif prod.container_type == 'Slim' and inv_slim:
                inv_slim.filled_stock = max(0, inv_slim.filled_stock - qty)
                if prod.is_refill and b_exchange:
                    inv_slim.empty_stock += qty
                
                log = InventoryLog(
                    item_id=inv_slim.id,
                    action_type='POS Walk-in Sale',
                    quantity_change=-qty,
                    notes=f"POS Sale #{order.order_number} ({prod.name} x{qty})",
                    performed_by=current_user_id
                )
                db.session.add(log)

                if prod.is_refill:
                    if cap_slim:
                        cap_slim.quantity_on_hand = max(0, cap_slim.quantity_on_hand - qty)
                    if seal_item:
                        seal_item.quantity_on_hand = max(0, seal_item.quantity_on_hand - qty)

        # Create Payment Record
        payment = Payment(
            payment_number=generate_payment_number(),
            customer_id=customer.id,
            order_id=order.id,
            amount=total_amount,
            payment_method=payment_method,
            payment_date=datetime.utcnow(),
            reference_no=order.order_number,
            notes=f"POS In-Store Walk-in ({payment_method})",
            received_by=current_user_id
        )
        db.session.add(payment)

        # If registered customer bought bottles without return, update customer container balance
        if customer.customer_type != 'Walk-in':
            bottle_diff = total_containers_delivered - total_empties_returned
            if bottle_diff != 0:
                customer.gallons_on_hand = max(0, customer.gallons_on_hand + bottle_diff)

        db.session.commit()

        if is_ajax:
            return jsonify({
                'success': True,
                'message': f"Transaction #{order.order_number} completed successfully!",
                'order_id': order.id,
                'order_number': order.order_number,
                'total_amount': order.total_amount,
                'amount_received': order.amount_received,
                'change_given': order.change_given,
                'receipt_url': url_for('pos.receipt', id=order.id)
            })

        flash(f"Sale #{order.order_number} completed! Total: ₱{total_amount:,.2f} | Change: ₱{change_given:,.2f}", 'success')
        return redirect(url_for('pos.receipt', id=order.id))

    except Exception as e:
        db.session.rollback()
        msg = f"Error processing POS sale: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.form.get('is_ajax') == '1':
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'danger')
        return redirect(url_for('pos.index'))

@pos_bp.route('/receipt/<int:id>')
@login_required
@cashier_required
def receipt(id):
    order = Order.query.get_or_404(id)
    payment = Payment.query.filter_by(order_id=order.id).first()
    station_name = SystemSetting.get_setting('station_name', current_app.config.get('STATION_NAME', 'Water Refilling System'))
    station_address = SystemSetting.get_setting('station_address', current_app.config.get('STATION_ADDRESS', ''))
    station_contact = SystemSetting.get_setting('station_contact', current_app.config.get('STATION_CONTACT', ''))
    receipt_header = SystemSetting.get_setting('receipt_header', 'WATER REFILLING SYSTEM')
    receipt_footer = SystemSetting.get_setting('receipt_footer', 'Thank you for your business! Clean, pure, and safe water every day.')

    return render_template(
        'pos/receipt.html',
        order=order,
        payment=payment,
        station_name=station_name,
        station_address=station_address,
        station_contact=station_contact,
        receipt_header=receipt_header,
        receipt_footer=receipt_footer
    )

@pos_bp.route('/quick-customer', methods=['POST'])
@login_required
@cashier_required
def quick_customer():
    name = request.form.get('name', '').strip()
    contact_number = request.form.get('contact_number', '').strip() or 'N/A'
    barangay = request.form.get('barangay', '').strip() or 'Poblacion Ward I'
    purok_street = request.form.get('purok_street', '').strip() or 'In-Store Registered'
    customer_type = request.form.get('customer_type', 'Household').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Customer name is required.'}), 400

    new_cust = Customer(
        name=name,
        contact_number=contact_number,
        barangay=barangay,
        purok_street=purok_street,
        customer_type=customer_type,
        gallons_on_hand=0,
        outstanding_balance=0.0
    )
    db.session.add(new_cust)
    db.session.commit()

    return jsonify({
        'success': True,
        'customer_id': new_cust.id,
        'customer_name': new_cust.name,
        'customer_type': new_cust.customer_type,
        'barangay': new_cust.barangay,
        'message': f"Customer '{new_cust.name}' registered successfully!"
    })
