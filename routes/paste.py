from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response, session, after_this_request
from flask_login import current_user, login_required
from sqlalchemy import or_, and_
from datetime import datetime
from app import db, app, limiter
from models import Paste, User, PasteView, Comment, PasteRevision, Notification, PasteCollection, FlaggedPaste, FlaggedComment
from forms import PasteForm, CommentForm, FlagContentForm
from utils import generate_short_id, highlight_code, sanitize_html, check_shadowban

paste_bp = Blueprint('paste', __name__)

@paste_bp.route('/')
def index():
    form = PasteForm(current_user=current_user)
    recent_pastes = Paste.get_recent_public_pastes(10)
    return render_template('index.html', form=form, recent_pastes=recent_pastes)

@paste_bp.route('/create', methods=['POST'])
@limiter.limit("20 per hour")
@check_shadowban
def create():
    # Pass current_user to populate collection choices
    form = PasteForm(current_user=current_user)
    if form.validate_on_submit():
        # Generate a unique short ID
        while True:
            short_id = generate_short_id()
            if not Paste.query.filter_by(short_id=short_id).first():
                break
        
        # Debug the expiration selection
        import logging
        logging.debug(f"Expiration option selected: {form.expiration.data}")
        
        # Special case for 10-minute expiration - just store the option number for later use
        expiration_option = int(form.expiration.data)
        # We'll handle the special case in the get_expiration_text function and our templates
        
        # Create the paste
        expiry_time = Paste.set_expiration(expiration_option)
        logging.debug(f"Calculated expiry time: {expiry_time}")
        
        comments_enabled = True  # Default to True
        if hasattr(form, 'comments_enabled') and form.comments_enabled is not None:
            comments_enabled = form.comments_enabled.data
            
        burn_after_read = False  # Default to False
        if hasattr(form, 'burn_after_read') and form.burn_after_read is not None:
            burn_after_read = form.burn_after_read.data
            
        # Get template content if a template was selected
        content = form.content.data
        syntax = form.syntax.data
        if form.template.data and form.template.data > 0:
            # Template was selected, load it
            from models import PasteTemplate
            template = PasteTemplate.query.get(form.template.data)
            if template:
                # Only use template content if user hasn't entered any content
                if not content.strip():
                    content = template.content
                    syntax = template.syntax
                
                # Increment template usage count
                template.increment_usage()
        
        # Test if we're reaching this code block
        import logging
        logging.debug(f"Syntax before detection check: {syntax}")
        
        # If syntax is set to 'text' (the default), try to auto-detect the language
        if syntax == 'text' and content.strip():
            from utils import detect_language
            from flask import current_app
            
            # Debug the content that we're attempting to detect
            sample = content[:100] + ("..." if len(content) > 100 else "")
            logging.debug(f"Content sample for detection: {sample}")
            
            detected_syntax = detect_language(content)
            current_app.logger.info(f"Auto-detected language: {detected_syntax}")
            logging.debug(f"Auto-detection returned: {detected_syntax}")
            
            syntax = detected_syntax
                
        paste = Paste(
            title=form.title.data or 'Untitled',
            content=content,
            syntax=syntax,
            visibility=form.visibility.data,
            expires_at=expiry_time,
            short_id=short_id,
            comments_enabled=comments_enabled,
            burn_after_read=burn_after_read
        )
        
        # Set user if logged in and not posting as guest
        post_as_guest = False
        if hasattr(form, 'post_as_guest') and form.post_as_guest is not None:
            post_as_guest = form.post_as_guest.data
            
        if current_user.is_authenticated and not post_as_guest:
            paste.user_id = current_user.id
            current_user.total_pastes += 1
            
            # Add to collection if selected and user is authenticated
            if hasattr(form, 'collection_id') and form.collection_id.data and form.collection_id.data > 0:
                # Verify the collection exists and belongs to the user
                collection = PasteCollection.query.get(form.collection_id.data)
                if collection and collection.user_id == current_user.id:
                    paste.collection_id = collection.id
                    logging.debug(f"Added paste to collection {collection.name} (ID: {collection.id})")
        
        # Calculate paste size
        paste.calculate_size()
        
        # Handle encryption if enabled
        if hasattr(form, 'enable_encryption') and form.enable_encryption.data:
            encryption_type = form.encryption_type.data
            encryption_password = None
            
            # Debug information
            import logging
            logging.debug(f"Encryption enabled with type: {encryption_type}")
            
            # For password-protected encryption
            if encryption_type == 'fernet-password' and form.encryption_password.data:
                encryption_password = form.encryption_password.data
                logging.debug("Using password-based encryption")
            else:
                logging.debug("Using random key encryption")
                    
            # Store the encryption type on the paste
            paste.encryption_method = encryption_type
                    
            # Encrypt the paste content
            if paste.encrypt(encryption_password):
                current_app.logger.info(f"Paste encrypted successfully with method: {encryption_type}")
                # Log extra confirmation
                logging.debug(f"Encryption successful. Is encrypted: {paste.is_encrypted}, Method: {paste.encryption_method}")
            else:
                current_app.logger.error("Failed to encrypt paste")
                flash('Failed to encrypt paste.', 'danger')
        
        db.session.add(paste)
        db.session.commit()
        
        flash('Paste created successfully!', 'success')
        return redirect(url_for('paste.view', short_id=paste.short_id))
    
    # If form validation fails
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('paste.index'))

@paste_bp.route('/<short_id>', methods=['GET', 'POST'])
def view(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if paste is private and user is not the author
    if paste.visibility == 'private' and (not current_user.is_authenticated or current_user.id != paste.user_id):
        abort(403)
    
    # Handle burn after read pastes
    is_burn_after_read = paste.burn_after_read
    is_paste_owner = current_user.is_authenticated and current_user.id == paste.user_id
    
    # Get or create a unique viewer ID for tracking view counts
    viewer_ip = request.remote_addr
    viewer_id = PasteView.get_or_create_viewer_id(session, viewer_ip)
    
    # Update view count only for unique viewers
    is_new_view = paste.update_view_count(viewer_id)
    
    # Handle encrypted content
    content = paste.content
    password_form = None
    decryption_error = None
    is_encrypted = paste.is_encrypted
    
    if is_encrypted:
        # Create a password form for encrypted pastes
        from forms import PastePasswordForm
        password_form = PastePasswordForm()
        
        # Check if this is a password submission
        if request.method == 'POST' and password_form.validate_on_submit():
            password = password_form.password.data
            decrypted_content = paste.decrypt(password)
            
            if decrypted_content:
                # Successfully decrypted
                content = decrypted_content
                # Store in session that this user has the correct password for this paste
                session_decrypted = session.get('decrypted_pastes', {})
                session_decrypted[paste.short_id] = True
                session['decrypted_pastes'] = session_decrypted
                flash('Paste decrypted successfully!', 'success')
            else:
                # Failed to decrypt
                decryption_error = "Invalid password. Please try again."
                flash('Failed to decrypt paste. Invalid password.', 'danger')
                # Show password form again
                return render_template('paste/password.html', paste=paste, form=password_form)
                
        # Check if we've already decrypted this paste in this session
        elif session.get('decrypted_pastes', {}).get(paste.short_id):
            # Paste was already decrypted in this session, decrypt again
            decrypted_content = paste.get_content()
            if decrypted_content:
                content = decrypted_content
            else:
                # This shouldn't normally happen, but just in case
                if 'decrypted_pastes' in session and paste.short_id in session['decrypted_pastes']:
                    session['decrypted_pastes'].pop(paste.short_id, None)
                decryption_error = "Session error. Please re-enter the password."
                # Show password form again
                return render_template('paste/password.html', paste=paste, form=password_form)
                
        # If password protected but no password provided, show password form
        elif paste.password_protected and request.method == 'GET':
            return render_template('paste/password.html', paste=paste, form=password_form)
        
        # For random-key encrypted pastes that aren't password protected
        elif not paste.password_protected:
            # Try to decrypt with default settings
            decrypted_content = paste.get_content()
            if decrypted_content:
                content = decrypted_content
            
    # Syntax highlighting (now using potentially decrypted content)
    highlighted_code, css = highlight_code(content, paste.syntax)
    
    # Initialize comment form if comments are enabled and user is logged in
    comment_form = None
    if paste.comments_enabled and current_user.is_authenticated:
        comment_form = CommentForm()
    
    # Get all comments for this paste
    comments = Comment.query.filter_by(paste_id=paste.id, parent_id=None).order_by(Comment.created_at.asc()).all()
    
    # Create a minimal form instance for CSRF token (for delete button)
    from flask_wtf import FlaskForm
    form = FlaskForm()
    
    # If this is a burn after read paste and this is a new view (not the owner viewing it),
    # mark it for deletion after the response is sent
    burn_notice = None
    
    # Add debug logging
    import logging
    logging.debug(f"Burn after read: {is_burn_after_read}")
    logging.debug(f"Is new view: {is_new_view}")
    logging.debug(f"Is paste owner: {is_paste_owner}")
    
    if is_burn_after_read:
        logging.debug(f"This is a burn-after-read paste")
        # Add burn notice even for paste owners, but don't delete
        burn_notice = "This paste was set to burn after reading. It will be permanently deleted after someone else views it."
        
        # Only delete if it's not the owner and this is a new view
        if is_new_view and not is_paste_owner:
            logging.debug(f"Will delete paste {short_id} after this request")
            burn_notice = "This paste was set to burn after reading. It will be permanently deleted after this view."
            
            # We'll delete the paste after showing it to the user
            @after_this_request
            def delete_burned_paste(response):
                try:
                    logging.debug(f"Executing burn after read deletion for paste {short_id}")
                    # Delete associated views first
                    view_count = PasteView.query.filter_by(paste_id=paste.id).delete()
                    logging.debug(f"Deleted {view_count} views for paste {short_id}")
                    
                    # Delete the paste
                    db.session.delete(paste)
                    db.session.commit()
                    logging.debug(f"Successfully deleted burn after read paste {short_id}")
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Error deleting burn after read paste: {e}")
                return response
    
    return render_template('paste/view.html', paste=paste, 
                          highlighted_code=highlighted_code, css=css, form=form,
                          comment_form=comment_form, comments=comments,
                          burn_notice=burn_notice)

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
    
    # Handle burn after read pastes
    is_burn_after_read = paste.burn_after_read
    is_paste_owner = current_user.is_authenticated and current_user.id == paste.user_id
    
    # Get or create a unique viewer ID for tracking view counts
    viewer_ip = request.remote_addr
    viewer_id = PasteView.get_or_create_viewer_id(session, viewer_ip)
    
    # Update view count only for unique viewers
    is_new_view = paste.update_view_count(viewer_id)
    
    # Handle encrypted content
    content = paste.content
    if paste.is_encrypted:
        # If password protected and not already decrypted in this session, redirect to the standard view
        if paste.password_protected and not session.get('decrypted_pastes', {}).get(paste.short_id):
            flash('This paste is password protected. Please enter the password to view.', 'warning')
            return redirect(url_for('paste.view', short_id=paste.short_id))
            
        # If we've already decrypted this paste or it's not password protected
        decrypted_content = paste.get_content()
        if decrypted_content:
            content = decrypted_content
    
    # If this is a burn after read paste and this is a new view (not the owner viewing it),
    # mark it for deletion after the response is sent
    
    # Add debug logging
    import logging
    logging.debug(f"RAW: Burn after read: {is_burn_after_read}")
    logging.debug(f"RAW: Is new view: {is_new_view}")
    logging.debug(f"RAW: Is paste owner: {is_paste_owner}")
    
    if is_burn_after_read and is_new_view and not is_paste_owner:
        logging.debug(f"RAW: Will delete paste {short_id} after this request")
        
        @after_this_request
        def delete_burned_paste(response):
            try:
                logging.debug(f"RAW: Executing burn after read deletion for paste {short_id}")
                # Delete associated views first
                view_count = PasteView.query.filter_by(paste_id=paste.id).delete()
                logging.debug(f"RAW: Deleted {view_count} views for paste {short_id}")
                
                # Delete the paste
                db.session.delete(paste)
                db.session.commit()
                logging.debug(f"RAW: Successfully deleted burn after read paste {short_id}")
            except Exception as e:
                db.session.rollback()
                logging.error(f"RAW: Error deleting burn after read paste: {e}")
            return response
    
    # Return plain text
    return Response(content, mimetype='text/plain')

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
    
    # Handle burn after read pastes
    is_burn_after_read = paste.burn_after_read
    is_paste_owner = current_user.is_authenticated and current_user.id == paste.user_id
    
    # Get or create a unique viewer ID for tracking view counts
    viewer_ip = request.remote_addr
    viewer_id = PasteView.get_or_create_viewer_id(session, viewer_ip)
    
    # Update view count only for unique viewers
    is_new_view = paste.update_view_count(viewer_id)
    
    # Handle encrypted content
    content = paste.content
    if paste.is_encrypted:
        # If password protected and not already decrypted in this session, redirect to the standard view
        if paste.password_protected and not session.get('decrypted_pastes', {}).get(paste.short_id):
            flash('This paste is password protected. Please enter the password to view.', 'warning')
            return redirect(url_for('paste.view', short_id=paste.short_id))
            
        # If we've already decrypted this paste or it's not password protected
        decrypted_content = paste.get_content()
        if decrypted_content:
            content = decrypted_content
    
    # Create download response
    filename = f"{paste.title.replace(' ', '_')}.txt"
    response = Response(content, mimetype='text/plain')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    # If this is a burn after read paste and this is a new view (not the owner viewing it),
    # mark it for deletion after the response is sent
    
    # Add debug logging
    import logging
    logging.debug(f"DOWNLOAD: Burn after read: {is_burn_after_read}")
    logging.debug(f"DOWNLOAD: Is new view: {is_new_view}")
    logging.debug(f"DOWNLOAD: Is paste owner: {is_paste_owner}")
    
    if is_burn_after_read and is_new_view and not is_paste_owner:
        logging.debug(f"DOWNLOAD: Will delete paste {short_id} after this request")
        
        @after_this_request
        def delete_burned_paste(resp):
            try:
                logging.debug(f"DOWNLOAD: Executing burn after read deletion for paste {short_id}")
                # Delete associated views first
                view_count = PasteView.query.filter_by(paste_id=paste.id).delete()
                logging.debug(f"DOWNLOAD: Deleted {view_count} views for paste {short_id}")
                
                # Delete the paste
                db.session.delete(paste)
                db.session.commit()
                logging.debug(f"DOWNLOAD: Successfully deleted burn after read paste {short_id}")
            except Exception as e:
                db.session.rollback()
                logging.error(f"DOWNLOAD: Error deleting burn after read paste: {e}")
            return resp
    
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
    
    # Handle burn after read pastes
    is_burn_after_read = paste.burn_after_read
    is_paste_owner = current_user.is_authenticated and current_user.id == paste.user_id
    
    # Get or create a unique viewer ID for tracking view counts
    viewer_ip = request.remote_addr
    viewer_id = PasteView.get_or_create_viewer_id(session, viewer_ip)
    
    # Update view count only for unique viewers
    is_new_view = paste.update_view_count(viewer_id)
        
    # Handle encrypted content
    content = paste.content
    if paste.is_encrypted:
        # If password protected and not already decrypted in this session, redirect to the standard view
        if paste.password_protected and not session.get('decrypted_pastes', {}).get(paste.short_id):
            flash('This paste is password protected. Please enter the password to view.', 'warning')
            return redirect(url_for('paste.view', short_id=paste.short_id))
            
        # If we've already decrypted this paste or it's not password protected
        decrypted_content = paste.get_content()
        if decrypted_content:
            content = decrypted_content
    
    # Syntax highlighting for embedding
    highlighted_code, css = highlight_code(content, paste.syntax)
    
    # If this is a burn after read paste and this is a new view (not the owner viewing it),
    # mark it for deletion after the response is sent
    burn_notice = None
    
    # Add debug logging
    import logging
    logging.debug(f"EMBED: Burn after read: {is_burn_after_read}")
    logging.debug(f"EMBED: Is new view: {is_new_view}")
    logging.debug(f"EMBED: Is paste owner: {is_paste_owner}")
    
    if is_burn_after_read:
        logging.debug(f"EMBED: This is a burn-after-read paste")
        # Add burn notice even for paste owners, but don't delete
        burn_notice = "This paste was set to burn after reading. It will be permanently deleted after someone else views it."
        
        # Only delete if it's not the owner and this is a new view
        if is_new_view and not is_paste_owner:
            logging.debug(f"EMBED: Will delete paste {short_id} after this request")
            burn_notice = "This paste was set to burn after reading. It will be permanently deleted after this view."
            
            # We'll delete the paste after showing it to the user
            @after_this_request
            def delete_burned_paste(response):
                try:
                    logging.debug(f"EMBED: Executing burn after read deletion for paste {short_id}")
                    # Delete associated views first
                    view_count = PasteView.query.filter_by(paste_id=paste.id).delete()
                    logging.debug(f"EMBED: Deleted {view_count} views for paste {short_id}")
                    
                    # Delete the paste
                    db.session.delete(paste)
                    db.session.commit()
                    logging.debug(f"EMBED: Successfully deleted burn after read paste {short_id}")
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"EMBED: Error deleting burn after read paste: {e}")
                return response
    
    return render_template('paste/embed.html', paste=paste, 
                          highlighted_code=highlighted_code, css=css,
                          burn_notice=burn_notice)

@paste_bp.route('/edit/<short_id>', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def edit(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if user has permission to edit
    if current_user.id != paste.user_id:
        abort(403)
    
    # Check if paste has expired
    if paste.is_expired():
        flash('This paste has expired and cannot be edited.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Pass current_user to populate collection choices
    form = PasteForm(current_user=current_user)
    
    if request.method == 'GET':
        form.title.data = paste.title
        form.content.data = paste.content
        form.syntax.data = paste.syntax
        form.visibility.data = paste.visibility
        form.comments_enabled.data = paste.comments_enabled
        form.burn_after_read.data = paste.burn_after_read
        # Set collection if paste is in a collection
        if hasattr(form, 'collection_id') and paste.collection_id:
            form.collection_id.data = paste.collection_id
        # Set post_as_guest to true if this paste was posted as a guest by the current user
        if hasattr(form, 'post_as_guest') and paste.user_id is None:
            form.post_as_guest.data = True
        # We don't pre-fill expiration as it's relative
        
    if form.validate_on_submit():
        # For registered users only: save current state as a revision before updating
        if current_user.is_authenticated:
            # Get edit description if it exists, otherwise use empty string
            edit_description = ""
            if hasattr(form, 'edit_description') and form.edit_description is not None:
                edit_description = form.edit_description.data
            paste.save_revision(description=edit_description)
            
        # Handle post_as_guest option
        post_as_guest = False
        if hasattr(form, 'post_as_guest') and form.post_as_guest is not None:
            post_as_guest = form.post_as_guest.data
            
        # Update user_id based on post_as_guest preference
        if post_as_guest:
            paste.user_id = None
        elif current_user.is_authenticated:
            paste.user_id = current_user.id
            
        # Update paste content
        paste.title = form.title.data
        paste.content = form.content.data
        
        # If syntax is set to 'text' (the default), try to auto-detect the language
        syntax = form.syntax.data
        if syntax == 'text' and paste.content.strip():
            from utils import detect_language
            from flask import current_app
            detected_syntax = detect_language(paste.content)
            current_app.logger.info(f"Auto-detected language during edit: {detected_syntax}")
            syntax = detected_syntax
            
        paste.syntax = syntax
        paste.visibility = form.visibility.data
        paste.comments_enabled = form.comments_enabled.data
        paste.burn_after_read = form.burn_after_read.data
        
        # Update collection if applicable
        if current_user.is_authenticated and hasattr(form, 'collection_id'):
            import logging
            if form.collection_id.data and form.collection_id.data > 0:
                # Verify the collection exists and belongs to the user
                collection = PasteCollection.query.get(form.collection_id.data)
                if collection and collection.user_id == current_user.id:
                    paste.collection_id = collection.id
                    logging.debug(f"Updated paste collection to {collection.name} (ID: {collection.id})")
            else:
                # Remove from collection if "None" is selected
                paste.collection_id = None
                logging.debug("Removed paste from collection")
        
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
@limiter.limit("10 per hour")
def delete(short_id):
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if user has permission to delete
    if current_user.id != paste.user_id:
        abort(403)
    
    try:
        # First delete associated paste views to avoid foreign key constraint issues
        PasteView.query.filter_by(paste_id=paste.id).delete()
        
        # Update user stats if needed
        if current_user.total_pastes > 0:
            current_user.total_pastes -= 1
            
        # Delete the paste
        db.session.delete(paste)
        db.session.commit()
        
        flash('Paste deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting paste: {e}")
        flash('An error occurred while deleting the paste.', 'danger')
    
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
    
    # Handle encrypted content
    content = paste.content
    if paste.is_encrypted:
        # If password protected and not already decrypted in this session, redirect to the standard view
        if paste.password_protected and not session.get('decrypted_pastes', {}).get(paste.short_id):
            flash('This paste is password protected. Please enter the password to view.', 'warning')
            return redirect(url_for('paste.view', short_id=paste.short_id))
            
        # If we've already decrypted this paste or it's not password protected
        decrypted_content = paste.get_content()
        if decrypted_content:
            content = decrypted_content
    
    # Syntax highlighting
    highlighted_code, css = highlight_code(content, paste.syntax)
    
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

@paste_bp.route('/<short_id>/revisions')
@login_required
def revisions(short_id):
    """View revision history for a paste (registered users only)"""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if user has permission to view revisions
    if current_user.id != paste.user_id:
        abort(403)
        
    # Get all revisions of this paste
    revisions = paste.get_revisions()
    
    # Create form for CSRF token
    from flask_wtf import FlaskForm
    form = FlaskForm()
    
    return render_template('paste/revisions.html', paste=paste, revisions=revisions, form=form)

@paste_bp.route('/<short_id>/revision/<int:revision_number>')
@login_required
def view_revision(short_id, revision_number):
    """View a specific revision of a paste (registered users only)"""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if user has permission to view revisions
    if current_user.id != paste.user_id:
        abort(403)
        
    # Get the specific revision
    revision = PasteRevision.query.filter_by(
        paste_id=paste.id, 
        revision_number=revision_number
    ).first_or_404()
    
    # Syntax highlighting
    highlighted_code, css = highlight_code(revision.content, revision.syntax)
    
    # Create form for CSRF token
    from flask_wtf import FlaskForm
    form = FlaskForm()
    
    return render_template('paste/view_revision.html', 
                          paste=paste, 
                          revision=revision, 
                          highlighted_code=highlighted_code, 
                          css=css, 
                          form=form)
                          
@paste_bp.route('/template/<int:template_id>')
def get_template(template_id):
    """Get a template's details"""
    from models import PasteTemplate
    
    template = PasteTemplate.query.get_or_404(template_id)
    
    # Return the template data as JSON
    return {
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'content': template.content,
        'syntax': template.syntax
    }
    
@paste_bp.route('/api/highlight', methods=['POST'])
def highlight_preview():
    """API endpoint for syntax highlighting preview"""
    import logging
    logging.debug("API highlight called")
    
    # Log the request data for debugging
    logging.debug(f"Request form: {request.form}")
    logging.debug(f"Request data: {request.get_data(as_text=True)}")
    
    content = request.form.get('content', '')
    syntax = request.form.get('syntax', 'text')
    
    logging.debug(f"Content: {content[:100]}...")  # Log first 100 chars
    logging.debug(f"Syntax: {syntax}")
    
    if not content or not content.strip():
        logging.debug("No content to highlight")
        return {'highlighted': '<div class="text-muted">No content to highlight</div>', 'css': ''}
        
    # If syntax is set to 'text', try to auto-detect the language
    if syntax == 'text' and content.strip():
        from utils import detect_language
        from flask import current_app
        detected_syntax = detect_language(content)
        current_app.logger.info(f"Auto-detected language in preview: {detected_syntax}")
        syntax = detected_syntax
        logging.debug(f"Using auto-detected syntax: {syntax}")
    
    try:
        # Get highlighted code
        highlighted_code, css = highlight_code(content, syntax)
        logging.debug(f"Highlighted code length: {len(highlighted_code)}")
        
        # Return the highlighted code as JSON
        return {
            'highlighted': highlighted_code,
            'css': css
        }
    except Exception as e:
        logging.error(f"Error highlighting code: {e}")
        return {
            'highlighted': f'<div class="alert alert-danger">Error highlighting code: {e}</div>',
            'css': ''
        }

@paste_bp.route('/<short_id>/fork', methods=['POST'])
@limiter.limit("20 per hour")
def fork(short_id):
    """Fork an existing paste"""
    original_paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if paste has expired
    if original_paste.is_expired():
        flash('Cannot fork an expired paste.', 'warning')
        return redirect(url_for('paste.index'))
    
    # Check if paste is private and user is not the author
    if original_paste.visibility == 'private' and (not current_user.is_authenticated or current_user.id != original_paste.user_id):
        abort(403)
    
    # Get the visibility (default to same as original)
    visibility = request.form.get('visibility', original_paste.visibility)
    
    # Check if the visibility is valid
    if visibility not in ['public', 'private', 'unlisted']:
        visibility = 'public'
    
    # Create the fork
    user_id = current_user.id if current_user.is_authenticated else None
    fork = original_paste.fork(user_id=user_id, visibility=visibility)
    
    # Create a notification for the original paste owner if they're a registered user
    if original_paste.user_id and user_id and original_paste.user_id != user_id:
        paste_title = original_paste.title if original_paste.title else "Untitled"
        user = User.query.get(user_id)
        username = user.username if user else "Anonymous"
        notification_message = f"forked your paste: '{paste_title}'"
        
        Notification.create_notification(
            user_id=original_paste.user_id,
            type='fork',
            message=notification_message,
            sender_id=user_id,
            paste_id=fork.id  # Link to the new fork
        )
    
    flash('Paste forked successfully!', 'success')
    return redirect(url_for('paste.view', short_id=fork.short_id))


@paste_bp.route('/flag/<string:short_id>', methods=['GET', 'POST'])
@login_required
def flag_paste(short_id):
    """Route for flagging a paste as inappropriate content"""
    paste = Paste.query.filter_by(short_id=short_id).first_or_404()
    
    # Check if the user already flagged this paste
    existing_flag = FlaggedPaste.query.filter_by(
        paste_id=paste.id, 
        reporter_id=current_user.id,
        status='pending'
    ).first()
    
    if existing_flag:
        flash('You have already flagged this paste. A moderator will review it soon.', 'info')
        return redirect(url_for('paste.view', short_id=short_id))
    
    form = FlagContentForm()
    
    if form.validate_on_submit():
        flag = FlaggedPaste(
            paste_id=paste.id,
            reporter_id=current_user.id,
            reason=form.reason.data,
            details=form.details.data
        )
        
        db.session.add(flag)
        db.session.commit()
        
        flash('Thank you for flagging this content. A moderator will review it soon.', 'success')
        return redirect(url_for('paste.view', short_id=short_id))
    
    return render_template(
        'paste/flag_paste.html',
        paste=paste,
        form=form
    )
