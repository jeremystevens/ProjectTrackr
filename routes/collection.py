from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
from app import db
from models import Paste, PasteCollection
from forms import CollectionForm

collection_bp = Blueprint('collection', __name__, url_prefix='/collections')

@collection_bp.route('/')
@login_required
def list_collections():
    """List all collections for the current user"""
    collections = PasteCollection.query.filter_by(user_id=current_user.id).order_by(
        PasteCollection.name
    ).all()
    
    # Get the count of pastes in each collection for display
    collection_stats = {}
    for collection in collections:
        paste_count = Paste.query.filter_by(collection_id=collection.id).count()
        collection_stats[collection.id] = {
            'paste_count': paste_count
        }
    
    return render_template('collection/list.html', 
                          collections=collections,
                          collection_stats=collection_stats)

@collection_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new collection"""
    form = CollectionForm()
    
    if form.validate_on_submit():
        collection = PasteCollection(
            name=form.name.data,
            description=form.description.data,
            is_public=form.is_public.data,
            user_id=current_user.id
        )
        
        db.session.add(collection)
        db.session.commit()
        
        flash('Collection created successfully!', 'success')
        return redirect(url_for('collection.list_collections'))
    
    return render_template('collection/create.html', form=form)

@collection_bp.route('/<int:collection_id>')
@login_required
def view(collection_id):
    """View a specific collection and its pastes"""
    collection = PasteCollection.query.get_or_404(collection_id)
    
    # Check permissions - only the owner or public collection viewers can access
    if collection.user_id != current_user.id and not collection.is_public:
        abort(403)  # Forbidden
    
    page = request.args.get('page', 1, type=int)
    
    # Get all pastes in the collection
    pastes = Paste.query.filter_by(collection_id=collection_id).order_by(
        Paste.created_at.desc()
    ).paginate(page=page, per_page=10)
    
    # If current user is the owner, prepare encryption keys for encrypted pastes
    encryption_keys = {}
    if collection.user_id == current_user.id:
        for paste in pastes.items:
            if paste.is_encrypted and paste.encryption_method == 'fernet-random' and paste.encryption_salt:
                encryption_keys[paste.short_id] = paste.encryption_salt
    
    return render_template('collection/view.html', 
                          collection=collection, 
                          pastes=pastes,
                          encryption_keys=encryption_keys)

@collection_bp.route('/<int:collection_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(collection_id):
    """Edit an existing collection"""
    collection = PasteCollection.query.get_or_404(collection_id)
    
    # Check permissions - only the owner can edit
    if collection.user_id != current_user.id:
        abort(403)  # Forbidden
    
    form = CollectionForm()
    
    if request.method == 'GET':
        form.name.data = collection.name
        form.description.data = collection.description
        form.is_public.data = collection.is_public
    
    if form.validate_on_submit():
        collection.name = form.name.data
        collection.description = form.description.data
        collection.is_public = form.is_public.data
        collection.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Collection updated successfully!', 'success')
        return redirect(url_for('collection.view', collection_id=collection.id))
    
    return render_template('collection/edit.html', form=form, collection=collection)

@collection_bp.route('/<int:collection_id>/delete', methods=['POST'])
@login_required
def delete(collection_id):
    """Delete a collection but not its pastes"""
    collection = PasteCollection.query.get_or_404(collection_id)
    
    # Check permissions - only the owner can delete
    if collection.user_id != current_user.id:
        abort(403)  # Forbidden
    
    # Remove collection_id from pastes (rather than deleting them)
    pastes = Paste.query.filter_by(collection_id=collection.id).all()
    for paste in pastes:
        paste.collection_id = None
    
    # Delete the collection
    db.session.delete(collection)
    db.session.commit()
    
    flash('Collection deleted successfully!', 'success')
    return redirect(url_for('collection.list_collections'))

@collection_bp.route('/<int:collection_id>/remove_paste/<int:paste_id>', methods=['POST'])
@login_required
def remove_paste(collection_id, paste_id):
    """Remove a paste from a collection"""
    collection = PasteCollection.query.get_or_404(collection_id)
    paste = Paste.query.get_or_404(paste_id)
    
    # Check permissions - only the owner can remove pastes
    if collection.user_id != current_user.id:
        abort(403)  # Forbidden
    
    # Remove collection association
    if paste.collection_id == collection.id:
        paste.collection_id = None
        db.session.commit()
        flash('Paste removed from collection.', 'success')
    else:
        flash('This paste is not in the specified collection.', 'warning')
    
    return redirect(url_for('collection.view', collection_id=collection.id))