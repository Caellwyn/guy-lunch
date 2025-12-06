from datetime import datetime
from app import db


class Attendance(db.Model):
    """Record of member attending a lunch."""
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    lunch_id = db.Column(db.Integer, db.ForeignKey('lunches.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    was_host = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint: one attendance record per member per lunch
    __table_args__ = (
        db.UniqueConstraint('lunch_id', 'member_id', name='unique_attendance'),
    )
    
    def __repr__(self):
        return f'<Attendance lunch={self.lunch_id} member={self.member_id}>'
