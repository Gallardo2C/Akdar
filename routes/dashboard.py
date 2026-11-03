from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, session
from sqlalchemy import func
from models import db, Order, Customer, Payment, InventoryItem, Product, User
from routes.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    start_of_today = datetime.combine(today, datetime.min.time())
    end_of_today = datetime.combine(today, datetime.max.time())

    # Today's Orders & Transactions (Both Walk-in and Delivery)
    today_orders = Order.query.filter(Order.delivery_date == today).all()
    today_total_transactions = len(today_orders)
    
    today_walkin_count = sum(1 for o in today_orders if o.order_type == 'Walk-in')
    today_delivery_count = sum(1 for o in today_orders if o.order_type != 'Walk-in')
    
    today_pending = sum(1 for o in today_orders if o.delivery_status == 'Pending')
    today_dispatched = sum(1 for o in today_orders if o.delivery_status == 'Dispatched')
    today_completed = sum(1 for o in today_orders if o.delivery_status in ['Delivered', 'Completed'])
    today_cancelled = sum(1 for o in today_orders if o.delivery_status == 'Cancelled')

    # Total containers delivered today
    today_gallons_delivered = sum(o.containers_delivered for o in today_orders if o.delivery_status in ['Delivered', 'Completed'])
    today_gallons_returned = sum(o.empty_containers_returned for o in today_orders if o.delivery_status in ['Delivered', 'Completed'])

    # Revenue & Receivables
    today_sales = db.session.query(func.coalesce(func.sum(Payment.amount), 0.0))\
        .filter(Payment.payment_date >= start_of_today, Payment.payment_date <= end_of_today)\
        .scalar()

    total_all_time_transactions = Order.query.count()

    total_receivables = db.session.query(func.coalesce(func.sum(Customer.outstanding_balance), 0.0))\
        .filter(Customer.outstanding_balance > 0)\
        .scalar()

    total_registered_customers = Customer.query.filter(Customer.is_active == True, Customer.customer_type != 'Walk-in').count()
    customers_with_debt = Customer.query.filter(Customer.outstanding_balance > 0).count()

    total_products = Product.query.filter_by(is_active=True).count()

    # Inventory Metrics
    round_container = InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
    slim_container = InventoryItem.query.filter_by(item_code='INV-SLM-5GAL').first()

    total_filled = (round_container.filled_stock if round_container else 0) + (slim_container.filled_stock if slim_container else 0)
    total_empty = (round_container.empty_stock if round_container else 0) + (slim_container.empty_stock if slim_container else 0)
    total_loaned = (round_container.loaned_stock if round_container else 0) + (slim_container.loaned_stock if slim_container else 0)
    total_damaged = (round_container.damaged_stock if round_container else 0) + (slim_container.damaged_stock if slim_container else 0)

    # Low stock alerts
    low_stock_items = [item for item in InventoryItem.query.all() if item.is_low_stock]

    # Recent transactions (both Walk-in POS and Delivery orders)
    recent_transactions = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    # 7-day trend chart
    chart_dates = []
    chart_sales_amounts = []
    chart_walkin_counts = []
    chart_delivery_counts = []

    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())
        chart_dates.append(day_date.strftime('%b %d'))

        # Sales collected
        d_sales = db.session.query(func.coalesce(func.sum(Payment.amount), 0.0))\
            .filter(Payment.payment_date >= day_start, Payment.payment_date <= day_end)\
            .scalar()
        chart_sales_amounts.append(float(d_sales))

        # Walk-in vs Delivery
        w_count = Order.query.filter(Order.delivery_date == day_date, Order.order_type == 'Walk-in').count()
        d_count = Order.query.filter(Order.delivery_date == day_date, Order.order_type != 'Walk-in').count()
        chart_walkin_counts.append(w_count)
        chart_delivery_counts.append(d_count)

    # Active riders for dispatch
    riders = User.query.filter(User.role.in_(['rider', 'staff', 'admin']), User.is_active == True).all()

    return render_template(
        'dashboard/index.html',
        today=today,
        today_total_transactions=today_total_transactions,
        today_walkin_count=today_walkin_count,
        today_delivery_count=today_delivery_count,
        today_pending=today_pending,
        today_dispatched=today_dispatched,
        today_completed=today_completed,
        today_cancelled=today_cancelled,
        today_gallons_delivered=today_gallons_delivered,
        today_gallons_returned=today_gallons_returned,
        today_sales=today_sales,
        total_all_time_transactions=total_all_time_transactions,
        total_receivables=total_receivables,
        total_registered_customers=total_registered_customers,
        total_products=total_products,
        customers_with_debt=customers_with_debt,
        round_container=round_container,
        slim_container=slim_container,
        total_filled=total_filled,
        total_empty=total_empty,
        total_loaned=total_loaned,
        total_damaged=total_damaged,
        low_stock_items=low_stock_items,
        recent_transactions=recent_transactions,
        chart_dates=chart_dates,
        chart_sales_amounts=chart_sales_amounts,
        chart_walkin_counts=chart_walkin_counts,
        chart_delivery_counts=chart_delivery_counts,
        riders=riders
    )
