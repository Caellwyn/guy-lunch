"""
API routes for AJAX/JSON endpoints.

Includes:
- Google Places search for location autocomplete
- Place details lookup
- Location details with member comments
- Profile picture upload
"""

from flask import Blueprint, request, jsonify, session, current_app
from app.services.places_service import places_service
from app.models import Location, Lunch, Rating, Member
from app import db

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/places/search')
def search_places():
    """
    Search for places using Google Places API.

    Query params:
        q: Search query (required, min 2 chars)

    Returns:
        JSON with 'success', 'places' array, and 'error' (if any)
    """
    query = request.args.get('q', '').strip()

    if len(query) < 2:
        return jsonify({
            'success': True,
            'places': [],
            'error': None
        })

    result = places_service.search_places(query)
    return jsonify(result)


@api_bp.route('/places/<place_id>')
def get_place_details(place_id):
    """
    Get detailed information about a place.

    Args:
        place_id: Google Place ID

    Returns:
        JSON with 'success', 'place' object, and 'error' (if any)
    """
    result = places_service.get_place_details(place_id)
    return jsonify(result)


@api_bp.route('/places/status')
def places_status():
    """Check if Google Places API is configured."""
    return jsonify({
        'configured': places_service.is_configured()
    })


@api_bp.route('/locations/<int:location_id>/details')
def get_location_details(location_id):
    """
    Get detailed location info including member comments.

    Returns location details, visit history, and member ratings with comments.
    """
    location = Location.query.get_or_404(location_id)

    # Get visit history
    visits = Lunch.query.filter_by(location_id=location_id).order_by(Lunch.date.desc()).all()

    # Get all ratings with comments for this location
    ratings_with_comments = Rating.query.join(Lunch).filter(
        Lunch.location_id == location_id,
        Rating.comment.isnot(None),
        Rating.comment != ''
    ).order_by(Rating.created_at.desc()).limit(10).all()

    comments = []
    for rating in ratings_with_comments:
        comments.append({
            'rating': rating.rating,
            'comment': rating.comment,
            'member_name': rating.member.name,
            'date': rating.created_at.strftime('%b %d, %Y') if rating.created_at else None
        })

    return jsonify({
        'success': True,
        'location': {
            'id': location.id,
            'name': location.name,
            'address': location.address,
            'phone': location.phone,
            'google_rating': location.google_rating,
            'avg_group_rating': location.avg_group_rating,
            'price_level': location.price_level,
            'cuisine_type': location.cuisine_type,
            'visit_count': len(visits),
            'last_visited': visits[0].date.strftime('%b %d, %Y') if visits else None,
            'comments': comments
        }
    })


@api_bp.route('/profile-picture/upload', methods=['POST'])
def upload_profile_picture():
    """
    Upload a profile picture to R2 storage.

    Requires member to be logged in (via session).
    Returns the R2 URL on success.
    """
    # Check if member is logged in
    member_id = session.get('member_id')
    if not member_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    member = Member.query.get(member_id)
    if not member:
        return jsonify({'success': False, 'error': 'Member not found'}), 404

    # Check for file
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    # Validate file type
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Invalid file type. Use JPG, PNG, GIF, or WebP.'}), 400

    # Upload to R2
    from app.services.storage_service import storage_service

    try:
        # Check if storage service is configured
        if not storage_service.s3_client:
            current_app.logger.error("R2 storage not configured - missing environment variables")
            return jsonify({'success': False, 'error': 'Storage not configured. Check R2 settings.'}), 500

        # Delete old picture if exists
        if member.profile_picture_url:
            storage_service.delete_file(member.profile_picture_url)

        # Upload new picture
        current_app.logger.info(f"Uploading profile picture for member {member_id}: {file.filename}")
        new_url = storage_service.upload_file(file, folder='profile_pictures')
        current_app.logger.info(f"Upload result: {new_url}")

        if new_url:
            # Save to member record immediately
            member.profile_picture_url = new_url
            db.session.commit()

            current_app.logger.info(f"Profile picture saved for member {member_id}: {new_url}")
            return jsonify({'success': True, 'url': new_url})
        else:
            current_app.logger.error(f"Upload returned None for member {member_id}")
            return jsonify({'success': False, 'error': 'Upload failed - no URL returned.'}), 500

    except Exception as e:
        current_app.logger.error(f"Profile picture upload error for member {member_id}: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'}), 500
