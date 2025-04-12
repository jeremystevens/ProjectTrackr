"""
Ultra-simplified pastebin application using Flask and MySQL.
No SQLAlchemy dialect conflicts because we're using pure pymysql.
"""
import os
import logging
import secrets
import string
from datetime import datetime, timedelta
import json
import hashlib
import pymysql
import pymysql.cursors
from flask import Flask, render_template, request, redirect, url_for, flash, abort, make_response, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Configure session
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

# Database configuration
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "db": os.environ.get("DB_NAME", "flaskbin"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# Use environment variables if available
if "DATABASE_URL" in os.environ:
    # Parse DATABASE_URL for MySQL
    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("mysql://"):
        parts = db_url[8:].split("@")
        user_pass, host_port_name = parts
        if ":" in user_pass:
            user, password = user_pass.split(":")
        else:
            user, password = user_pass, ""
        if "/" in host_port_name:
            host_port, db_name = host_port_name.split("/")
        else:
            host_port, db_name = host_port_name, "flaskbin"
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, 3306
        
        DB_CONFIG.update({
            "host": host,
            "user": user,
            "password": password,
            "db": db_name,
            "port": int(port)
        })

# Create table queries
CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(64) NOT NULL UNIQUE,
        email VARCHAR(120) NOT NULL UNIQUE,
        password_hash VARCHAR(256) NOT NULL,
        created_at DATETIME NOT NULL,
        last_login DATETIME,
        is_admin BOOLEAN DEFAULT FALSE,
        api_key VARCHAR(64),
        is_banned BOOLEAN DEFAULT FALSE,
        shadowbanned BOOLEAN DEFAULT FALSE,
        free_ai_trials_used INT DEFAULT 0,
        failed_login_attempts INT DEFAULT 0,
        locked_until DATETIME NULL,
        security_question VARCHAR(255) NULL,
        security_answer_hash VARCHAR(256) NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pastes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        short_id VARCHAR(16) NOT NULL UNIQUE,
        title VARCHAR(255),
        content TEXT NOT NULL,
        language VARCHAR(30) DEFAULT 'plaintext',
        created_at DATETIME NOT NULL,
        expires_at DATETIME,
        views INT DEFAULT 0,
        user_id INT,
        is_public BOOLEAN DEFAULT TRUE,
        comments_enabled BOOLEAN DEFAULT TRUE,
        burn_after_read BOOLEAN DEFAULT FALSE,
        is_encrypted BOOLEAN DEFAULT FALSE,
        encryption_salt VARCHAR(32),
        encryption_iv VARCHAR(32),
        forked_from INT,
        fork_of VARCHAR(16),
        collection_id INT,
        ai_summary TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY (forked_from) REFERENCES pastes(id) ON DELETE SET NULL,
        FOREIGN KEY (collection_id) REFERENCES paste_collections(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS comments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        paste_id INT NOT NULL,
        user_id INT,
        content TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        FOREIGN KEY (paste_id) REFERENCES pastes(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paste_collections (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        user_id INT,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        is_public BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tags (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(50) NOT NULL UNIQUE,
        created_at DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paste_tags (
        paste_id INT NOT NULL,
        tag_id INT NOT NULL,
        PRIMARY KEY (paste_id, tag_id),
        FOREIGN KEY (paste_id) REFERENCES pastes(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS flagged_pastes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        paste_id INT NOT NULL,
        reporter_id INT,
        reason TEXT,
        created_at DATETIME NOT NULL,
        resolved BOOLEAN DEFAULT FALSE,
        resolved_by INT,
        resolved_at DATETIME,
        FOREIGN KEY (paste_id) REFERENCES pastes(id) ON DELETE CASCADE,
        FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS paste_revisions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        paste_id INT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        user_id INT,
        FOREIGN KEY (paste_id) REFERENCES pastes(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        message TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        read BOOLEAN DEFAULT FALSE,
        link VARCHAR(255),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
]

def get_db_connection():
    """Get a database connection."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize the database by creating tables if they don't exist."""
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Could not connect to database for initialization")
            return False
        
        with conn.cursor() as cursor:
            for table_query in CREATE_TABLES:
                cursor.execute(table_query)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

def generate_short_id(length=8):
    """Generate a random short ID for pastes."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

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

class UserProxy:
    def __init__(self, user_dict):
        self.user_dict = user_dict or {}
    
    def is_authenticated(self):
        return True
    
    def __getattr__(self, name):
        return self.user_dict.get(name)

def timesince(dt):
    """Format datetime as relative time since."""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

# Register template filters
app.jinja_env.filters['timesince'] = timesince

# Make functions available in templates
@app.context_processor
def utility_processor():
    return {
        'is_authenticated': is_authenticated,
        'get_current_user': lambda: UserProxy(get_current_user())
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    """Home page / paste creation form."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        language = request.form.get('language', 'plaintext')
        expiration = request.form.get('expiration', 'never')
        visibility = request.form.get('visibility', 'public')
        comments_enabled = 'comments_enabled' in request.form
        burn_after_read = 'burn_after_read' in request.form
        encrypt_paste = 'encrypt_paste' in request.form
        encryption_password = request.form.get('encryption_password', '')
        
        if not content:
            flash('Paste content cannot be empty.', 'danger')
            return redirect(url_for('index'))
        
        # Handle expiration
        expires_at = None
        if expiration == '10min':
            expires_at = datetime.utcnow() + timedelta(minutes=10)
        elif expiration == '1h':
            expires_at = datetime.utcnow() + timedelta(hours=1)
        elif expiration == '1d':
            expires_at = datetime.utcnow() + timedelta(days=1)
        elif expiration == '1w':
            expires_at = datetime.utcnow() + timedelta(weeks=1)
        elif expiration == '1m':
            expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Handle visibility
        is_public = visibility == 'public'
        
        # Generate a unique short_id
        short_id = generate_short_id()
        
        # Handle encryption
        encryption_salt = None
        encryption_iv = None
        if encrypt_paste and encryption_password:
            # Generate salt and iv for encryption
            encryption_salt = secrets.token_hex(16)
            encryption_iv = secrets.token_hex(16)
            
            # This is a simplified encryption example - in a real app, use a proper encryption library
            key = hashlib.pbkdf2_hmac('sha256', encryption_password.encode(), 
                                       encryption_salt.encode(), 100000).hex()
            # Note: In a real implementation, encrypt the content with the key and iv
            
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO pastes (
                    short_id, title, content, language, created_at, expires_at, 
                    user_id, is_public, comments_enabled, burn_after_read,
                    is_encrypted, encryption_salt, encryption_iv
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    short_id, title, content, language, datetime.utcnow(), expires_at,
                    session.get('user_id'), is_public, comments_enabled, burn_after_read,
                    encrypt_paste, encryption_salt, encryption_iv
                ))
            conn.commit()
            conn.close()
            
            return redirect(url_for('view_paste', short_id=short_id))
        except Exception as e:
            logger.error(f"Error creating paste: {e}")
            flash('An error occurred while saving your paste.', 'danger')
            return redirect(url_for('index'))
    
    # Get recent public pastes
    recent_pastes = []
    user_pastes = []
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get recent public pastes
            cursor.execute("""
                SELECT p.*, u.username 
                FROM pastes p
                LEFT JOIN users u ON p.user_id = u.id
                WHERE p.is_public = TRUE AND (p.expires_at IS NULL OR p.expires_at > %s)
                ORDER BY p.created_at DESC
                LIMIT 10
            """, (datetime.utcnow(),))
            recent_pastes = cursor.fetchall()
            
            # Get user's pastes if authenticated
            if is_authenticated():
                cursor.execute("""
                    SELECT p.*, u.username 
                    FROM pastes p
                    LEFT JOIN users u ON p.user_id = u.id
                    WHERE p.user_id = %s
                    ORDER BY p.created_at DESC
                    LIMIT 10
                """, (session['user_id'],))
                user_pastes = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Error getting pastes: {e}")
    
    return render_template('index.html', recent_pastes=recent_pastes, user_pastes=user_pastes)

@app.route('/<short_id>')
def view_paste(short_id):
    """View a paste."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get the paste
            cursor.execute("""
                SELECT p.*, u.username 
                FROM pastes p
                LEFT JOIN users u ON p.user_id = u.id
                WHERE p.short_id = %s
            """, (short_id,))
            paste = cursor.fetchone()
            
            if not paste:
                conn.close()
                abort(404)
            
            # Check if paste is expired
            if paste['expires_at'] and paste['expires_at'] < datetime.utcnow():
                cursor.execute("DELETE FROM pastes WHERE id = %s", (paste['id'],))
                conn.commit()
                conn.close()
                flash('This paste has expired.', 'warning')
                return redirect(url_for('index'))
            
            # Check if paste is burn after read
            if paste['burn_after_read']:
                burn_paste = paste.copy()
                cursor.execute("DELETE FROM pastes WHERE id = %s", (paste['id'],))
                conn.commit()
                
                # Get comments if needed for the soon-to-be-deleted paste
                comments = []
                if burn_paste['comments_enabled']:
                    cursor.execute("""
                        SELECT c.*, u.username 
                        FROM comments c
                        LEFT JOIN users u ON c.user_id = u.id
                        WHERE c.paste_id = %s
                        ORDER BY c.created_at ASC
                    """, (burn_paste['id'],))
                    comments = cursor.fetchall()
                
                conn.close()
                flash('This paste was set to burn after reading. It has been deleted.', 'warning')
                return render_template('view.html', paste=burn_paste, comments=comments, related_pastes=[])
            
            # Increment view count
            cursor.execute("UPDATE pastes SET views = views + 1 WHERE id = %s", (paste['id'],))
            
            # Get comments
            comments = []
            if paste['comments_enabled']:
                cursor.execute("""
                    SELECT c.*, u.username 
                    FROM comments c
                    LEFT JOIN users u ON c.user_id = u.id
                    WHERE c.paste_id = %s
                    ORDER BY c.created_at ASC
                """, (paste['id'],))
                comments = cursor.fetchall()
            
            # Get related pastes
            related_pastes = []
            if paste['user_id']:
                cursor.execute("""
                    SELECT p.*, u.username 
                    FROM pastes p
                    LEFT JOIN users u ON p.user_id = u.id
                    WHERE p.user_id = %s AND p.id != %s AND p.is_public = TRUE
                    ORDER BY p.created_at DESC
                    LIMIT 5
                """, (paste['user_id'], paste['id']))
                related_pastes = cursor.fetchall()
            
        conn.commit()
        conn.close()
        
        return render_template('view.html', paste=paste, comments=comments, related_pastes=related_pastes)
    except Exception as e:
        logger.error(f"Error viewing paste: {e}")
        flash('An error occurred while retrieving the paste.', 'danger')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint for Render."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
        conn.close()
        
        if version:
            return jsonify({
                'status': 'ok',
                'message': 'Database connection successful',
                'db_version': version.get('VERSION()', 'unknown')
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Database connection failed'
            }), 500
    except Exception as e:
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

# Initialize the database on startup
init_db()

# Run the app if executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)