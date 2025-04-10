from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, func, desc, case, extract
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash
from app import db
from models import User, Paste, Comment, PasteView
from forms import ProfileEditForm

user_bp = Blueprint('user', __name__, url_prefix='/u')

@user_bp.route('/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    
    # If viewing own profile, show all pastes, otherwise show only public and unlisted
    if current_user.is_authenticated and current_user.id == user.id:
        pastes = Paste.query.filter_by(user_id=user.id).order_by(
            Paste.created_at.desc()
        ).paginate(page=page, per_page=10)
    else:
        pastes = Paste.query.filter(
            Paste.user_id == user.id,
            Paste.visibility != 'private',
            or_(Paste.expires_at.is_(None), Paste.expires_at > datetime.utcnow())
        ).order_by(Paste.created_at.desc()).paginate(page=page, per_page=10)
    
    return render_template('user/profile.html', user=user, pastes=pastes)

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
