"""
Member portal routes - authentication and member dashboard.

Uses magic link authentication - members receive a login link via email.
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from datetime import date, datetime, timedelta
import secrets

from app import db
from app.models import Member, Lunch, Attendance, Location, Rating, Setting

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
            # In local dev, auto-login as Josh Johnson (or first member as fallback)
            if is_local_development():
                member = Member.query.filter_by(email='caellwyn@gmail.com').first() or Member.query.first()
                if member:
                    set_member_session(member)
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


def set_member_session(member):
    """Set session variables for a logged-in member."""
    session['member_id'] = member.id
    session['member_name'] = member.name
    session.permanent = True

    # Check if this member is the secretary
    secretary_id = Setting.get('secretary_member_id')
    is_secretary = bool(secretary_id and int(secretary_id) == member.id)
    session['is_secretary'] = is_secretary

    # Debug logging
    from flask import current_app
    current_app.logger.info(f"set_member_session: member={member.id}, secretary_id={secretary_id}, is_secretary={is_secretary}")


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
    set_member_session(member)

    # Clean up used token (single-use)
    member.magic_link_token = None
    member.magic_link_expires = None
    db.session.commit()

    flash(f'Welcome back, {member.name}!', 'success')

    # Redirect to secretary dashboard if they're the secretary, otherwise member dashboard
    if session.get('is_secretary'):
        next_url = request.args.get('next') or url_for('secretary.dashboard')
    else:
        next_url = request.args.get('next') or url_for('member.dashboard')
    return redirect(next_url)


@member_bp.route('/logout')
def logout():
    """Log out member."""
    session.pop('member_id', None)
    session.pop('member_name', None)
    session.pop('is_secretary', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))


@member_bp.route('/dev-login')
def dev_login():
    """Backdoor for development to skip email."""
    if not current_app.debug:
        return "Not available in production", 403

    # Preserve admin authentication if present
    was_admin = session.get('admin_authenticated')

    # Clear member session (but not admin)
    session.pop('member_id', None)
    session.pop('member_name', None)
    session.pop('is_secretary', None)

    # Log in as Josh Johnson (or first member as fallback)
    member = Member.query.filter_by(email='caellwyn@gmail.com').first() or Member.query.first()
    if not member:
        return "No members found in database", 404

    set_member_session(member)

    # Restore admin authentication
    if was_admin:
        session['admin_authenticated'] = True

    flash(f'Dev Login Successful as {member.name}', 'success')

    # Redirect to secretary dashboard if they're the secretary
    if session.get('is_secretary'):
        return redirect(url_for('secretary.dashboard'))
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
    from app.services.email_jobs import get_hosting_queue
    queue = get_hosting_queue(limit=100)

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
    from app.services.email_jobs import get_hosting_queue
    queue = get_hosting_queue(limit=100)

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

    # Check for ratable lunch (most recent completed lunch they attended but haven't rated)
    ratable_lunch = None
    recent_attended_lunch = Lunch.query.join(Attendance).filter(
        Attendance.member_id == member.id,
        Lunch.status == 'completed'
    ).order_by(Lunch.date.desc()).first()

    if recent_attended_lunch:
        # Check if they've already rated it
        existing_rating = Rating.query.filter_by(
            lunch_id=recent_attended_lunch.id,
            member_id=member.id
        ).first()
        if not existing_rating or existing_rating.rating is None:
            ratable_lunch = recent_attended_lunch

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
                           total_hosted=total_hosted,
                           ratable_lunch=ratable_lunch)


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


# ============== MEMBER PROFILES ==============

@member_bp.route('/profile')
@member_required
def my_profile():
    """Redirect to current member's profile."""
    member = get_current_member()
    if not member:
        return redirect(url_for('member.login'))
    return redirect(url_for('member.view_profile', member_id=member.id))


@member_bp.route('/profile/<int:member_id>')
@member_required
def view_profile(member_id):
    """View a member's profile."""
    current_member = get_current_member()
    if not current_member:
        return redirect(url_for('member.login'))

    profile_member = Member.query.get_or_404(member_id)
    is_own_profile = (current_member.id == profile_member.id)

    # Get stats
    from app.models import Photo, PhotoTag
    total_attended = Attendance.query.filter_by(member_id=profile_member.id).count()
    times_hosted = profile_member.total_hosting_count or 0

    # Get photos uploaded by this member
    uploaded_photos = Photo.query.filter_by(uploaded_by=profile_member.id).order_by(
        Photo.created_at.desc()
    ).limit(12).all()

    # Get photos where this member is tagged
    tagged_photos = Photo.query.join(PhotoTag).filter(
        PhotoTag.member_id == profile_member.id
    ).order_by(Photo.created_at.desc()).limit(12).all()

    return render_template('member/profile.html',
                           member=current_member,
                           profile_member=profile_member,
                           is_own_profile=is_own_profile,
                           total_attended=total_attended,
                           times_hosted=times_hosted,
                           uploaded_photos=uploaded_photos,
                           tagged_photos=tagged_photos)


@member_bp.route('/profile/edit', methods=['GET', 'POST'])
@member_required
def edit_profile():
    """Edit your own profile."""
    member = get_current_member()
    if not member:
        return redirect(url_for('member.login'))

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip() or None
        business = request.form.get('business', '').strip() or None
        website = request.form.get('website', '').strip() or None
        bio = request.form.get('bio', '').strip() or None
        profile_public = request.form.get('profile_public') == 'on'

        # Validation
        if not name:
            flash('Name is required.', 'error')
            return render_template('member/edit_profile.html', member=member)

        if not email:
            flash('Email is required.', 'error')
            return render_template('member/edit_profile.html', member=member)

        # Check if email is taken by another member
        existing = Member.query.filter(Member.email == email, Member.id != member.id).first()
        if existing:
            flash('That email is already in use by another member.', 'error')
            return render_template('member/edit_profile.html', member=member)

        # Validate website URL if provided
        if website and not (website.startswith('http://') or website.startswith('https://')):
            website = 'https://' + website

        # Note: Profile picture is handled via AJAX upload (/api/profile-picture/upload)
        # and saved immediately, so we don't need to process it here on form submit.

        # Update member
        member.name = name
        member.email = email
        member.phone = phone
        member.business = business
        member.website = website
        member.bio = bio[:500] if bio else None  # Limit bio to 500 chars
        member.profile_public = profile_public

        # Update session name if it changed
        session['member_name'] = member.name

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('member.view_profile', member_id=member.id))

    return render_template('member/edit_profile.html', member=member)


# ============== RATING ==============

@member_bp.route('/rate/<int:lunch_id>', methods=['GET', 'POST'])
@member_required
def rate_lunch(lunch_id):
    """Rate a lunch you attended."""
    member = get_current_member()
    if not member:
        return redirect(url_for('member.login'))

    lunch = Lunch.query.get_or_404(lunch_id)

    # Verify member attended this lunch
    attendance = Attendance.query.filter_by(
        lunch_id=lunch_id,
        member_id=member.id
    ).first()

    if not attendance:
        flash("You can only rate lunches you attended.", 'error')
        return redirect(url_for('member.dashboard'))

    # Check for existing rating
    existing_rating = Rating.query.filter_by(
        lunch_id=lunch_id,
        member_id=member.id
    ).first()

    if request.method == 'POST':
        rating_value = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip() or None

        if not rating_value or rating_value < 1 or rating_value > 5:
            flash('Please select a rating between 1 and 5 stars.', 'error')
            return render_template('member/rate_lunch.html',
                                   member=member,
                                   lunch=lunch,
                                   existing_rating=existing_rating)

        if existing_rating:
            existing_rating.rating = rating_value
            existing_rating.comment = comment
        else:
            new_rating = Rating(
                lunch_id=lunch_id,
                member_id=member.id,
                rating=rating_value,
                comment=comment
            )
            db.session.add(new_rating)

        # Update location average rating
        if lunch.location:
            location = lunch.location
            all_ratings = Rating.query.join(Lunch).filter(
                Lunch.location_id == location.id,
                Rating.rating.isnot(None)
            ).all()
            if all_ratings:
                avg = sum(r.rating for r in all_ratings) / len(all_ratings)
                location.avg_group_rating = round(avg, 2)

        db.session.commit()
        flash('Thanks for your rating!', 'success')
        return redirect(url_for('member.dashboard'))

    return render_template('member/rate_lunch.html',
                           member=member,
                           lunch=lunch,
                           existing_rating=existing_rating)
