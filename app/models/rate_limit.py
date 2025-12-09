"""
Rate limiting model for tracking request counts.

Used to prevent abuse of email-sending endpoints like magic link requests.
"""

from datetime import datetime, timedelta
from app import db


class RateLimit(db.Model):
    """Track rate-limited actions by key (e.g., email address or IP)."""
    __tablename__ = 'rate_limits'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), nullable=False, index=True)  # e.g., email or IP
    action = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'magic_link'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @classmethod
    def check_rate_limit(cls, key, action, max_requests, window_minutes):
        """
        Check if the key has exceeded the rate limit for the given action.

        Args:
            key: The identifier to rate limit (e.g., email address)
            action: The action being rate limited (e.g., 'magic_link')
            max_requests: Maximum number of requests allowed in the window
            window_minutes: Time window in minutes

        Returns:
            tuple: (is_allowed: bool, requests_remaining: int, retry_after_seconds: int or None)
        """
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        # Count requests in the current window
        request_count = cls.query.filter(
            cls.key == key.lower(),
            cls.action == action,
            cls.timestamp >= window_start
        ).count()

        if request_count >= max_requests:
            # Find the oldest request in the window to calculate retry time
            oldest_in_window = cls.query.filter(
                cls.key == key.lower(),
                cls.action == action,
                cls.timestamp >= window_start
            ).order_by(cls.timestamp.asc()).first()

            if oldest_in_window:
                retry_after = (oldest_in_window.timestamp + timedelta(minutes=window_minutes) - datetime.utcnow()).total_seconds()
                retry_after = max(0, int(retry_after))
            else:
                retry_after = window_minutes * 60

            return (False, 0, retry_after)

        return (True, max_requests - request_count - 1, None)

    @classmethod
    def record_request(cls, key, action):
        """
        Record a request for rate limiting purposes.

        Args:
            key: The identifier (e.g., email address)
            action: The action being performed (e.g., 'magic_link')
        """
        record = cls(
            key=key.lower(),
            action=action,
            timestamp=datetime.utcnow()
        )
        db.session.add(record)
        db.session.commit()

    @classmethod
    def cleanup_old_records(cls, older_than_minutes=60):
        """
        Clean up rate limit records older than the specified time.

        Call this periodically (e.g., via cron) to prevent table bloat.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        deleted = cls.query.filter(cls.timestamp < cutoff).delete()
        db.session.commit()
        return deleted
