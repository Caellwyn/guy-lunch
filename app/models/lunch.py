from datetime import datetime
from app import db


class Lunch(db.Model):
    """Weekly lunch event."""
    __tablename__ = 'lunches'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    host_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=True)
    expected_attendance = db.Column(db.Integer, nullable=True)
    actual_attendance = db.Column(db.Integer, nullable=True)
    reservation_confirmed = db.Column(db.Boolean, default=False)
    host_confirmed = db.Column(db.Boolean, default=False)  # Host confirmed they will host
    status = db.Column(db.String(20), default='planned')  # planned, completed, cancelled
    confirmation_token = db.Column(db.String(64), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='lunch', lazy='dynamic', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='lunch', lazy='dynamic', cascade='all, delete-orphan')
    photos = db.relationship('Photo', backref='lunch', lazy='dynamic')
    
    @property
    def restaurant(self):
        return self.location.name if self.location else "TBD"

    def __repr__(self):
        return f'<Lunch {self.date}>'
