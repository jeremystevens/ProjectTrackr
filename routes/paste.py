from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
import secrets
from datetime import datetime, timedelta
from app import db
from models import Paste, PasteView

paste_bp = Blueprint('paste', __name__, url_prefix='/paste')

@paste_bp.route('/')
def index():
    # Redirect to main index for now
    return redirect(url_for('index'))

@paste_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip() or 'Untitled Paste'
        content = request.form.get('content')
        language = request.form.get('language', 'plaintext')
        expiration = request.form.get('expiration', 'never')
        is_public = 'is_public' in request.form
        burn_after_read = 'burn_after_read' in request.form
        
        # Check if content is provided
        if not content:
            flash('Paste content cannot be empty.', 'danger')
            return redirect(url_for('paste.new'))
        
        # Determine expiration date
        expires_at = None
        if expiration != 'never':
            if expiration == '10min':
                expires_at = datetime.utcnow() + timedelta(minutes=10)
            elif expiration == '1hour':
                expires_at = datetime.utcnow() + timedelta(hours=1)
            elif expiration == '1day':
                expires_at = datetime.utcnow() + timedelta(days=1)
            elif expiration == '1week':
                expires_at = datetime.utcnow() + timedelta(weeks=1)
            elif expiration == '1month':
                expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Create new paste
        new_paste = Paste(
            short_id=secrets.token_urlsafe(6),
            title=title,
            content=content,
            language=language,
            expires_at=expires_at,
            is_public=is_public,
            burn_after_read=burn_after_read,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(new_paste)
        db.session.commit()
        
        flash('Paste created successfully!', 'success')
        return redirect(url_for('paste.view', short_id=new_paste.short_id))
    
    return render_template('paste/new.html')

@paste_bp.route('/<short_id>')
def view(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste is expired
    if paste.expires_at and paste.expires_at < datetime.utcnow():
        db.session.delete(paste)
        db.session.commit()
        flash('This paste has expired.', 'warning')
        return redirect(url_for('index'))
    
    # Check if paste is burn after read
    if paste.burn_after_read:
        # Record the view before deleting
        paste_view = PasteView(
            paste_id=paste.id,
            viewer_ip=request.remote_addr,
            user_agent=request.user_agent.string,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(paste_view)
        
        # Get paste content before deleting
        content = paste.content
        title = paste.title
        language = paste.language
        
        # Delete the paste
        db.session.delete(paste)
        db.session.commit()
        
        # Display the paste one time
        flash('This was a burn-after-read paste and has been deleted.', 'warning')
        return render_template('paste/burn_after_read.html', 
                               title=title, 
                               content=content, 
                               language=language)
    
    # Record the view
    paste_view = PasteView(
        paste_id=paste.id,
        viewer_ip=request.remote_addr,
        user_agent=request.user_agent.string,
        user_id=current_user.id if current_user.is_authenticated else None
    )
    db.session.add(paste_view)
    
    # Increment view count
    paste.views += 1
    db.session.commit()
    
    return render_template('paste/view.html', paste=paste)

@paste_bp.route('/<short_id>/delete')
@login_required
def delete(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if user owns the paste
    if paste.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to delete this paste.', 'danger')
        return redirect(url_for('paste.view', short_id=short_id))
    
    db.session.delete(paste)
    db.session.commit()
    
    flash('Paste deleted successfully!', 'success')
    return redirect(url_for('index'))
