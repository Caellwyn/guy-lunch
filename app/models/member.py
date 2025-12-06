from datetime import datetime
from app import db


class Member(db.Model):
    """Lunch group member."""
    __tablename__ = 'members'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    member_type = db.Column(db.String(20), default='regular')  # regular, guest, inactive
    attendance_since_hosting = db.Column(db.Integer, default=0)
    last_hosted_date = db.Column(db.DateTime, nullable=True)
    total_hosting_count = db.Column(db.Integer, default=0)
    first_attended = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    hosted_lunches = db.relationship('Lunch', backref='host', lazy='dynamic')
    attendances = db.relationship('Attendance', backref='member', lazy='dynamic')
    ratings = db.relationship('Rating', backref='member', lazy='dynamic')
    uploaded_photos = db.relationship('Photo', backref='uploader', lazy='dynamic')
    
    def __repr__(self):
        return f'<Member {self.name}>'
    
    @property
    def is_active(self):
        return self.member_type == 'regular'
