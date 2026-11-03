import unittest
from datetime import date
from app import create_app
from models import db, User, Customer, Product, Order, Payment, InventoryItem, InventoryLog, SystemSetting

class SystemTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_database_seeded(self):
        user_count = User.query.count()
        customer_count = Customer.query.count()
        product_count = Product.query.count()
        order_count = Order.query.count()
        inv_count = InventoryItem.query.count()

        print(f"Users: {user_count}, Customers: {customer_count}, Products: {product_count}, Orders: {order_count}, Inventory: {inv_count}")
        self.assertGreaterEqual(user_count, 3)
        self.assertGreaterEqual(customer_count, 8)
        self.assertGreaterEqual(product_count, 5)
        self.assertGreaterEqual(order_count, 5)
        self.assertGreaterEqual(inv_count, 4)

    def test_login_flow_and_branding(self):
        # 1. Login page loads with new system branding
        res = self.client.get('/auth/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Water Refilling System', res.data)

        # 2. Login with admin credentials
        login_res = self.client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Water Refilling System', login_res.data)

    def test_cashier_login_and_pos_access(self):
        # Login as Cashier
        login_res = self.client.post('/auth/login', data={
            'username': 'cashier',
            'password': 'cashier123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        # Cashier is directed to POS interface
        self.assertIn(b'Point of Sale (POS) Register', login_res.data)

    def test_dashboard_and_modules(self):
        # Log in as admin
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'})

        # Dashboard
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Water Refilling System', res.data)

        # POS Register
        res = self.client.get('/pos/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Point of Sale (POS) Register', res.data)

        # Customers
        res = self.client.get('/customers/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Customer Management', res.data)

        # Products Catalog
        res = self.client.get('/products/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Product Catalog Management', res.data)

        # Orders & Transactions
        res = self.client.get('/orders/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Orders & Transactions', res.data)

        # Payments
        res = self.client.get('/payments/')
        self.assertEqual(res.status_code, 200)

        # Receivables
        res = self.client.get('/payments/receivables')
        self.assertEqual(res.status_code, 200)

        # Inventory
        res = self.client.get('/inventory/')
        self.assertEqual(res.status_code, 200)

        # Reports
        res = self.client.get('/reports/')
        self.assertEqual(res.status_code, 200)

        # Employees Management (Admin)
        res = self.client.get('/employees/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Employee & User Access Control', res.data)

        # System Settings (Admin)
        res = self.client.get('/settings/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Station Configuration & System Settings', res.data)

    def test_role_based_access_control(self):
        # Login as Cashier
        self.client.post('/auth/login', data={'username': 'cashier', 'password': 'cashier123'})

        # Cashier should NOT be able to access Employee Management
        emp_res = self.client.get('/employees/', follow_redirects=True)
        self.assertEqual(emp_res.status_code, 200)
        self.assertIn(b'Access restricted', emp_res.data)

        # Cashier should NOT be able to access System Settings
        set_res = self.client.get('/settings/', follow_redirects=True)
        self.assertEqual(set_res.status_code, 200)
        self.assertIn(b'Access restricted', set_res.data)

    def test_walk_in_pos_transaction_flow(self):
        # 1. Login as Cashier
        self.client.post('/auth/login', data={'username': 'cashier', 'password': 'cashier123'})

        # Initial filled stock
        round_inv = InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
        initial_filled = round_inv.filled_stock if round_inv else 0
        prod = Product.query.filter_by(code='REF-RND').first()

        # 2. Perform Walk-in counter sale (2 refills @ ₱25 = ₱50, cash tendered ₱100, change ₱50)
        # Customer registration is NOT required!
        res = self.client.post('/pos/checkout', data={
            'walk_in_name': 'Walk-in Customer (In-Store)',
            'product_id[]': [prod.id],
            'quantity[]': [2],
            'bottle_exchange[]': ['1'],
            'discount_type': 'none',
            'discount_value': 0,
            'payment_method': 'Cash',
            'amount_received': 100.00,
            'notes': 'Fast physical counter sale'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check receipt generated
        self.assertIn(b'Official Store Receipt', res.data)
        self.assertIn(b'Change Given:', res.data)
        self.assertIn(b'50.00', res.data)

        # Check order record in database
        latest_order = Order.query.filter_by(order_type='Walk-in').order_by(Order.id.desc()).first()
        self.assertIsNotNone(latest_order)
        self.assertEqual(latest_order.total_amount, 50.00)
        self.assertEqual(latest_order.amount_received, 100.00)
        self.assertEqual(latest_order.change_given, 50.00)
        self.assertEqual(latest_order.delivery_status, 'Completed')
        self.assertEqual(latest_order.payment_status, 'Paid')

        # Check payment record created
        latest_payment = Payment.query.filter_by(order_id=latest_order.id).first()
        self.assertIsNotNone(latest_payment)
        self.assertEqual(latest_payment.amount, 50.00)

        # Check inventory was deducted
        if round_inv:
            db.session.refresh(round_inv)
            self.assertEqual(round_inv.filled_stock, initial_filled - 2)

    def test_full_delivery_and_container_workflow(self):
        # 1. Login as staff
        self.client.post('/auth/login', data={'username': 'staff', 'password': 'staff123'})

        # 2. Register a new customer
        cust_res = self.client.post('/customers/create', data={
            'name': 'Minglanilla Food Stop',
            'customer_type': 'Commercial / Eatery',
            'contact_number': '0929-111-9988',
            'barangay': 'Calajo-an',
            'purok_street': 'Sitio Tabucanal Highway',
            'landmark_notes': 'Beside 7-Eleven convenience store',
            'initial_gallons': 0,
            'initial_balance': 0.00
        }, follow_redirects=True)
        self.assertEqual(cust_res.status_code, 200)

        customer = Customer.query.filter_by(name='Minglanilla Food Stop').first()
        self.assertIsNotNone(customer)

        initial_gallons = customer.gallons_on_hand

        # 3. Create delivery order for customer (4 Round Gallon Refills @ P25 = P100)
        prod = Product.query.filter_by(code='REF-RND').first()
        rider = User.query.filter_by(role='rider').first()

        order_res = self.client.post('/orders/create', data={
            'customer_id': customer.id,
            'delivery_date': date.today().strftime('%Y-%m-%d'),
            'delivery_time_slot': 'Morning (8:00 AM - 12:00 NN)',
            'delivery_address': customer.full_address,
            'barangay': customer.barangay,
            'contact_number': customer.contact_number,
            'delivery_notes': 'Deliver to kitchen door',
            'assigned_staff_id': rider.id if rider else '',
            'product_id[]': [prod.id],
            'quantity[]': [4]
        }, follow_redirects=True)
        self.assertEqual(order_res.status_code, 200)

        order = Order.query.filter_by(customer_id=customer.id).order_by(Order.id.desc()).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total_amount, 100.00)
        self.assertEqual(order.delivery_status, 'Pending')

        # 4. Dispatch the order
        dispatch_res = self.client.post(f'/orders/{order.id}/status', data={
            'delivery_status': 'Dispatched',
            'assigned_staff_id': rider.id if rider else ''
        }, follow_redirects=True)
        self.assertEqual(dispatch_res.status_code, 200)
        db.session.refresh(order)
        self.assertEqual(order.delivery_status, 'Dispatched')

        # 5. Mark as Delivered with 3 empty containers returned and paid in full
        deliver_res = self.client.post(f'/orders/{order.id}/status', data={
            'delivery_status': 'Delivered',
            'empty_containers_returned': 3,
            'payment_option': 'cash_full',
            'payment_method': 'Cash on Delivery',
            'amount_collected': 100.00,
            'payment_reference': 'OR-TEST-01'
        }, follow_redirects=True)
        self.assertEqual(deliver_res.status_code, 200)

        db.session.refresh(order)
        db.session.refresh(customer)
        self.assertEqual(order.delivery_status, 'Delivered')
        self.assertEqual(order.payment_status, 'Paid')
        self.assertEqual(customer.gallons_on_hand, initial_gallons + 1)

    def test_refill_batch_production(self):
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'})

        round_inv = InventoryItem.query.filter_by(item_code='INV-RND-5GAL').first()
        initial_empty = round_inv.empty_stock
        initial_filled = round_inv.filled_stock

        batch_qty = 2
        res = self.client.post('/inventory/refill-batch', data={
            'item_id': round_inv.id,
            'batch_quantity': batch_qty
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        db.session.refresh(round_inv)
        self.assertEqual(round_inv.empty_stock, initial_empty - batch_qty)
        self.assertEqual(round_inv.filled_stock, initial_filled + batch_qty)

    def test_csv_export(self):
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'})
        res = self.client.get('/reports/export-sales')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'text/csv')
        self.assertIn(b'Reference No.', res.data)

if __name__ == '__main__':
    unittest.main()
