# Import all models here so they're registered with SQLAlchemy
from app.models.member import Member
from app.models.location import Location
from app.models.lunch import Lunch
from app.models.attendance import Attendance
from app.models.rating import Rating
from app.models.photo import Photo, PhotoTag

__all__ = ['Member', 'Location', 'Lunch', 'Attendance', 'Rating', 'Photo', 'PhotoTag']
