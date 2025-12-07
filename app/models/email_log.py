from datetime import datetime
from app import db


class EmailLog(db.Model):
    """Track all sent emails."""
    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)
    email_type = db.Column(db.String(50), nullable=False)  # host_confirmation, secretary_reminder, announcement, rating_request
    recipient_email = db.Column(db.String(120), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=True)
    subject = db.Column(db.String(255), nullable=False)

    # Link to lunch if applicable
    lunch_id = db.Column(db.Integer, db.ForeignKey('lunches.id'), nullable=True)

    # Brevo tracking
    brevo_message_id = db.Column(db.String(100), nullable=True)

    # Status tracking
    status = db.Column(db.String(20), default='sent')  # sent, delivered, opened, clicked, bounced, failed
    error_message = db.Column(db.Text, nullable=True)

    # Timestamps
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    lunch = db.relationship('Lunch', backref=db.backref('email_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<EmailLog {self.email_type} to {self.recipient_email}>'
