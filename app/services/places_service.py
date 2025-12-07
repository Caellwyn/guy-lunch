"""
Google Places API integration for Tuesday Lunch Scheduler.

Uses the Google Places API (New) for:
- Place Autocomplete (search as you type)
- Place Details (get full info for a selected place)

Requires: GOOGLE_PLACES_API_KEY environment variable
"""

import os
import requests
from typing import Optional
from flask import current_app


class PlacesService:
    """Service for Google Places API interactions."""

    # Google Places API endpoints
    AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
    DETAILS_URL = "https://places.googleapis.com/v1/places"

    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_PLACES_API_KEY')

    def is_configured(self) -> bool:
        """Check if the API key is configured."""
        return bool(self.api_key)

    def search_places(self, query: str, location_bias: dict = None) -> dict:
        """
        Search for places using autocomplete.

        Args:
            query: Search text (e.g., "pizza longview wa")
            location_bias: Optional dict with 'lat' and 'lng' for location bias

        Returns:
            dict with 'success', 'places' (list), and 'error' (if failed)
        """
        if not self.api_key:
            return {
                'success': False,
                'places': [],
                'error': 'Google Places API key not configured'
            }

        if not query or len(query) < 2:
            return {
                'success': True,
                'places': [],
                'error': None
            }

        try:
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.api_key,
            }

            # Build request body
            body = {
                'input': query,
                'includedPrimaryTypes': ['restaurant', 'cafe', 'bar', 'meal_takeaway', 'meal_delivery'],
                'languageCode': 'en',
            }

            # Add location bias if provided (Longview, WA area by default)
            if location_bias:
                body['locationBias'] = {
                    'circle': {
                        'center': {
                            'latitude': location_bias.get('lat', 46.1382),
                            'longitude': location_bias.get('lng', -122.9382)
                        },
                        'radius': 50000.0  # 50km radius
                    }
                }
            else:
                # Default to Longview, WA area
                body['locationBias'] = {
                    'circle': {
                        'center': {
                            'latitude': 46.1382,
                            'longitude': -122.9382
                        },
                        'radius': 50000.0
                    }
                }

            response = requests.post(
                self.AUTOCOMPLETE_URL,
                headers=headers,
                json=body,
                timeout=10
            )

            if response.status_code != 200:
                current_app.logger.error(f"Places API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'places': [],
                    'error': f'API error: {response.status_code}'
                }

            data = response.json()
            suggestions = data.get('suggestions', [])

            # Parse suggestions into a simpler format
            places = []
            for suggestion in suggestions:
                place_prediction = suggestion.get('placePrediction', {})
                if place_prediction:
                    places.append({
                        'place_id': place_prediction.get('placeId'),
                        'name': place_prediction.get('structuredFormat', {}).get('mainText', {}).get('text', ''),
                        'address': place_prediction.get('structuredFormat', {}).get('secondaryText', {}).get('text', ''),
                        'description': place_prediction.get('text', {}).get('text', ''),
                    })

            return {
                'success': True,
                'places': places,
                'error': None
            }

        except requests.exceptions.Timeout:
            current_app.logger.error("Places API timeout")
            return {
                'success': False,
                'places': [],
                'error': 'Request timed out'
            }
        except Exception as e:
            current_app.logger.error(f"Places API exception: {e}")
            return {
                'success': False,
                'places': [],
                'error': str(e)
            }

    def get_place_details(self, place_id: str) -> dict:
        """
        Get detailed information about a place.

        Args:
            place_id: Google Place ID

        Returns:
            dict with 'success', 'place' (dict), and 'error' (if failed)
        """
        if not self.api_key:
            return {
                'success': False,
                'place': None,
                'error': 'Google Places API key not configured'
            }

        if not place_id:
            return {
                'success': False,
                'place': None,
                'error': 'Place ID required'
            }

        try:
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.api_key,
                'X-Goog-FieldMask': 'id,displayName,formattedAddress,nationalPhoneNumber,rating,priceLevel,primaryType,websiteUri,googleMapsUri'
            }

            url = f"{self.DETAILS_URL}/{place_id}"

            response = requests.get(
                url,
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                current_app.logger.error(f"Places Details API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'place': None,
                    'error': f'API error: {response.status_code}'
                }

            data = response.json()

            # Parse price level (Google returns like "PRICE_LEVEL_MODERATE")
            price_level_map = {
                'PRICE_LEVEL_FREE': 0,
                'PRICE_LEVEL_INEXPENSIVE': 1,
                'PRICE_LEVEL_MODERATE': 2,
                'PRICE_LEVEL_EXPENSIVE': 3,
                'PRICE_LEVEL_VERY_EXPENSIVE': 4,
            }
            price_level_str = data.get('priceLevel', '')
            price_level = price_level_map.get(price_level_str, None)

            # Map primary type to cuisine
            primary_type = data.get('primaryType', '')
            cuisine_map = {
                'restaurant': 'Restaurant',
                'cafe': 'Cafe',
                'bar': 'Bar & Grill',
                'meal_takeaway': 'Takeout',
                'meal_delivery': 'Delivery',
                'american_restaurant': 'American',
                'italian_restaurant': 'Italian',
                'mexican_restaurant': 'Mexican',
                'chinese_restaurant': 'Chinese',
                'japanese_restaurant': 'Japanese',
                'thai_restaurant': 'Thai',
                'indian_restaurant': 'Indian',
                'pizza_restaurant': 'Pizza',
                'seafood_restaurant': 'Seafood',
                'steak_house': 'Steakhouse',
                'breakfast_restaurant': 'Breakfast',
                'brunch_restaurant': 'Brunch',
                'hamburger_restaurant': 'Burgers',
                'sandwich_shop': 'Sandwiches',
            }
            cuisine = cuisine_map.get(primary_type, primary_type.replace('_', ' ').title() if primary_type else None)

            place = {
                'place_id': data.get('id'),
                'name': data.get('displayName', {}).get('text', ''),
                'address': data.get('formattedAddress', ''),
                'phone': data.get('nationalPhoneNumber', ''),
                'google_rating': data.get('rating'),
                'price_level': price_level,
                'cuisine_type': cuisine,
                'website': data.get('websiteUri', ''),
                'maps_url': data.get('googleMapsUri', ''),
            }

            return {
                'success': True,
                'place': place,
                'error': None
            }

        except requests.exceptions.Timeout:
            current_app.logger.error("Places Details API timeout")
            return {
                'success': False,
                'place': None,
                'error': 'Request timed out'
            }
        except Exception as e:
            current_app.logger.error(f"Places Details API exception: {e}")
            return {
                'success': False,
                'place': None,
                'error': str(e)
            }


# Singleton instance
places_service = PlacesService()
