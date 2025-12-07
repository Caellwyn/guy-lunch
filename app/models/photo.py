from datetime import datetime
from app import db


class Photo(db.Model):
    """Photo from a lunch event."""
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    lunch_id = db.Column(db.Integer, db.ForeignKey('lunches.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    caption = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tags = db.relationship('PhotoTag', backref='photo', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def signed_url(self):
        from app.services.storage_service import storage_service
        return storage_service.get_presigned_url(self.file_url)

    def __repr__(self):
        return f'<Photo {self.id} lunch={self.lunch_id}>'


class PhotoTag(db.Model):
    """Tag linking a member to a photo."""
    __tablename__ = 'photo_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint: one tag per member per photo
    __table_args__ = (
        db.UniqueConstraint('photo_id', 'member_id', name='unique_photo_tag'),
    )
    
    # Relationship to member
    member = db.relationship('Member', backref='photo_tags')
    
    def __repr__(self):
        return f'<PhotoTag photo={self.photo_id} member={self.member_id}>'
