import csv
import io
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, Response, session
from sqlalchemy import func
from models import db, Order, OrderItem, Payment, Customer, InventoryItem, Product, User
from routes.auth import login_required, admin_required

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    today = date.today()
    preset = request.args.get('preset', 'month') # today, week, month, year, custom
    
    if preset == 'today':
        start_date = today
        end_date = today
    elif preset == 'week':
        start_date = today - timedelta(days=today.weekday()) # Start of current week (Monday)
        end_date = today
    elif preset == 'year':
        start_date = date(today.year, 1, 1)
        end_date = today
    elif preset == 'month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    else:
        # custom
        start_str = request.args.get('start_date', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_str = request.args.get('end_date', today.strftime('%Y-%m-%d'))
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)
        try:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Orders within period
    period_orders = Order.query.filter(Order.delivery_date >= start_date, Order.delivery_date <= end_date).order_by(Order.created_at.desc()).all()
    
    total_orders = len(period_orders)
    completed_orders = [o for o in period_orders if o.delivery_status in ['Delivered', 'Completed']]
    total_completed = len(completed_orders)
    total_sales_value = sum(o.total_amount for o in completed_orders)
    
    # Walk-in vs Delivery breakdown
    walkin_orders = [o for o in completed_orders if o.order_type == 'Walk-in']
    delivery_orders = [o for o in completed_orders if o.order_type != 'Walk-in']
    walkin_sales = sum(o.total_amount for o in walkin_orders)
    delivery_sales = sum(o.total_amount for o in delivery_orders)

    total_gallons_delivered = sum(o.containers_delivered for o in completed_orders)
    total_empties_collected = sum(o.empty_containers_returned for o in completed_orders)

    # Actual payments collected within period
    period_payments = Payment.query.filter(Payment.payment_date >= start_dt, Payment.payment_date <= end_dt).all()
    total_payments_collected = sum(p.amount for p in period_payments)

    # Best-selling products during this period
    product_stats = {}
    for o in completed_orders:
        for item in o.items:
            pname = item.product_name
            if pname not in product_stats:
                product_stats[pname] = {'quantity': 0, 'revenue': 0.0}
            product_stats[pname]['quantity'] += item.quantity
            product_stats[pname]['revenue'] += item.subtotal

    best_selling_products = sorted(
        [{'name': k, 'quantity': v['quantity'], 'revenue': v['revenue']} for k, v in product_stats.items()],
        key=lambda x: x['revenue'],
        reverse=True
    )

    # Cashier Transaction Summaries
    cashier_stats = {}
    for o in completed_orders:
        creator_name = o.creator.full_name if o.creator else 'System/Admin'
        if creator_name not in cashier_stats:
            cashier_stats[creator_name] = {'transactions': 0, 'sales': 0.0, 'walkin': 0, 'delivery': 0}
        cashier_stats[creator_name]['transactions'] += 1
        cashier_stats[creator_name]['sales'] += o.total_amount
        if o.order_type == 'Walk-in':
            cashier_stats[creator_name]['walkin'] += 1
        else:
            cashier_stats[creator_name]['delivery'] += 1

    cashier_summaries = sorted(
        [{'cashier': k, 'transactions': v['transactions'], 'sales': v['sales'], 'walkin': v['walkin'], 'delivery': v['delivery']} for k, v in cashier_stats.items()],
        key=lambda x: x['sales'],
        reverse=True
    )

    # Barangay delivery distribution
    barangay_stats = {}
    for o in delivery_orders:
        b = o.barangay or 'Unknown'
        barangay_stats[b] = barangay_stats.get(b, 0) + o.containers_delivered
    top_barangays = sorted(barangay_stats.items(), key=lambda x: x[1], reverse=True)

    # Inventory status & low stock items
    inventory_items = InventoryItem.query.all()
    low_stock_items = [item for item in inventory_items if item.is_low_stock]

    # Outstanding credit status
    total_unpaid_receivables = db.session.query(func.coalesce(func.sum(Customer.outstanding_balance), 0.0)).scalar()

    return render_template(
        'reports/index.html',
        preset=preset,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        total_orders=total_orders,
        total_completed=total_completed,
        total_sales_value=total_sales_value,
        walkin_sales=walkin_sales,
        delivery_sales=delivery_sales,
        walkin_count=len(walkin_orders),
        delivery_count=len(delivery_orders),
        total_payments_collected=total_payments_collected,
        total_gallons_delivered=total_gallons_delivered,
        total_empties_collected=total_empties_collected,
        total_unpaid_receivables=total_unpaid_receivables,
        best_selling_products=best_selling_products,
        cashier_summaries=cashier_summaries,
        top_barangays=top_barangays,
        completed_orders=completed_orders,
        inventory_items=inventory_items,
        low_stock_items=low_stock_items
    )

@reports_bp.route('/gallon-audit')
@login_required
def gallon_audit():
    containers = InventoryItem.query.filter_by(category='Container').all()
    customers_with_gallons = Customer.query.filter(Customer.gallons_on_hand > 0).order_by(Customer.gallons_on_hand.desc()).all()
    total_gallons_with_customers = sum(c.gallons_on_hand for c in customers_with_gallons)

    return render_template(
        'reports/gallon_audit.html',
        containers=containers,
        customers_with_gallons=customers_with_gallons,
        total_gallons_with_customers=total_gallons_with_customers
    )

@reports_bp.route('/export-sales')
@login_required
def export_sales():
    orders = Order.query.order_by(Order.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Reference No.',
        'Order Type',
        'Customer Name',
        'Location / Barangay',
        'Date & Time',
        'Status',
        'Payment Status',
        'Payment Method',
        'Total Amount (PHP)',
        'Discount (PHP)',
        'Amount Paid (PHP)',
        'Cashier / Staff'
    ])

    for o in orders:
        writer.writerow([
            o.order_number,
            o.order_type,
            o.display_customer_name,
            o.barangay,
            o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else '',
            o.delivery_status,
            o.payment_status,
            o.payment_method or 'Cash',
            f"{o.total_amount:.2f}",
            f"{o.discount:.2f}",
            f"{o.amount_paid:.2f}",
            o.creator.full_name if o.creator else 'System'
        ])

    output.seek(0)
    filename = f"Water_Refilling_Sales_Report_{date.today().strftime('%Y%m%d')}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
