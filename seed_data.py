from datetime import datetime, date, timedelta
from models import db, User, Customer, Product, Order, OrderItem, Payment, InventoryItem, InventoryLog

def seed_database(app):
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()

        # Check if already seeded
        if User.query.first():
            print("Database already contains data. Skipping initial seeding.")
            return

        print("Seeding database with Minglanilla Water Refilling Station data...")

        # 1. Users (Owner/Admin, Cashier, Staff, Delivery Rider)
        admin = User(
            username='admin',
            full_name='Juanita Dela Cruz',
            role='admin',
            phone='0917-555-9283'
        )
        admin.set_password('admin123')

        cashier = User(
            username='cashier',
            full_name='Maria Cashier',
            role='cashier',
            phone='0919-333-7788'
        )
        cashier.set_password('cashier123')

        staff = User(
            username='staff',
            full_name='Mark Fernandez',
            role='staff',
            phone='0918-222-3344'
        )
        staff.set_password('staff123')

        rider = User(
            username='rider',
            full_name='Junjun Cañedo',
            role='rider',
            phone='0922-888-1122'
        )
        rider.set_password('rider123')

        db.session.add_all([admin, cashier, staff, rider])
        db.session.commit()

        # 2. Products
        products = [
            Product(code='REF-RND', name='5-Gallon Round Gallon (Refill)', category='Refill', unit_price=25.00, container_type='Round', is_refill=True),
            Product(code='REF-SLM', name='5-Gallon Slim Gallon w/ Faucet (Refill)', category='Refill', unit_price=30.00, container_type='Slim', is_refill=True),
            Product(code='NEW-RND', name='5-Gallon Round Container (New Bottle + Water)', category='New Container', unit_price=220.00, container_type='Round', is_refill=False),
            Product(code='NEW-SLM', name='5-Gallon Slim Container w/ Faucet (New Bottle + Water)', category='New Container', unit_price=240.00, container_type='Slim', is_refill=False),
            Product(code='BOT-10L', name='10-Liter Dispenser Bottle (Refill)', category='Refill', unit_price=15.00, container_type='Round', is_refill=True),
            Product(code='BOT-500', name='Bottled Water 500ml Purified (Case of 24)', category='Bottled Water', unit_price=180.00, container_type='None', is_refill=False),
            Product(code='CAP-RND', name='Replacement Non-Spill Round Cap', category='Supply', unit_price=10.00, container_type='None', is_refill=False),
        ]
        db.session.add_all(products)
        db.session.commit()

        # 3. Inventory Items (Containers & Consumables)
        inv_round = InventoryItem(
            item_code='INV-RND-5GAL',
            item_name='5-Gallon Round Gallon Containers',
            category='Container',
            container_type='Round',
            filled_stock=48,
            empty_stock=32,
            loaned_stock=65,
            damaged_stock=4,
            unit='gallons',
            reorder_level=20
        )
        inv_slim = InventoryItem(
            item_code='INV-SLM-5GAL',
            item_name='5-Gallon Slim Gallon Containers with Faucet',
            category='Container',
            container_type='Slim',
            filled_stock=40,
            empty_stock=25,
            loaned_stock=55,
            damaged_stock=3,
            unit='gallons',
            reorder_level=20
        )
        inv_caps_round = InventoryItem(
            item_code='CAP-RND-BLUE',
            item_name='Blue Non-Spill Caps (for Round Gallons)',
            category='Cap / Seal',
            container_type='Round',
            quantity_on_hand=450,
            unit='pcs',
            reorder_level=100
        )
        inv_caps_slim = InventoryItem(
            item_code='CAP-SLM-WHITE',
            item_name='White Screw Caps with Plug (for Slim Gallons)',
            category='Cap / Seal',
            container_type='Slim',
            quantity_on_hand=380,
            unit='pcs',
            reorder_level=80
        )
        inv_seals = InventoryItem(
            item_code='SEAL-HEAT-SHRINK',
            item_name='Heat Shrink Security Bottle Neck Seals',
            category='Cap / Seal',
            container_type='None',
            quantity_on_hand=820,
            unit='seals',
            reorder_level=200
        )
        db.session.add_all([inv_round, inv_slim, inv_caps_round, inv_caps_slim, inv_seals])
        db.session.commit()

        # Initial Inventory Logs
        log1 = InventoryLog(item_id=inv_round.id, action_type='Stock In', quantity_change=149, notes='Initial baseline container inventory setup', performed_by=admin.id)
        log2 = InventoryLog(item_id=inv_slim.id, action_type='Stock In', quantity_change=123, notes='Initial baseline container inventory setup', performed_by=admin.id)
        log3 = InventoryLog(item_id=inv_round.id, action_type='Production Refill', quantity_change=25, notes='Morning purified water refilling batch completed', performed_by=staff.id)
        db.session.add_all([log1, log2, log3])
        db.session.commit()

        # 4. Customers in Minglanilla, Cebu
        customers = [
            Customer(
                name="Aling Nena's Sari-Sari Store",
                customer_type="Commercial / Sari-sari Store",
                contact_number="0917-111-2233",
                barangay="Poblacion Ward I",
                purok_street="Purok Rosas, Near Public Market",
                landmark_notes="Green gate beside St. Cecilia Pharmacy",
                outstanding_balance=250.00,
                gallons_on_hand=8
            ),
            Customer(
                name="Dr. Roberto Tan Dental Clinic",
                customer_type="Office / Business",
                contact_number="0922-333-4455",
                barangay="Poblacion Ward II",
                purok_street="2nd Floor Commercial Bldg, National Highway",
                landmark_notes="Across Minglanilla Town Plaza",
                outstanding_balance=0.00,
                gallons_on_hand=3
            ),
            Customer(
                name="Maria Elena Santos",
                customer_type="Household",
                contact_number="0933-444-5566",
                barangay="Linao",
                purok_street="Sitio Riverside, Block 4 Lot 12",
                landmark_notes="Near Linao Barangay Hall, yellow bungalow",
                outstanding_balance=0.00,
                gallons_on_hand=2
            ),
            Customer(
                name="Minglanilla Central School Canteen",
                customer_type="Institution / School",
                contact_number="0919-555-6677",
                barangay="Poblacion Ward I",
                purok_street="School Compound, Bonifacio St.",
                landmark_notes="Main Canteen Building entrance",
                outstanding_balance=400.00,
                gallons_on_hand=12
            ),
            Customer(
                name="Calajo-an Bakeshop & Coffee Corner",
                customer_type="Commercial / Eatery",
                contact_number="0920-666-7788",
                barangay="Calajo-an",
                purok_street="Purok Pag-asa, Highway Corner",
                landmark_notes="Beside Petron Gas Station",
                outstanding_balance=0.00,
                gallons_on_hand=5
            ),
            Customer(
                name="Engr. Danilo & Grace Reyes",
                customer_type="Household",
                contact_number="0915-777-8899",
                barangay="Tungkop",
                purok_street="Phase 2, Deca Homes Tungkop",
                landmark_notes="Block 15 Lot 8, corner lot with carport",
                outstanding_balance=0.00,
                gallons_on_hand=3
            ),
            Customer(
                name="Pakigne Eatery & Carenderia",
                customer_type="Commercial / Eatery",
                contact_number="0928-888-9900",
                barangay="Pakigne",
                purok_street="Sitio Mohon, Highway Road",
                landmark_notes="Fronting Pakigne Covered Court",
                outstanding_balance=150.00,
                gallons_on_hand=6
            ),
            Customer(
                name="Pastor James Miller / Grace Chapel",
                customer_type="Institution / Church",
                contact_number="0932-999-0011",
                barangay="Tubod",
                purok_street="Tubod Heights Access Road",
                landmark_notes="White church building with bell tower",
                outstanding_balance=0.00,
                gallons_on_hand=4
            ),
            Customer(
                name="Tulay Seaside Restobar",
                customer_type="Commercial / Eatery",
                contact_number="0916-222-7711",
                barangay="Tulay",
                purok_street="Coastal Road, Sitio Baybay",
                landmark_notes="Blue wooden canopy by the sea",
                outstanding_balance=0.00,
                gallons_on_hand=5
            ),
            Customer(
                name="Tungkil Family Pharmacy",
                customer_type="Commercial / Business",
                contact_number="0921-333-8822",
                barangay="Tungkil",
                purok_street="Purok Santan, Main Road",
                landmark_notes="Beside 7-Eleven Tungkil",
                outstanding_balance=0.00,
                gallons_on_hand=2
            )
        ]
        db.session.add_all(customers)
        db.session.commit()

        # 5. Orders and Payments
        c1, c2, c3, c4, c5, c6, c7 = customers[0], customers[1], customers[2], customers[3], customers[4], customers[5], customers[6]
        p_ref_rnd, p_ref_slm, p_new_rnd = products[0], products[1], products[2]

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Order 1: Delivered yesterday, fully paid (Cash on Delivery)
        o1 = Order(
            order_number='WDMS-2026-0001',
            customer_id=c2.id,
            delivery_address=c2.full_address,
            barangay=c2.barangay,
            contact_number=c2.contact_number,
            order_date=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=8, minutes=30),
            delivery_date=yesterday,
            delivery_time_slot='Morning (8:00 AM - 12:00 NN)',
            delivery_notes='Deliver to 2nd-floor clinic receptionist',
            assigned_staff_id=rider.id,
            created_by=staff.id,
            delivery_status='Delivered',
            payment_status='Paid',
            total_amount=75.00,
            amount_paid=75.00,
            containers_delivered=3,
            empty_containers_returned=3,
            delivered_at=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=10, minutes=45)
        )
        db.session.add(o1)
        db.session.flush()

        item1 = OrderItem(order_id=o1.id, product_id=p_ref_rnd.id, product_name=p_ref_rnd.name, quantity=3, unit_price=25.00, subtotal=75.00)
        pay1 = Payment(
            payment_number='PAY-2026-0001',
            customer_id=c2.id,
            order_id=o1.id,
            amount=75.00,
            payment_method='Cash on Delivery',
            payment_date=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=10, minutes=45),
            reference_no='OR-8821',
            notes='Paid in exact cash to delivery rider Junjun',
            received_by=rider.id
        )
        db.session.add_all([item1, pay1])

        # Order 2: Delivered yesterday, credit (Unpaid) for Aling Nena's Sari-Sari Store
        o2 = Order(
            order_number='WDMS-2026-0002',
            customer_id=c1.id,
            delivery_address=c1.full_address,
            barangay=c1.barangay,
            contact_number=c1.contact_number,
            order_date=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=14, minutes=15),
            delivery_date=yesterday,
            delivery_time_slot='Afternoon (1:00 PM - 5:00 PM)',
            delivery_notes='Leave 6 round gallons, take 4 empties (2 loaned)',
            assigned_staff_id=rider.id,
            created_by=staff.id,
            delivery_status='Delivered',
            payment_status='Unpaid',
            total_amount=150.00,
            amount_paid=0.00,
            containers_delivered=6,
            empty_containers_returned=4,
            delivered_at=datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=15, minutes=30)
        )
        db.session.add(o2)
        db.session.flush()

        item2 = OrderItem(order_id=o2.id, product_id=p_ref_rnd.id, product_name=p_ref_rnd.name, quantity=6, unit_price=25.00, subtotal=150.00)
        db.session.add(item2)

        # Order 3: Delivered Today, Paid
        o3 = Order(
            order_number='WDMS-2026-0003',
            customer_id=c5.id,
            delivery_address=c5.full_address,
            barangay=c5.barangay,
            contact_number=c5.contact_number,
            order_date=datetime.combine(today, datetime.min.time()) + timedelta(hours=8, minutes=10),
            delivery_date=today,
            delivery_time_slot='Morning (8:00 AM - 12:00 NN)',
            delivery_notes='For bakery baking section, place directly near water filter tank',
            assigned_staff_id=rider.id,
            created_by=staff.id,
            delivery_status='Delivered',
            payment_status='Paid',
            total_amount=125.00,
            amount_paid=125.00,
            containers_delivered=5,
            empty_containers_returned=5,
            delivered_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=9, minutes=40)
        )
        db.session.add(o3)
        db.session.flush()

        item3 = OrderItem(order_id=o3.id, product_id=p_ref_rnd.id, product_name=p_ref_rnd.name, quantity=5, unit_price=25.00, subtotal=125.00)
        pay3 = Payment(
            payment_number='PAY-2026-0002',
            customer_id=c5.id,
            order_id=o3.id,
            amount=125.00,
            payment_method='Cash on Delivery',
            payment_date=datetime.combine(today, datetime.min.time()) + timedelta(hours=9, minutes=40),
            reference_no='OR-8822',
            notes='Paid in full at bakery cashier',
            received_by=rider.id
        )
        db.session.add_all([item3, pay3])

        # Order 4: Dispatched (Out for Delivery right now)
        o4 = Order(
            order_number='WDMS-2026-0004',
            customer_id=c3.id,
            delivery_address=c3.full_address,
            barangay=c3.barangay,
            contact_number=c3.contact_number,
            order_date=datetime.combine(today, datetime.min.time()) + timedelta(hours=10, minutes=0),
            delivery_date=today,
            delivery_time_slot='Morning (8:00 AM - 12:00 NN)',
            delivery_notes='Call upon arrival at Sitio Riverside',
            assigned_staff_id=rider.id,
            created_by=staff.id,
            delivery_status='Dispatched',
            payment_status='Unpaid',
            total_amount=60.00,
            amount_paid=0.00,
            containers_delivered=2,
            empty_containers_returned=0
        )
        db.session.add(o4)
        db.session.flush()

        item4 = OrderItem(order_id=o4.id, product_id=p_ref_slm.id, product_name=p_ref_slm.name, quantity=2, unit_price=30.00, subtotal=60.00)
        db.session.add(item4)

        # Order 5: Pending delivery for this afternoon
        o5 = Order(
            order_number='WDMS-2026-0005',
            customer_id=c6.id,
            delivery_address=c6.full_address,
            barangay=c6.barangay,
            contact_number=c6.contact_number,
            order_date=datetime.combine(today, datetime.min.time()) + timedelta(hours=11, minutes=20),
            delivery_date=today,
            delivery_time_slot='Afternoon (1:00 PM - 5:00 PM)',
            delivery_notes='Ring doorbell at gate with Deca Homes sticker',
            assigned_staff_id=rider.id,
            created_by=staff.id,
            delivery_status='Pending',
            payment_status='Unpaid',
            total_amount=90.00,
            amount_paid=0.00,
            containers_delivered=3,
            empty_containers_returned=0
        )
        db.session.add(o5)
        db.session.flush()

        item5 = OrderItem(order_id=o5.id, product_id=p_ref_slm.id, product_name=p_ref_slm.name, quantity=3, unit_price=30.00, subtotal=90.00)
        db.session.add(item5)

        # Order 6: Pending delivery for Central School
        o6 = Order(
            order_number='WDMS-2026-0006',
            customer_id=c4.id,
            delivery_address=c4.full_address,
            barangay=c4.barangay,
            contact_number=c4.contact_number,
            order_date=datetime.combine(today, datetime.min.time()) + timedelta(hours=11, minutes=45),
            delivery_date=today,
            delivery_time_slot='Afternoon (1:00 PM - 5:00 PM)',
            delivery_notes='Deliver before 3:00 PM recess. Exchange 10 empty round containers.',
            assigned_staff_id=rider.id,
            created_by=staff.id,
            delivery_status='Pending',
            payment_status='Unpaid',
            total_amount=250.00,
            amount_paid=0.00,
            containers_delivered=10,
            empty_containers_returned=0
        )
        db.session.add(o6)
        db.session.flush()

        item6 = OrderItem(order_id=o6.id, product_id=p_ref_rnd.id, product_name=p_ref_rnd.name, quantity=10, unit_price=25.00, subtotal=250.00)
        db.session.add(item6)

        db.session.commit()
        print("Database successfully seeded with realistic Minglanilla water station operational data!")

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    seed_database(app)
