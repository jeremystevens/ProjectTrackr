from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from datetime import datetime
from app import db, limiter
from models import User
from forms import LoginForm, RegistrationForm, RequestPasswordResetForm, SecurityAnswerForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('paste.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # Check if user exists first
        if user is None:
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form)
            
        # Ban check
        if user.is_account_banned():
            if user.banned_until:
                flash(f'Your account has been temporarily banned until {user.banned_until.strftime("%Y-%m-%d %H:%M")}. ' +
                      f'Reason: {user.ban_reason or "Violation of terms of service"}', 'danger')
            else:
                flash(f'Your account has been permanently banned. ' +
                      f'Reason: {user.ban_reason or "Violation of terms of service"}', 'danger')
            return render_template('auth/login.html', form=form)
            
        # Account lockout check
        if user.is_account_locked():
            remaining_mins = user.get_lockout_remaining_time()
            flash(f'This account is temporarily locked due to too many failed attempts. ' +
                  f'Please try again in {remaining_mins} minute(s).', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Password check
        if not user.check_password(form.password.data):
            # Record the failed login attempt and check if account is now locked
            user.record_failed_login()
            
            if user.is_account_locked():
                remaining_mins = user.get_lockout_remaining_time()
                flash(f'Too many failed login attempts. Your account has been locked for ' +
                      f'{remaining_mins} minute(s).', 'danger')
            else:
                # Calculate remaining attempts
                remaining_attempts = 5 - user.failed_login_attempts
                flash(f'Invalid username or password. {remaining_attempts} attempts remaining ' +
                      f'before your account is temporarily locked.', 'danger')
            
            return render_template('auth/login.html', form=form)
        
        # Successful login - reset failed attempt counters
        user.reset_failed_attempts(login_only=True)
        
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
@limiter.limit("5 per hour")
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
@limiter.limit("5 per hour")
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
@limiter.limit("10 per hour")
def security_question(user_id):
    if current_user.is_authenticated:
        return redirect(url_for('paste.index'))
        
    # Get the user
    user = User.query.get_or_404(user_id)
    
    # Check for banned account
    if user.is_account_banned():
        if user.banned_until:
            flash(f'This account has been temporarily banned until {user.banned_until.strftime("%Y-%m-%d %H:%M")}. ' +
                  f'Password reset is not available.', 'danger')
        else:
            flash(f'This account has been permanently banned. ' +
                  f'Password reset is not available.', 'danger')
        return redirect(url_for('auth.reset_request'))
    
    # Check for account lockout
    if user.is_account_locked():
        remaining_mins = user.get_lockout_remaining_time()
        flash(f'This account is temporarily locked due to too many failed attempts. ' +
              f'Please try again in {remaining_mins} minute(s).', 'danger')
        return redirect(url_for('auth.reset_request'))
    
    form = SecurityAnswerForm()
    if form.validate_on_submit():
        if user.check_security_answer(form.security_answer.data):
            # Reset failed attempts on successful verification
            user.reset_failed_attempts()
            
            # Generate the token
            token = user.generate_reset_token()
            return redirect(url_for('auth.reset_token', token=token))
        else:
            # Record failed reset attempt
            user.record_failed_reset_attempt()
            
            if user.is_account_locked():
                remaining_mins = user.get_lockout_remaining_time()
                flash(f'Too many failed attempts. Password reset has been locked for ' +
                     f'{remaining_mins} minute(s).', 'danger')
                return redirect(url_for('auth.reset_request'))
            else:
                # Calculate remaining attempts
                remaining_attempts = 3 - user.failed_reset_attempts
                flash(f'Incorrect security answer. {remaining_attempts} attempts remaining ' +
                     f'before password reset is temporarily locked.', 'danger')
    
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
        
    # Check for banned account - don't allow banned users to reset passwords
    if user.is_account_banned():
        if user.banned_until:
            flash(f'This account has been temporarily banned until {user.banned_until.strftime("%Y-%m-%d %H:%M")}. ' +
                  f'Password reset is not available.', 'danger')
        else:
            flash(f'This account has been permanently banned. ' +
                  f'Password reset is not available.', 'danger')
        return redirect(url_for('auth.reset_request'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', form=form)
