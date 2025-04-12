#!/usr/bin/env python3
"""
Ultra-simplified pastebin application using Flask and MySQL.
No SQLAlchemy dialect conflicts because we're using pure pymysql.
"""
import os
import logging
import secrets
import string
from datetime import datetime, timedelta
import pymysql
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask import make_response, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key')

# MySQL connection parameters
DB_CONFIG = {
    'host': '185.212.71.204',
    'port': 3306,
    'user': 'u213077714_flaskbin',
    'password': 'hOJ27K?5',
    'database': 'u213077714_flaskbin',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Database table names for reference
TABLES = {
    'pastes': 'pastes',
    'users': 'users',
    'comments': 'comments',
    'paste_revisions': 'paste_revisions',
    'paste_collections': 'paste_collections',
    'tags': 'tags',
    'paste_tags': 'paste_tags',
    'notifications': 'notifications',
    'flagged_pastes': 'flagged_pastes',
    'flagged_comments': 'flagged_comments'
}

def get_db_connection():
    """Get a database connection."""
    return pymysql.connect(**DB_CONFIG)

def generate_short_id(length=8):
    """Generate a random short ID for pastes."""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def get_current_user():
    """Get the current user from the session."""
    if 'user_id' not in session:
        return None
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
            user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None

def is_authenticated():
    """Check if the user is authenticated."""
    return 'user_id' in session

# Create a UserProxy to mimic Flask-Login's current_user
class UserProxy:
    @property
    def is_authenticated(self):
        return is_authenticated()
    
    def __getattr__(self, name):
        user = get_current_user()
        if user is None:
            return None
        return user.get(name)

# Create a global current_user proxy
current_user = UserProxy()

def timesince(dt):
    """Format datetime as relative time since."""
    if not dt:
        return "never"
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "just now"

# Register filters and global functions
app.jinja_env.filters['timesince'] = timesince
app.jinja_env.globals.update(
    is_authenticated=is_authenticated,
    get_current_user=get_current_user,
    current_user=current_user
)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Home page / paste creation form."""
    if request.method == 'POST':
        # Handle paste creation
        title = request.form.get('title', '').strip() or 'Untitled Paste'
        content = request.form.get('content', '')
        language = request.form.get('language', 'plaintext')
        expiration = request.form.get('expiration', 'never')
        is_public = 'is_public' in request.form
        burn_after_read = 'burn_after_read' in request.form
        
        # Validate content
        if not content:
            flash('Paste content cannot be empty.', 'danger')
            return redirect(url_for('index'))
        
        # Set expiration date
        expires_at = None
        if expiration != 'never':
            if expiration == '10min':
                expires_at = datetime.utcnow() + timedelta(minutes=10)
            elif expiration == '1hour':
                expires_at = datetime.utcnow() + timedelta(hours=1)
            elif expiration == '1day':
                expires_at = datetime.utcnow() + timedelta(days=1)
            elif expiration == '1week':
                expires_at = datetime.utcnow() + timedelta(weeks=1)
            elif expiration == '1month':
                expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Create new paste
        short_id = generate_short_id()
        user_id = session.get('user_id')
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO pastes (
                    short_id, title, content, language, created_at, expires_at, 
                    is_public, burn_after_read, user_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    short_id, title, content, language, datetime.utcnow(), expires_at,
                    is_public, burn_after_read, user_id
                ))
            conn.commit()
            conn.close()
            
            # Redirect to the new paste
            flash('Paste created successfully!', 'success')
            return redirect(url_for('view_paste', short_id=short_id))
        except Exception as e:
            logger.error(f"Error creating paste: {e}")
            flash('An error occurred while creating the paste.', 'danger')
            return redirect(url_for('index'))
    
    # GET request - show form with recent pastes
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
            SELECT p.*, u.username
            FROM pastes p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.is_public = 1
            ORDER BY p.created_at DESC
            LIMIT 10
            """
            cursor.execute(sql)
            recent_pastes = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Error getting recent pastes: {e}")
        recent_pastes = []
    
    return render_template('index.html', recent_pastes=recent_pastes)

@app.route('/<short_id>')
def view_paste(short_id):
    """View a paste."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get the paste
            sql = """
            SELECT p.*, u.username
            FROM pastes p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.short_id = %s
            """
            cursor.execute(sql, (short_id,))
            paste = cursor.fetchone()
            
            if not paste:
                conn.close()
                abort(404)
            
            # Check if paste is expired
            if paste['expires_at'] and paste['expires_at'] < datetime.utcnow():
                # Delete the paste
                cursor.execute("DELETE FROM pastes WHERE id = %s", (paste['id'],))
                conn.commit()
                conn.close()
                flash('This paste has expired.', 'warning')
                return redirect(url_for('index'))
            
            # Check if burn after read
            if paste['burn_after_read']:
                # Keep content but mark for deletion
                content = paste['content']
                title = paste['title']
                language = paste['language']
                
                # Delete the paste
                cursor.execute("DELETE FROM pastes WHERE id = %s", (paste['id'],))
                conn.commit()
                conn.close()
                
                # Render special template for burn-after-read
                flash('This was a burn-after-read paste and has been deleted.', 'warning')
                # For now, just render the normal view since we don't have a special template
                return render_template('view.html', 
                                     paste={
                                         'title': title,
                                         'content': content,
                                         'language': language,
                                         'burn_after_read': True,
                                         'created_at': datetime.utcnow(),
                                         'user': None
                                     })
            
            # Get comments if comments are enabled
            comments = []
            if paste.get('comments_enabled', False):
                sql = """
                SELECT c.*, u.username
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.paste_id = %s
                ORDER BY c.created_at ASC
                """
                cursor.execute(sql, (paste['id'],))
                comments = cursor.fetchall()
            
            # Increment view count
            cursor.execute("UPDATE pastes SET views = views + 1 WHERE id = %s", (paste['id'],))
            conn.commit()
        conn.close()
        
        return render_template('view.html', paste=paste, comments=comments)
    except Exception as e:
        logger.error(f"Error viewing paste: {e}")
        flash('An error occurred while retrieving the paste.', 'danger')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()['VERSION()']
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'database': 'mysql',
            'version': version,
            'time': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/raw/<short_id>')
def raw_paste(short_id):
    """View raw paste content."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM pastes WHERE short_id = %s", (short_id,))
            paste = cursor.fetchone()
            
            if not paste:
                conn.close()
                abort(404)
            
            # Check if paste is expired
            if paste['expires_at'] and paste['expires_at'] < datetime.utcnow():
                # Delete the paste
                cursor.execute("DELETE FROM pastes WHERE id = %s", (paste['id'],))
                conn.commit()
                conn.close()
                flash('This paste has expired.', 'warning')
                return redirect(url_for('index'))
        conn.close()
        
        # Return plain text response
        response = make_response(paste['content'])
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        
        return response
    except Exception as e:
        logger.error(f"Error viewing raw paste: {e}")
        flash('An error occurred while retrieving the paste.', 'danger')
        return redirect(url_for('index'))



@app.route('/<short_id>/comment', methods=['POST'])
def add_comment(short_id):
    """Add a comment to a paste."""
    if not is_authenticated():
        flash('You must be logged in to comment.', 'danger')
        return redirect(url_for('view_paste', short_id=short_id))
    
    comment_text = request.form.get('comment', '').strip()
    if not comment_text:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('view_paste', short_id=short_id))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get paste id
            cursor.execute("SELECT id, comments_enabled FROM pastes WHERE short_id = %s", (short_id,))
            paste = cursor.fetchone()
            
            if not paste:
                conn.close()
                abort(404)
            
            if not paste.get('comments_enabled', False):
                conn.close()
                flash('Comments are not enabled for this paste.', 'danger')
                return redirect(url_for('view_paste', short_id=short_id))
            
            # Add comment
            sql = """
            INSERT INTO comments (paste_id, user_id, content, created_at)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                paste['id'], session['user_id'], comment_text, datetime.utcnow()
            ))
        conn.commit()
        conn.close()
        
        flash('Comment added successfully!', 'success')
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        flash('An error occurred while adding your comment.', 'danger')
    
    return redirect(url_for('view_paste', short_id=short_id))

@app.route('/<short_id>/report', methods=['POST'])
def report_paste(short_id):
    """Report a paste for inappropriate content."""
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for reporting.', 'danger')
        return redirect(url_for('view_paste', short_id=short_id))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get paste id
            cursor.execute("SELECT id FROM pastes WHERE short_id = %s", (short_id,))
            paste = cursor.fetchone()
            
            if not paste:
                conn.close()
                abort(404)
            
            # Add report
            user_id = session.get('user_id')
            sql = """
            INSERT INTO flagged_pastes (paste_id, reporter_id, reason, created_at)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                paste['id'], user_id, reason, datetime.utcnow()
            ))
        conn.commit()
        conn.close()
        
        flash('Paste reported. Thank you for helping keep our platform safe.', 'success')
    except Exception as e:
        logger.error(f"Error reporting paste: {e}")
        flash('An error occurred while reporting the paste.', 'danger')
    
    return redirect(url_for('view_paste', short_id=short_id))

@app.route('/<short_id>/fork', methods=['POST'])
def fork_paste(short_id):
    """Fork a paste."""
    if not is_authenticated():
        flash('You must be logged in to fork pastes.', 'danger')
        return redirect(url_for('view_paste', short_id=short_id))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get original paste
            cursor.execute("SELECT * FROM pastes WHERE short_id = %s", (short_id,))
            original_paste = cursor.fetchone()
            
            if not original_paste:
                conn.close()
                abort(404)
            
            # Create new paste as a fork
            new_short_id = generate_short_id()
            user_id = session['user_id']
            
            sql = """
            INSERT INTO pastes (
                short_id, title, content, language, created_at, is_public, 
                user_id, forked_from, fork_of
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                new_short_id, 
                f"Fork of {original_paste['title']}", 
                original_paste['content'],
                original_paste['language'],
                datetime.utcnow(),
                original_paste['is_public'],
                user_id,
                original_paste['id'],
                original_paste['short_id']
            ))
        conn.commit()
        conn.close()
        
        flash('Paste forked successfully!', 'success')
        return redirect(url_for('view_paste', short_id=new_short_id))
    except Exception as e:
        logger.error(f"Error forking paste: {e}")
        flash('An error occurred while forking the paste.', 'danger')
        return redirect(url_for('view_paste', short_id=short_id))

@app.route('/download/<short_id>')
def download_paste(short_id):
    """Download a paste as a text file."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM pastes WHERE short_id = %s", (short_id,))
            paste = cursor.fetchone()
            
            if not paste:
                conn.close()
                abort(404)
            
            # Check if paste is expired
            if paste['expires_at'] and paste['expires_at'] < datetime.utcnow():
                # Delete the paste
                cursor.execute("DELETE FROM pastes WHERE id = %s", (paste['id'],))
                conn.commit()
                conn.close()
                flash('This paste has expired.', 'warning')
                return redirect(url_for('index'))
        conn.close()
        
        # Set filename based on paste title
        filename = f"{paste['title'] or 'untitled'}.txt"
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '-', '_')).strip()
        
        # Create response with file download
        response = make_response(paste['content'])
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = "text/plain"
        
        return response
    except Exception as e:
        logger.error(f"Error downloading paste: {e}")
        flash('An error occurred while downloading the paste.', 'danger')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if is_authenticated():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        remember = 'remember_me' in request.form
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                if remember:
                    # Set session to expire after 30 days
                    session.permanent = True
                    app.permanent_session_lifetime = timedelta(days=30)
                
                # Update last login time
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE users SET last_login = %s WHERE id = %s", 
                                  (datetime.utcnow(), user['id']))
                conn.commit()
                conn.close()
                
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'danger')
        except Exception as e:
            logger.error(f"Error during login: {e}")
            flash('An error occurred during login.', 'danger')
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """User logout."""
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    """User registration."""
    if is_authenticated():
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Validate inputs
    if not username or not email or not password:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('index'))
    
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('index'))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if username or email already exists
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                conn.close()
                flash('Username or email already exists.', 'danger')
                return redirect(url_for('index'))
            
            # Create new user
            password_hash = generate_password_hash(password)
            api_key = generate_short_id(32)
            
            sql = """
            INSERT INTO users (username, email, password_hash, created_at, last_login, api_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                username, email, password_hash, datetime.utcnow(), datetime.utcnow(), api_key
            ))
            
            # Get the new user's ID
            user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Log the user in
        session['user_id'] = user_id
        
        flash('Registration successful!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        flash('An error occurred during registration.', 'danger')
        return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return render_template('errors/500.html'), 500

# Run the app if executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)