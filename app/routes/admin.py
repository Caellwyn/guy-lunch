from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify, Response
from markupsafe import Markup
from datetime import date, timedelta, datetime
import csv
import io
import secrets
import os
from app import db
from app.models import Member, Location, Lunch, Attendance, Setting, Photo
from app.services.storage_service import storage_service
from app.services.email_jobs import get_hosting_queue

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

    # Get hosting queue (top 5) - uses queue_position override if set
    hosting_queue = get_hosting_queue(limit=5)
    
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
    
    # Get next host suggestion (uses queue_position override if set)
    queue = get_hosting_queue(limit=1)
    next_host = queue[0] if queue else None
    
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

    # Get current secretary
    secretary_id = Setting.get('secretary_member_id')
    current_secretary = Member.query.get(int(secretary_id)) if secretary_id else None

    # Get regular members for secretary dropdown
    regular_members = Member.query.filter_by(member_type='regular').order_by(Member.name).all()

    return render_template('admin/members.html',
                           members=members,
                           current_secretary=current_secretary,
                           regular_members=regular_members)


@admin_bp.route('/members/set-secretary', methods=['POST'])
@admin_required
def set_secretary():
    """Set the group secretary."""
    member_id = request.form.get('secretary_id')

    if member_id:
        member = Member.query.get(int(member_id))
        if member and member.member_type == 'regular':
            Setting.set('secretary_member_id', str(member.id))
            flash(f'{member.name} is now the group secretary.', 'success')
        else:
            flash('Invalid member selected.', 'error')
    else:
        # Clear secretary
        Setting.set('secretary_member_id', '')
        flash('Secretary role has been cleared.', 'success')

    return redirect(url_for('admin.members'))


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

        # Profile fields
        member.phone = request.form.get('phone', '').strip() or None
        member.business = request.form.get('business', '').strip() or None
        website = request.form.get('website', '').strip() or None
        if website and not (website.startswith('http://') or website.startswith('https://')):
            website = 'https://' + website
        member.website = website
        bio = request.form.get('bio', '').strip() or None
        member.bio = bio[:500] if bio else None
        member.profile_public = request.form.get('profile_public') == 'on'

        db.session.commit()
        flash(f'Updated {member.name}', 'success')
        return redirect(url_for('admin.members'))

    return render_template('admin/edit_member.html', member=member)


@admin_bp.route('/hosting-queue')
@admin_required
def hosting_queue():
    """View the full hosting queue."""
    members = get_hosting_queue(limit=100)  # Get all members in queue order
    return render_template('admin/hosting_queue.html', members=members)


@admin_bp.route('/hosting-queue/swap', methods=['GET', 'POST'])
@admin_required
def swap_hosts():
    """Swap two members' positions in the hosting queue."""
    members = get_hosting_queue(limit=100)  # Get all members in queue order

    if request.method == 'POST':
        member1_id = request.form.get('member1_id', type=int)
        member2_id = request.form.get('member2_id', type=int)

        if not member1_id or not member2_id:
            flash('Please select two members to swap.', 'error')
            return render_template('admin/swap_hosts.html', members=members)

        if member1_id == member2_id:
            flash('Cannot swap a member with themselves.', 'error')
            return render_template('admin/swap_hosts.html', members=members)

        member1 = Member.query.get(member1_id)
        member2 = Member.query.get(member2_id)

        if not member1 or not member2:
            flash('One or both members not found.', 'error')
            return render_template('admin/swap_hosts.html', members=members)

        if member1.member_type != 'regular' or member2.member_type != 'regular':
            flash('Both members must be active regular members.', 'error')
            return render_template('admin/swap_hosts.html', members=members)

        # Swap their attendance_since_hosting values
        member1.attendance_since_hosting, member2.attendance_since_hosting = \
            member2.attendance_since_hosting, member1.attendance_since_hosting

        db.session.commit()

        flash(f'Swapped positions: {member1.name} ↔ {member2.name}', 'success')
        return redirect(url_for('admin.hosting_queue'))

    return render_template('admin/swap_hosts.html', members=members)


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


# ============== EMAIL PREVIEW ROUTES ==============

def get_next_tuesday():
    """Get the next Tuesday date."""
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0 and today.weekday() == 1:
        return today
    return today + timedelta(days=days_until_tuesday)


def substitute_brevo_params(html_content, params):
    """Replace Brevo {{ params.X }} placeholders with actual values for preview."""
    import re
    for key, value in params.items():
        # Match {{ params.KEY }} with optional whitespace
        pattern = r'\{\{\s*params\.' + key + r'\s*\}\}'
        html_content = re.sub(pattern, str(value), html_content)
    return html_content


@admin_bp.route('/emails')
@admin_required
def emails():
    """Email template management and preview hub."""
    return render_template('admin/emails.html')


@admin_bp.route('/emails/preview/<email_type>')
@admin_required
def preview_email(email_type):
    """Preview an email template with sample data.

    Templates use Brevo syntax {{ params.VARIABLE_NAME }}.
    For preview, we substitute sample values from the database.
    """
    next_tuesday = get_next_tuesday()
    app_url = current_app.config.get('APP_URL', 'http://localhost:5000')

    # Get sample data from database (uses queue_position override if set)
    queue = get_hosting_queue(limit=2)
    next_host = queue[0] if len(queue) > 0 else None
    backup_host = queue[1] if len(queue) > 1 else None

    recent_locations = Location.query.order_by(Location.last_visited.desc()).limit(5).all()
    sample_location = recent_locations[0] if recent_locations else None

    sample_member = Member.query.filter_by(member_type='regular').first()
    sample_token = secrets.token_urlsafe(32)

    # Use Flask's url_for to generate proper static URLs
    # In production, these would be hosted externally (Brevo CDN, etc.)
    ai_guy_logo = url_for('static', filename='emails/Ai_guy_transparent.png', _external=True)
    header_img = url_for('static', filename='emails/announcment_header.jpg', _external=True)
    location_bg = url_for('static', filename='emails/announcment_Location_backgound.jpg', _external=True)
    intel_bg = url_for('static', filename='emails/announcement_intel_report_background.jpg', _external=True)

    # Build params dict based on email type (matching Brevo template variables)
    if email_type == 'host_confirmation':
        template_file = 'emails/host_confirmation.html'
        params = {
            'HOST_NAME': next_host.name if next_host else 'John Smith',
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'CONFIRM_URL': f"{app_url}/confirm/{sample_token}",
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = f"You're Hosting Tuesday Lunch - {next_tuesday.strftime('%B %d')}"
        recipient = next_host.email if next_host else 'host@example.com'

    elif email_type == 'secretary_reminder_confirmed':
        template_file = 'emails/secretary_reminder.html'
        host_name = next_host.name if next_host else 'John Smith'
        location_name = sample_location.name if sample_location else "Sample Restaurant"
        location_address = sample_location.address if sample_location else "123 Main St, Longview, WA"
        location_phone = sample_location.phone if sample_location else "(360) 555-1234"
        params = {
            'EMAIL_TITLE': f"Make Reservation - {location_name}",
            'EMAIL_HEADING': "Time to Make the Reservation!",
            'INTRO_TEXT': f"{host_name} has selected a location for this week's lunch. Please call to make a reservation.",
            'BOX_BG_COLOR': '#f0fdf4',
            'BOX_BORDER_COLOR': '#22c55e',
            'BOX_LABEL_COLOR': '#166534',
            'BOX_TITLE_COLOR': '#14532d',
            'BOX_TEXT_COLOR': '#166534',
            'BOX_LABEL': "This Week's Location",
            'BOX_TITLE': location_name,
            'BOX_CONTENT': f"Address: {location_address}<br>Phone: {location_phone}",
            'LUNCH_DATE': next_tuesday.strftime('%A, %B %d, %Y'),
            'EXPECTED_ATTENDANCE': '18',
            'HOST_NAME': host_name,
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = f"Make Reservation - {location_name}"
        recipient = 'secretary@example.com'

    elif email_type == 'secretary_reminder_not_confirmed':
        template_file = 'emails/secretary_reminder.html'
        host_name = next_host.name if next_host else 'John Smith'
        host_email = next_host.email if next_host else 'host@example.com'
        backup_name = backup_host.name if backup_host else 'Jane Doe'
        backup_email = backup_host.email if backup_host else 'backup@example.com'
        params = {
            'EMAIL_TITLE': "ALERT: Host Has Not Confirmed Location",
            'EMAIL_HEADING': "Host Has Not Responded",
            'INTRO_TEXT': f"{host_name} has not yet selected a restaurant for this week's lunch.",
            'BOX_BG_COLOR': '#fef2f2',
            'BOX_BORDER_COLOR': '#dc2626',
            'BOX_LABEL_COLOR': '#991b1b',
            'BOX_TITLE_COLOR': '#7f1d1d',
            'BOX_TEXT_COLOR': '#991b1b',
            'BOX_LABEL': "Action Required",
            'BOX_TITLE': "Please Contact Host",
            'BOX_CONTENT': f"Primary: {host_name} ({host_email})<br>Backup: {backup_name} ({backup_email})",
            'LUNCH_DATE': next_tuesday.strftime('%A, %B %d, %Y'),
            'EXPECTED_ATTENDANCE': '18',
            'HOST_NAME': host_name,
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = "ALERT: Host Has Not Confirmed Location"
        recipient = 'secretary@example.com'

    elif email_type == 'announcement':
        template_file = 'emails/announcement_V2.html'
        location_name = sample_location.name if sample_location else "The Local Pub & Grill"
        location_address = sample_location.address if sample_location else "456 Industrial Way, Longview, WA 98632"
        params = {
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'LOCATION_NAME': location_name,
            'LOCATION_ADDRESS': location_address,
            'GOOGLE_MAPS_URL': f"https://www.google.com/maps/search/?api=1&query={location_address.replace(' ', '+')}",
            'START_TIME': '12 hundred hours (12:00 PM)',
            'HOST_NAME': next_host.name if next_host else 'Richard Smith',
            'LOCATION_CUISINE': sample_location.cuisine_type if sample_location else "Classic American Pub Fare",
            'LOCATION_RATING': f"{sample_location.avg_group_rating:.1f}" if sample_location and sample_location.avg_group_rating else "4.6",
            'LOCATION_PRICE': '$' * (sample_location.price_level if sample_location and sample_location.price_level else 2) + " (Mid-Range)",
            'LAST_VISITED': sample_location.last_visited.strftime('%B %d, %Y') if sample_location and sample_location.last_visited else "First Engagement!",
            # Image URLs - using Flask static file serving
            'HEADER_IMAGE_URL': header_img,
            'LOCATION_BG_IMAGE_URL': location_bg,
            'INTEL_BG_IMAGE_URL': intel_bg,
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = f"Guy Lunch Briefing - {next_tuesday.strftime('%B %d')} at {location_name}"
        recipient = 'all members'

    elif email_type == 'rating_request':
        template_file = 'emails/rating_request.html'
        location_name = sample_location.name if sample_location else "Sample Restaurant"
        params = {
            'MEMBER_NAME': sample_member.name if sample_member else 'John Smith',
            'LOCATION_NAME': location_name,
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'HOST_NAME': next_host.name if next_host else 'Jane Doe',
            'RATING_URL': f"{app_url}/rate/{sample_token}",
            'ATTENDANCE_COUNT': '18',
            'VISIT_TEXT': 'Our 3rd visit here',
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = f"Rate Today's Lunch at {location_name}"
        recipient = sample_member.email if sample_member else 'member@example.com'

    else:
        flash(f'Unknown email type: {email_type}', 'error')
        return redirect(url_for('admin.emails'))

    # Read the template file and substitute Brevo params for preview
    import os
    template_path = os.path.join(current_app.root_path, 'templates', template_file)
    with open(template_path, 'r', encoding='utf-8') as f:
        raw_html = f.read()

    # Substitute {{ params.X }} with actual values
    email_html = substitute_brevo_params(raw_html, params)

    return render_template('admin/email_preview.html',
                           email_type=email_type,
                           email_html=Markup(email_html),
                           subject=subject,
                           recipient=recipient,
                           brevo_params=params)


@admin_bp.route('/emails/live-preview/<email_type>')
@admin_required
def live_preview_email(email_type):
    """
    Preview an email with LIVE working links.

    Creates real database records (lunch, tokens) so all links work.
    No email is sent - just renders in browser for testing.
    """
    from app.models import Lunch, Rating
    import os

    next_tuesday = get_next_tuesday()
    app_url = current_app.config.get('APP_URL', request.url_root.rstrip('/'))

    # Get the next host (uses queue_position override if set)
    queue = get_hosting_queue(limit=2)
    next_host = queue[0] if len(queue) > 0 else None
    backup_host = queue[1] if len(queue) > 1 else None

    # Get or create a test lunch for next Tuesday
    test_lunch = Lunch.query.filter_by(date=next_tuesday).first()
    if not test_lunch:
        test_lunch = Lunch(
            date=next_tuesday,
            host_id=next_host.id if next_host else None,
            status='planned'
        )
        db.session.add(test_lunch)
        db.session.flush()

    # Image URLs
    ai_guy_logo = url_for('static', filename='emails/Ai_guy_transparent.png', _external=True)
    header_img = url_for('static', filename='emails/announcment_header.jpg', _external=True)
    location_bg = url_for('static', filename='emails/announcment_Location_backgound.jpg', _external=True)
    intel_bg = url_for('static', filename='emails/announcement_intel_report_background.jpg', _external=True)

    # Build params based on email type with REAL tokens
    if email_type == 'host_confirmation':
        # Generate a real confirmation token
        token = secrets.token_urlsafe(32)
        test_lunch.confirmation_token = token
        test_lunch.reservation_confirmed = False
        test_lunch.location_id = None
        db.session.commit()

        template_file = 'emails/host_confirmation.html'
        params = {
            'HOST_NAME': next_host.name if next_host else 'Test Host',
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'CONFIRM_URL': f"{app_url}/confirm/{token}",
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = f"You're Hosting Tuesday Lunch - {next_tuesday.strftime('%B %d')}"
        recipient = next_host.name if next_host else 'Test Host'
        recipient_email = next_host.email if next_host else 'test@example.com'

    elif email_type == 'secretary_reminder':
        # Check if lunch has a location confirmed
        if test_lunch.location_id and test_lunch.reservation_confirmed:
            location = Location.query.get(test_lunch.location_id)
            template_file = 'emails/secretary_reminder.html'
            params = {
                'EMAIL_TITLE': f"Make Reservation - {location.name}",
                'EMAIL_HEADING': "Time to Make the Reservation!",
                'INTRO_TEXT': f"{next_host.name if next_host else 'The host'} has selected a location for this week's lunch. Please call to make a reservation.",
                'BOX_BG_COLOR': '#f0fdf4',
                'BOX_BORDER_COLOR': '#22c55e',
                'BOX_LABEL_COLOR': '#166534',
                'BOX_TITLE_COLOR': '#14532d',
                'BOX_TEXT_COLOR': '#166534',
                'BOX_LABEL': "This Week's Location",
                'BOX_TITLE': location.name,
                'BOX_CONTENT': f"Address: {location.address or 'N/A'}<br>Phone: {location.phone or 'N/A'}",
                'LUNCH_DATE': next_tuesday.strftime('%A, %B %d, %Y'),
                'EXPECTED_ATTENDANCE': '18',
                'HOST_NAME': next_host.name if next_host else 'Host',
                'AI_GUY_LOGO_URL': ai_guy_logo,
            }
            subject = f"Make Reservation - {location.name}"
        else:
            # Not confirmed - show alert version
            template_file = 'emails/secretary_reminder.html'
            params = {
                'EMAIL_TITLE': "ALERT: Host Has Not Confirmed Location",
                'EMAIL_HEADING': "Host Has Not Responded",
                'INTRO_TEXT': f"{next_host.name if next_host else 'The host'} has not yet selected a restaurant for this week's lunch.",
                'BOX_BG_COLOR': '#fef2f2',
                'BOX_BORDER_COLOR': '#dc2626',
                'BOX_LABEL_COLOR': '#991b1b',
                'BOX_TITLE_COLOR': '#7f1d1d',
                'BOX_TEXT_COLOR': '#991b1b',
                'BOX_LABEL': "Action Required",
                'BOX_TITLE': "Please Contact Host",
                'BOX_CONTENT': f"Primary: {next_host.name if next_host else 'N/A'} ({next_host.email if next_host else 'N/A'})<br>Backup: {backup_host.name if backup_host else 'N/A'} ({backup_host.email if backup_host else 'N/A'})",
                'LUNCH_DATE': next_tuesday.strftime('%A, %B %d, %Y'),
                'EXPECTED_ATTENDANCE': '18',
                'HOST_NAME': next_host.name if next_host else 'Host',
                'AI_GUY_LOGO_URL': ai_guy_logo,
            }
            subject = "ALERT: Host Has Not Confirmed Location"
        recipient = 'Secretary'
        recipient_email = 'secretary@example.com'

    elif email_type == 'announcement':
        # Need a location for announcement
        if not test_lunch.location_id:
            # Use most recent location for testing
            sample_location = Location.query.order_by(Location.last_visited.desc()).first()
            if sample_location:
                test_lunch.location_id = sample_location.id
                test_lunch.reservation_confirmed = True
                db.session.commit()

        location = Location.query.get(test_lunch.location_id) if test_lunch.location_id else None
        if not location:
            flash('No location available for announcement preview. Please add a location first.', 'error')
            return redirect(url_for('admin.email_jobs'))

        template_file = 'emails/announcement_V2.html'
        params = {
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'LOCATION_NAME': location.name,
            'LOCATION_ADDRESS': location.address or 'Address TBD',
            'GOOGLE_MAPS_URL': f"https://www.google.com/maps/search/?api=1&query={(location.address or location.name).replace(' ', '+')}",
            'START_TIME': '12 hundred hours (12:00 PM)',
            'HOST_NAME': next_host.name if next_host else 'Host',
            'LOCATION_CUISINE': location.cuisine_type or 'Great Food',
            'LOCATION_RATING': f"{location.avg_group_rating:.1f}" if location.avg_group_rating else "New!",
            'LOCATION_PRICE': ('$' * location.price_level if location.price_level else '$$') + " (Mid-Range)",
            'LAST_VISITED': location.last_visited.strftime('%B %d, %Y') if location.last_visited else "First Engagement!",
            'HEADER_IMAGE_URL': header_img,
            'LOCATION_BG_IMAGE_URL': location_bg,
            'INTEL_BG_IMAGE_URL': intel_bg,
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = f"Guy Lunch Briefing - {next_tuesday.strftime('%B %d')} at {location.name}"
        recipient = 'All Members'
        recipient_email = 'all@example.com'

    elif email_type == 'rating_request':
        # Need a location and a member for rating
        sample_member = Member.query.filter_by(member_type='regular').first()
        location = Location.query.get(test_lunch.location_id) if test_lunch.location_id else None

        if not location:
            sample_location = Location.query.order_by(Location.last_visited.desc()).first()
            if sample_location:
                test_lunch.location_id = sample_location.id
                db.session.commit()
                location = sample_location

        if not location:
            flash('No location available for rating preview. Please add a location first.', 'error')
            return redirect(url_for('admin.email_jobs'))

        # Create or get a rating record with a real token
        rating_token = secrets.token_urlsafe(32)
        test_rating = Rating.query.filter_by(
            lunch_id=test_lunch.id,
            member_id=sample_member.id if sample_member else None
        ).first()

        if not test_rating and sample_member:
            test_rating = Rating(
                lunch_id=test_lunch.id,
                member_id=sample_member.id,
                rating_token=rating_token
            )
            db.session.add(test_rating)
        elif test_rating:
            test_rating.rating_token = rating_token
            test_rating.rating = None  # Reset so we can test
        db.session.commit()

        template_file = 'emails/rating_request.html'
        params = {
            'MEMBER_NAME': sample_member.name if sample_member else 'Test Member',
            'LOCATION_NAME': location.name,
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'HOST_NAME': next_host.name if next_host else 'Host',
            'RATING_URL': f"{app_url}/rate/{rating_token}",
            'ATTENDANCE_COUNT': '18',
            'VISIT_TEXT': f"Visit #{location.visit_count + 1}" if location.visit_count else "First visit!",
            'AI_GUY_LOGO_URL': ai_guy_logo,
        }
        subject = f"Rate Today's Lunch at {location.name}"
        recipient = sample_member.name if sample_member else 'Test Member'
        recipient_email = sample_member.email if sample_member else 'test@example.com'

    else:
        flash(f'Unknown email type: {email_type}', 'error')
        return redirect(url_for('admin.email_jobs'))

    # Read and render the template
    template_path = os.path.join(current_app.root_path, 'templates', template_file)
    with open(template_path, 'r', encoding='utf-8') as f:
        raw_html = f.read()

    email_html = substitute_brevo_params(raw_html, params)

    # Wrap in a preview container with banner
    preview_html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Preview: {email_type}</title>
        <style>
            .preview-banner {{
                background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%);
                color: white;
                padding: 16px 24px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                position: sticky;
                top: 0;
                z-index: 1000;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .preview-banner h2 {{
                margin: 0 0 8px 0;
                font-size: 18px;
            }}
            .preview-banner p {{
                margin: 4px 0;
                font-size: 14px;
                opacity: 0.9;
            }}
            .preview-banner .meta {{
                display: flex;
                gap: 24px;
                flex-wrap: wrap;
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid rgba(255,255,255,0.2);
            }}
            .preview-banner .meta span {{
                font-size: 13px;
            }}
            .preview-banner .meta strong {{
                color: #fbbf24;
            }}
            .preview-banner a {{
                color: #fbbf24;
                text-decoration: none;
            }}
            .preview-banner a:hover {{
                text-decoration: underline;
            }}
            .email-container {{
                max-width: 100%;
                margin: 0;
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0;">
        <div class="preview-banner">
            <h2>LIVE PREVIEW MODE - All Links Work!</h2>
            <p>This is how the email will look. Click any links to test the full flow. No email was sent.</p>
            <div class="meta">
                <span><strong>Type:</strong> {email_type.replace('_', ' ').title()}</span>
                <span><strong>To:</strong> {recipient} ({recipient_email})</span>
                <span><strong>Subject:</strong> {subject}</span>
                <span><a href="{url_for('admin.email_jobs')}">&larr; Back to Email Jobs</a></span>
            </div>
        </div>
        <div class="email-container">
            {email_html}
        </div>
    </body>
    </html>
    '''

    return preview_html


# ============== EMAIL JOB TRIGGERS ==============

@admin_bp.route('/emails/jobs')
@admin_required
def email_jobs():
    """Email job management page - view and trigger email jobs."""
    from app.models import EmailLog, Lunch

    # Get next Tuesday info
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0 and today.weekday() == 1:
        next_tuesday = today
    else:
        next_tuesday = today + timedelta(days=days_until_tuesday)

    # Get lunch for next Tuesday
    next_lunch = Lunch.query.filter_by(date=next_tuesday).first()

    # Get recent email logs
    recent_emails = EmailLog.query.order_by(EmailLog.sent_at.desc()).limit(20).all()

    # Get hosting queue (uses queue_position override if set)
    hosting_queue = get_hosting_queue(limit=3)

    return render_template('admin/email_jobs.html',
                           next_tuesday=next_tuesday,
                           next_lunch=next_lunch,
                           recent_emails=recent_emails,
                           hosting_queue=hosting_queue)


@admin_bp.route('/emails/trigger/<job_name>', methods=['POST'])
@admin_required
def trigger_email_job(job_name):
    """Manually trigger an email job."""
    from app.services.email_jobs import run_email_job

    # Check for dry_run parameter
    dry_run = request.form.get('dry_run', 'false').lower() == 'true'

    result = run_email_job(job_name, dry_run=dry_run)

    if result['success']:
        flash(f"Job '{job_name}' completed: {result.get('message', 'Success')}", 'success')
    else:
        flash(f"Job '{job_name}' failed: {result.get('message', 'Unknown error')}", 'error')

    return redirect(url_for('admin.email_jobs'))


@admin_bp.route('/emails/logs')
@admin_required
def email_logs():
    """View all email logs."""
    from app.models import EmailLog

    page = request.args.get('page', 1, type=int)
    per_page = 50

    logs = EmailLog.query.order_by(EmailLog.sent_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('admin/email_logs.html', logs=logs)


# ============== SETTINGS ==============

@admin_bp.route('/settings')
@admin_required
def settings():
    """Application settings page."""
    members = Member.query.filter(
        Member.member_type.in_(['regular', 'guest'])
    ).order_by(Member.name).all()

    # Get current settings
    secretary_id = Setting.get('secretary_member_id')
    secretary = Member.query.get(int(secretary_id)) if secretary_id else None

    return render_template('admin/settings.html',
                           members=members,
                           secretary=secretary)


# Secretary assignment moved to /admin/members/set-secretary


# ============== LOCATIONS MANAGEMENT ==============

@admin_bp.route('/locations')
@admin_required
def locations():
    """Location management page."""
    all_locations = Location.query.order_by(Location.name).all()
    return render_template('admin/locations.html', locations=all_locations)


@admin_bp.route('/locations/add', methods=['POST'])
@admin_required
def add_location():
    """Add a new location."""
    name = request.form.get('name', '').strip()
    address = request.form.get('address', '').strip()
    phone = request.form.get('phone', '').strip()
    google_place_id = request.form.get('google_place_id', '').strip()
    google_rating = request.form.get('google_rating', '').strip()
    price_level = request.form.get('price_level', '').strip()
    cuisine_type = request.form.get('cuisine_type', '').strip()
    group_friendly = request.form.get('group_friendly') == 'on'

    if not name:
        flash('Restaurant name is required.', 'error')
        return redirect(url_for('admin.locations'))

    # Check if location with this Google Place ID already exists
    if google_place_id:
        existing = Location.query.filter_by(google_place_id=google_place_id).first()
        if existing:
            flash(f'{existing.name} already exists in the database.', 'error')
            return redirect(url_for('admin.locations'))

    # Create new location
    location = Location(
        name=name,
        address=address or None,
        phone=phone or None,
        google_place_id=google_place_id or None,
        google_rating=float(google_rating) if google_rating else None,
        price_level=int(price_level) if price_level else None,
        cuisine_type=cuisine_type or None,
        group_friendly=group_friendly,
        visit_count=0
    )
    db.session.add(location)
    db.session.commit()

    flash(f'Added {location.name}!', 'success')
    return redirect(url_for('admin.locations'))


@admin_bp.route('/locations/<int:location_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_location(location_id):
    """Edit a location."""
    location = Location.query.get_or_404(location_id)

    if request.method == 'POST':
        location.name = request.form.get('name', location.name).strip()
        location.address = request.form.get('address', '').strip() or None
        location.phone = request.form.get('phone', '').strip() or None
        location.cuisine_type = request.form.get('cuisine_type', '').strip() or None
        location.group_friendly = request.form.get('group_friendly') == 'on'

        price_level = request.form.get('price_level', '').strip()
        location.price_level = int(price_level) if price_level else None

        google_rating = request.form.get('google_rating', '').strip()
        location.google_rating = float(google_rating) if google_rating else None

        avg_group_rating = request.form.get('avg_group_rating', '').strip()
        location.avg_group_rating = float(avg_group_rating) if avg_group_rating else None

        db.session.commit()
        flash(f'Updated {location.name}.', 'success')
        return redirect(url_for('admin.locations'))

    return render_template('admin/edit_location.html', location=location)


@admin_bp.route('/locations/<int:location_id>/delete', methods=['POST'])
@admin_required
def delete_location(location_id):
    """Delete a location."""
    location = Location.query.get_or_404(location_id)
    name = location.name

    # Clear references in lunches
    Lunch.query.filter_by(location_id=location_id).update({'location_id': None})

    db.session.delete(location)
    db.session.commit()

    flash(f'Deleted {name}.', 'success')
    return redirect(url_for('admin.locations'))


@admin_bp.route('/photos')
@admin_required
def photos():
    """Manage uploaded photos."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    photos = Photo.query.order_by(Photo.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/photos.html', photos=photos)


@admin_bp.route('/photos/delete/<int:photo_id>', methods=['POST'])
@admin_required
def delete_photo(photo_id):
    """Delete a photo."""
    photo = Photo.query.get_or_404(photo_id)
    
    # Delete from R2
    if photo.file_url:
        storage_service.delete_file(photo.file_url)
    
    # Delete from DB
    db.session.delete(photo)
    db.session.commit()
    
    flash('Photo deleted successfully.', 'success')
    return redirect(url_for('admin.photos'))
