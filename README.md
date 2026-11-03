# Water Refilling System

A modern, professional, blueprint-inspired management application and Cashier Point of Sale (POS) system designed for actual physical water refilling stations.

---

## 💧 Key System Capabilities

1. **Modern Blueprint Theme & Technical Interface**:
   - Clean technical visual identity featuring blueprint navy, cyan, white, and subtle technical grid lines.
   - High-contrast typography (`Inter` + `JetBrains Mono`) for financial figures, codes, and stock indicators.
   - Fully responsive design engineered for desktops, tablets, touch POS terminals, and mobile devices.

2. **Dedicated In-Store Cashier Point of Sale (POS)** (`/pos`):
   - Fast, practical 2-column cashier interface.
   - Searchable product catalog with instant keyboard search and category tabs.
   - Touch-friendly cart stepper controls with bottle exchange toggle for refills.
   - Real-time subtotal, discount selection (Senior/PWD 20%, 5%, 10%, Custom PHP), and grand total calculation.
   - Cash payment handling with quick tender shortcut buttons (`Exact`, `₱50`, `₱100`, `₱200`, `₱500`, `₱1,000`).
   - Instant automatic change calculation and tender validation.
   - Direct integration with printable 80mm thermal receipts and full-sheet slips.

3. **Physical Walk-in Customer Transactions**:
   - Designed for actual physical in-store walk-in customer operations.
   - Customer account creation or login is **strictly optional** — cashiers process walk-in transactions instantly.
   - Automated linkage to system walk-in customer records with optional ad-hoc customer naming.
   - Instant stock deduction and returned empty bottle tracking upon purchase.

4. **Comprehensive Administrator Dashboard** (`/dashboard`):
   - Real database-driven metrics: Total Sales Today, Total Transactions, Registered Customers, Active Products.
   - Real-time container inventory strip: Filled Ready, Empty in Station, Loaned to Customers, Damaged/Condemned.
   - 7-Day revenue and sales performance chart powered by Chart.js.
   - Low-stock supply warnings (caps, shrink seals, and container levels).
   - Unified recent transaction log displaying both in-store walk-in POS sales and delivery dispatches.

5. **Product & Pricing Management** (`/products`):
   - Product catalog with code, name, category, container type, price, and active status.
   - Add new products, update prices, toggle active/inactive status.
   - Linked to station container and consumable inventory levels.

6. **Customer Management & Profiles** (`/customers`):
   - Customer profiles tracking order history, containers held on hand, and outstanding debt.
   - Filter by barangay, customer type (Household, Sari-sari Store, Eatery, Business), and credit status.
   - Returning customer badges and instant shortcuts to start a POS sale or delivery order.

7. **Gallon Container Inventory & Production** (`/inventory`):
   - Tracks 5-Gallon Round and Slim containers:
     $$\text{Total Owned} = \text{Filled} + \text{Empty} + \text{Loaned (Customers)} + \text{Damaged}$$
   - **Run Refill Production Batch**: Automatically moves empty containers to filled stock and deducts bottle caps and heat-shrink neck seals.
   - Inventory movement audit log (`/inventory/logs`).

8. **Sales, Payments, and Receivables** (`/payments`):
   - Payment transaction ledger with method tracking (Cash, GCash, Bank Transfer, Cash on Delivery).
   - Dedicated customer receivables monitor (`/payments/receivables`) with credit collection modals.
   - Printable official acknowledgement receipts.

9. **Reports & Business Analytics** (`/reports`):
   - Period sales summaries with presets: Today's Sales, This Week, This Month, Annual Sales, Custom Date Range.
   - Walk-in POS vs. Delivery revenue breakdown.
   - Best-selling products report by volume and gross revenue.
   - Cashier transaction performance summaries.
   - One-click sales export to CSV for Microsoft Excel.

10. **Role-Based Access Control & Staff Management** (`/employees`):
    - Dedicated Employee Management module for Administrators.
    - Role permissions:
      - **Administrator**: Full system access, employee management, system settings.
      - **Cashier**: Fast POS register, customer lookup/registration, transaction records, receipts.
      - **Staff**: POS register, orders, customer profiles, inventory refill batches, reports.
      - **Delivery Rider**: View assigned delivery dispatches and mark deliveries.

11. **System Settings** (`/settings`):
    - Admin configurable station name, tagline, address, phone numbers, and email.
    - Customizable printed receipt headers and footer thank-you notes.
    - Configurable container reorder alert thresholds.

---

## 🔑 Pre-Configured Demo Accounts

| Role | Username | Password | Full Name | Default Landing |
| :--- | :--- | :--- | :--- | :--- |
| **Station Administrator** | `admin` | `admin123` | Juanita Dela Cruz | Administrator Dashboard |
| **Station Cashier** | `cashier` | `cashier123` | Maria Cashier | In-Store POS Register |
| **Refilling Station Staff** | `staff` | `staff123` | Mark Fernandez | Operations Dashboard |
| **Delivery Rider** | `rider` | `rider123` | Junjun Cañedo | Deliveries Board |

*(One-click demo buttons are provided directly on the Login page for rapid demonstration).*

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.10+ (Tested on Python 3.12)
- Dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Launch the Application
Run the runner script:
```bash
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
*(The SQLite database `water_station.db` will initialize and seed automatically).*

### 3. Run Automated System Tests
```bash
python test_system.py
```
This tests:
- Database initialization and pre-seeded operational data
- User authentication and role-based permissions
- In-store Cashier POS walk-in transaction workflow
- Cashier tender validation and change calculation
- Dynamic delivery order dispatch & container exchange
- Production refilling batches and supply deductions
- Product catalog management
- CSV sales export
