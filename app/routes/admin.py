from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify, Response
from markupsafe import Markup
from datetime import date, timedelta, datetime
import csv
import io
import secrets
import os
from app import db
from app.models import Member, Location, Lunch, Attendance, Setting

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

    # Get sample data from database
    next_host = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).first()

    backup_host = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).offset(1).first()

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

    # Get hosting queue
    hosting_queue = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).limit(3).all()

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


@admin_bp.route('/settings/secretary', methods=['POST'])
@admin_required
def set_secretary():
    """Set the secretary member."""
    member_id = request.form.get('secretary_id')

    if member_id:
        member = Member.query.get(int(member_id))
        if member:
            Setting.set('secretary_member_id', str(member.id))
            flash(f'{member.name} is now set as the secretary.', 'success')
        else:
            flash('Invalid member selected.', 'error')
    else:
        # Clear secretary
        Setting.set('secretary_member_id', '')
        flash('Secretary has been cleared.', 'success')

    return redirect(url_for('admin.settings'))

