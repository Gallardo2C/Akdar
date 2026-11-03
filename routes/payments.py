from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy import func
from models import db, Payment, Customer, Order, User
from routes.auth import login_required

payments_bp = Blueprint('payments', __name__)

def generate_payment_number():
    year = datetime.now().year
    count = Payment.query.count() + 1
    return f"PAY-{year}-{count:04d}"

@payments_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    date_filter = request.args.get('date', '').strip()
    payment_method = request.args.get('method', '').strip()

    query = Payment.query

    if search:
        search_filter = f"%{search}%"
        query = query.join(Customer).filter(
            (Payment.payment_number.ilike(search_filter)) |
            (Customer.name.ilike(search_filter)) |
            (Payment.reference_no.ilike(search_filter))
        )

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            start_date = datetime.combine(filter_date, datetime.min.time())
            end_date = datetime.combine(filter_date, datetime.max.time())
            query = query.filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
        except ValueError:
            pass

    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)

    payments = query.order_by(Payment.payment_date.desc()).all()
    
    # Total collected sum
    total_collected = sum(p.amount for p in payments)
    
    # Active customers for quick collection modal
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name.asc()).all()

    return render_template(
        'payments/index.html',
        payments=payments,
        total_collected=total_collected,
        search=search,
        selected_date=date_filter,
        selected_method=payment_method,
        customers=customers
    )

@payments_bp.route('/receivables')
@login_required
def receivables():
    # Customers with outstanding balances
    customers_with_balance = Customer.query.filter(Customer.outstanding_balance > 0).order_by(Customer.outstanding_balance.desc()).all()
    total_uncollected = sum(c.outstanding_balance for c in customers_with_balance)

    # Unpaid orders list
    unpaid_orders = Order.query.filter(Order.payment_status.in_(['Unpaid', 'Partial']), Order.delivery_status == 'Delivered').order_by(Order.created_at.desc()).all()

    return render_template(
        'payments/receivables.html',
        customers=customers_with_balance,
        total_uncollected=total_uncollected,
        unpaid_orders=unpaid_orders
    )

@payments_bp.route('/record', methods=['POST'])
@login_required
def record():
    customer_id = request.form.get('customer_id', type=int)
    order_id = request.form.get('order_id', type=int) or None
    amount = float(request.form.get('amount', 0.0) or 0.0)
    payment_method = request.form.get('payment_method', 'Cash')
    reference_no = request.form.get('reference_no', '').strip()
    notes = request.form.get('notes', '').strip()

    if not customer_id or amount <= 0:
        flash('Please select a valid customer and payment amount greater than zero.', 'danger')
        return redirect(request.referrer or url_for('payments.index'))

    customer = Customer.query.get_or_404(customer_id)

    # Create Payment transaction
    pay = Payment(
        payment_number=generate_payment_number(),
        customer_id=customer.id,
        order_id=order_id,
        amount=amount,
        payment_method=payment_method,
        payment_date=datetime.utcnow(),
        reference_no=reference_no,
        notes=notes or f'Balance payment collection for {customer.name}',
        received_by=session.get('user_id')
    )
    db.session.add(pay)

    # Deduct from customer's outstanding balance
    customer.outstanding_balance = max(0.0, customer.outstanding_balance - amount)

    # If linked to a specific order, update order payment details
    if order_id:
        order = db.session.get(Order, order_id)
        if order:
            order.amount_paid += amount
            if order.amount_paid >= order.total_amount:
                order.payment_status = 'Paid'
            else:
                order.payment_status = 'Partial'

    db.session.commit()
    flash(f'Payment of P{amount:,.2f} recorded successfully for {customer.name}! Receipt #{pay.payment_number}.', 'success')
    return redirect(request.referrer or url_for('payments.index'))

@payments_bp.route('/<int:id>/receipt')
@login_required
def receipt(id):
    payment = Payment.query.get_or_404(id)
    return render_template('payments/receipt.html', payment=payment)
