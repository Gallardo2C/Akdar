from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')  # 'admin', 'cashier', 'staff', 'rider'
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders_created = db.relationship('Order', foreign_keys='Order.created_by', backref='creator', lazy=True)
    orders_assigned = db.relationship('Order', foreign_keys='Order.assigned_staff_id', backref='rider', lazy=True)
    payments_received = db.relationship('Payment', backref='receiver', lazy=True)
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_cashier(self):
        return self.role in ['cashier', 'admin', 'staff']

    def can_manage_employees(self):
        return self.role == 'admin'

    def can_manage_settings(self):
        return self.role == 'admin'

    def can_manage_products(self):
        return self.role in ['admin', 'staff']

    def can_access_pos(self):
        return self.role in ['cashier', 'admin', 'staff']

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    customer_type = db.Column(db.String(50), nullable=False, default='Household') 
    # Household, Commercial / Sari-sari Store, Office / Business, Eatery / Carinderia, Walk-in
    contact_number = db.Column(db.String(25), nullable=False)
    barangay = db.Column(db.String(80), nullable=False)  # Minglanilla Barangays or In-Store
    purok_street = db.Column(db.String(150), nullable=False)
    landmark_notes = db.Column(db.String(200), nullable=True)
    
    outstanding_balance = db.Column(db.Float, default=0.0)  # Unpaid credits in PHP
    gallons_on_hand = db.Column(db.Integer, default=0)       # Containers currently with customer
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders = db.relationship('Order', backref='customer', lazy=True, order_by='desc(Order.created_at)')
    payments = db.relationship('Payment', backref='customer', lazy=True, order_by='desc(Payment.payment_date)')

    @property
    def full_address(self):
        if self.customer_type == 'Walk-in' and not self.purok_street:
            return "Physical Walk-in (In-Store)"
        parts = [self.purok_street, self.barangay, "Minglanilla, Cebu"]
        return ", ".join([p for p in parts if p])

    @property
    def completed_orders_count(self):
        return sum(1 for o in self.orders if o.delivery_status in ['Delivered', 'Completed'])

    @property
    def total_spent(self):
        return sum(o.total_amount for o in self.orders if o.delivery_status in ['Delivered', 'Completed'])

    @property
    def is_returning(self):
        return self.completed_orders_count > 1

    def __repr__(self):
        return f"<Customer {self.name} - {self.barangay}>"


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(40), nullable=False, default='Refill') # Refill, New Container, Bottled Water, Supply
    unit_price = db.Column(db.Float, nullable=False)
    container_type = db.Column(db.String(30), default='Round') # Round, Slim, Small, None
    is_refill = db.Column(db.Boolean, default=True) # Requires/expects an empty return
    is_active = db.Column(db.Boolean, default=True)

    @property
    def inventory_item(self):
        """Link to corresponding InventoryItem if available"""
        if self.container_type == 'Round':
            return InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
        elif self.container_type == 'Slim':
            return InventoryItem.query.filter_by(item_code='INV-SLM-5GAL').first()
        elif 'CAP' in self.code.upper():
            return InventoryItem.query.filter(InventoryItem.item_code.like('%CAP%')).first()
        return None

    @property
    def current_stock_display(self):
        inv = self.inventory_item
        if inv:
            if inv.category == 'Container':
                return f"{inv.filled_stock} ready"
            return f"{inv.quantity_on_hand} {inv.unit}"
        return "In Stock"

    def __repr__(self):
        return f"<Product {self.name} - P{self.unit_price:.2f}>"


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    order_type = db.Column(db.String(25), default='Delivery') # 'Delivery' or 'Walk-in'
    
    delivery_address = db.Column(db.String(250), nullable=False)
    barangay = db.Column(db.String(80), nullable=False)
    contact_number = db.Column(db.String(25), nullable=False)
    
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_date = db.Column(db.Date, default=date.today)
    delivery_time_slot = db.Column(db.String(50), default='Morning (8:00 AM - 12:00 NN)')
    delivery_notes = db.Column(db.Text, nullable=True)
    
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Status tracking
    # For Delivery: Pending, Dispatched, Delivered, Cancelled
    # For Walk-in: Completed, Cancelled
    delivery_status = db.Column(db.String(25), default='Pending') 
    payment_status = db.Column(db.String(25), default='Unpaid')   # Unpaid, Paid, Partial
    
    total_amount = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    
    # POS payment fields
    discount = db.Column(db.Float, default=0.0)
    amount_received = db.Column(db.Float, default=0.0)
    change_given = db.Column(db.Float, default=0.0)
    walk_in_customer_name = db.Column(db.String(120), nullable=True)
    
    # Gallon container exchange monitoring
    containers_delivered = db.Column(db.Integer, default=0)
    empty_containers_returned = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan', lazy=True)
    payments = db.relationship('Payment', backref='order', lazy=True)

    @property
    def payment_method(self):
        if self.payments:
            return self.payments[0].payment_method
        return 'Cash'

    @property
    def display_customer_name(self):
        if self.walk_in_customer_name:
            return self.walk_in_customer_name
        if self.customer:
            return self.customer.name
        return "Walk-in Customer"

    @property
    def is_walkin(self):
        return self.order_type == 'Walk-in'

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items)

    @property
    def balance_due(self):
        return max(0.0, self.total_amount - self.amount_paid)

    @property
    def gallon_net_change(self):
        return self.containers_delivered - self.empty_containers_returned

    def __repr__(self):
        return f"<Order {self.order_number} ({self.order_type}) - {self.delivery_status}>"


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    product = db.relationship('Product', lazy=True)

    def __repr__(self):
        return f"<OrderItem {self.product_name} x {self.quantity}>"


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default='Cash') # Cash, GCash, Bank Transfer, Cash on Delivery
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    reference_no = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.String(250), nullable=True)
    
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Payment {self.payment_number} - P{self.amount:.2f}>"


class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'
    
    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(30), unique=True, nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(40), nullable=False) # 'Container', 'Cap / Seal', 'Supplies'
    container_type = db.Column(db.String(30), default='None') # 'Round', 'Slim', 'None'
    
    # For Water Gallon Containers:
    filled_stock = db.Column(db.Integer, default=0)   # Refilled & ready in station
    empty_stock = db.Column(db.Integer, default=0)    # Empty in station waiting for refill
    loaned_stock = db.Column(db.Integer, default=0)   # Loaned / currently in customer possession
    damaged_stock = db.Column(db.Integer, default=0)  # Cracked / defective / condemned
    
    # For Consumables (Caps, Seal shrink films, etc.):
    quantity_on_hand = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(20), default='pcs')     # 'gallons', 'pcs', 'caps', 'rolls'
    reorder_level = db.Column(db.Integer, default=20)
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    logs = db.relationship('InventoryLog', backref='item', lazy=True, order_by='desc(InventoryLog.created_at)')

    @property
    def total_containers_owned(self):
        if self.category == 'Container':
            return self.filled_stock + self.empty_stock + self.loaned_stock + self.damaged_stock
        return self.quantity_on_hand

    @property
    def is_low_stock(self):
        if self.category == 'Container':
            return self.filled_stock <= self.reorder_level
        return self.quantity_on_hand <= self.reorder_level

    def __repr__(self):
        return f"<InventoryItem {self.item_name}>"


class InventoryLog(db.Model):
    __tablename__ = 'inventory_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False) 
    # 'Production Refill', 'Dispatched Delivery', 'Empties Returned', 'POS Walk-in Sale', 'Stock In', 'Damage Recorded', 'Adjustment'
    quantity_change = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(250), nullable=True)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    performer = db.relationship('User', lazy=True)

    def __repr__(self):
        return f"<InventoryLog {self.action_type} - {self.quantity_change}>"


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_setting(cls, key, default=''):
        record = db.session.get(cls, key)
        if record:
            return record.value
        return default

    @classmethod
    def set_setting(cls, key, value, description=None):
        record = db.session.get(cls, key)
        if record:
            record.value = str(value)
            if description:
                record.description = description
        else:
            record = cls(key=key, value=str(value), description=description)
            db.session.add(record)
        db.session.commit()
        return record


def init_and_migrate_database(app):
    """
    Ensures new schema columns and required base records are present
    without breaking or dropping any existing tables or relationships.
    """
    import sqlite3
    with app.app_context():
        db.create_all()

        # Database migrations for SQLite
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if 'sqlite:///' in db_uri:
            db_path = db_uri.replace('sqlite:///', '')
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Check columns in 'orders' table
                cursor.execute("PRAGMA table_info(orders);")
                columns = [info[1] for info in cursor.fetchall()]

                new_order_cols = [
                    ("order_type", "VARCHAR(25) DEFAULT 'Delivery'"),
                    ("discount", "FLOAT DEFAULT 0.0"),
                    ("amount_received", "FLOAT DEFAULT 0.0"),
                    ("change_given", "FLOAT DEFAULT 0.0"),
                    ("walk_in_customer_name", "VARCHAR(120) DEFAULT NULL"),
                ]

                for col_name, col_type in new_order_cols:
                    if col_name not in columns:
                        cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type};")

                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Migration notice: {e}")

        # Ensure default Walk-in Customer exists for instant physical transactions
        walkin = Customer.query.filter_by(customer_type='Walk-in').first()
        if not walkin:
            walkin = Customer(
                name="Walk-in Customer",
                customer_type="Walk-in",
                contact_number="In-Store",
                barangay="Station Walk-in",
                purok_street="Store Counter",
                landmark_notes="Standard walk-in customer profile (no account required)",
                outstanding_balance=0.0,
                gallons_on_hand=0
            )
            db.session.add(walkin)
            db.session.commit()

        # Ensure Cashier account exists
        cashier = User.query.filter_by(role='cashier').first()
        if not cashier:
            cashier_user = User(
                username='cashier',
                full_name='Maria Cashier',
                role='cashier',
                phone='0919-333-7788'
            )
            cashier_user.set_password('cashier123')
            db.session.add(cashier_user)
            db.session.commit()

        # Ensure initial System Settings exist
        default_settings = [
            ('station_name', 'Water Refilling System', 'Business Display Name'),
            ('station_subtitle', 'Commercial Station Management & Point of Sale', 'Business Subtitle / Slogan'),
            ('station_address', 'Poblacion Ward II, Minglanilla, Cebu, Philippines 6046', 'Physical Station Address'),
            ('station_contact', '+63 (032) 272-8819 / 0917-555-9283', 'Official Contact Number(s)'),
            ('station_email', 'operations@waterrefillingsystem.com', 'Official Business Email'),
            ('receipt_header', 'WATER REFILLING SYSTEM', 'Printed Receipt Header Title'),
            ('receipt_footer', 'Thank you for your business! Clean, pure, and safe water every day.', 'Printed Receipt Footer Note'),
            ('reorder_threshold_default', '20', 'Default container low-stock threshold alert level'),
        ]

        for k, v, d in default_settings:
            if not db.session.get(SystemSetting, k):
                s = SystemSetting(key=k, value=v, description=d)
                db.session.add(s)
        db.session.commit()
