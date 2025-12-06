from datetime import datetime
from app import db


class Location(db.Model):
    """Restaurant location."""
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    google_place_id = db.Column(db.String(100), nullable=True)
    google_rating = db.Column(db.Numeric(2, 1), nullable=True)  # e.g., 4.5
    price_level = db.Column(db.Integer, nullable=True)  # 1-4
    cuisine_type = db.Column(db.String(50), nullable=True)
    group_friendly = db.Column(db.Boolean, default=True)
    last_visited = db.Column(db.Date, nullable=True)
    visit_count = db.Column(db.Integer, default=0)
    avg_group_rating = db.Column(db.Numeric(2, 1), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lunches = db.relationship('Lunch', backref='location', lazy='dynamic')
    
    def __repr__(self):
        return f'<Location {self.name}>'
