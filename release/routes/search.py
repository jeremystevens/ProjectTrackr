from flask import Blueprint, render_template, request, flash
from sqlalchemy import or_, and_
from datetime import datetime
from models import Paste, User, Tag
from flask_login import current_user

search_bp = Blueprint('search', __name__, url_prefix='/search')

@search_bp.route('/')
def search():
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', 'content')
    page = request.args.get('page', 1, type=int)
    
    if not query:
        return render_template('search/results.html', pastes=None, query='', 
                               search_type=search_type, total=0)
    
    # Base query - only public and unexpired pastes
    base_query = Paste.query.filter(
        and_(
            Paste.visibility == 'public',
            or_(Paste.expires_at.is_(None), Paste.expires_at > datetime.utcnow())
        )
    )
    
    # Add search conditions based on search type
    if search_type == 'content':
        pastes_query = base_query.filter(Paste.content.ilike(f'%{query}%'))
    elif search_type == 'title':
        pastes_query = base_query.filter(Paste.title.ilike(f'%{query}%'))
    elif search_type == 'syntax':
        pastes_query = base_query.filter(Paste.syntax == query)
    elif search_type == 'author':
        # First find users matching the query
        users = User.query.filter(User.username.ilike(f'%{query}%')).all()
        user_ids = [user.id for user in users]
        if not user_ids:
            # If no users found, return empty results
            return render_template('search/results.html', pastes=None, query=query, 
                                  search_type=search_type, total=0)
        pastes_query = base_query.filter(Paste.user_id.in_(user_ids))
    elif search_type == 'tag':
        # Check if user is premium for tag search
        if not current_user.is_authenticated or not current_user.is_premium:
            flash("Tag search is a Premium feature. Please upgrade your account to use it.", "warning")
            return render_template('search/results.html', pastes=None, query=query, 
                                  search_type=search_type, total=0, premium_required=True)
        
        # Find tags matching the query
        tag = Tag.query.filter(Tag.name.ilike(f'%{query}%')).first()
        if not tag:
            # If no matching tag found, return empty results
            return render_template('search/results.html', pastes=None, query=query, 
                                  search_type=search_type, total=0)
        
        # Find pastes with this tag through the many-to-many relationship
        pastes_query = base_query.filter(Paste.tags.any(Tag.id == tag.id))
    
    # Get total count for pagination
    total = pastes_query.count()
    
    # Get paginated results
    pastes = pastes_query.order_by(Paste.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('search/results.html', pastes=pastes, query=query, 
                          search_type=search_type, total=total)

@search_bp.route('/archive/<syntax>')
def archive_by_syntax(syntax):
    page = request.args.get('page', 1, type=int)
    
    pastes = Paste.query.filter(
        and_(
            Paste.visibility == 'public',
            Paste.syntax == syntax,
            or_(Paste.expires_at.is_(None), Paste.expires_at > datetime.utcnow())
        )
    ).order_by(Paste.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('archive/index.html', pastes=pastes, 
                          title=f'Pastes with {syntax} syntax')
