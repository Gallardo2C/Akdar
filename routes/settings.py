from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, SystemSetting
from routes.auth import login_required, admin_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
@login_required
@admin_required
def index():
    station_name = SystemSetting.get_setting('station_name', current_app.config.get('STATION_NAME', 'Water Refilling System'))
    station_subtitle = SystemSetting.get_setting('station_subtitle', current_app.config.get('STATION_SUBTITLE', ''))
    station_address = SystemSetting.get_setting('station_address', current_app.config.get('STATION_ADDRESS', ''))
    station_contact = SystemSetting.get_setting('station_contact', current_app.config.get('STATION_CONTACT', ''))
    station_email = SystemSetting.get_setting('station_email', current_app.config.get('STATION_EMAIL', ''))
    receipt_header = SystemSetting.get_setting('receipt_header', 'WATER REFILLING SYSTEM')
    receipt_footer = SystemSetting.get_setting('receipt_footer', 'Thank you for your business! Clean, pure, and safe water every day.')
    reorder_threshold = SystemSetting.get_setting('reorder_threshold_default', '20')

    all_settings = SystemSetting.query.order_by(SystemSetting.key.asc()).all()

    return render_template(
        'settings/index.html',
        station_name=station_name,
        station_subtitle=station_subtitle,
        station_address=station_address,
        station_contact=station_contact,
        station_email=station_email,
        receipt_header=receipt_header,
        receipt_footer=receipt_footer,
        reorder_threshold=reorder_threshold,
        all_settings=all_settings
    )

@settings_bp.route('/update', methods=['POST'])
@login_required
@admin_required
def update():
    fields = [
        ('station_name', request.form.get('station_name', 'Water Refilling System').strip(), 'Business Display Name'),
        ('station_subtitle', request.form.get('station_subtitle', '').strip(), 'Business Subtitle / Slogan'),
        ('station_address', request.form.get('station_address', '').strip(), 'Physical Station Address'),
        ('station_contact', request.form.get('station_contact', '').strip(), 'Official Contact Number(s)'),
        ('station_email', request.form.get('station_email', '').strip(), 'Official Business Email'),
        ('receipt_header', request.form.get('receipt_header', 'WATER REFILLING SYSTEM').strip(), 'Printed Receipt Header Title'),
        ('receipt_footer', request.form.get('receipt_footer', '').strip(), 'Printed Receipt Footer Note'),
        ('reorder_threshold_default', request.form.get('reorder_threshold_default', '20').strip(), 'Default container low-stock threshold alert level'),
    ]

    for key, val, desc in fields:
        if val is not None:
            SystemSetting.set_setting(key, val, desc)

    flash('System settings updated successfully!', 'success')
    return redirect(url_for('settings.index'))
