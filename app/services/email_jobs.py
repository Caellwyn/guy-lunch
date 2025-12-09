"""
Scheduled email jobs for Tuesday Lunch Scheduler.

Jobs:
1. Thursday 9am - Host reminders (3-tier: In Hole, On Deck, At Bat)
2. Friday 9am - Secretary status email (consolidated status of all 3 hosts)
3. Monday 9am - Group announcement
4. Tuesday 6pm - Rating request (conditional)

Each job can be triggered manually from the admin dashboard or
run automatically via cron.

Host Reminder Logic:
- In the Hole (3 weeks out): Send if NOT (confirmed AND has location)
- On Deck (2 weeks out): Send if NOT (confirmed AND has location)
- At Bat (this week): ALWAYS send (courtesy reminder)
"""

import os
import secrets
from datetime import date, timedelta, datetime
from flask import current_app

from app import db
from app.models import Member, Lunch, Location, Attendance, EmailLog, Setting, Rating
from app.services.email_service import email_service


def get_next_tuesday(from_date: date = None) -> date:
    """Get the next Tuesday from the given date."""
    if from_date is None:
        from_date = date.today()

    days_until_tuesday = (1 - from_date.weekday()) % 7
    if days_until_tuesday == 0 and from_date.weekday() != 1:
        days_until_tuesday = 7

    return from_date + timedelta(days=days_until_tuesday)


def get_this_tuesday(from_date: date = None) -> date:
    """Get this week's Tuesday (for rating requests on Tuesday)."""
    if from_date is None:
        from_date = date.today()

    # If it's Tuesday, return today
    if from_date.weekday() == 1:
        return from_date

    # Otherwise get the most recent Tuesday
    days_since_tuesday = (from_date.weekday() - 1) % 7
    return from_date - timedelta(days=days_since_tuesday)


def get_hosting_queue(limit: int = 5) -> list:
    """Get members in hosting queue order.

    Uses queue_position if set (manual secretary override),
    otherwise falls back to attendance_since_hosting (natural order).

    Sorting:
    - Members with queue_position set come first, ordered by queue_position ASC
    - Members without queue_position come after, ordered by attendance_since_hosting DESC
    """
    from sqlalchemy import case, nullslast

    # Custom ordering: queue_position first (if set), then attendance_since_hosting
    # NULLS LAST ensures members without queue_position come after those with it
    return Member.query.filter_by(member_type='regular').order_by(
        # Primary: queue_position (lower = higher priority), NULLs last
        nullslast(Member.queue_position.asc()),
        # Secondary: attendance_since_hosting (higher = higher priority)
        Member.attendance_since_hosting.desc(),
        # Tertiary: name for consistent ordering
        Member.name
    ).limit(limit).all()


def get_or_create_lunch(lunch_date: date) -> Lunch:
    """Get existing lunch or create a new one."""
    lunch = Lunch.query.filter_by(date=lunch_date).first()
    if not lunch:
        lunch = Lunch(date=lunch_date, status='planned')
        db.session.add(lunch)
        db.session.commit()
    return lunch


def get_average_attendance(weeks: int = 4) -> int:
    """Get average attendance over recent weeks."""
    recent_lunches = Lunch.query.filter(
        Lunch.actual_attendance.isnot(None)
    ).order_by(Lunch.date.desc()).limit(weeks).all()

    if not recent_lunches:
        return 15  # Default estimate

    total = sum(l.actual_attendance for l in recent_lunches)
    return round(total / len(recent_lunches))


# ============== JOB 1: Host Reminders (Thursday 9am) ==============

def get_upcoming_tuesdays() -> dict:
    """
    Get the next 3 Tuesdays for the 3-tier host reminder system.

    Returns:
        dict with 'at_bat' (this week), 'on_deck' (next week), 'in_hole' (3 weeks out)
    """
    today = date.today()

    # Get this coming Tuesday (At Bat)
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0 and today.weekday() != 1:
        days_until_tuesday = 7
    # If it's Tuesday or later in the week, At Bat is this Tuesday
    # If it's earlier, At Bat is the upcoming Tuesday
    at_bat_date = today + timedelta(days=days_until_tuesday)

    return {
        'at_bat': at_bat_date,
        'on_deck': at_bat_date + timedelta(weeks=1),
        'in_hole': at_bat_date + timedelta(weeks=2),
    }


def was_reminder_already_sent(lunch_id: int, email_type: str, recipient_email: str) -> bool:
    """Check if a specific reminder type was already sent for this lunch."""
    existing = EmailLog.query.filter_by(
        lunch_id=lunch_id,
        email_type=email_type,
        recipient_email=recipient_email,
        status='sent'
    ).first()
    return existing is not None


def send_host_reminder(
    host: Member,
    lunch: Lunch,
    reminder_tier: str,
    dry_run: bool = False
) -> dict:
    """
    Send a host reminder email for a specific tier.

    Args:
        host: The Member who is hosting
        lunch: The Lunch record
        reminder_tier: One of 'at_bat', 'on_deck', 'in_hole'
        dry_run: If True, don't actually send

    Returns:
        dict with 'success', 'message', 'skipped'
    """
    result = {
        'success': False,
        'message': None,
        'skipped': False
    }

    email_type = f'host_reminder_{reminder_tier}'
    is_confirmed = lunch.host_confirmed and lunch.location_id

    # Skip logic (except At Bat always sends)
    if reminder_tier != 'at_bat' and is_confirmed:
        result['skipped'] = True
        result['message'] = f"Skipped {reminder_tier} - already confirmed with location"
        return result

    # Check if already sent this specific reminder
    if was_reminder_already_sent(lunch.id, email_type, host.email):
        result['skipped'] = True
        result['message'] = f"Skipped {reminder_tier} - already sent"
        return result

    # Generate confirmation token if not exists
    if not lunch.confirmation_token:
        lunch.confirmation_token = secrets.token_urlsafe(32)
    if not lunch.host_id:
        lunch.host_id = host.id
    db.session.commit()

    # Build confirmation URL
    app_url = os.environ.get('APP_URL', 'http://localhost:5000')
    confirm_url = f"{app_url}/confirm/{lunch.confirmation_token}"

    # Customize message based on tier and confirmation status
    tier_labels = {
        'at_bat': ("You're AT BAT!", "This Tuesday"),
        'on_deck': ("You're ON DECK!", "Next Tuesday"),
        'in_hole': ("You're IN THE HOLE!", "In 3 Weeks"),
    }
    tier_label, time_frame = tier_labels[reminder_tier]

    # Different subject/tone based on confirmation status (for At Bat)
    if reminder_tier == 'at_bat' and is_confirmed:
        subject = f"Reminder: You're Hosting This Tuesday - {lunch.date.strftime('%B %d')}"
        status_message = "You're all set! Here's a reminder of your hosting details."
    else:
        subject = f"{tier_label} Hosting Tuesday Lunch - {lunch.date.strftime('%B %d')}"
        status_message = "Please confirm you'll be hosting and select a restaurant."

    # Get location name if set
    location_name = None
    if lunch.location_id:
        location = Location.query.get(lunch.location_id)
        location_name = location.name if location else None

    params = {
        'HOST_NAME': host.name,
        'LUNCH_DATE': lunch.date.strftime('%B %d, %Y'),
        'CONFIRM_URL': confirm_url,
        'TIER_LABEL': tier_label,
        'TIME_FRAME': time_frame,
        'STATUS_MESSAGE': status_message,
        'IS_CONFIRMED': 'yes' if lunch.host_confirmed else 'no',
        'HAS_LOCATION': 'yes' if lunch.location_id else 'no',
        'LOCATION_NAME': location_name or 'Not yet selected',
    }

    email_result = email_service.send_email(
        to_email=host.email,
        to_name=host.name,
        subject=subject,
        template_file='emails/host_reminder.html',
        params=params,
        email_type=email_type,
        lunch_id=lunch.id,
        dry_run=dry_run
    )

    if email_result['success']:
        result['success'] = True
        result['message'] = f"{tier_label} reminder sent to {host.name}"
    else:
        result['message'] = f"Failed to send email: {email_result['error']}"

    return result


def send_host_reminders(dry_run: bool = False) -> dict:
    """
    Send host reminder emails to the next 3 hosts (At Bat, On Deck, In the Hole).

    Called: Thursday 9am
    Purpose: Rolling 3-week reminder system for upcoming hosts

    Logic:
    - In the Hole: Send if NOT (confirmed AND has location)
    - On Deck: Send if NOT (confirmed AND has location)
    - At Bat: ALWAYS send as courtesy reminder

    Returns:
        dict with 'success', 'results' (list), 'message'
    """
    result = {
        'success': False,
        'results': [],
        'message': None
    }

    try:
        # Get the next 3 Tuesdays
        tuesdays = get_upcoming_tuesdays()

        # Get the hosting queue (need at least 3 hosts)
        queue = get_hosting_queue(limit=3)
        if len(queue) < 3:
            result['message'] = f'Only {len(queue)} members in hosting queue, need at least 3'
            return result

        # Map positions to tiers
        tier_mapping = [
            ('at_bat', tuesdays['at_bat'], queue[0]),
            ('on_deck', tuesdays['on_deck'], queue[1]),
            ('in_hole', tuesdays['in_hole'], queue[2]),
        ]

        sent_count = 0
        skipped_count = 0

        for tier, lunch_date, host in tier_mapping:
            # Get or create lunch record for this date
            lunch = get_or_create_lunch(lunch_date)

            # Ensure host is assigned
            if not lunch.host_id:
                lunch.host_id = host.id
                db.session.commit()

            # Send reminder
            reminder_result = send_host_reminder(host, lunch, tier, dry_run)
            reminder_result['tier'] = tier
            reminder_result['host_name'] = host.name
            reminder_result['lunch_date'] = lunch_date.isoformat()
            result['results'].append(reminder_result)

            if reminder_result['success']:
                sent_count += 1
            elif reminder_result['skipped']:
                skipped_count += 1

        result['success'] = True
        result['message'] = f"Host reminders: {sent_count} sent, {skipped_count} skipped"

    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        current_app.logger.error(f"Host reminders job error: {e}")

    return result


# Legacy function name for backwards compatibility
def send_host_confirmation_email(dry_run: bool = False) -> dict:
    """Legacy wrapper - now calls send_host_reminders."""
    return send_host_reminders(dry_run=dry_run)


# ============== JOB 2: Secretary Status Email (Friday 9am) ==============

def get_host_status_for_lunch(lunch: Lunch, host: Member) -> dict:
    """Get the confirmation status for a host/lunch pair."""
    if not lunch or not host:
        return {
            'host_name': 'Unknown',
            'host_email': None,
            'lunch_date': None,
            'host_confirmed': False,
            'location_selected': False,
            'location_name': None,
            'location_phone': None,
            'location_address': None,
        }

    location = Location.query.get(lunch.location_id) if lunch.location_id else None

    return {
        'host_name': host.name,
        'host_email': host.email,
        'lunch_date': lunch.date,
        'host_confirmed': lunch.host_confirmed or False,
        'location_selected': lunch.location_id is not None,
        'location_name': location.name if location else None,
        'location_phone': location.phone if location else None,
        'location_address': location.address if location else None,
    }


def send_secretary_reminder(dry_run: bool = False) -> dict:
    """
    Send consolidated secretary status email for all 3 upcoming hosts.

    Called: Friday 9am
    Purpose: Single email showing status of At Bat, On Deck, and In the Hole hosts.
             Big red warning if At Bat host hasn't confirmed.

    Returns:
        dict with 'success', 'message', 'host_statuses'
    """
    result = {
        'success': False,
        'message': None,
        'host_statuses': []
    }

    try:
        # Get secretary from settings
        secretary_id = Setting.get('secretary_member_id')
        if not secretary_id:
            result['message'] = 'No secretary configured. Go to Admin > Settings to set one.'
            return result

        secretary = db.session.get(Member, int(secretary_id))
        if not secretary or not secretary.email:
            result['message'] = 'Secretary member not found or has no email.'
            return result

        # Get the next 3 Tuesdays and hosting queue
        tuesdays = get_upcoming_tuesdays()
        queue = get_hosting_queue(limit=3)

        if len(queue) < 3:
            result['message'] = f'Only {len(queue)} members in hosting queue, need at least 3'
            return result

        # Build status for each tier
        tiers = [
            ('at_bat', 'AT BAT', tuesdays['at_bat'], queue[0]),
            ('on_deck', 'ON DECK', tuesdays['on_deck'], queue[1]),
            ('in_hole', 'IN THE HOLE', tuesdays['in_hole'], queue[2]),
        ]

        host_statuses = []
        at_bat_status = None

        for tier_key, tier_label, lunch_date, host in tiers:
            lunch = Lunch.query.filter_by(date=lunch_date).first()
            status = get_host_status_for_lunch(lunch, host)
            status['tier'] = tier_key
            status['tier_label'] = tier_label
            host_statuses.append(status)

            if tier_key == 'at_bat':
                at_bat_status = status

        result['host_statuses'] = host_statuses

        # Determine urgency level
        at_bat_ready = at_bat_status['host_confirmed'] and at_bat_status['location_selected']

        # Build email params
        params = {
            'SECRETARY_NAME': secretary.name,
            'AT_BAT_READY': 'yes' if at_bat_ready else 'no',
            'AT_BAT_HOST': host_statuses[0]['host_name'],
            'AT_BAT_DATE': host_statuses[0]['lunch_date'].strftime('%B %d') if host_statuses[0]['lunch_date'] else 'N/A',
            'AT_BAT_CONFIRMED': 'yes' if host_statuses[0]['host_confirmed'] else 'no',
            'AT_BAT_LOCATION': host_statuses[0]['location_name'] or 'Not selected',
            'AT_BAT_LOCATION_PHONE': host_statuses[0]['location_phone'] or 'N/A',
            'AT_BAT_LOCATION_ADDRESS': host_statuses[0]['location_address'] or 'N/A',
            'AT_BAT_EMAIL': host_statuses[0]['host_email'] or 'N/A',

            'ON_DECK_HOST': host_statuses[1]['host_name'],
            'ON_DECK_DATE': host_statuses[1]['lunch_date'].strftime('%B %d') if host_statuses[1]['lunch_date'] else 'N/A',
            'ON_DECK_CONFIRMED': 'yes' if host_statuses[1]['host_confirmed'] else 'no',
            'ON_DECK_LOCATION': host_statuses[1]['location_name'] or 'Not selected',

            'IN_HOLE_HOST': host_statuses[2]['host_name'],
            'IN_HOLE_DATE': host_statuses[2]['lunch_date'].strftime('%B %d') if host_statuses[2]['lunch_date'] else 'N/A',
            'IN_HOLE_CONFIRMED': 'yes' if host_statuses[2]['host_confirmed'] else 'no',
            'IN_HOLE_LOCATION': host_statuses[2]['location_name'] or 'Not selected',

            'EXPECTED_ATTENDANCE': str(get_average_attendance()),
        }

        # Subject line varies based on urgency
        if at_bat_ready:
            subject = f"Host Status: Ready for Tuesday - {host_statuses[0]['location_name']}"
        else:
            subject = "ACTION NEEDED: At Bat Host Has Not Confirmed!"

        # Send email
        email_result = email_service.send_email(
            to_email=secretary.email,
            to_name=secretary.name,
            subject=subject,
            template_file='emails/secretary_status.html',
            params=params,
            email_type='secretary_status',
            lunch_id=None,  # Not specific to one lunch
            dry_run=dry_run
        )

        if email_result['success']:
            result['success'] = True
            result['message'] = f"Secretary status email sent ({'ready' if at_bat_ready else 'ACTION NEEDED'})"
        else:
            result['message'] = f"Failed to send email: {email_result['error']}"

    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        current_app.logger.error(f"Secretary status email job error: {e}")

    return result


# ============== JOB 3: Group Announcement (Monday 9am) ==============

def send_group_announcement(dry_run: bool = False) -> dict:
    """
    Send group announcement email to all active members.

    Called: Monday 9am
    Purpose: Announce location details for Tuesday lunch

    Returns:
        dict with 'success', 'sent_count', 'failed_count', 'message'
    """
    result = {
        'success': False,
        'sent_count': 0,
        'failed_count': 0,
        'message': None
    }

    try:
        # Get next Tuesday (should be tomorrow)
        next_tuesday = get_next_tuesday()
        lunch = Lunch.query.filter_by(date=next_tuesday).first()

        if not lunch:
            result['message'] = 'No lunch record found for Tuesday'
            return result

        if not lunch.location_id:
            result['message'] = 'No location set for Tuesday lunch'
            return result

        location = Location.query.get(lunch.location_id)
        host = Member.query.get(lunch.host_id) if lunch.host_id else None

        # Get all active members
        members = Member.query.filter_by(member_type='regular').all()
        if not members:
            result['message'] = 'No active members found'
            return result

        # Build Google Maps URL
        maps_query = location.address.replace(' ', '+') if location.address else location.name.replace(' ', '+')
        maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_query}"

        # Build params
        params = {
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'LOCATION_NAME': location.name,
            'LOCATION_ADDRESS': location.address or 'Address not available',
            'GOOGLE_MAPS_URL': maps_url,
            'START_TIME': '12 hundred hours (12:00 PM)',
            'HOST_NAME': host.name if host else 'TBD',
            'LOCATION_CUISINE': location.cuisine_type or 'Various',
            'LOCATION_RATING': f"{location.avg_group_rating:.1f}" if location.avg_group_rating else "Not yet rated",
            'LOCATION_PRICE': '$' * (location.price_level or 2),
            'LAST_VISITED': location.last_visited.strftime('%B %d, %Y') if location.last_visited else 'First visit!',
        }

        # Build recipient list
        recipients = [{'email': m.email, 'name': m.name} for m in members if m.email]

        # Send bulk email
        subject = f"Guy Lunch Briefing - {next_tuesday.strftime('%B %d')} at {location.name}"

        bulk_result = email_service.send_bulk_email(
            recipients=recipients,
            subject=subject,
            template_file='emails/announcement_V2.html',
            params=params,
            email_type='announcement',
            lunch_id=lunch.id,
            dry_run=dry_run
        )

        result['sent_count'] = bulk_result['sent']
        result['failed_count'] = bulk_result['failed']
        result['success'] = bulk_result['sent'] > 0
        result['message'] = f"Announcement sent to {bulk_result['sent']} members, {bulk_result['failed']} failed"

    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        current_app.logger.error(f"Group announcement job error: {e}")

    return result


# ============== JOB 4: Rating Request (Tuesday 6pm) ==============

def send_rating_requests(dry_run: bool = False) -> dict:
    """
    Send rating request emails to members who attended today's lunch.

    Called: Tuesday 6pm
    Purpose: Request ratings from attendees after lunch

    Returns:
        dict with 'success', 'sent_count', 'failed_count', 'message'
    """
    result = {
        'success': False,
        'sent_count': 0,
        'failed_count': 0,
        'message': None
    }

    try:
        # Get today's lunch (should be Tuesday)
        today = get_this_tuesday()
        lunch = Lunch.query.filter_by(date=today).first()

        if not lunch:
            result['message'] = 'No lunch record found for today'
            return result

        # Check if attendance has been logged
        attendances = Attendance.query.filter_by(lunch_id=lunch.id).all()
        if not attendances:
            result['message'] = 'Attendance not logged yet - skipping rating requests'
            return result

        location = Location.query.get(lunch.location_id) if lunch.location_id else None
        host = Member.query.get(lunch.host_id) if lunch.host_id else None

        if not location:
            result['message'] = 'No location set for this lunch'
            return result

        app_url = os.environ.get('APP_URL', 'http://localhost:5000')

        # Send to each attendee
        sent = 0
        failed = 0

        for attendance in attendances:
            member = attendance.member
            if not member or not member.email:
                continue

            # Check if rating already exists for this member/lunch
            existing_rating = Rating.query.filter_by(
                lunch_id=lunch.id,
                member_id=member.id
            ).first()

            if existing_rating and existing_rating.rating is not None:
                # Already rated, skip
                continue

            # Generate unique rating token
            rating_token = secrets.token_urlsafe(32)

            # Create or update rating record with token (rating is NULL until submitted)
            if existing_rating:
                existing_rating.rating_token = rating_token
            else:
                new_rating = Rating(
                    lunch_id=lunch.id,
                    member_id=member.id,
                    rating_token=rating_token,
                    rating=None  # Will be set when user submits
                )
                db.session.add(new_rating)

            db.session.commit()

            # Generate individual URLs for each star rating (1-5)
            base_rating_url = f"{app_url}/rate/{rating_token}"

            params = {
                'MEMBER_NAME': member.name,
                'LOCATION_NAME': location.name,
                'LUNCH_DATE': today.strftime('%B %d, %Y'),
                'HOST_NAME': host.name if host else 'Unknown',
                'RATING_URL_1': f"{base_rating_url}/1",
                'RATING_URL_2': f"{base_rating_url}/2",
                'RATING_URL_3': f"{base_rating_url}/3",
                'RATING_URL_4': f"{base_rating_url}/4",
                'RATING_URL_5': f"{base_rating_url}/5",
                'ATTENDANCE_COUNT': str(len(attendances)),
                'VISIT_TEXT': f"Visit #{location.visit_count}" if hasattr(location, 'visit_count') and location.visit_count else 'First visit',
                'AI_GUY_LOGO_URL': f"{app_url}/static/images/ai-guy-logo.png",
            }

            email_result = email_service.send_email(
                to_email=member.email,
                to_name=member.name,
                subject=f"Rate Today's Lunch at {location.name}",
                template_file='emails/rating_request.html',
                params=params,
                email_type='rating_request',
                lunch_id=lunch.id,
                dry_run=dry_run
            )

            if email_result['success']:
                sent += 1
            else:
                failed += 1

        result['sent_count'] = sent
        result['failed_count'] = failed
        result['success'] = sent > 0
        result['message'] = f"Rating requests sent to {sent} attendees, {failed} failed"

    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        current_app.logger.error(f"Rating request job error: {e}")

    return result


# ============== Manual Trigger Function ==============

def run_email_job(job_name: str, dry_run: bool = False) -> dict:
    """
    Run a specific email job by name.

    Args:
        job_name: One of 'host_confirmation', 'secretary_reminder',
                  'announcement', 'rating_request'
        dry_run: If True, don't actually send emails

    Returns:
        Job result dict
    """
    jobs = {
        'host_confirmation': send_host_confirmation_email,  # Legacy name
        'host_reminders': send_host_reminders,  # New 3-tier system
        'secretary_reminder': send_secretary_reminder,
        'secretary_status': send_secretary_reminder,  # Alias for clarity
        'announcement': send_group_announcement,
        'rating_request': send_rating_requests,
    }

    if job_name not in jobs:
        return {
            'success': False,
            'message': f"Unknown job: {job_name}. Valid jobs: {list(jobs.keys())}"
        }

    return jobs[job_name](dry_run=dry_run)
