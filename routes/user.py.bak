from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import User, Paste

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # Get public pastes by this user
    pastes = Paste.query.filter_by(user_id=user.id, is_public=True).order_by(Paste.created_at.desc()).all()
    
    return render_template('user/profile.html', user=user, pastes=pastes)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    # Get all pastes by the logged-in user
    pastes = Paste.query.filter_by(user_id=current_user.id).order_by(Paste.created_at.desc()).all()
    
    return render_template('user/dashboard.html', pastes=pastes)

@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Update email
        email = request.form.get('email')
        if email and email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash('Email already exists.', 'danger')
            else:
                current_user.email = email
                db.session.commit()
                flash('Email updated successfully!', 'success')
        
        # Update password
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if current_password and new_password and confirm_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password updated successfully!', 'success')
        
        return redirect(url_for('user.settings'))
    
    return render_template('user/settings.html')

@user_bp.route('/regenerate_api_key')
@login_required
def regenerate_api_key():
    current_user.generate_api_key()
    db.session.commit()
    
    flash('API key regenerated successfully!', 'success')
    return redirect(url_for('user.settings'))
