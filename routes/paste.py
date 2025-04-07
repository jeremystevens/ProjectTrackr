from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response
from flask_login import current_user, login_required
from sqlalchemy import or_, and_
from datetime import datetime
from app import db
from models import Paste, User
from forms import PasteForm
from utils import generate_short_id, highlight_code, sanitize_html

paste_bp = Blueprint('paste', __name__)

@paste_bp.route('/')
def index():
    form = PasteForm()
    recent_pastes = Paste.get_recent_public_pastes(10)
    return render_template('index.html', form=form, recent_pastes=recent_pastes)

@paste_bp.route('/create', methods=['POST'])
def create():
    form = PasteForm()
    if form.validate_on_submit():
        # Generate a unique short ID
        while True:
            short_id = generate_short_id()
            if not Paste.query.filter_by(short_id=short_id).first():
                break
        
        # Create the paste
        paste = Paste(
            title=form.title.data or 'Untitled',
            content=form.content.data,
            syntax=form.syntax.data,
            visibility=form.visibility.data,
            expires_at=Paste.set_expiration(form.expiration.data),
            short_id=short_id
        )
        
        # Set user if logged in
        if current_user.is_authenticated:
            paste.user_id = current_user.id
            current_user.total_pastes += 1
        
        # Calculate paste size
        paste.calculate_size()
        
        db.session.add(paste)
        db.session.commit()
        
        flash('Paste created successfully!', 'success')
        return redirect(url_for('paste.view', short_id=paste.short_id))
    
    # If form validation fails
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('paste.index'))

@paste_bp.route('/<short_id>')
def view(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if paste is private and user is not the author
    if paste.visibility == 'private' and (not current_user.is_authenticated or current_user.id != paste.user_id):
        abort(403)
    
    # Update view count
    paste.update_view_count()
    
    # Syntax highlighting
    highlighted_code, css = highlight_code(paste.content, paste.syntax)
    
    return render_template('paste/view.html', paste=paste, 
                          highlighted_code=highlighted_code, css=css)

@paste_bp.route('/raw/<short_id>')
def raw(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if paste is private and user is not the author
    if paste.visibility == 'private' and (not current_user.is_authenticated or current_user.id != paste.user_id):
        abort(403)
    
    # Return plain text
    return Response(paste.content, mimetype='text/plain')

@paste_bp.route('/download/<short_id>')
def download(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if paste is private and user is not the author
    if paste.visibility == 'private' and (not current_user.is_authenticated or current_user.id != paste.user_id):
        abort(403)
    
    # Create download response
    filename = f"{paste.title.replace(' ', '_')}.txt"
    response = Response(paste.content, mimetype='text/plain')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@paste_bp.route('/embed/<short_id>')
def embed(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if paste is private and user is not the author
    if paste.visibility == 'private' and (not current_user.is_authenticated or current_user.id != paste.user_id):
        abort(403)
    
    # Syntax highlighting for embedding
    highlighted_code, css = highlight_code(paste.content, paste.syntax)
    
    return render_template('paste/embed.html', paste=paste, 
                          highlighted_code=highlighted_code, css=css)

@paste_bp.route('/edit/<short_id>', methods=['GET', 'POST'])
@login_required
def edit(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if user has permission to edit
    if current_user.id != paste.user_id:
        abort(403)
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired and cannot be edited.', 'warning')
        return redirect(url_for('paste.index'))
    
    form = PasteForm()
    
    if request.method == 'GET':
        form.title.data = paste.title
        form.content.data = paste.content
        form.syntax.data = paste.syntax
        form.visibility.data = paste.visibility
        # We don't pre-fill expiration as it's relative
        
    if form.validate_on_submit():
        paste.title = form.title.data
        paste.content = form.content.data
        paste.syntax = form.syntax.data
        paste.visibility = form.visibility.data
        
        # Only update expiration if it's changed
        if form.expiration.data != '0' or paste.expires_at is None:
            paste.expires_at = Paste.set_expiration(form.expiration.data)
        
        # Recalculate paste size
        paste.calculate_size()
        
        db.session.commit()
        flash('Paste updated successfully!', 'success')
        return redirect(url_for('paste.view', short_id=paste.short_id))
    
    return render_template('paste/edit.html', form=form, paste=paste)

@paste_bp.route('/delete/<short_id>', methods=['POST'])
@login_required
def delete(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if user has permission to delete
    if current_user.id != paste.user_id:
        abort(403)
    
    current_user.total_pastes -= 1
    db.session.delete(paste)
    db.session.commit()
    
    flash('Paste deleted successfully.', 'success')
    return redirect(url_for('user.profile', username=current_user.username))

@paste_bp.route('/print/<short_id>')
def print_view(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if paste is private and user is not the author
    if paste.visibility == 'private' and (not current_user.is_authenticated or current_user.id != paste.user_id):
        abort(403)
    
    # Syntax highlighting
    highlighted_code, css = highlight_code(paste.content, paste.syntax)
    
    return render_template('paste/print.html', paste=paste, 
                          highlighted_code=highlighted_code, css=css)

@paste_bp.route('/archive')
def archive():
    page = request.args.get('page', 1, type=int)
    pastes = Paste.query.filter(
        (Paste.visibility == 'public') & 
        ((Paste.expires_at.is_(None)) | (Paste.expires_at > datetime.utcnow()))
    ).order_by(Paste.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('archive/index.html', pastes=pastes)
