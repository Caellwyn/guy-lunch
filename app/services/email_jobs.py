"""
Scheduled email jobs for Tuesday Lunch Scheduler.

Jobs:
1. Thursday 9am - Host confirmation email
2. Friday 9am - Secretary reminder (conditional)
3. Monday 9am - Group announcement
4. Tuesday 6pm - Rating request (conditional)

Each job can be triggered manually from the admin dashboard or
run automatically via cron.
"""

import os
import secrets
from datetime import date, timedelta, datetime
from flask import current_app

from app import db
from app.models import Member, Lunch, Location, Attendance, EmailLog, Setting
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
    """Get members in hosting queue order."""
    return Member.query.filter_by(member_type='regular').order_by(
        Member.attendance_since_hosting.desc(),
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


# ============== JOB 1: Host Confirmation (Thursday 9am) ==============

def send_host_confirmation_email(dry_run: bool = False) -> dict:
    """
    Send host confirmation email to the next person in the hosting queue.

    Called: Thursday 9am
    Purpose: Notify host they're up, link to select restaurant

    Returns:
        dict with 'success', 'host_name', 'lunch_date', 'message'
    """
    result = {
        'success': False,
        'host_name': None,
        'lunch_date': None,
        'message': None
    }

    try:
        # Get next Tuesday
        next_tuesday = get_next_tuesday()
        result['lunch_date'] = next_tuesday.isoformat()

        # Get or create lunch record
        lunch = get_or_create_lunch(next_tuesday)

        # Get next host from queue
        next_host = get_hosting_queue(limit=1)
        if not next_host:
            result['message'] = 'No active members in hosting queue'
            return result

        next_host = next_host[0]
        result['host_name'] = next_host.name

        # Generate confirmation token if not exists
        if not lunch.confirmation_token:
            lunch.confirmation_token = secrets.token_urlsafe(32)
            lunch.host_id = next_host.id
            db.session.commit()

        # Build confirmation URL
        app_url = os.environ.get('APP_URL', 'http://localhost:5000')
        confirm_url = f"{app_url}/confirm/{lunch.confirmation_token}"

        # Send email
        params = {
            'HOST_NAME': next_host.name,
            'LUNCH_DATE': next_tuesday.strftime('%B %d, %Y'),
            'CONFIRM_URL': confirm_url,
        }

        email_result = email_service.send_email(
            to_email=next_host.email,
            to_name=next_host.name,
            subject=f"You're Hosting Tuesday Lunch - {next_tuesday.strftime('%B %d')}",
            template_file='emails/host_confirmation.html',
            params=params,
            email_type='host_confirmation',
            lunch_id=lunch.id,
            dry_run=dry_run
        )

        if email_result['success']:
            result['success'] = True
            result['message'] = f"Host confirmation sent to {next_host.name}"
        else:
            result['message'] = f"Failed to send email: {email_result['error']}"

    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        current_app.logger.error(f"Host confirmation job error: {e}")

    return result


# ============== JOB 2: Secretary Reminder (Friday 9am) ==============

def send_secretary_reminder(dry_run: bool = False) -> dict:
    """
    Send secretary reminder - either reservation details or alert.

    Called: Friday 9am
    Purpose: If host confirmed location, send reservation details.
             If not confirmed, send alert with backup host info.

    Returns:
        dict with 'success', 'reminder_type', 'message'
    """
    result = {
        'success': False,
        'reminder_type': None,  # 'confirmed' or 'not_confirmed'
        'message': None
    }

    try:
        # Get next Tuesday's lunch
        next_tuesday = get_next_tuesday()
        lunch = Lunch.query.filter_by(date=next_tuesday).first()

        if not lunch:
            result['message'] = 'No lunch record found for next Tuesday'
            return result

        # Get secretary from settings
        secretary_id = Setting.get('secretary_member_id')
        if not secretary_id:
            result['message'] = 'No secretary configured. Go to Admin > Settings to set one.'
            return result

        secretary = Member.query.get(int(secretary_id))
        if not secretary or not secretary.email:
            result['message'] = 'Secretary member not found or has no email.'
            return result

        secretary_email = secretary.email
        secretary_name = secretary.name

        # Check if location is confirmed
        if lunch.location_id and lunch.reservation_confirmed:
            # Location confirmed - send reservation reminder
            result['reminder_type'] = 'confirmed'
            location = Location.query.get(lunch.location_id)
            host = Member.query.get(lunch.host_id) if lunch.host_id else None

            params = {
                'EMAIL_TITLE': f"Make Reservation - {location.name}",
                'EMAIL_HEADING': "Time to Make the Reservation!",
                'INTRO_TEXT': f"{host.name if host else 'The host'} has selected a location for this week's lunch. Please call to make a reservation.",
                'BOX_BG_COLOR': '#f0fdf4',
                'BOX_BORDER_COLOR': '#22c55e',
                'BOX_LABEL_COLOR': '#166534',
                'BOX_TITLE_COLOR': '#14532d',
                'BOX_TEXT_COLOR': '#166534',
                'BOX_LABEL': "This Week's Location",
                'BOX_TITLE': location.name,
                'BOX_CONTENT': f"Address: {location.address or 'N/A'}<br>Phone: {location.phone or 'N/A'}",
                'LUNCH_DATE': next_tuesday.strftime('%A, %B %d, %Y'),
                'EXPECTED_ATTENDANCE': str(get_average_attendance()),
                'HOST_NAME': host.name if host else 'Unknown',
            }

            subject = f"Make Reservation - {location.name}"
            template = 'emails/secretary_reminder.html'

        else:
            # Location NOT confirmed - send alert
            result['reminder_type'] = 'not_confirmed'
            host = Member.query.get(lunch.host_id) if lunch.host_id else None
            host_name = host.name if host else 'Unknown'
            host_email = host.email if host else 'unknown'

            # Get backup host
            queue = get_hosting_queue(limit=2)
            backup = queue[1] if len(queue) > 1 else None
            backup_name = backup.name if backup else 'N/A'
            backup_email = backup.email if backup else 'N/A'

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
                'EXPECTED_ATTENDANCE': str(get_average_attendance()),
                'HOST_NAME': host_name,
            }

            subject = "ALERT: Host Has Not Confirmed Location"
            template = 'emails/secretary_reminder.html'

        # Send email
        email_result = email_service.send_email(
            to_email=secretary_email,
            to_name=secretary_name,
            subject=subject,
            template_file=template,
            params=params,
            email_type='secretary_reminder',
            lunch_id=lunch.id,
            dry_run=dry_run
        )

        if email_result['success']:
            result['success'] = True
            result['message'] = f"Secretary reminder ({result['reminder_type']}) sent"
        else:
            result['message'] = f"Failed to send email: {email_result['error']}"

    except Exception as e:
        result['message'] = f"Error: {str(e)}"
        current_app.logger.error(f"Secretary reminder job error: {e}")

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

            # Generate unique rating token for this member/lunch
            rating_token = secrets.token_urlsafe(32)
            rating_url = f"{app_url}/rate/{lunch.id}/{rating_token}"

            params = {
                'MEMBER_NAME': member.name,
                'LOCATION_NAME': location.name,
                'LUNCH_DATE': today.strftime('%B %d, %Y'),
                'HOST_NAME': host.name if host else 'Unknown',
                'RATING_URL': rating_url,
                'ATTENDANCE_COUNT': str(len(attendances)),
                'VISIT_TEXT': f"Visit #{location.visit_count}" if hasattr(location, 'visit_count') and location.visit_count else 'First visit',
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
        'host_confirmation': send_host_confirmation_email,
        'secretary_reminder': send_secretary_reminder,
        'announcement': send_group_announcement,
        'rating_request': send_rating_requests,
    }

    if job_name not in jobs:
        return {
            'success': False,
            'message': f"Unknown job: {job_name}. Valid jobs: {list(jobs.keys())}"
        }

    return jobs[job_name](dry_run=dry_run)
