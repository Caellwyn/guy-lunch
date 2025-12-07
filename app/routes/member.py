"""
Member portal routes - authentication and member dashboard.

Uses magic link authentication - members receive a login link via email.
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from datetime import date, datetime, timedelta
import secrets

from app import db
from app.models import Member, Lunch, Attendance, Location

member_bp = Blueprint('member', __name__, url_prefix='/member')


# ============== AUTHENTICATION ==============

def is_local_development():
    """Check if running in local development mode."""
    return current_app.debug or current_app.config.get('FLASK_ENV') == 'development'


def member_required(f):
    """Decorator to require member authentication.
    
    In local development (debug mode), auto-logs in as first member if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('member_id'):
            # In local dev, auto-login as first member
            if is_local_development():
                member = Member.query.first()
                if member:
                    session['member_id'] = member.id
                    session['member_name'] = member.name
                    session.permanent = True
                else:
                    return redirect(url_for('member.login', next=request.url))
            else:
                return redirect(url_for('member.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_current_member():
    """Get the currently logged-in member."""
    member_id = session.get('member_id')
    if member_id:
        return Member.query.get(member_id)
    return None


@member_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Member login page - request magic link."""
    if session.get('member_id'):
        return redirect(url_for('member.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('member/login.html')

        # Find member by email
        member = Member.query.filter_by(email=email).first()

        if not member:
            # Don't reveal if email exists or not (security)
            flash('If that email is registered, you will receive a login link shortly.', 'success')
            return render_template('member/login.html')

        if member.member_type == 'inactive':
            flash('If that email is registered, you will receive a login link shortly.', 'success')
            return render_template('member/login.html')

        # Generate magic link token and store on member
        token = secrets.token_urlsafe(32)
        member.magic_link_token = token
        member.magic_link_expires = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()

        # Send magic link email
        from app.services.email_service import email_service
        app_url = current_app.config.get('APP_URL', 'http://localhost:5000')
        magic_link_url = f"{app_url}/member/auth/{token}"

        result = email_service.send_email(
            to_email=member.email,
            to_name=member.name,
            subject="Your Tuesday Lunch Login Link",
            template_file='emails/magic_link.html',
            params={
                'MEMBER_NAME': member.name,
                'MAGIC_LINK_URL': magic_link_url,
                'EXPIRES_MINUTES': '15',
            },
            email_type='magic_link',
            dry_run=False
        )

        if result['success']:
            flash('Check your email! A login link has been sent.', 'success')
        else:
            flash('If that email is registered, you will receive a login link shortly.', 'success')
            current_app.logger.error(f"Failed to send magic link to {email}: {result.get('error')}")

        return render_template('member/login.html')

    return render_template('member/login.html')


@member_bp.route('/auth/<token>')
def authenticate(token):
    """Validate magic link token and log in member."""
    # Look up member by token
    member = Member.query.filter_by(magic_link_token=token).first()

    if not member:
        flash('This login link is invalid or has expired. Please request a new one.', 'error')
        return redirect(url_for('member.login'))

    # Check if token has expired
    if member.magic_link_expires and datetime.utcnow() > member.magic_link_expires:
        # Token expired - clean it up
        member.magic_link_token = None
        member.magic_link_expires = None
        db.session.commit()
        flash('This login link has expired. Please request a new one.', 'error')
        return redirect(url_for('member.login'))

    # Success! Log in the member
    session['member_id'] = member.id
    session['member_name'] = member.name
    session.permanent = True

    # Clean up used token (single-use)
    member.magic_link_token = None
    member.magic_link_expires = None
    db.session.commit()

    flash(f'Welcome back, {member.name}!', 'success')

    # Redirect to original destination or dashboard
    next_url = request.args.get('next') or url_for('member.dashboard')
    return redirect(next_url)


@member_bp.route('/logout')
def logout():
    """Log out member."""
    session.pop('member_id', None)
    session.pop('member_name', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))


@member_bp.route('/dev-login')
def dev_login():
    """Backdoor for development to skip email."""
    if not current_app.debug:
        return "Not available in production", 403
    
    # Log in as the first member found
    member = Member.query.first()
    if not member:
        return "No members found in database", 404
        
    session['member_id'] = member.id
    session['member_name'] = member.name
    session.permanent = True
    
    flash(f'Dev Login Successful as {member.name}', 'success')
    return redirect(url_for('member.dashboard'))


# ============== MEMBER DASHBOARD ==============

def get_next_tuesday():
    """Get the next Tuesday date."""
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0 and today.weekday() == 1:
        return today
    return today + timedelta(days=days_until_tuesday)


def calculate_hosting_position(member):
    """
    Calculate member's position in the hosting queue.
    Returns (position, total_in_queue).
    """
    queue = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).all()

    for i, m in enumerate(queue):
        if m.id == member.id:
            return (i + 1, len(queue))

    return (None, len(queue))


def estimate_hosting_date(member, position):
    """
    Estimate when member will host based on queue position.
    Assumes weekly lunches on Tuesday.
    """
    if position is None or position <= 0:
        return None

    next_tuesday = get_next_tuesday()
    # Position 1 = this Tuesday (or next Tuesday if already passed today)
    weeks_until_hosting = position - 1
    estimated_date = next_tuesday + timedelta(weeks=weeks_until_hosting)

    return estimated_date


def get_baseball_lineup():
    """
    Get the hosting lineup in baseball batting order style.
    Returns dict with 'at_bat', 'on_deck', 'in_hole', 'dugout' lists.
    """
    queue = Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
        Member.name
    ).all()

    lineup = {
        'at_bat': queue[0] if len(queue) > 0 else None,
        'on_deck': queue[1] if len(queue) > 1 else None,
        'in_hole': queue[2] if len(queue) > 2 else None,  # "In the hole" = 3rd up
        'dugout': queue[3:] if len(queue) > 3 else [],
    }

    return lineup


@member_bp.route('/')
@member_required
def dashboard():
    """Member portal dashboard."""
    member = get_current_member()
    if not member:
        return redirect(url_for('member.login'))

    # Get hosting position and estimate
    position, total_members = calculate_hosting_position(member)
    estimated_hosting_date = estimate_hosting_date(member, position)

    # Get baseball lineup
    lineup = get_baseball_lineup()

    # Determine member's status in the lineup
    member_status = None
    if lineup['at_bat'] and lineup['at_bat'].id == member.id:
        member_status = 'at_bat'
    elif lineup['on_deck'] and lineup['on_deck'].id == member.id:
        member_status = 'on_deck'
    elif lineup['in_hole'] and lineup['in_hole'].id == member.id:
        member_status = 'in_hole'
    else:
        member_status = 'dugout'

    # Get next/upcoming lunch info
    next_tuesday = get_next_tuesday()
    upcoming_lunch = Lunch.query.filter_by(date=next_tuesday).first()

    # Get member's recent attendance history
    recent_attendances = Attendance.query.filter_by(member_id=member.id).join(
        Lunch
    ).order_by(Lunch.date.desc()).limit(10).all()

    # Stats
    total_attended = Attendance.query.filter_by(member_id=member.id).count()
    total_hosted = member.total_hosting_count or 0

    return render_template('member/dashboard.html',
                           member=member,
                           position=position,
                           total_members=total_members,
                           estimated_hosting_date=estimated_hosting_date,
                           lineup=lineup,
                           member_status=member_status,
                           upcoming_lunch=upcoming_lunch,
                           next_tuesday=next_tuesday,
                           recent_attendances=recent_attendances,
                           total_attended=total_attended,
                           total_hosted=total_hosted)


@member_bp.route('/lineup')
@member_required
def lineup():
    """Full hosting lineup page."""
    member = get_current_member()
    if not member:
        return redirect(url_for('member.login'))

    lineup = get_baseball_lineup()

    # Calculate estimated dates for everyone
    next_tuesday = get_next_tuesday()
    lineup_with_dates = []

    # At bat
    if lineup['at_bat']:
        lineup_with_dates.append({
            'member': lineup['at_bat'],
            'position': 1,
            'status': 'at_bat',
            'estimated_date': next_tuesday,
        })

    # On deck
    if lineup['on_deck']:
        lineup_with_dates.append({
            'member': lineup['on_deck'],
            'position': 2,
            'status': 'on_deck',
            'estimated_date': next_tuesday + timedelta(weeks=1),
        })

    # In the hole
    if lineup['in_hole']:
        lineup_with_dates.append({
            'member': lineup['in_hole'],
            'position': 3,
            'status': 'in_hole',
            'estimated_date': next_tuesday + timedelta(weeks=2),
        })

    # Dugout
    for i, m in enumerate(lineup['dugout']):
        position = 4 + i
        lineup_with_dates.append({
            'member': m,
            'position': position,
            'status': 'dugout',
            'estimated_date': next_tuesday + timedelta(weeks=position - 1),
        })

    return render_template('member/lineup.html',
                           member=member,
                           lineup=lineup,
                           lineup_with_dates=lineup_with_dates)


@member_bp.route('/history')
@member_required
def history():
    """Member's lunch attendance history."""
    member = get_current_member()
    if not member:
        return redirect(url_for('member.login'))

    # Get all attendance records for this member
    attendances = Attendance.query.filter_by(member_id=member.id).join(
        Lunch
    ).order_by(Lunch.date.desc()).all()

    # Stats
    total_attended = len(attendances)
    times_hosted = sum(1 for a in attendances if a.was_host)

    return render_template('member/history.html',
                           member=member,
                           attendances=attendances,
                           total_attended=total_attended,
                           times_hosted=times_hosted)


@member_bp.route('/gallery')
@member_required
def gallery():
    """Photo gallery placeholder."""
    member = get_current_member()
    if not member:
        return redirect(url_for('member.login'))

    # Placeholder for Phase 4.3
    return render_template('member/gallery.html', member=member)
