from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Lunch, Location, Member, Rating

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - simple landing for now."""
    return render_template('index.html')


@main_bp.route('/health')
def health():
    """Health check endpoint for Railway."""
    return {'status': 'healthy', 'app': 'Tuesday Lunch Scheduler'}


# ============== HOST CONFIRMATION FLOW ==============

@main_bp.route('/confirm/<token>')
def confirm_host(token):
    """Host confirmation page - select a restaurant."""
    # Find the lunch by token
    lunch = Lunch.query.filter_by(confirmation_token=token).first()

    if not lunch:
        flash('Invalid or expired confirmation link.', 'error')
        return render_template('public/invalid_token.html')

    # Check if already confirmed
    if lunch.location_id and lunch.reservation_confirmed:
        location = Location.query.get(lunch.location_id)
        return render_template('public/already_confirmed.html',
                               lunch=lunch,
                               location=location)

    # Get the host
    host = Member.query.get(lunch.host_id) if lunch.host_id else None

    # Get recent locations for selection
    recent_locations = Location.query.filter_by(group_friendly=True).order_by(
        Location.last_visited.desc()
    ).limit(10).all()

    return render_template('public/confirm_host.html',
                           lunch=lunch,
                           host=host,
                           recent_locations=recent_locations,
                           token=token)


@main_bp.route('/confirm/<token>', methods=['POST'])
def submit_confirmation(token):
    """Handle host's restaurant selection."""
    lunch = Lunch.query.filter_by(confirmation_token=token).first()

    if not lunch:
        flash('Invalid or expired confirmation link.', 'error')
        return redirect(url_for('main.index'))

    # Get selection type
    selection_type = request.form.get('selection_type')

    if selection_type == 'existing':
        # Selected an existing location
        location_id = request.form.get('location_id')
        if not location_id:
            flash('Please select a restaurant.', 'error')
            return redirect(url_for('main.confirm_host', token=token))

        location = Location.query.get(int(location_id))
        if not location:
            flash('Invalid location selected.', 'error')
            return redirect(url_for('main.confirm_host', token=token))

        # Update lunch record
        lunch.location_id = location.id
        lunch.reservation_confirmed = True
        db.session.commit()

        flash(f'Confirmed! You selected {location.name}.', 'success')
        return render_template('public/confirmation_success.html',
                               lunch=lunch,
                               location=location)

    elif selection_type == 'new':
        # Suggested a new location
        new_name = request.form.get('new_location_name', '').strip()
        new_address = request.form.get('new_location_address', '').strip()
        new_phone = request.form.get('new_location_phone', '').strip()
        group_friendly = request.form.get('group_friendly') == 'on'

        # Google Places data (optional)
        google_place_id = request.form.get('google_place_id', '').strip()
        google_rating = request.form.get('google_rating', '').strip()
        price_level = request.form.get('price_level', '').strip()
        cuisine_type = request.form.get('cuisine_type', '').strip()

        if not new_name:
            flash('Please enter a restaurant name.', 'error')
            return redirect(url_for('main.confirm_host', token=token))

        if not group_friendly:
            flash('Please confirm the restaurant can accommodate our group.', 'error')
            return redirect(url_for('main.confirm_host', token=token))

        # Check if location with this Google Place ID already exists
        existing_location = None
        if google_place_id:
            existing_location = Location.query.filter_by(google_place_id=google_place_id).first()

        if existing_location:
            # Use existing location instead of creating duplicate
            location = existing_location
        else:
            # Create new location with Google Places data
            location = Location(
                name=new_name,
                address=new_address or None,
                phone=new_phone or None,
                google_place_id=google_place_id or None,
                google_rating=float(google_rating) if google_rating else None,
                price_level=int(price_level) if price_level else None,
                cuisine_type=cuisine_type or None,
                group_friendly=True,
                visit_count=0
            )
            db.session.add(location)
            db.session.flush()  # Get the ID

        # Update lunch record
        lunch.location_id = location.id
        lunch.reservation_confirmed = True
        db.session.commit()

        if existing_location:
            flash(f'Confirmed! You selected {location.name}.', 'success')
        else:
            flash(f'Confirmed! You added {location.name} as a new location.', 'success')
        return render_template('public/confirmation_success.html',
                               lunch=lunch,
                               location=location)

    else:
        flash('Invalid selection.', 'error')
        return redirect(url_for('main.confirm_host', token=token))


# ============== RATING SUBMISSION FLOW ==============
# One-click rating from email - no form needed!

@main_bp.route('/rate/<token>/<int:rating_value>')
def submit_rating(token, rating_value):
    """One-click rating submission from email."""
    # Validate rating value
    if rating_value < 1 or rating_value > 5:
        flash('Invalid rating value.', 'error')
        return render_template('public/invalid_token.html')

    # Find the rating record by token
    rating_record = Rating.query.filter_by(rating_token=token).first()

    if not rating_record:
        flash('Invalid or expired rating link.', 'error')
        return render_template('public/invalid_token.html')

    # Get lunch and location for display
    lunch = Lunch.query.get(rating_record.lunch_id)
    location = Location.query.get(lunch.location_id) if lunch and lunch.location_id else None

    # Check if already rated
    if rating_record.rating is not None:
        return render_template('public/already_rated.html',
                               rating=rating_record,
                               lunch=lunch,
                               location=location)

    # Save the rating
    rating_record.rating = rating_value

    # Update location's average rating
    if location:
        # Calculate new average from all ratings for this location
        all_ratings = Rating.query.join(Lunch).filter(
            Lunch.location_id == location.id,
            Rating.rating.isnot(None)
        ).all()

        # Include this new rating in the calculation
        total = sum(r.rating for r in all_ratings) + rating_value
        count = len(all_ratings) + 1
        location.avg_group_rating = round(total / count, 1)

    db.session.commit()

    # Show thank you page
    return render_template('public/rating_thanks.html',
                           rating=rating_record,
                           lunch=lunch,
                           location=location)
