from datetime import datetime
from app import db


class Rating(db.Model):
    """Member rating for a lunch location."""
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    lunch_id = db.Column(db.Integer, db.ForeignKey('lunches.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # 1-5, NULL until submitted
    comment = db.Column(db.Text, nullable=True)
    rating_token = db.Column(db.String(64), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint: one rating per member per lunch
    __table_args__ = (
        db.UniqueConstraint('lunch_id', 'member_id', name='unique_rating'),
        db.CheckConstraint('rating IS NULL OR (rating >= 1 AND rating <= 5)', name='valid_rating'),
    )
    
    def __repr__(self):
        return f'<Rating lunch={self.lunch_id} member={self.member_id} rating={self.rating}>'
