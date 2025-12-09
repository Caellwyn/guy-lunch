
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from app import db
from app.models import Photo, Lunch, Member, Location, PhotoTag, Attendance
from app.services.storage_service import storage_service
from app.routes.member import member_required, get_current_member
from datetime import datetime

gallery_bp = Blueprint('gallery', __name__, url_prefix='/gallery')

@gallery_bp.route('/')
@member_required
def index():
    """Gallery main page."""
    page = request.args.get('page', 1, type=int)
    lunch_id = request.args.get('lunch_id', type=int)
    location_id = request.args.get('location_id', type=int)
    tagged_member_id_raw = request.args.get('tagged_member_id', '')
    tagged_member_id = int(tagged_member_id_raw) if tagged_member_id_raw.isdigit() else None
    per_page = 20
    
    query = Photo.query
    
    if lunch_id:
        query = query.filter_by(lunch_id=lunch_id)
        
    if location_id:
        query = query.join(Lunch).filter(Lunch.location_id == location_id)
        
    if tagged_member_id:
        # Filter to photos where this member is tagged; distinct avoids duplicates from multiple tags
        query = query.join(PhotoTag).filter(PhotoTag.member_id == tagged_member_id).distinct()
        
    photos = query.order_by(Photo.created_at.desc()).distinct().paginate(page=page, per_page=per_page, error_out=False)
    
    # Get lunches that have photos for the sidebar navigation
    # We want lunches that have at least one photo, ordered by date
    lunches_with_photos = Lunch.query.join(Photo).distinct().order_by(Lunch.date.desc()).all()
    
    # Get lunches the current member attended (for upload dropdown)
    current_member = get_current_member()
    attended_lunches = Lunch.query.join(Attendance).filter(
        Attendance.member_id == current_member.id
    ).order_by(Lunch.date.desc()).limit(20).all()
    
    # Get all lunches for the calendar
    all_lunches = Lunch.query.order_by(Lunch.date.asc()).all()
    lunches_json = [{
        'id': l.id,
        'date': l.date.strftime('%Y-%m-%d'),
        'restaurant': l.restaurant,
        'photo_count': l.photos.count()
    } for l in all_lunches]
    
    # Get lists for filters
    # Allow filtering by any member (including guests) to avoid mismatches when tagging
    members = Member.query.order_by(Member.name).all()
    locations = Location.query.order_by(Location.name).all()
    
    return render_template('member/gallery.html',
                           photos=photos,
                           lunches=attended_lunches,
                           lunches_with_photos=lunches_with_photos,
                           lunches_json=lunches_json,
                           members=members,
                           locations=locations,
                           current_lunch_id=lunch_id,
                           current_location_id=location_id,
                           current_tagged_member_id=tagged_member_id,
                           current_tagged_member_id_raw=tagged_member_id_raw,
                           current_member=current_member)

@gallery_bp.route('/lunch/<int:lunch_id>/attendees')
@member_required
def get_lunch_attendees(lunch_id):
    """Get attendees for a specific lunch."""
    lunch = Lunch.query.get_or_404(lunch_id)
    attendees = []
    for attendance in lunch.attendances:
        attendees.append({
            'id': attendance.member.id,
            'name': attendance.member.name
        })
    return jsonify(attendees)


@gallery_bp.route('/upload', methods=['POST'])
@member_required
def upload():
    """Handle photo upload."""
    if 'photo' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('gallery.index'))

    file = request.files['photo']
    lunch_id = request.form.get('lunch_id')
    caption = request.form.get('caption')
    tagged_member_ids = request.form.getlist('tagged_members')

    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('gallery.index'))

    # Verify member attended this lunch
    current_member = get_current_member()
    if lunch_id:
        attendance = Attendance.query.filter_by(
            lunch_id=lunch_id,
            member_id=current_member.id
        ).first()
        if not attendance:
            flash('You can only upload photos for lunches you attended.', 'error')
            return redirect(url_for('gallery.index'))

    if file:
        # Upload to R2
        file_url = storage_service.upload_file(file)
        
        if file_url:
            # Create database record
            photo = Photo(
                lunch_id=lunch_id,
                uploaded_by=session['member_id'],
                file_url=file_url,
                caption=caption
            )
            db.session.add(photo)
            db.session.flush() # Flush to get photo.id
            
            # Add tags
            if tagged_member_ids:
                for member_id in tagged_member_ids:
                    # Verify attendance (double check)
                    attendance = Attendance.query.filter_by(lunch_id=lunch_id, member_id=member_id).first()
                    if attendance:
                        tag = PhotoTag(photo_id=photo.id, member_id=member_id)
                        db.session.add(tag)
            
            db.session.commit()
            
            flash('Photo uploaded successfully!', 'success')
        else:
            flash('Error uploading file. Please try again.', 'error')
            
    return redirect(url_for('gallery.index'))

@gallery_bp.route('/delete/<int:photo_id>', methods=['POST'])
@member_required
def delete(photo_id):
    """Delete a photo."""
    photo = Photo.query.get_or_404(photo_id)
    current_member_id = session['member_id']
    
    # Only allow deletion by uploader or admin (if we had admin role check)
    if photo.uploaded_by != current_member_id:
        flash('You can only delete photos you uploaded.', 'error')
        return redirect(url_for('gallery.index'))
        
    # Note: We might want to delete from R2 as well, but for now let's just remove from DB
    # or implement soft delete. R2 deletion requires another method in storage_service.
    
    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted.', 'success')
    return redirect(url_for('gallery.index'))


@gallery_bp.route('/photo/<int:photo_id>/details')
@member_required
def photo_details(photo_id):
    """Get photo details including tags and potential taggable members."""
    photo = Photo.query.get_or_404(photo_id)
    
    # Get tags
    tags = [{'id': t.id, 'member_name': t.member.name, 'member_id': t.member_id} for t in photo.tags]
    
    # Get potential taggable members (attendees of the lunch)
    # Filter out members who are already tagged
    tagged_member_ids = [t['member_id'] for t in tags]
    
    attendees = []
    if photo.lunch:
        for attendance in photo.lunch.attendances:
            if attendance.member_id not in tagged_member_ids:
                attendees.append({
                    'id': attendance.member.id,
                    'name': attendance.member.name
                })
            
    return jsonify({
        'id': photo.id,
        'created_at_iso': photo.created_at.isoformat(),
        'tags': tags,
        'attendees': attendees,
        'caption': photo.caption,
        'uploader': photo.uploader.name,
        'lunch_date': photo.lunch.date.strftime('%B %d, %Y') if photo.lunch else 'Unknown Date',
        'restaurant': photo.lunch.restaurant if photo.lunch else 'Unknown Location'
    })


@gallery_bp.route('/photo/<int:photo_id>/tag', methods=['POST'])
@member_required
def tag_photo(photo_id):
    """Tag a member in a photo."""
    photo = Photo.query.get_or_404(photo_id)
    data = request.get_json()
    member_id = data.get('member_id')
    
    if not member_id:
        return jsonify({'error': 'Member ID required'}), 400
        
    # Verify member attended the lunch
    attendance = Attendance.query.filter_by(lunch_id=photo.lunch_id, member_id=member_id).first()
    if not attendance:
        return jsonify({'error': 'Member did not attend this lunch'}), 400
        
    # Check if already tagged
    existing_tag = PhotoTag.query.filter_by(photo_id=photo_id, member_id=member_id).first()
    if existing_tag:
        return jsonify({'error': 'Member already tagged'}), 400
        
    tag = PhotoTag(photo_id=photo_id, member_id=member_id)
    db.session.add(tag)
    db.session.commit()
    
    return jsonify({'success': True, 'tag': {'id': tag.id, 'member_name': tag.member.name}})
