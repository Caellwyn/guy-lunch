"""
Secretary Portal - Simplified interface for the group secretary.

The secretary needs:
1. Take attendance each Tuesday
2. See upcoming lunch details (location, phone) to make reservations
3. Nothing else - keep it simple!
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import date, timedelta
from app import db
from app.models import Member, Location, Lunch, Attendance, Setting

secretary_bp = Blueprint('secretary', __name__, url_prefix='/secretary')


def secretary_required(f):
    """Decorator to require secretary authentication via member login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Must be logged in as a member
        if not session.get('member_id'):
            flash('Please log in to access the secretary portal.', 'error')
            return redirect(url_for('member.login'))

        # Must be the designated secretary
        secretary_id = Setting.get('secretary_member_id')
        if not secretary_id or int(secretary_id) != session.get('member_id'):
            flash('You do not have secretary access.', 'error')
            return redirect(url_for('member.dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def get_next_tuesday():
    """Get the next Tuesday date (or today if it's Tuesday)."""
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0 and today.weekday() == 1:
        return today
    return today + timedelta(days=days_until_tuesday)


@secretary_bp.route('/')
@secretary_required
def dashboard():
    """Secretary dashboard - simple overview."""
    next_tuesday = get_next_tuesday()

    # Get or create this week's lunch
    lunch = Lunch.query.filter_by(date=next_tuesday).first()
    location = Location.query.get(lunch.location_id) if lunch and lunch.location_id else None
    host = Member.query.get(lunch.host_id) if lunch and lunch.host_id else None

    # Get last week's lunch for reference
    last_tuesday = next_tuesday - timedelta(days=7)
    last_lunch = Lunch.query.filter_by(date=last_tuesday).first()

    return render_template('secretary/dashboard.html',
                           next_tuesday=next_tuesday,
                           lunch=lunch,
                           location=location,
                           host=host,
                           last_lunch=last_lunch)


@secretary_bp.route('/attendance')
@secretary_required
def attendance():
    """Attendance tracking page."""
    # Get the lunch date from query param or default to this/next Tuesday
    lunch_date_str = request.args.get('date')
    if lunch_date_str:
        lunch_date = date.fromisoformat(lunch_date_str)
    else:
        lunch_date = get_next_tuesday()

    # Get or create lunch record
    lunch = Lunch.query.filter_by(date=lunch_date).first()
    if not lunch:
        lunch = Lunch(date=lunch_date, status='planned')
        db.session.add(lunch)
        db.session.commit()

    # Get all active members for the checklist
    members = Member.query.filter(
        Member.member_type.in_(['regular', 'guest'])
    ).order_by(Member.name).all()

    # Get already recorded attendance
    existing_attendance = {a.member_id: a for a in lunch.attendances.all()}

    # Get the host (either from lunch record or next in queue)
    from app.services.email_jobs import get_hosting_queue
    if lunch.host_id:
        current_host = Member.query.get(lunch.host_id)
    else:
        queue = get_hosting_queue(limit=1)
        current_host = queue[0] if queue else None

    # Get location info
    location = Location.query.get(lunch.location_id) if lunch.location_id else None

    return render_template('secretary/attendance.html',
                           lunch=lunch,
                           lunch_date=lunch_date,
                           members=members,
                           existing_attendance=existing_attendance,
                           current_host=current_host,
                           location=location)


@secretary_bp.route('/attendance', methods=['POST'])
@secretary_required
def save_attendance():
    """Save attendance for a lunch."""
    lunch_date_str = request.form.get('lunch_date')
    lunch_date = date.fromisoformat(lunch_date_str) if lunch_date_str else get_next_tuesday()

    lunch = Lunch.query.filter_by(date=lunch_date).first()
    if not lunch:
        flash('Lunch not found.', 'error')
        return redirect(url_for('secretary.attendance'))

    # Get list of member IDs who attended
    attendee_ids = request.form.getlist('attendees')
    host_id = request.form.get('host_id')

    # Clear existing attendance for this lunch
    Attendance.query.filter_by(lunch_id=lunch.id).delete()

    # Record attendance
    for member_id in attendee_ids:
        member = Member.query.get(int(member_id))
        if member:
            was_host = (str(member_id) == str(host_id))
            attendance_record = Attendance(
                lunch_id=lunch.id,
                member_id=member.id,
                was_host=was_host
            )
            db.session.add(attendance_record)

            # Update member's attendance counter
            if was_host:
                member.attendance_since_hosting = 0
                member.last_hosted_date = lunch_date
                member.total_hosting_count = (member.total_hosting_count or 0) + 1
            else:
                member.attendance_since_hosting = (member.attendance_since_hosting or 0) + 1

    # Update lunch record
    lunch.actual_attendance = len(attendee_ids)
    lunch.host_id = int(host_id) if host_id else None
    lunch.status = 'completed'

    db.session.commit()
    flash(f'Attendance saved! {len(attendee_ids)} members attended.', 'success')
    return redirect(url_for('secretary.dashboard'))


@secretary_bp.route('/add-guest', methods=['POST'])
@secretary_required
def add_guest():
    """Quick add a guest during attendance tracking."""
    from flask import jsonify

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    member = Member(
        name=name,
        email=email or None,
        member_type='guest',
        attendance_since_hosting=0,
        first_attended=date.today()
    )
    db.session.add(member)
    db.session.commit()

    return jsonify({
        'id': member.id,
        'name': member.name,
        'member_type': member.member_type
    })


@secretary_bp.route('/hosting-order')
@secretary_required
def hosting_order():
    """Manage the hosting order with drag-and-drop."""
    from app.services.email_jobs import get_hosting_queue
    # Get all regular members ordered by hosting queue (respects queue_position override)
    members = get_hosting_queue(limit=100)

    return render_template('secretary/hosting_order.html', members=members)


@secretary_bp.route('/hosting-order/reorder', methods=['POST'])
@secretary_required
def reorder_hosting():
    """Save new hosting order from drag-and-drop.

    Sets queue_position for manual ordering.
    Does NOT modify attendance_since_hosting (that's the actual count).
    """
    from flask import jsonify

    data = request.get_json()
    if not data or 'order' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    member_ids = data['order']  # List of member IDs in new order

    # Set queue_position for each member (1 = hosts next, 2 = on deck, etc.)
    for index, member_id in enumerate(member_ids):
        member = Member.query.get(int(member_id))
        if member and member.member_type == 'regular':
            member.queue_position = index + 1  # 1-indexed

    db.session.commit()

    return jsonify({'success': True, 'message': 'Hosting order updated'})


@secretary_bp.route('/hosting-order/auto-organize', methods=['POST'])
@secretary_required
def auto_organize_hosting():
    """Reset hosting order to natural order based on attendance_since_hosting.

    Simply clears all queue_position values, letting the natural order
    (based on attendance_since_hosting) take over.
    """
    from flask import jsonify

    # Clear all queue_position overrides - order reverts to attendance_since_hosting
    members = Member.query.filter_by(member_type='regular').all()
    for member in members:
        member.queue_position = None

    db.session.commit()

    return jsonify({'success': True, 'message': 'Hosting order reset to default (by attendance count)'})


@secretary_bp.route('/transfer', methods=['GET', 'POST'])
@secretary_required
def transfer_role():
    """Transfer the secretary role to another member."""
    regular_members = Member.query.filter_by(member_type='regular').order_by(Member.name).all()

    # Get current secretary (should be the logged-in user)
    current_member_id = session.get('member_id')

    if request.method == 'POST':
        new_secretary_id = request.form.get('new_secretary_id')
        confirm = request.form.get('confirm')

        if not new_secretary_id:
            flash('Please select a member to transfer the role to.', 'error')
            return redirect(url_for('secretary.transfer_role'))

        if confirm != 'yes':
            flash('Please confirm the transfer.', 'error')
            return redirect(url_for('secretary.transfer_role'))

        new_secretary = Member.query.get(int(new_secretary_id))
        if not new_secretary or new_secretary.member_type != 'regular':
            flash('Invalid member selected.', 'error')
            return redirect(url_for('secretary.transfer_role'))

        if new_secretary.id == current_member_id:
            flash('You are already the secretary.', 'error')
            return redirect(url_for('secretary.transfer_role'))

        # Transfer the role
        Setting.set('secretary_member_id', str(new_secretary.id))

        # Update session - current user is no longer secretary
        session['is_secretary'] = False

        flash(f'Secretary role transferred to {new_secretary.name}. You no longer have secretary access.', 'success')
        return redirect(url_for('member.dashboard'))

    return render_template('secretary/transfer.html',
                           members=regular_members,
                           current_member_id=current_member_id)
