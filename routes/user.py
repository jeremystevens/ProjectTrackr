from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, func, desc, case, extract
from datetime import datetime, timedelta
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
    else:
        pastes = Paste.query.filter(
            Paste.user_id == user.id,
            Paste.visibility != 'private',
            or_(Paste.expires_at.is_(None), Paste.expires_at > datetime.utcnow())
        ).order_by(Paste.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('user/profile.html', user=user, pastes=pastes, collections=collections)

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
    
    # Get user collections with paste count
    collections_query = db.session.query(
        PasteCollection,
        func.count(Paste.id).label('paste_count')
    ).outerjoin(
        Paste, Paste.collection_id == PasteCollection.id
    ).filter(
        PasteCollection.user_id == current_user.id
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
    
    # Limit to 3 collections for dashboard preview
    preview_collections = collections[:3] if collections else []
    
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
        'collections': preview_collections,
        'total_collections': len(collections)
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
