import os
from flask import Flask, render_template, session, g
from config import Config
from models import db, bcrypt, User, SystemSetting, init_and_migrate_database
from seed_data import seed_database

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.pos import pos_bp
    from routes.customers import customers_bp
    from routes.orders import orders_bp
    from routes.products import products_bp
    from routes.inventory import inventory_bp
    from routes.payments import payments_bp
    from routes.reports import reports_bp
    from routes.employees import employees_bp
    from routes.settings import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(employees_bp, url_prefix='/employees')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Template filters
    @app.template_filter('php')
    def php_currency(val):
        try:
            return f"₱{float(val):,.2f}"
        except (ValueError, TypeError):
            return "₱0.00"

    @app.template_filter('format_dt')
    def format_dt(dt, format='%b %d, %Y %I:%M %p'):
        if not dt:
            return '—'
        return dt.strftime(format)

    @app.template_filter('format_d')
    def format_d(d, format='%b %d, %Y'):
        if not d:
            return '—'
        return d.strftime(format)

    # Context processors
    @app.context_processor
    def inject_global_data():
        current_user = None
        user_id = session.get('user_id')
        if user_id:
            current_user = db.session.get(User, user_id)

        # Dynamic station settings from DB or Config fallback
        station_name = SystemSetting.get_setting('station_name', app.config.get('STATION_NAME', 'Water Refilling System'))
        station_subtitle = SystemSetting.get_setting('station_subtitle', app.config.get('STATION_SUBTITLE', 'Commercial Management & Point of Sale'))
        station_address = SystemSetting.get_setting('station_address', app.config.get('STATION_ADDRESS', 'Poblacion Ward II, Minglanilla, Cebu'))
        station_contact = SystemSetting.get_setting('station_contact', app.config.get('STATION_CONTACT', '+63 (032) 272-8819'))
        station_email = SystemSetting.get_setting('station_email', app.config.get('STATION_EMAIL', ''))
        receipt_header = SystemSetting.get_setting('receipt_header', 'WATER REFILLING SYSTEM')
        receipt_footer = SystemSetting.get_setting('receipt_footer', 'Thank you for your business!')

        return {
            'current_user': current_user,
            'system_brand': 'Water Refilling System',
            'station_name': station_name,
            'station_subtitle': station_subtitle,
            'station_address': station_address,
            'station_contact': station_contact,
            'station_email': station_email,
            'receipt_header': receipt_header,
            'receipt_footer': receipt_footer
        }

    # About Page / Specifications
    @app.route('/about')
    def about():
        return render_template('about.html')

    # Auto-initialize and migrate database on startup
    with app.app_context():
        db.create_all()
        seed_database(app)
        init_and_migrate_database(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
