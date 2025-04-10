from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import current_user, login_required
from datetime import datetime
from app import db
from models import Comment, Paste, User
from forms import CommentForm, CommentEditForm
from utils import sanitize_html

comment_bp = Blueprint('comment', __name__)

@comment_bp.route('/paste/<short_id>/comment', methods=['POST'])
@login_required
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
        
        flash('Your comment has been added.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('paste.view', short_id=short_id))

@comment_bp.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
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