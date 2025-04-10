from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user

from app import db
from models import Notification

# Create a blueprint for notification routes
notification_bp = Blueprint('notification', __name__)


@notification_bp.route('/notifications')
@login_required
def list_notifications():
    """View all notifications for the current user"""
    # Get notifications for the current user, ordered by creation time (newest first)
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).all()
    
    # Get unread notification count
    unread_count = Notification.get_unread_count(current_user.id)
    
    return render_template(
        'notification/list.html',
        notifications=notifications,
        unread_count=unread_count
    )


@notification_bp.route('/notifications/unread')
@login_required
def unread_notifications():
    """View unread notifications for the current user"""
    # Get unread notifications for the current user, ordered by creation time (newest first)
    notifications = (current_user.notifications
                     .filter_by(read=False)
                     .order_by(Notification.created_at.desc())
                     .all())
    
    # Get unread notification count
    unread_count = len(notifications)
    
    return render_template(
        'notification/list.html',
        notifications=notifications,
        unread_count=unread_count,
        unread_only=True
    )


@notification_bp.route('/notifications/mark_read/<int:notification_id>')
@login_required
def mark_as_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Check if the notification belongs to the current user
    if notification.user_id != current_user.id:
        flash('You do not have permission to access this notification.', 'danger')
        return redirect(url_for('notification.list_notifications'))
    
    # Mark the notification as read
    Notification.mark_as_read(notification_id)
    
    # Check if there's a redirect URL in the request
    redirect_url = request.args.get('redirect')
    
    if redirect_url and redirect_url.startswith('/'):
        # Only allow internal redirects
        return redirect(redirect_url)
    
    # Default redirect to the notification's target if it has a paste or comment
    if notification.paste_id:
        return redirect(url_for('paste.view', paste_id=notification.paste_id))
    elif notification.comment_id and notification.paste_id:
        return redirect(url_for('paste.view', paste_id=notification.paste_id, _anchor=f'comment-{notification.comment_id}'))
    
    # Otherwise redirect back to notifications list
    return redirect(url_for('notification.list_notifications'))


@notification_bp.route('/notifications/mark_all_read')
@login_required
def mark_all_as_read():
    """Mark all notifications as read for the current user"""
    Notification.mark_all_as_read(current_user.id)
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notification.list_notifications'))


@notification_bp.route('/notifications/delete/<int:notification_id>')
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    notification = Notification.query.get_or_404(notification_id)
    
    # Check if the notification belongs to the current user
    if notification.user_id != current_user.id:
        flash('You do not have permission to delete this notification.', 'danger')
        return redirect(url_for('notification.list_notifications'))
    
    # Delete the notification
    db.session.delete(notification)
    db.session.commit()
    
    flash('Notification deleted.', 'success')
    return redirect(url_for('notification.list_notifications'))


@notification_bp.route('/notifications/count')
@login_required
def notification_count():
    """Get the number of unread notifications for the current user (JSON response)"""
    count = Notification.get_unread_count(current_user.id)
    return jsonify({'count': count})