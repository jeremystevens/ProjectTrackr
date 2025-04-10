from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, func, desc, case, extract
from datetime import datetime, timedelta
from app import db
from models import (
    User, Paste, Comment, PasteView, SiteSettings, AuditLog,
    FlaggedPaste, FlaggedComment
)
from functools import wraps

# Create a blueprint for admin routes
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin_user():
            flash('You do not have permission to access the admin area.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Admin dashboard
@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    # Get stats for the admin dashboard
    total_users = User.query.count()
    total_pastes = Paste.query.count()
    total_comments = Comment.query.count()
    
    # Get flagged content stats
    pending_flagged_pastes = FlaggedPaste.get_pending_count()
    pending_flagged_comments = FlaggedComment.get_pending_count()
    
    # Get recent site activity
    recent_pastes = Paste.query.order_by(Paste.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
    
    # Get recent admin activity
    recent_admin_actions = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_pastes=total_pastes,
        total_comments=total_comments,
        pending_flagged_pastes=pending_flagged_pastes,
        pending_flagged_comments=pending_flagged_comments,
        recent_pastes=recent_pastes,
        recent_users=recent_users,
        recent_comments=recent_comments,
        recent_admin_actions=recent_admin_actions
    )

# List of flagged pastes
@admin_bp.route('/flags/pastes')
@login_required
@admin_required
def flagged_pastes():
    status = request.args.get('status', 'pending')
    flagged = FlaggedPaste.query.filter_by(status=status)
    
    if status == 'pending':
        flagged = flagged.order_by(FlaggedPaste.created_at.asc())
    else:
        flagged = flagged.order_by(FlaggedPaste.reviewed_at.desc())
    
    flagged = flagged.all()
    
    return render_template(
        'admin/flagged_pastes.html',
        flagged_pastes=flagged,
        status=status
    )

# Review a specific flagged paste
@admin_bp.route('/flags/pastes/<int:flag_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def review_flagged_paste(flag_id):
    flag = FlaggedPaste.query.get_or_404(flag_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Update the flag status
        if action in ['approve', 'reject']:
            flag.status = 'approved' if action == 'approve' else 'rejected'
            flag.reviewed_at = datetime.utcnow()
            flag.reviewed_by_id = current_user.id
            
            # If approved, take additional actions against the paste
            if action == 'approve':
                # Log the admin action
                AuditLog.log(
                    admin_id=current_user.id,
                    action='flag_paste_approved',
                    entity_type='paste',
                    entity_id=flag.paste_id,
                    details=f"Flag ID: {flag.id}, Reason: {flag.reason}",
                    ip_address=request.remote_addr
                )
                
                # Decide what to do with the paste based on the flag reason
                if request.form.get('delete_paste'):
                    # Delete the paste
                    db.session.delete(flag.paste)
                    flash('The flagged paste has been deleted.', 'success')
                    
                    # Log the deletion
                    AuditLog.log(
                        admin_id=current_user.id,
                        action='delete_paste',
                        entity_type='paste',
                        entity_id=flag.paste_id,
                        details=f"Deleted due to flag: {flag.reason}",
                        ip_address=request.remote_addr
                    )
            else:
                # Rejected flag
                AuditLog.log(
                    admin_id=current_user.id,
                    action='flag_paste_rejected',
                    entity_type='paste',
                    entity_id=flag.paste_id,
                    details=f"Flag ID: {flag.id}, Reason: {flag.reason}",
                    ip_address=request.remote_addr
                )
                flash('The flag has been marked as rejected.', 'info')
            
            db.session.commit()
            return redirect(url_for('admin.flagged_pastes'))
    
    return render_template(
        'admin/review_flagged_paste.html',
        flag=flag
    )

# List of flagged comments
@admin_bp.route('/flags/comments')
@login_required
@admin_required
def flagged_comments():
    status = request.args.get('status', 'pending')
    flagged = FlaggedComment.query.filter_by(status=status)
    
    if status == 'pending':
        flagged = flagged.order_by(FlaggedComment.created_at.asc())
    else:
        flagged = flagged.order_by(FlaggedComment.reviewed_at.desc())
    
    flagged = flagged.all()
    
    return render_template(
        'admin/flagged_comments.html',
        flagged_comments=flagged,
        status=status
    )

# Review a specific flagged comment
@admin_bp.route('/flags/comments/<int:flag_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def review_flagged_comment(flag_id):
    flag = FlaggedComment.query.get_or_404(flag_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Update the flag status
        if action in ['approve', 'reject']:
            flag.status = 'approved' if action == 'approve' else 'rejected'
            flag.reviewed_at = datetime.utcnow()
            flag.reviewed_by_id = current_user.id
            
            # If approved, take additional actions against the comment
            if action == 'approve':
                # Log the admin action
                AuditLog.log(
                    admin_id=current_user.id,
                    action='flag_comment_approved',
                    entity_type='comment',
                    entity_id=flag.comment_id,
                    details=f"Flag ID: {flag.id}, Reason: {flag.reason}",
                    ip_address=request.remote_addr
                )
                
                # Decide what to do with the comment based on the flag reason
                if request.form.get('delete_comment'):
                    # Delete the comment
                    db.session.delete(flag.comment)
                    flash('The flagged comment has been deleted.', 'success')
                    
                    # Log the deletion
                    AuditLog.log(
                        admin_id=current_user.id,
                        action='delete_comment',
                        entity_type='comment',
                        entity_id=flag.comment_id,
                        details=f"Deleted due to flag: {flag.reason}",
                        ip_address=request.remote_addr
                    )
            else:
                # Rejected flag
                AuditLog.log(
                    admin_id=current_user.id,
                    action='flag_comment_rejected',
                    entity_type='comment',
                    entity_id=flag.comment_id,
                    details=f"Flag ID: {flag.id}, Reason: {flag.reason}",
                    ip_address=request.remote_addr
                )
                flash('The flag has been marked as rejected.', 'info')
            
            db.session.commit()
            return redirect(url_for('admin.flagged_comments'))
    
    return render_template(
        'admin/review_flagged_comment.html',
        flag=flag
    )

# User management
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '')
    
    # Base query
    users_query = User.query
    
    # Apply search filter if provided
    if query:
        users_query = users_query.filter(
            or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        )
    
    # Paginate the results
    users = users_query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template(
        'admin/users.html',
        users=users,
        query=query
    )

# User detail and edit
@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'toggle_admin':
            # Toggle admin status
            user.is_admin = not user.is_admin
            db.session.commit()
            
            AuditLog.log(
                admin_id=current_user.id,
                action=f"{'add' if user.is_admin else 'remove'}_admin_role",
                entity_type='user',
                entity_id=user.id,
                details=f"Changed admin status to {user.is_admin}",
                ip_address=request.remote_addr
            )
            
            flash(f"Admin status for {user.username} has been {'granted' if user.is_admin else 'revoked'}.", 'success')
            return redirect(url_for('admin.user_detail', user_id=user.id))
            
        elif action == 'toggle_premium':
            # Toggle premium status
            user.is_premium = not user.is_premium
            db.session.commit()
            
            AuditLog.log(
                admin_id=current_user.id,
                action=f"{'add' if user.is_premium else 'remove'}_premium_status",
                entity_type='user',
                entity_id=user.id,
                details=f"Changed premium status to {user.is_premium}",
                ip_address=request.remote_addr
            )
            
            flash(f"Premium status for {user.username} has been {'granted' if user.is_premium else 'revoked'}.", 'success')
            return redirect(url_for('admin.user_detail', user_id=user.id))
            
        elif action == 'unlock_account':
            # Unlock a locked account
            user.account_locked_until = None
            user.failed_login_attempts = 0
            user.failed_reset_attempts = 0
            db.session.commit()
            
            AuditLog.log(
                admin_id=current_user.id,
                action="unlock_account",
                entity_type='user',
                entity_id=user.id,
                details="Manually unlocked account",
                ip_address=request.remote_addr
            )
            
            flash(f"Account for {user.username} has been unlocked.", 'success')
            return redirect(url_for('admin.user_detail', user_id=user.id))
    
    # Get user statistics
    total_pastes = Paste.query.filter_by(user_id=user.id).count()
    total_comments = Comment.query.filter_by(user_id=user.id).count()
    recent_pastes = Paste.query.filter_by(user_id=user.id).order_by(Paste.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/user_detail.html',
        user=user,
        total_pastes=total_pastes,
        total_comments=total_comments,
        recent_pastes=recent_pastes
    )

# Site settings
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        # Process form submission to update settings
        for key in request.form:
            if key.startswith('setting_'):
                setting_key = key[8:]  # Remove 'setting_' prefix
                value = request.form.get(key)
                
                # Determine value type
                value_type = 'string'
                if value.lower() in ['true', 'false', 'yes', 'no', '0', '1']:
                    value_type = 'boolean'
                elif value.isdigit():
                    value_type = 'integer'
                
                # Update or create the setting
                SiteSettings.set(
                    key=setting_key,
                    value=value,
                    value_type=value_type,
                    updated_by_id=current_user.id
                )
        
        flash('Site settings have been updated.', 'success')
        return redirect(url_for('admin.settings'))
    
    # Get all current settings
    settings_query = SiteSettings.query.all()
    
    # If no settings exist, create default ones
    if not settings_query:
        defaults = [
            {
                'key': 'site_name',
                'value': 'FlaskBin',
                'description': 'The name of the site displayed in the header and title'
            },
            {
                'key': 'allow_guest_pastes',
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Whether to allow guest users to create pastes'
            },
            {
                'key': 'max_paste_size',
                'value': '500000',
                'value_type': 'integer',
                'description': 'Maximum paste size in bytes'
            },
            {
                'key': 'enable_rate_limiting',
                'value': 'true',
                'value_type': 'boolean',
                'description': 'Enable rate limiting for API endpoints'
            },
            {
                'key': 'maintenance_mode',
                'value': 'false',
                'value_type': 'boolean',
                'description': 'Put the site in maintenance mode (only admins can access)'
            }
        ]
        
        for default in defaults:
            SiteSettings.set(
                key=default['key'],
                value=default['value'],
                value_type=default.get('value_type', 'string'),
                description=default.get('description'),
                updated_by_id=current_user.id
            )
        
        # Reload settings
        settings_query = SiteSettings.query.all()
    
    return render_template(
        'admin/settings.html',
        settings=settings_query
    )

# Audit log
@admin_bp.route('/audit-log')
@login_required
@admin_required
def audit_log():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    
    # Base query
    log_query = AuditLog.query
    
    # Apply action filter if provided
    if action_filter:
        log_query = log_query.filter(AuditLog.action == action_filter)
    
    # Paginate the results
    logs = log_query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get unique actions for filter dropdown
    unique_actions = db.session.query(AuditLog.action).distinct().all()
    
    return render_template(
        'admin/audit_log.html',
        logs=logs,
        unique_actions=[action[0] for action in unique_actions],
        action_filter=action_filter
    )

# API endpoint to manually flag a paste
@admin_bp.route('/api/flag-paste', methods=['POST'])
@login_required
@admin_required
def api_flag_paste():
    paste_id = request.form.get('paste_id')
    reason = request.form.get('reason', 'admin_flagged')
    details = request.form.get('details', 'Manually flagged by admin')
    
    if not paste_id:
        return jsonify({'success': False, 'message': 'Paste ID is required'}), 400
    
    paste = Paste.query.get(paste_id)
    if not paste:
        return jsonify({'success': False, 'message': 'Paste not found'}), 404
    
    # Check if already flagged
    existing_flag = FlaggedPaste.query.filter_by(paste_id=paste_id, status='pending').first()
    if existing_flag:
        return jsonify({'success': False, 'message': 'This paste is already flagged'}), 400
    
    # Create the flag
    flag = FlaggedPaste(
        paste_id=paste_id,
        reporter_id=current_user.id,
        reason=reason,
        details=details
    )
    
    db.session.add(flag)
    db.session.commit()
    
    # Log the action
    AuditLog.log(
        admin_id=current_user.id,
        action="manually_flag_paste",
        entity_type='paste',
        entity_id=paste_id,
        details=f"Reason: {reason}, Details: {details}",
        ip_address=request.remote_addr
    )
    
    return jsonify({'success': True, 'message': 'Paste has been flagged for review'})

# API endpoint to manually flag a comment
@admin_bp.route('/api/flag-comment', methods=['POST'])
@login_required
@admin_required
def api_flag_comment():
    comment_id = request.form.get('comment_id')
    reason = request.form.get('reason', 'admin_flagged')
    details = request.form.get('details', 'Manually flagged by admin')
    
    if not comment_id:
        return jsonify({'success': False, 'message': 'Comment ID is required'}), 400
    
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({'success': False, 'message': 'Comment not found'}), 404
    
    # Check if already flagged
    existing_flag = FlaggedComment.query.filter_by(comment_id=comment_id, status='pending').first()
    if existing_flag:
        return jsonify({'success': False, 'message': 'This comment is already flagged'}), 400
    
    # Create the flag
    flag = FlaggedComment(
        comment_id=comment_id,
        reporter_id=current_user.id,
        reason=reason,
        details=details
    )
    
    db.session.add(flag)
    db.session.commit()
    
    # Log the action
    AuditLog.log(
        admin_id=current_user.id,
        action="manually_flag_comment",
        entity_type='comment',
        entity_id=comment_id,
        details=f"Reason: {reason}, Details: {details}",
        ip_address=request.remote_addr
    )
    
    return jsonify({'success': True, 'message': 'Comment has been flagged for review'})