from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, InventoryItem, InventoryLog, User
from routes.auth import login_required

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
@login_required
def index():
    containers = InventoryItem.query.filter_by(category='Container').all()
    consumables = InventoryItem.query.filter(InventoryItem.category.in_(['Cap / Seal', 'Supplies'])).all()
    recent_logs = InventoryLog.query.order_by(InventoryLog.created_at.desc()).limit(15).all()

    # Calculate overall container summary
    total_owned = sum(c.total_containers_owned for c in containers)
    total_filled = sum(c.filled_stock for c in containers)
    total_empty = sum(c.empty_stock for c in containers)
    total_loaned = sum(c.loaned_stock for c in containers)
    total_damaged = sum(c.damaged_stock for c in containers)

    return render_template(
        'inventory/index.html',
        containers=containers,
        consumables=consumables,
        recent_logs=recent_logs,
        total_owned=total_owned,
        total_filled=total_filled,
        total_empty=total_empty,
        total_loaned=total_loaned,
        total_damaged=total_damaged
    )

@inventory_bp.route('/refill-batch', methods=['POST'])
@login_required
def refill_batch():
    item_id = request.form.get('item_id', type=int)
    batch_quantity = request.form.get('batch_quantity', type=int)
    current_user_id = session.get('user_id')

    if not item_id or not batch_quantity or batch_quantity <= 0:
        flash('Please specify a valid container type and batch quantity.', 'danger')
        return redirect(url_for('inventory.index'))

    item = InventoryItem.query.get_or_404(item_id)

    if item.empty_stock < batch_quantity:
        flash(f'Cannot refill {batch_quantity} gallons. Only {item.empty_stock} empty containers available in station.', 'warning')
        return redirect(url_for('inventory.index'))

    # Move from empty to filled
    item.empty_stock -= batch_quantity
    item.filled_stock += batch_quantity

    # Log container refill
    log_container = InventoryLog(
        item_id=item.id,
        action_type='Production Refill',
        quantity_change=batch_quantity,
        notes=f'Purified water refilling batch: {batch_quantity} empty bottles refilled & sealed',
        performed_by=current_user_id
    )
    db.session.add(log_container)

    # Automatically deduct caps & seal bands
    if item.container_type == 'Round':
        cap_item = InventoryItem.query.filter_by(item_code='CAP-RND-BLUE').first()
    else:
        cap_item = InventoryItem.query.filter_by(item_code='CAP-SLM-WHITE').first()

    seal_item = InventoryItem.query.filter_by(item_code='SEAL-HEAT-SHRINK').first()

    if cap_item:
        cap_item.quantity_on_hand = max(0, cap_item.quantity_on_hand - batch_quantity)
        log_cap = InventoryLog(
            item_id=cap_item.id,
            action_type='Production Refill',
            quantity_change=-batch_quantity,
            notes=f'Caps used for {batch_quantity} refilled gallons',
            performed_by=current_user_id
        )
        db.session.add(log_cap)

    if seal_item:
        seal_item.quantity_on_hand = max(0, seal_item.quantity_on_hand - batch_quantity)
        log_seal = InventoryLog(
            item_id=seal_item.id,
            action_type='Production Refill',
            quantity_change=-batch_quantity,
            notes=f'Heat shrink seals used for {batch_quantity} refilled gallons',
            performed_by=current_user_id
        )
        db.session.add(log_seal)

    db.session.commit()
    flash(f'Refilling batch completed! {batch_quantity} gallons refilled, capped, and added to Ready/Filled stock.', 'success')
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/adjust', methods=['POST'])
@login_required
def adjust():
    item_id = request.form.get('item_id', type=int)
    action_type = request.form.get('action_type')  # 'Stock In', 'Damage Recorded', 'Adjustment'
    quantity = request.form.get('quantity', type=int)
    notes = request.form.get('notes', '').strip()
    current_user_id = session.get('user_id')

    if not item_id or not quantity or quantity <= 0:
        flash('Please provide valid adjustment details.', 'danger')
        return redirect(url_for('inventory.index'))

    item = InventoryItem.query.get_or_404(item_id)

    if item.category == 'Container':
        if action_type == 'Damage Recorded':
            stock_source = request.form.get('stock_source', 'empty')  # 'empty' or 'filled'
            if stock_source == 'empty':
                if item.empty_stock < quantity:
                    flash(f'Insufficient empty stock ({item.empty_stock}) to mark as damaged.', 'warning')
                    return redirect(url_for('inventory.index'))
                item.empty_stock -= quantity
            else:
                if item.filled_stock < quantity:
                    flash(f'Insufficient filled stock ({item.filled_stock}) to mark as damaged.', 'warning')
                    return redirect(url_for('inventory.index'))
                item.filled_stock -= quantity
            
            item.damaged_stock += quantity
            log_note = f'Marked {quantity} containers as damaged/condemned. {notes}'

        elif action_type == 'Stock In':
            # Newly acquired bottles added to empty stock
            item.empty_stock += quantity
            log_note = f'Purchased/added {quantity} new container bottles to station stock. {notes}'

        else: # General adjustment
            item.empty_stock += quantity
            log_note = f'Manual inventory adjustment: {quantity}. {notes}'

    else: # Consumable
        if action_type == 'Stock In':
            item.quantity_on_hand += quantity
            log_note = f'Restocked {quantity} {item.unit}. {notes}'
        else:
            item.quantity_on_hand = max(0, item.quantity_on_hand - quantity)
            log_note = f'Inventory reduction of {quantity} {item.unit}. {notes}'

    log = InventoryLog(
        item_id=item.id,
        action_type=action_type,
        quantity_change=quantity,
        notes=log_note,
        performed_by=current_user_id
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Inventory update recorded for {item.item_name}.', 'success')
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/logs')
@login_required
def logs():
    logs_list = InventoryLog.query.order_by(InventoryLog.created_at.desc()).all()
    return render_template('inventory/logs.html', logs=logs_list)
