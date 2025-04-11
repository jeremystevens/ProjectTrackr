from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, func, desc, case, extract
from datetime import datetime, timedelta
import json
import csv
import io
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from app import db
from models import User, Paste, Comment, PasteView, PasteCollection
from forms import ProfileEditForm

user_bp = Blueprint('user', __name__, url_prefix='/u')

@user_bp.route('/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    collections = None
    encryption_keys = {}
    
    # If viewing own profile, show all pastes and collections, otherwise show only public and unlisted
    if current_user.is_authenticated and current_user.id == user.id:
        pastes = Paste.query.filter_by(user_id=user.id).order_by(
            Paste.created_at.desc()
        ).paginate(page=page, per_page=10)
        
        # Get collections with paste count for each collection
        collections_query = db.session.query(
            PasteCollection,
            func.count(Paste.id).label('paste_count')
        ).outerjoin(
            Paste, Paste.collection_id == PasteCollection.id
        ).filter(
            PasteCollection.user_id == user.id
        ).group_by(
            PasteCollection.id
        ).order_by(
            PasteCollection.name
        ).all()
        
        # Convert to a list of collection objects with paste_count attribute
        collections = []
        for collection, paste_count in collections_query:
            collection.paste_count = paste_count
            collections.append(collection)
            
        # Store encryption keys for random-key encrypted pastes
        for paste in pastes.items:
            if paste.is_encrypted and paste.encryption_method == 'fernet-random' and paste.encryption_salt:
                encryption_keys[paste.short_id] = paste.encryption_salt
    else:
        pastes = Paste.query.filter(
            Paste.user_id == user.id,
            Paste.visibility != 'private',
            or_(Paste.expires_at.is_(None), Paste.expires_at > datetime.utcnow())
        ).order_by(Paste.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('user/profile.html', user=user, pastes=pastes, 
                           collections=collections, encryption_keys=encryption_keys)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Display a detailed dashboard with enhanced user statistics
    """
    # Time periods for statistics
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Basic stats
    total_pastes = Paste.query.filter_by(user_id=current_user.id).count()
    active_pastes = Paste.query.filter(
        Paste.user_id == current_user.id,
        or_(Paste.expires_at.is_(None), Paste.expires_at > now)
    ).count()
    expired_pastes = Paste.query.filter(
        Paste.user_id == current_user.id,
        Paste.expires_at.isnot(None),
        Paste.expires_at <= now
    ).count()
    
    # Recent activity
    pastes_last_week = Paste.query.filter(
        Paste.user_id == current_user.id,
        Paste.created_at >= week_ago
    ).count()
    
    pastes_last_month = Paste.query.filter(
        Paste.user_id == current_user.id,
        Paste.created_at >= month_ago
    ).count()
    
    # Total views stats
    total_views = db.session.query(func.count(PasteView.id)).join(Paste).filter(
        Paste.user_id == current_user.id
    ).scalar() or 0
    
    views_last_week = db.session.query(func.count(PasteView.id)).join(Paste).filter(
        Paste.user_id == current_user.id,
        PasteView.created_at >= week_ago
    ).scalar() or 0
    
    views_last_month = db.session.query(func.count(PasteView.id)).join(Paste).filter(
        Paste.user_id == current_user.id,
        PasteView.created_at >= month_ago
    ).scalar() or 0
    
    # Comments stats
    total_comments = db.session.query(func.count(Comment.id)).join(Paste).filter(
        Paste.user_id == current_user.id
    ).scalar() or 0
    
    comments_received_last_week = db.session.query(func.count(Comment.id)).join(Paste).filter(
        Paste.user_id == current_user.id,
        Comment.created_at >= week_ago
    ).scalar() or 0
    
    # Get comments made by the user on others' pastes
    comments_made = Comment.query.filter(
        Comment.user_id == current_user.id
    ).count()
    
    comments_made_last_week = Comment.query.filter(
        Comment.user_id == current_user.id,
        Comment.created_at >= week_ago
    ).count()
    
    # Most viewed pastes
    most_viewed_pastes = db.session.query(
        Paste, func.count(PasteView.id).label('view_count')
    ).join(PasteView).filter(
        Paste.user_id == current_user.id
    ).group_by(Paste.id).order_by(desc('view_count')).limit(5).all()
    
    # Most commented pastes
    most_commented_pastes = db.session.query(
        Paste, func.count(Comment.id).label('comment_count')
    ).join(Comment).filter(
        Paste.user_id == current_user.id
    ).group_by(Paste.id).order_by(desc('comment_count')).limit(5).all()
    
    # Paste syntax distribution
    syntax_distribution = db.session.query(
        Paste.syntax, func.count(Paste.id).label('count')
    ).filter(
        Paste.user_id == current_user.id
    ).group_by(Paste.syntax).order_by(desc('count')).all()
    
    # Paste visibility distribution
    visibility_distribution = db.session.query(
        Paste.visibility, func.count(Paste.id).label('count')
    ).filter(
        Paste.user_id == current_user.id
    ).group_by(Paste.visibility).all()
    
    # Weekly activity (for charts)
    day_labels = [(now - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
    
    # Pastes created by day of week
    daily_pastes = []
    for i in range(6, -1, -1):
        day_start = now - timedelta(days=i)
        day_end = now - timedelta(days=i-1) if i > 0 else now
        count = Paste.query.filter(
            Paste.user_id == current_user.id,
            Paste.created_at >= day_start,
            Paste.created_at < day_end
        ).count()
        daily_pastes.append(count)
    
    # Views received by day of week
    daily_views = []
    for i in range(6, -1, -1):
        day_start = now - timedelta(days=i)
        day_end = now - timedelta(days=i-1) if i > 0 else now
        count = db.session.query(func.count(PasteView.id)).join(Paste).filter(
            Paste.user_id == current_user.id,
            PasteView.created_at >= day_start,
            PasteView.created_at < day_end
        ).scalar() or 0
        daily_views.append(count)
    
    # Note: Collections are now displayed on the profile page instead of the dashboard
    
    # Get total collections count
    total_collections = PasteCollection.query.filter_by(user_id=current_user.id).count()
    
    stats = {
        'total_pastes': total_pastes,
        'active_pastes': active_pastes,
        'expired_pastes': expired_pastes,
        'pastes_last_week': pastes_last_week,
        'pastes_last_month': pastes_last_month,
        'total_views': total_views,
        'views_last_week': views_last_week,
        'views_last_month': views_last_month,
        'total_comments': total_comments,
        'comments_received_last_week': comments_received_last_week,
        'comments_made': comments_made,
        'comments_made_last_week': comments_made_last_week,
        'most_viewed_pastes': most_viewed_pastes,
        'most_commented_pastes': most_commented_pastes,
        'syntax_distribution': syntax_distribution,
        'visibility_distribution': visibility_distribution,
        'day_labels': day_labels,
        'daily_pastes': daily_pastes,
        'daily_views': daily_views,
        'total_collections': total_collections
    }
    
    return render_template('user/dashboard.html', stats=stats)

@user_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileEditForm()
    
    if request.method == 'GET':
        form.email.data = current_user.email
        form.bio.data = current_user.bio
        form.website.data = current_user.website
        form.location.data = current_user.location
    
    if form.validate_on_submit():
        # Check if email is being changed
        if form.email.data != current_user.email:
            # Check if email is already in use
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already in use by another account.', 'danger')
                return render_template('user/edit_profile.html', form=form)
            
            current_user.email = form.email.data
        
        # Update other fields
        current_user.bio = form.bio.data
        current_user.website = form.website.data
        current_user.location = form.location.data
        
        # Update password if provided
        if form.new_password.data:
            if not form.current_password.data:
                flash('Current password is required to set a new password.', 'danger')
                return render_template('user/edit_profile.html', form=form)
                
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('user/edit_profile.html', form=form)
                
            current_user.set_password(form.new_password.data)
            flash('Password updated successfully.', 'success')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile', username=current_user.username))
    
    return render_template('user/edit_profile.html', form=form)

@user_bp.route('/export', methods=['GET', 'POST'])
@login_required
def export_pastes():
    """
    Export user's pastes in various formats (JSON, CSV, etc.)
    """
    if request.method == 'GET':
        # Get all user collections for the dropdown
        collections = PasteCollection.query.filter_by(user_id=current_user.id).all()
        return render_template('user/export.html', collections=collections)
    
    # Handle export request (POST)
    export_format = request.form.get('format', 'json')
    collection_id = request.form.get('collection_id', None)
    include_private = 'include_private' in request.form
    
    # Query pastes based on filters
    query = Paste.query.filter_by(user_id=current_user.id)
    
    # Filter by collection if specified
    if collection_id and collection_id != '0':
        query = query.filter_by(collection_id=int(collection_id))
    
    # Filter by visibility unless include_private is checked
    if not include_private:
        query = query.filter(Paste.visibility != 'private')
    
    pastes = query.order_by(Paste.created_at.desc()).all()
    
    # If no pastes found
    if not pastes:
        flash('No pastes found matching your criteria.', 'warning')
        return redirect(url_for('user.export_pastes'))
    
    # Format data for export
    if export_format == 'json':
        paste_data = []
        for paste in pastes:
            # Format dates as ISO strings
            created_at = paste.created_at.isoformat() if paste.created_at else None
            expires_at = paste.expires_at.isoformat() if paste.expires_at else None
            
            data = {
                'title': paste.title,
                'content': paste.content,
                'syntax': paste.syntax,
                'visibility': paste.visibility,
                'created_at': created_at,
                'expires_at': expires_at,
                'size': paste.size,
                'comments_enabled': paste.comments_enabled,
                'burn_after_read': paste.burn_after_read,
                'short_id': paste.short_id
            }
            paste_data.append(data)
        
        # Create a filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"flaskbin_export_{current_user.username}_{timestamp}.json"
        
        # Create response with JSON data
        response = Response(
            json.dumps(paste_data, indent=2),
            mimetype='application/json'
        )
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
        
    elif export_format == 'csv':
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row
        writer.writerow([
            'Title', 'Content', 'Syntax', 'Visibility', 
            'Created At', 'Expires At', 'Size', 
            'Comments Enabled', 'Burn After Read', 'Short ID'
        ])
        
        # Write data rows
        for paste in pastes:
            created_at = paste.created_at.isoformat() if paste.created_at else ''
            expires_at = paste.expires_at.isoformat() if paste.expires_at else ''
            
            writer.writerow([
                paste.title,
                paste.content,
                paste.syntax,
                paste.visibility,
                created_at,
                expires_at,
                paste.size,
                paste.comments_enabled,
                paste.burn_after_read,
                paste.short_id
            ])
        
        # Create a filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"flaskbin_export_{current_user.username}_{timestamp}.csv"
        
        # Set response headers for CSV download
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/csv'
        )
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
        
    elif export_format == 'plaintext':
        # For plaintext export, we'll create a single text file with all paste contents
        output = io.StringIO()
        
        for paste in pastes:
            # Write paste metadata as comments
            output.write(f"# Title: {paste.title}\n")
            output.write(f"# Syntax: {paste.syntax}\n")
            output.write(f"# Created: {paste.created_at}\n")
            output.write(f"# Short ID: {paste.short_id}\n")
            output.write(f"# Visibility: {paste.visibility}\n")
            output.write("#" + "-" * 40 + "\n\n")
            
            # Write paste content
            output.write(paste.content)
            output.write("\n\n" + "#" + "=" * 60 + "\n\n")
        
        # Create a filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"flaskbin_export_{current_user.username}_{timestamp}.txt"
        
        # Set response headers for text download
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/plain'
        )
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
    
    # If format not supported
    flash('Unsupported export format selected.', 'danger')
    return redirect(url_for('user.export_pastes'))

@user_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_pastes():
    """
    Import pastes from a file (JSON, CSV, etc.)
    """
    from utils import generate_short_id
    
    if request.method == 'GET':
        # Get all user collections for the dropdown
        collections = PasteCollection.query.filter_by(user_id=current_user.id).all()
        return render_template('user/import.html', collections=collections)
    
    # Handle import request (POST)
    if 'import_file' not in request.files:
        flash('No file selected for import.', 'danger')
        return redirect(url_for('user.import_pastes'))
    
    import_file = request.files['import_file']
    if import_file.filename == '':
        flash('No file selected for import.', 'danger')
        return redirect(url_for('user.import_pastes'))
    
    import_format = request.form.get('format', 'json')
    collection_id = request.form.get('collection_id', None)
    
    # Convert collection_id to int if provided, otherwise None
    if collection_id and collection_id != '0':
        collection_id = int(collection_id)
        # Verify the collection exists and belongs to the user
        collection = PasteCollection.query.get(collection_id)
        if not collection or collection.user_id != current_user.id:
            flash('Invalid collection selected.', 'danger')
            return redirect(url_for('user.import_pastes'))
    else:
        collection_id = None
    
    success_count = 0
    error_count = 0
    
    try:
        if import_format == 'json':
            # Parse JSON file
            content = import_file.read().decode('utf-8')
            paste_data = json.loads(content)
            
            # Handle both single object and array formats
            if not isinstance(paste_data, list):
                paste_data = [paste_data]
            
            for data in paste_data:
                try:
                    # Generate a unique short ID
                    while True:
                        short_id = generate_short_id()
                        if not Paste.query.filter_by(short_id=short_id).first():
                            break
                    
                    # Create the paste
                    paste = Paste(
                        title=data.get('title', 'Imported Paste'),
                        content=data.get('content', ''),
                        syntax=data.get('syntax', 'text'),
                        visibility=data.get('visibility', 'private'),
                        user_id=current_user.id,
                        short_id=short_id,
                        comments_enabled=data.get('comments_enabled', True),
                        burn_after_read=data.get('burn_after_read', False),
                        collection_id=collection_id
                    )
                    
                    # Set expiration if provided, otherwise never expires
                    if 'expires_at' in data and data['expires_at']:
                        try:
                            expires_at = datetime.fromisoformat(data['expires_at'])
                            # Only set if it's in the future
                            if expires_at > datetime.utcnow():
                                paste.expires_at = expires_at
                        except ValueError:
                            # Invalid date format, leave as None (never expires)
                            pass
                    
                    # Calculate paste size
                    paste.calculate_size()
                    
                    db.session.add(paste)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    import logging
                    logging.error(f"Error importing paste: {str(e)}")
            
            db.session.commit()
                
        elif import_format == 'csv':
            # Parse CSV file
            content = import_file.read().decode('utf-8')
            reader = csv.reader(io.StringIO(content))
            
            # Skip header row
            next(reader, None)
            
            for row in reader:
                try:
                    # Ensure the row has enough columns
                    if len(row) < 3:
                        continue
                    
                    # Generate a unique short ID
                    while True:
                        short_id = generate_short_id()
                        if not Paste.query.filter_by(short_id=short_id).first():
                            break
                    
                    # Extract data from row
                    title = row[0] if len(row) > 0 else 'Imported Paste'
                    content = row[1] if len(row) > 1 else ''
                    syntax = row[2] if len(row) > 2 else 'text'
                    visibility = row[3] if len(row) > 3 else 'private'
                    
                    # Create the paste
                    paste = Paste(
                        title=title,
                        content=content,
                        syntax=syntax,
                        visibility=visibility,
                        user_id=current_user.id,
                        short_id=short_id,
                        comments_enabled=True,
                        burn_after_read=False,
                        collection_id=collection_id
                    )
                    
                    # Calculate paste size
                    paste.calculate_size()
                    
                    db.session.add(paste)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    import logging
                    logging.error(f"Error importing paste from CSV: {str(e)}")
            
            db.session.commit()
        
        else:
            flash('Unsupported import format selected.', 'danger')
            return redirect(url_for('user.import_pastes'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Import failed: {str(e)}', 'danger')
        return redirect(url_for('user.import_pastes'))
    
    # Update user's total pastes count
    if success_count > 0:
        current_user.total_pastes += success_count
        db.session.commit()
    
    # Show results
    if success_count > 0:
        flash(f'Successfully imported {success_count} pastes.', 'success')
    if error_count > 0:
        flash(f'Failed to import {error_count} pastes due to errors.', 'warning')
    
    return redirect(url_for('user.profile', username=current_user.username))
