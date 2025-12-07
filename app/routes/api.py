"""
API routes for AJAX/JSON endpoints.

Includes:
- Google Places search for location autocomplete
- Place details lookup
"""

from flask import Blueprint, request, jsonify
from app.services.places_service import places_service

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
