
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app import db
from app.models import Photo, Lunch, Member
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
    per_page = 20
    
    query = Photo.query
    
    if lunch_id:
        query = query.filter_by(lunch_id=lunch_id)
        
    photos = query.order_by(Photo.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get lunches that have photos for the sidebar navigation
    # We want lunches that have at least one photo, ordered by date
    lunches_with_photos = Lunch.query.join(Photo).distinct().order_by(Lunch.date.desc()).all()
    
    # Get recent lunches for the upload dropdown (all recent lunches, not just ones with photos)
    recent_lunches = Lunch.query.order_by(Lunch.date.desc()).limit(10).all()
    
    return render_template('member/gallery.html', 
                           photos=photos, 
                           lunches=recent_lunches, 
                           lunches_with_photos=lunches_with_photos,
                           current_lunch_id=lunch_id,
                           current_member=get_current_member())

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
    
    if file.filename == '':
        flash('No selected file', 'error')
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
