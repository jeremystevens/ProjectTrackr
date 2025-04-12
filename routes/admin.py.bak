from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import User, Paste, FlaggedPaste

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin required decorator
def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/')
@admin_required
def index():
    return render_template('admin/index.html')

@admin_bp.route('/users')
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/pastes')
@admin_required
def pastes():
    pastes = Paste.query.all()
    return render_template('admin/pastes.html', pastes=pastes)

@admin_bp.route('/flags')
@admin_required
def flags():
    flagged_pastes = FlaggedPaste.query.filter_by(resolved=False).all()
    return render_template('admin/flags.html', flagged_pastes=flagged_pastes)

@admin_bp.route('/user/<int:user_id>/toggle_admin')
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent self-demotion
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    flash(f"Admin status for {user.username} {'enabled' if user.is_admin else 'disabled'} successfully!", 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/user/<int:user_id>/toggle_ban')
@admin_required
def toggle_ban(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent self-ban
    if user.id == current_user.id:
        flash('You cannot ban yourself.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_banned = not user.is_banned
    
    if user.is_banned:
        user.ban_reason = request.args.get('reason', 'Violation of terms of service')
    else:
        user.ban_reason = None
    
    db.session.commit()
    
    flash(f"User {user.username} {'banned' if user.is_banned else 'unbanned'} successfully!", 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/paste/<int:paste_id>/delete')
@admin_required
def delete_paste(paste_id):
    paste = Paste.query.get_or_404(paste_id)
    
    db.session.delete(paste)
    db.session.commit()
    
    flash('Paste deleted successfully!', 'success')
    return redirect(url_for('admin.pastes'))

@admin_bp.route('/flag/<int:flag_id>/resolve')
@admin_required
def resolve_flag(flag_id):
    flag = FlaggedPaste.query.get_or_404(flag_id)
    
    flag.resolved = True
    flag.resolved_by = current_user.id
    flag.resolved_at = datetime.utcnow()
    flag.resolution_note = request.args.get('note', 'Resolved by admin')
    
    db.session.commit()
    
    flash('Flag resolved successfully!', 'success')
    return redirect(url_for('admin.flags'))
