from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import current_user, login_required
from datetime import datetime
from app import db, limiter
from models import Comment, Paste, User, Notification, FlaggedComment
from forms import CommentForm, CommentEditForm, FlagContentForm
from utils import sanitize_html, check_shadowban

comment_bp = Blueprint('comment', __name__)

@comment_bp.route('/paste/<short_id>/comment', methods=['POST'])
@login_required
@limiter.limit("30 per hour")
@check_shadowban
def add_comment(short_id):
    """Add a comment to a paste"""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if comments are enabled for this paste
    if not paste.comments_enabled:
        flash('Comments are disabled for this paste.', 'warning')
        return redirect(url_for('paste.view', short_id=short_id))
    
    form = CommentForm()
    if form.validate_on_submit():
        # Sanitize content to prevent XSS
        sanitized_content = sanitize_html(form.content.data)
        
        comment = Comment(
            content=sanitized_content,
            user_id=current_user.id,
            paste_id=paste.id,
            parent_id=form.parent_id.data if form.parent_id.data else None
        )
        
        db.session.add(comment)
        db.session.commit()
        
        # Create notification for the paste owner (if not the commenter)
        if paste.user_id and paste.user_id != current_user.id:
            paste_title = paste.title if paste.title else "Untitled"
            notification_message = f"commented on your paste: '{paste_title}'"
            Notification.create_notification(
                user_id=paste.user_id,
                type='comment',
                message=notification_message,
                sender_id=current_user.id,
                paste_id=paste.id,
                comment_id=comment.id
            )
            
        # If this is a reply, notify the parent comment author
        if form.parent_id.data:
            parent_comment = Comment.query.get(form.parent_id.data)
            if parent_comment and parent_comment.user_id != current_user.id:
                notification_message = f"replied to your comment on '{paste.title}'"
                Notification.create_notification(
                    user_id=parent_comment.user_id,
                    type='comment',
                    message=notification_message,
                    sender_id=current_user.id,
                    paste_id=paste.id,
                    comment_id=comment.id
                )
        
        flash('Your comment has been added.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('paste.view', short_id=short_id))

@comment_bp.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per hour")
@check_shadowban
def edit_comment(comment_id):
    """Edit an existing comment"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user has permission to edit this comment
    if comment.user_id != current_user.id:
        abort(403)
    
    # Get the paste to check if it's expired
    paste = Paste.query.get_or_404(comment.paste_id)
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    form = CommentEditForm()
    
    if request.method == 'GET':
        form.content.data = comment.content
    
    if form.validate_on_submit():
        # Sanitize content to prevent XSS
        sanitized_content = sanitize_html(form.content.data)
        
        comment.content = sanitized_content
        comment.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Your comment has been updated.', 'success')
        return redirect(url_for('paste.view', short_id=paste.short_id))
    
    return render_template('comment/edit.html', form=form, comment=comment, paste=paste)

@comment_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
@limiter.limit("15 per hour")
def delete_comment(comment_id):
    """Delete a comment"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user has permission to delete this comment
    if comment.user_id != current_user.id:
        abort(403)
    
    # Get the paste to redirect back
    paste = Paste.query.get_or_404(comment.paste_id)
    short_id = paste.short_id
    
    try:
        db.session.delete(comment)
        db.session.commit()
        flash('Your comment has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete comment. Please try again.', 'danger')
    
    return redirect(url_for('paste.view', short_id=short_id))

@comment_bp.route('/comment/<int:comment_id>/reply', methods=['GET'])
@login_required
def reply_form(comment_id):
    """Show form for replying to a comment"""
    parent_comment = Comment.query.get_or_404(comment_id)
    paste = Paste.query.get_or_404(parent_comment.paste_id)
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if comments are enabled for this paste
    if not paste.comments_enabled:
        flash('Comments are disabled for this paste.', 'warning')
        return redirect(url_for('paste.view', short_id=paste.short_id))
    
    form = CommentForm()
    form.parent_id.data = comment_id
    
    return render_template('comment/reply.html', form=form, parent_comment=parent_comment, paste=paste)


@comment_bp.route('/comment/<int:comment_id>/flag', methods=['GET', 'POST'])
@login_required
def flag_comment(comment_id):
    """Route for flagging a comment as inappropriate content"""
    comment = Comment.query.get_or_404(comment_id)
    paste = Paste.query.get_or_404(comment.paste_id)
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if the user already flagged this comment
    existing_flag = FlaggedComment.query.filter_by(
        comment_id=comment.id, 
        reporter_id=current_user.id,
        status='pending'
    ).first()
    
    if existing_flag:
        flash('You have already flagged this comment. A moderator will review it soon.', 'info')
        return redirect(url_for('paste.view', short_id=paste.short_id))
    
    form = FlagContentForm()
    
    if form.validate_on_submit():
        flag = FlaggedComment(
            comment_id=comment.id,
            reporter_id=current_user.id,
            reason=form.reason.data,
            details=form.details.data
        )
        
        db.session.add(flag)
        db.session.commit()
        
        flash('Thank you for flagging this comment. A moderator will review it soon.', 'success')
        return redirect(url_for('paste.view', short_id=paste.short_id))
    
    return render_template(
        'comment/flag_comment.html',
        comment=comment,
        paste=paste,
        form=form
    )