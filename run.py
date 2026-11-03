import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"================================================================")
    print(f" WATER REFILLING SYSTEM")
    print(f" Commercial Station Management & Cashier Point of Sale (POS)")
    print(f" Running at: http://127.0.0.1:{port}")
    print(f" Demo Accounts:")
    print(f"   Station Admin:   admin   / admin123")
    print(f"   Station Cashier: cashier / cashier123  (Direct POS access)")
    print(f"   Station Staff:   staff   / staff123")
    print(f"   Delivery Rider:  rider   / rider123")
    print(f"================================================================")
    app.run(host='0.0.0.0', port=port, debug=True)
