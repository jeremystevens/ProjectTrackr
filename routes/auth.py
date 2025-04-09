from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from datetime import datetime
from app import db
from models import User
from forms import LoginForm, RegistrationForm, RequestPasswordResetForm, SecurityAnswerForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('paste.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=form.remember.data)
        flash(f'Welcome back, {user.username}!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('paste.index')
            
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('paste.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        # Handle security question
        if form.security_question.data == 'custom' and form.custom_question.data.strip():
            user.security_question = form.custom_question.data.strip()
        else:
            # Use the predefined question text rather than just the key
            question_dict = dict(form.security_question.choices)
            user.security_question = question_dict.get(form.security_question.data)
            
        # Set security answer (will be hashed)
        user.set_security_answer(form.security_answer.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('paste.index'))

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('paste.index'))
        
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # Store user_id in session for the security question step
        session['reset_user_id'] = user.id
        return redirect(url_for('auth.security_question', user_id=user.id))
        
    return render_template('auth/reset_request.html', form=form)
    
@auth_bp.route('/reset_password/security_question/<int:user_id>', methods=['GET', 'POST'])
def security_question(user_id):
    if current_user.is_authenticated:
        return redirect(url_for('paste.index'))
        
    # Get the user
    user = User.query.get_or_404(user_id)
    
    form = SecurityAnswerForm()
    if form.validate_on_submit():
        if user.check_security_answer(form.security_answer.data):
            # Generate the token
            token = user.generate_reset_token()
            return redirect(url_for('auth.reset_token', token=token))
        else:
            flash('Incorrect security answer. Please try again.', 'danger')
    
    return render_template('auth/security_question.html', form=form, security_question=user.security_question)
    
@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('paste.index'))
        
    # Verify the token and get the user
    user = User.verify_reset_token(token)
    if not user:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.reset_request'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', form=form)
