from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify, Response
from datetime import date, timedelta, datetime
import csv
import io
from app import db
from app.models import Member, Location, Lunch, Attendance

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == current_app.config['ADMIN_PASSWORD']:
            session['admin_authenticated'] = True
            session.permanent = True
            next_url = request.args.get('next') or url_for('admin.dashboard')
            return redirect(next_url)
        flash('Invalid password', 'error')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Log out admin."""
    session.pop('admin_authenticated', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('main.index'))


@admin_bp.route('/')
@admin_required
def dashboard():
    """Main admin dashboard."""
    # Get or create this week's lunch (next Tuesday)
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7  # Tuesday is weekday 1
    if days_until_tuesday == 0 and today.weekday() == 1:
        next_tuesday = today  # It's Tuesday
    else:
        next_tuesday = today + timedelta(days=days_until_tuesday)
    
    current_lunch = Lunch.query.filter_by(date=next_tuesday).first()
    
    # Get hosting queue (top 5)
    hosting_queue = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).limit(5).all()
    
    # Get recent lunches
    recent_lunches = Lunch.query.order_by(Lunch.date.desc()).limit(5).all()
    
    # Get member stats
    total_members = Member.query.filter_by(member_type='regular').count()
    total_guests = Member.query.filter_by(member_type='guest').count()
    
    return render_template('admin/dashboard.html',
                           current_lunch=current_lunch,
                           next_tuesday=next_tuesday,
                           hosting_queue=hosting_queue,
                           recent_lunches=recent_lunches,
                           total_members=total_members,
                           total_guests=total_guests)


@admin_bp.route('/attendance', methods=['GET', 'POST'])
@admin_required
def attendance():
    """Attendance tracking page."""
    # Get the lunch date from query param or default to this/next Tuesday
    lunch_date_str = request.args.get('date')
    if lunch_date_str:
        lunch_date = date.fromisoformat(lunch_date_str)
    else:
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0 and today.weekday() == 1:
            lunch_date = today
        else:
            lunch_date = today + timedelta(days=days_until_tuesday)
    
    # Get or create lunch record
    lunch = Lunch.query.filter_by(date=lunch_date).first()
    if not lunch:
        lunch = Lunch(date=lunch_date, status='planned')
        db.session.add(lunch)
        db.session.commit()
    
    if request.method == 'POST':
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
        flash(f'Attendance saved: {len(attendee_ids)} attendees', 'success')
        return redirect(url_for('admin.dashboard'))
    
    # Get all active members for the checklist
    members = Member.query.filter(
        Member.member_type.in_(['regular', 'guest'])
    ).order_by(Member.name).all()
    
    # Get already recorded attendance
    existing_attendance = {a.member_id: a for a in lunch.attendances.all()}
    
    # Get next host suggestion
    next_host = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).first()
    
    return render_template('admin/attendance.html',
                           lunch=lunch,
                           members=members,
                           existing_attendance=existing_attendance,
                           next_host=next_host)


@admin_bp.route('/members')
@admin_required
def members():
    """Member management page."""
    members = Member.query.order_by(Member.member_type, Member.name).all()
    return render_template('admin/members.html', members=members)


@admin_bp.route('/members/add', methods=['GET', 'POST'])
@admin_required
def add_member():
    """Add a new member."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        member_type = request.form.get('member_type', 'regular')
        
        if not name:
            flash('Name is required', 'error')
            return redirect(url_for('admin.add_member'))
        
        # Check for duplicate email
        if email and Member.query.filter_by(email=email).first():
            flash('A member with this email already exists', 'error')
            return redirect(url_for('admin.add_member'))
        
        member = Member(
            name=name,
            email=email or None,
            member_type=member_type,
            attendance_since_hosting=0,
            first_attended=date.today()
        )
        db.session.add(member)
        db.session.commit()
        
        flash(f'Added {name} as {member_type}', 'success')
        return redirect(url_for('admin.members'))
    
    return render_template('admin/add_member.html')


@admin_bp.route('/members/<int:member_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_member(member_id):
    """Edit a member."""
    member = Member.query.get_or_404(member_id)
    
    if request.method == 'POST':
        member.name = request.form.get('name', member.name).strip()
        member.email = request.form.get('email', '').strip() or None
        member.member_type = request.form.get('member_type', member.member_type)
        
        # Allow manual adjustment of attendance counter
        new_count = request.form.get('attendance_since_hosting')
        if new_count is not None and new_count.isdigit():
            member.attendance_since_hosting = int(new_count)
        
        db.session.commit()
        flash(f'Updated {member.name}', 'success')
        return redirect(url_for('admin.members'))
    
    return render_template('admin/edit_member.html', member=member)


@admin_bp.route('/hosting-queue')
@admin_required
def hosting_queue():
    """View the full hosting queue."""
    members = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).all()
    return render_template('admin/hosting_queue.html', members=members)


@admin_bp.route('/add-guest', methods=['POST'])
@admin_required
def add_guest():
    """Quick add a guest during attendance tracking."""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    lunch_date = request.form.get('lunch_date')
    
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


@admin_bp.route('/seed-members', methods=['POST'])
@admin_required
def seed_members_route():
    """One-time route to seed initial members."""
    from app.seed_members import seed_members
    result = seed_members()
    flash(f"Seeded members: {result['added']} added, {result['skipped']} skipped, {result['total']} total", 'success')
    return redirect(url_for('admin.members'))


# ============== INITIAL SETUP ROUTES ==============

@admin_bp.route('/setup')
@admin_required
def setup():
    """Initial setup wizard."""
    member_count = Member.query.count()
    has_historical_data = Member.query.filter(Member.last_hosted_date.isnot(None)).count() > 0
    
    return render_template('admin/setup.html',
                           member_count=member_count,
                           has_historical_data=has_historical_data)


@admin_bp.route('/setup/export-template')
@admin_required
def export_member_template():
    """Export CSV template with current members for data entry."""
    members = Member.query.order_by(Member.name).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        'name',
        'email', 
        'member_type',
        'attendance_since_hosting',
        'last_hosted_date',
        'total_hosting_count',
        'first_attended'
    ])
    
    # Data rows (existing members or empty template)
    if members:
        for m in members:
            writer.writerow([
                m.name,
                m.email,
                m.member_type,
                m.attendance_since_hosting or 0,
                m.last_hosted_date.strftime('%Y-%m-%d') if m.last_hosted_date else '',
                m.total_hosting_count or 0,
                m.first_attended.strftime('%Y-%m-%d') if m.first_attended else ''
            ])
    else:
        # Example row
        writer.writerow([
            'John Doe',
            'john@example.com',
            'regular',
            '3',
            '2024-11-15',
            '5',
            '2020-01-01'
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=members_template.csv'}
    )


@admin_bp.route('/setup/import', methods=['GET', 'POST'])
@admin_required
def import_members():
    """Import members and historical data from CSV."""
    if request.method == 'GET':
        return render_template('admin/import.html')
    
    # Handle CSV upload
    if 'csv_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('admin.import_members'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin.import_members'))
    
    if not file.filename.endswith('.csv'):
        flash('File must be a CSV', 'error')
        return redirect(url_for('admin.import_members'))
    
    try:
        # Read CSV
        stream = io.StringIO(file.stream.read().decode('utf-8-sig'))  # utf-8-sig handles BOM
        reader = csv.DictReader(stream)
        
        results = {'added': 0, 'updated': 0, 'errors': []}
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                email = row.get('email', '').strip().lower()
                if not email:
                    results['errors'].append(f"Row {row_num}: Missing email")
                    continue
                
                name = row.get('name', '').strip()
                if not name:
                    results['errors'].append(f"Row {row_num}: Missing name")
                    continue
                
                # Parse optional fields
                member_type = row.get('member_type', 'regular').strip() or 'regular'
                if member_type not in ('regular', 'guest', 'inactive'):
                    member_type = 'regular'
                
                attendance = int(row.get('attendance_since_hosting', 0) or 0)
                hosting_count = int(row.get('total_hosting_count', 0) or 0)
                
                last_hosted = None
                if row.get('last_hosted_date', '').strip():
                    try:
                        last_hosted = datetime.strptime(row['last_hosted_date'].strip(), '%Y-%m-%d')
                    except ValueError:
                        results['errors'].append(f"Row {row_num}: Invalid last_hosted_date format (use YYYY-MM-DD)")
                
                first_attended = None
                if row.get('first_attended', '').strip():
                    try:
                        first_attended = datetime.strptime(row['first_attended'].strip(), '%Y-%m-%d').date()
                    except ValueError:
                        results['errors'].append(f"Row {row_num}: Invalid first_attended format (use YYYY-MM-DD)")
                
                # Find or create member
                member = Member.query.filter_by(email=email).first()
                if member:
                    # Update existing
                    member.name = name
                    member.member_type = member_type
                    member.attendance_since_hosting = attendance
                    member.total_hosting_count = hosting_count
                    member.last_hosted_date = last_hosted
                    member.first_attended = first_attended
                    results['updated'] += 1
                else:
                    # Create new
                    member = Member(
                        name=name,
                        email=email,
                        member_type=member_type,
                        attendance_since_hosting=attendance,
                        total_hosting_count=hosting_count,
                        last_hosted_date=last_hosted,
                        first_attended=first_attended
                    )
                    db.session.add(member)
                    results['added'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Row {row_num}: {str(e)}")
        
        db.session.commit()
        
        # Build flash message
        msg = f"Import complete: {results['added']} added, {results['updated']} updated"
        if results['errors']:
            msg += f", {len(results['errors'])} errors"
            for err in results['errors'][:5]:  # Show first 5 errors
                flash(err, 'error')
            if len(results['errors']) > 5:
                flash(f"...and {len(results['errors']) - 5} more errors", 'error')
        
        flash(msg, 'success')
        return redirect(url_for('admin.setup'))
        
    except Exception as e:
        flash(f'Error processing CSV: {str(e)}', 'error')
        return redirect(url_for('admin.import_members'))

