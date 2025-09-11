"""
VeritasLogic Backend API
Handles user registration, authentication, and billing
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory, redirect, url_for, Response
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import jwt
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import bcrypt
import secrets
import stripe
from shared.pricing_config import is_business_email

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

app = Flask(__name__, static_folder='veritaslogic_multipage_website', static_url_path='')
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Serve static files (HTML, CSS, JS)
@app.route('/')
def serve_index():
    return send_from_directory('veritaslogic_multipage_website', 'index.html')

@app.route('/analysis')
def serve_streamlit_app():
    """Simple redirect to Streamlit - development approach"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirecting to Analysis Platform</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .redirect-container {
                text-align: center;
                background: rgba(255,255,255,0.1);
                padding: 3rem;
                border-radius: 20px;
                backdrop-filter: blur(10px);
                max-width: 500px;
            }
            .spinner {
                border: 4px solid rgba(255,255,255,0.3);
                border-top: 4px solid white;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 0 auto 2rem;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .btn {
                background: white;
                color: #667eea;
                padding: 1rem 2rem;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                margin: 1rem 0.5rem;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            .btn:hover { 
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            }
            .alt-btn {
                background: transparent;
                color: white;
                border: 2px solid white;
            }
        </style>
    </head>
    <body>
        <div class="redirect-container">
            <div class="spinner"></div>
            <h1>🚀 Launching Analysis Platform</h1>
            <p>Opening your complete ASC analysis platform...</p>
            <p>ASC 606 • ASC 842 • ASC 718 • ASC 805 • ASC 340-40 • Research Assistant</p>
            
            <button class="btn" onclick="openStreamlit()">
                Open Analysis Platform
            </button>
            <br>
            <button class="alt-btn btn" onclick="window.close()">
                Cancel
            </button>
            
            <p style="font-size: 14px; margin-top: 2rem; opacity: 0.8;">
                If the platform doesn't open automatically, click the button above.
            </p>
        </div>
        
        <script>
            function openStreamlit() {
                // Streamlit is now on external port 3002!
                const streamlitUrl = 'https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tmm3.picard.replit.dev:3002';
                window.open(streamlitUrl, '_blank');
            }
            
            // Auto-launch after 2 seconds
            setTimeout(openStreamlit, 2000);
        </script>
    </body>
    </html>
    '''

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('veritaslogic_multipage_website', path)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'veritaslogic-secret-key-change-in-production')


# Database connection
def get_db_connection():
    """Get database connection using Replit environment variables"""
    try:
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST'),
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            port=os.environ.get('PGPORT'),
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

# Helper functions
def sanitize_string(value, max_length=200, allow_chars=None):
    """
    Sanitize string input to prevent injection attacks
    
    Args:
        value (str): Input string to sanitize
        max_length (int): Maximum allowed length
        allow_chars (str): Additional allowed characters beyond alphanumeric, spaces, and basic punctuation
        
    Returns:
        str: Sanitized string
    """
    if not value or not isinstance(value, str):
        return ""
    
    # Remove null bytes and control characters
    value = value.replace('\x00', '').replace('\r', '').replace('\n', ' ')
    
    # Trim whitespace and limit length
    value = value.strip()[:max_length]
    
    # Define base allowed characters (alphanumeric, spaces, basic punctuation)
    base_pattern = r'[a-zA-Z0-9\s\-_@\.\'"]'
    if allow_chars:
        base_pattern = base_pattern[:-1] + re.escape(allow_chars) + ']'
    
    # Keep only allowed characters
    sanitized = ''.join(re.findall(base_pattern, value))
    
    return sanitized.strip()

def sanitize_email(email):
    """
    Sanitize email address with stricter validation
    
    Args:
        email (str): Email address to sanitize
        
    Returns:
        str: Sanitized email address
    """
    if not email or not isinstance(email, str):
        return ""
    
    # Basic email sanitization
    email = email.strip().lower()
    
    # Remove dangerous characters but keep email-valid ones
    email = sanitize_string(email, max_length=254, allow_chars='+')
    
    # Basic email format validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return ""
    
    return email

def verify_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token'}

# Password management functions
def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return password_hash.decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def generate_reset_token():
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)


# API Routes
@app.route('/api/signup', methods=['POST'])
def signup():
    """Handle user registration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'first_name', 'last_name', 'company_name', 'job_title', 'terms_accepted', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        if not data.get('terms_accepted'):
            return jsonify({'error': 'Terms and conditions must be accepted'}), 400
        
        # Sanitize all input fields
        email = sanitize_email(data.get('email', ''))
        first_name = sanitize_string(data.get('first_name', ''), max_length=50)
        last_name = sanitize_string(data.get('last_name', ''), max_length=50)
        company_name = sanitize_string(data.get('company_name', ''), max_length=100)
        job_title = sanitize_string(data.get('job_title', ''), max_length=100)
        password = data.get('password', '')
        
        # Validate sanitized inputs
        if not email:
            return jsonify({'error': 'Valid email address is required'}), 400
        if not first_name or not last_name:
            return jsonify({'error': 'First name and last name are required'}), 400
        if not company_name or not job_title:
            return jsonify({'error': 'Company name and job title are required'}), 400
        
        # Validate password strength
        is_valid, password_message = validate_password(password)
        if not is_valid:
            return jsonify({'error': password_message}), 400
        
        # Check if user already exists
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Email already registered'}), 409
        
        # Validate business email - reject personal emails
        if not is_business_email(email):
            conn.close()
            return jsonify({
                'error': 'Only business email addresses are accepted. Please use your company email address to register.'
            }), 400
        
        # Hash password before storing
        password_hash = hash_password(password)
        
        # Business email validated - create verified account immediately
        cursor.execute("""
            INSERT INTO users (email, first_name, last_name, company_name, job_title, 
                             password_hash, is_legacy_user, status, verified_at, free_analyses_remaining)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, 'verified', NOW(), 0)
            RETURNING id
        """, (email, first_name, last_name, company_name, job_title, password_hash))
        
        user_id = cursor.fetchone()['id']
        
        # Add trial credits transaction (use config value)
        cursor.execute("""
            INSERT INTO credit_transactions (user_id, amount, reason)
            VALUES (%s, 200, 'trial_grant')
        """, (user_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Business email {email} successfully registered and verified")
        
        return jsonify({
            'message': 'Registration successful! Your account is ready to use. You can now log in.',
            'user_id': user_id,
            'auto_verified': True
        }), 201
            
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login with password support and legacy email-only fallback"""
    try:
        data = request.get_json()
        email = sanitize_email(data.get('email', ''))
        password = data.get('password', '')
        
        if not email:
            return jsonify({'error': 'Valid email address is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, first_name, last_name, company_name, job_title, 
                   status, credits_balance, free_analyses_remaining,
                   password_hash, is_legacy_user
            FROM users 
            WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check authentication based on user type
        if user['is_legacy_user']:
            # Legacy user - email-only authentication (no password required)
            if password:
                return jsonify({'error': 'Legacy users should not provide a password'}), 400
        else:
            # New user - password required
            if not password:
                return jsonify({'error': 'Password is required'}), 400
            
            if not user['password_hash']:
                return jsonify({'error': 'User account is corrupted. Please contact support'}), 500
            
            # Verify password
            if not verify_password(password, user['password_hash']):
                return jsonify({'error': 'Invalid password'}), 401
        
        # Generate login token
        login_token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(days=7),
            'purpose': 'authentication'
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'message': 'Login successful',
            'token': login_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'company_name': user['company_name'],
                'job_title': user['job_title'],
                'credits_balance': float(user['credits_balance']),
                'free_analyses_remaining': user['free_analyses_remaining']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Handle forgot password request"""
    try:
        data = request.get_json()
        email = sanitize_email(data.get('email', ''))
        
        if not email:
            return jsonify({'error': 'Valid email address is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Check if user exists and is not a legacy user
        cursor.execute("""
            SELECT id, first_name, is_legacy_user 
            FROM users 
            WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        
        if not user:
            # Return success even if user doesn't exist for security
            return jsonify({
                'message': 'If an account with that email exists, you will receive a password reset email.'
            }), 200
        
        if user['is_legacy_user']:
            conn.close()
            return jsonify({
                'error': 'Legacy users cannot reset passwords. Please contact support for assistance.'
            }), 400
        
        # Generate reset token
        reset_token = generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        
        # Store reset token
        cursor.execute("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user['id'], reset_token, expires_at))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Password reset token generated for user {email}")
        
        # In a production environment, you would send an email here
        # For now, we'll return the token in the response (remove in production)
        return jsonify({
            'message': 'Password reset instructions have been sent to your email.',
            'reset_token': reset_token  # Remove this in production
        }), 200
        
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return jsonify({'error': 'Password reset request failed'}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Handle password reset with token"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        new_password = data.get('new_password', '')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required'}), 400
        
        # Validate new password
        is_valid, password_message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': password_message}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Find valid reset token
        cursor.execute("""
            SELECT prt.user_id, u.email
            FROM password_reset_tokens prt
            JOIN users u ON prt.user_id = u.id
            WHERE prt.token = %s 
              AND prt.expires_at > NOW()
              AND prt.used_at IS NULL
        """, (token,))
        
        reset_request = cursor.fetchone()
        
        if not reset_request:
            conn.close()
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        user_id = reset_request['user_id']
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update user password and mark as non-legacy
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s, is_legacy_user = FALSE
            WHERE id = %s
        """, (password_hash, user_id))
        
        # Mark token as used
        cursor.execute("""
            UPDATE password_reset_tokens 
            SET used_at = NOW()
            WHERE token = %s
        """, (token,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Password reset successful for user {reset_request['email']}")
        
        return jsonify({
            'message': 'Password has been reset successfully. You can now log in with your new password.'
        }), 200
        
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({'error': 'Password reset failed'}), 500

@app.route('/api/change-password', methods=['POST'])
def change_password():
    """Handle password change for authenticated users"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization token'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        # Validate new password
        is_valid, password_message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': password_message}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get user data
        cursor.execute("""
            SELECT password_hash, is_legacy_user
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password (unless legacy user)
        if user['is_legacy_user']:
            # Legacy users don't need to provide current password
            pass
        else:
            if not current_password:
                return jsonify({'error': 'Current password is required'}), 400
            
            if not user['password_hash'] or not verify_password(current_password, user['password_hash']):
                conn.close()
                return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update password and mark as non-legacy
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s, is_legacy_user = FALSE
            WHERE id = %s
        """, (password_hash, user_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Password changed successfully for user ID {user_id}")
        
        return jsonify({
            'message': 'Password has been changed successfully.'
        }), 200
        
    except Exception as e:
        logger.error(f"Change password error: {e}")
        return jsonify({'error': 'Password change failed'}), 500

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """Get user profile information"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization token'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get user data
        cursor.execute("""
            SELECT id, email, first_name, last_name, company_name, job_title,
                   credits_balance, free_analyses_remaining, created_at
            FROM users 
            WHERE id = %s AND status = 'verified'
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Get recent analyses
        cursor.execute("""
            SELECT asc_standard, billed_credits, completed_at
            FROM analyses 
            WHERE user_id = %s AND status = 'completed'
            ORDER BY completed_at DESC 
            LIMIT 10
        """, (user_id,))
        
        recent_analyses = cursor.fetchall()
        
        # Get credit transaction history
        cursor.execute("""
            SELECT amount, reason, created_at
            FROM credit_transactions
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id,))
        
        transactions = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'company_name': user['company_name'],
                'job_title': user['job_title'],
                'credits_balance': float(user['credits_balance']),
                'free_analyses_remaining': user['free_analyses_remaining'],
                'member_since': user['created_at'].isoformat()
            },
            'recent_analyses': [
                {
                    'asc_standard': analysis['asc_standard'],
                    'cost': float(analysis['billed_credits']),
                    'completed_at': analysis['completed_at'].isoformat()
                }
                for analysis in recent_analyses
            ],
            'transactions': [
                {
                    'amount': float(transaction['amount']),
                    'reason': transaction['reason'],
                    'date': transaction['created_at'].isoformat()
                }
                for transaction in transactions
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/user/check-credits', methods=['POST'])
def check_user_credits():
    """Check if user has sufficient credits for analysis"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization token'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        data = request.get_json()
        required_credits = data.get('required_credits', 0)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT credits_balance, free_analyses_remaining
            FROM users 
            WHERE id = %s AND status = 'verified'
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        can_proceed = (
            user['free_analyses_remaining'] > 0 or 
            user['credits_balance'] >= required_credits
        )
        
        return jsonify({
            'can_proceed': can_proceed,
            'credits_balance': float(user['credits_balance']),
            'free_analyses_remaining': user['free_analyses_remaining'],
            'is_free_analysis': user['free_analyses_remaining'] > 0
        }), 200
        
    except Exception as e:
        logger.error(f"Check credits error: {e}")
        return jsonify({'error': 'Failed to check credits'}), 500

@app.route('/api/user/record-analysis', methods=['POST'])
def record_analysis():
    """Record completed analysis and handle billing"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization token'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        data = request.get_json()
        
        # Extract billing information
        asc_standard = data.get('asc_standard')
        words_count = data.get('words_count', 0)
        estimate_cap_credits = Decimal(str(data.get('estimate_cap_credits', 0)))
        actual_credits = Decimal(str(data.get('actual_credits', 0)))
        billed_credits = Decimal(str(data.get('billed_credits', 0)))
        is_free_analysis = data.get('is_free_analysis', False)
        price_tier = data.get('price_tier', 2)  # Default to tier 2 if not provided
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Insert analysis record
        cursor.execute("""
            INSERT INTO analyses (user_id, asc_standard, words_count, estimate_cap_credits, 
                                actual_credits, billed_credits, price_tier, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'completed')
            RETURNING id
        """, (user_id, asc_standard, words_count, estimate_cap_credits, actual_credits, billed_credits, price_tier))
        
        analysis_id = cursor.fetchone()['id']
        
        if is_free_analysis:
            # Deduct from free analyses count
            cursor.execute("""
                UPDATE users 
                SET free_analyses_remaining = GREATEST(free_analyses_remaining - 1, 0)
                WHERE id = %s
            """, (user_id,))
            
            # Record credit transaction for tracking
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, analysis_id, amount, reason)
                VALUES (%s, %s, %s, 'analysis_charge')
            """, (user_id, analysis_id, 0))
            
        else:
            # Deduct from credits balance
            cursor.execute("""
                UPDATE users 
                SET credits_balance = GREATEST(credits_balance - %s, 0)
                WHERE id = %s
            """, (billed_credits, user_id))
            
            # Record credit transaction
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, analysis_id, amount, reason)
                VALUES (%s, %s, %s, 'analysis_charge')
            """, (user_id, analysis_id, -billed_credits))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Analysis recorded for user {user_id}: {asc_standard}, cost: {billed_credits}")
        
        return jsonify({
            'message': 'Analysis recorded successfully',
            'analysis_id': analysis_id,
            'billed_amount': float(billed_credits),
            'is_free_analysis': is_free_analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Record analysis error: {e}")
        return jsonify({'error': 'Failed to record analysis'}), 500

# Stripe Payment Endpoints
@app.route('/api/stripe/config', methods=['GET'])
def get_stripe_config():
    """Get Stripe publishable key for frontend"""
    return jsonify({'publishable_key': STRIPE_PUBLISHABLE_KEY}), 200

@app.route('/api/stripe/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """Create a Stripe payment intent for credit purchase"""
    try:
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        amount = data.get('amount')
        
        # Validate amount against available credit packages
        from shared.pricing_config import CREDIT_PACKAGES
        valid_amounts = [pkg['amount'] for pkg in CREDIT_PACKAGES]
        
        if not amount or amount not in valid_amounts:
            return jsonify({'error': f'Invalid credit amount. Must be one of: {valid_amounts}'}), 400
        
        # Get user info for payment metadata
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create payment intent with Stripe
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Stripe uses cents
            currency='usd',
            metadata={
                'user_id': user_id,
                'user_email': user['email'],
                'credit_amount': amount,
                'type': 'credit_purchase'
            }
        )
        
        logger.info(f"Created payment intent {intent.id} for user {user_id}, amount: ${amount}")
        
        return jsonify({
            'client_secret': intent.client_secret,
            'amount': amount
        }), 200
        
    except stripe.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return jsonify({'error': 'Payment processing error'}), 500
    except Exception as e:
        logger.error(f"Create payment intent error: {e}")
        return jsonify({'error': 'Failed to create payment intent'}), 500

@app.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    logger.info("=== WEBHOOK RECEIVED ===")
    logger.info(f"Headers: {dict(request.headers)}")
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    logger.info(f"Payload size: {len(payload)} bytes")
    logger.info(f"Signature header present: {bool(sig_header)}")
    
    # Verify webhook signature in production
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    if endpoint_secret and sig_header:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            logger.info("Webhook signature verified successfully")
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return jsonify({'error': 'Invalid signature'}), 400
    else:
        # For development without signature verification
        try:
            event = stripe.Event.construct_from(
                request.get_json(), stripe.api_key
            )
            logger.info("Using unsigned webhook (development mode)")
        except ValueError as e:
            logger.error(f"Invalid payload in webhook: {e}")
            return jsonify({'error': 'Invalid payload'}), 400
    
    logger.info(f"Event type: {event['type']}")
    logger.info(f"Event ID: {event.get('id', 'N/A')}")
    
    # Handle payment success
    if event['type'] == 'payment_intent.succeeded':
        logger.info("Processing payment_intent.succeeded event")
        payment_intent = event['data']['object']
        
        try:
            user_id = payment_intent['metadata']['user_id']
            credit_amount = Decimal(payment_intent['metadata']['credit_amount'])
            payment_id = payment_intent['id']
            
            logger.info(f"Processing payment for user {user_id}, amount: ${credit_amount}, payment_id: {payment_id}")
            
            conn = get_db_connection()
            if not conn:
                logger.error("Database connection failed in webhook")
                return jsonify({'error': 'Database error'}), 500
            
            cursor = conn.cursor()
            
            # Add credits to user's balance
            cursor.execute("""
                UPDATE users 
                SET credits_balance = credits_balance + %s
                WHERE id = %s
            """, (credit_amount, user_id))
            
            rows_affected = cursor.rowcount
            logger.info(f"Updated {rows_affected} user records")
            
            # Record credit purchase transaction
            from shared.pricing_config import CREDIT_EXPIRATION_MONTHS
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, reason, expires_at, stripe_payment_id)
                VALUES (%s, %s, 'stripe_purchase', NOW() + INTERVAL '%s months', %s)
            """, (user_id, credit_amount, CREDIT_EXPIRATION_MONTHS, payment_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"=== WEBHOOK SUCCESS: User {user_id} credited ${credit_amount} ===")
            
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': 'Processing failed'}), 500
    else:
        logger.info(f"Ignoring event type: {event['type']}")
    
    logger.info("=== WEBHOOK COMPLETE ===")
    return jsonify({'received': True}), 200

@app.route('/api/stripe/webhook/test', methods=['GET', 'POST'])
def test_webhook():
    """Test endpoint to verify webhook accessibility"""
    logger.info(f"=== WEBHOOK TEST CALLED - {request.method} ===")
    logger.info(f"Headers: {dict(request.headers)}")
    if request.method == 'POST':
        logger.info(f"Body: {request.get_data()}")
    return jsonify({
        'status': 'webhook_accessible',
        'method': request.method,
        'timestamp': datetime.now().isoformat(),
        'message': 'Webhook endpoint is accessible!'
    }), 200

# Credit Purchase Endpoints
@app.route('/api/credit-packages', methods=['GET'])
def get_credit_packages():
    """Get available credit purchase packages"""
    from shared.pricing_config import get_credit_packages
    try:
        packages = get_credit_packages()
        return jsonify({'packages': packages}), 200
    except Exception as e:
        logger.error(f"Error getting credit packages: {e}")
        return jsonify({'error': 'Failed to get credit packages'}), 500

@app.route('/api/purchase-credits', methods=['POST'])
def purchase_credits():
    """Legacy endpoint - redirects to Stripe payment flow"""
    return jsonify({
        'error': 'This endpoint is deprecated. Use /api/stripe/create-payment-intent for payments.',
        'redirect': '/api/stripe/create-payment-intent'
    }), 400

@app.route('/api/user/wallet-balance', methods=['GET'])
def get_wallet_balance():
    """Get user's current wallet balance"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get current wallet balance
        cursor.execute("""
            SELECT credits_balance FROM users WHERE id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'balance': float(result['credits_balance'])
            }), 200
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Wallet balance error: {e}")
        return jsonify({'error': 'Failed to get wallet balance'}), 500

@app.route('/api/user/purchase-credits', methods=['POST'])
def user_purchase_credits():
    """User credit purchase endpoint (matches wallet manager calls)"""
    try:
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        amount = data.get('credit_amount')
        
        if not amount or amount < 10:
            return jsonify({'error': 'Invalid credit amount. Minimum $10'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Add credits to user's balance
        cursor.execute("""
            UPDATE users 
            SET credits_balance = credits_balance + %s
            WHERE id = %s
        """, (amount, user_id))
        
        # Record credit purchase transaction
        cursor.execute("""
            INSERT INTO credit_transactions (user_id, amount, reason, created_at)
            VALUES (%s, %s, 'wallet_topup', NOW())
        """, (user_id, amount))
        
        # Get updated balance
        cursor.execute("""
            SELECT credits_balance FROM users WHERE id = %s
        """, (user_id,))
        
        new_balance = cursor.fetchone()['credits_balance']
        
        conn.commit()
        conn.close()
        
        logger.info(f"User {user_id} purchased ${amount} credits. New balance: ${new_balance}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully added ${amount:.2f} to your wallet!',
            'amount_purchased': amount,
            'new_balance': float(new_balance)
        }), 200
        
    except Exception as e:
        logger.error(f"Purchase credits error: {e}")
        return jsonify({'success': False, 'error': 'Failed to purchase credits'}), 500

@app.route('/api/user/charge-wallet', methods=['POST'])
def charge_wallet():
    """Charge user's wallet for analysis"""
    try:
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        charge_amount = data.get('charge_amount')
        
        if not charge_amount or charge_amount <= 0:
            return jsonify({'error': 'Invalid charge amount'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Check if user has sufficient balance
        cursor.execute("""
            SELECT credits_balance FROM users WHERE id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        current_balance = float(result['credits_balance'])
        
        if current_balance < charge_amount:
            conn.close()
            return jsonify({'error': f'Insufficient balance. You have ${current_balance:.2f}, need ${charge_amount:.2f}'}), 400
        
        # Deduct credits from user's balance
        new_balance = current_balance - charge_amount
        cursor.execute("""
            UPDATE users 
            SET credits_balance = %s
            WHERE id = %s
        """, (new_balance, user_id))
        
        # Record charge transaction
        cursor.execute("""
            INSERT INTO credit_transactions (user_id, amount, reason, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, -charge_amount, "analysis_charge"))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User {user_id} charged ${charge_amount}. New balance: ${new_balance}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully charged ${charge_amount:.2f}',
            'charge_amount': charge_amount,
            'remaining_balance': new_balance,
            'transaction_id': f'charge_{user_id}_{int(datetime.now().timestamp())}'
        }), 200
        
    except Exception as e:
        logger.error(f"Charge wallet error: {e}")
        return jsonify({'error': 'Failed to charge wallet'}), 500

@app.route('/api/user/auto-credit', methods=['POST'])
def auto_credit_wallet():
    """Auto-credit user's wallet for failed analysis"""
    try:
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        credit_amount = data.get('credit_amount')
        
        if not credit_amount or credit_amount <= 0:
            return jsonify({'error': 'Invalid credit amount'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Add credits to user's balance
        cursor.execute("""
            UPDATE users 
            SET credits_balance = credits_balance + %s
            WHERE id = %s
        """, (credit_amount, user_id))
        
        # Get updated balance
        cursor.execute("""
            SELECT credits_balance FROM users WHERE id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        new_balance = float(result['credits_balance'])
        
        # Record auto-credit transaction
        cursor.execute("""
            INSERT INTO credit_transactions (user_id, amount, reason, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, credit_amount, "admin_topup"))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Auto-credited ${credit_amount} to user {user_id}. New balance: ${new_balance}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully credited ${credit_amount:.2f} for failed analysis',
            'credit_amount': credit_amount,
            'new_balance': new_balance
        }), 200
        
    except Exception as e:
        logger.error(f"Auto-credit error: {e}")
        return jsonify({'error': 'Failed to auto-credit wallet'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

@app.route('/api/user/usage-stats', methods=['GET'])
def get_usage_stats():
    """Get user usage statistics for dashboard"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get total analyses count
        cursor.execute("""
            SELECT COUNT(*) as total_analyses 
            FROM analyses 
            WHERE user_id = %s AND status = 'completed'
        """, (user_id,))
        result = cursor.fetchone()
        total_analyses = result['total_analyses'] if result else 0
        
        # Get this month's analyses
        cursor.execute("""
            SELECT COUNT(*) as month_analyses 
            FROM analyses 
            WHERE user_id = %s AND status = 'completed'
            AND completed_at >= date_trunc('month', CURRENT_DATE)
        """, (user_id,))
        result = cursor.fetchone()
        month_analyses = result['month_analyses'] if result else 0
        
        # Get total spent
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_spent
            FROM credit_transactions 
            WHERE user_id = %s AND reason = 'analysis_charge'
        """, (user_id,))
        result = cursor.fetchone()
        total_spent = result['total_spent'] if result else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_analyses': int(total_analyses),
                'analyses_this_month': int(month_analyses),
                'total_spent': float(total_spent)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Usage stats error: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch usage statistics'}), 500

@app.route('/api/user/analysis-history', methods=['GET'])
def get_analysis_history():
    """Get user's analysis history for dashboard"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get recent analyses with details
        cursor.execute("""
            SELECT 
                a.id,
                a.asc_standard,
                a.completed_at,
                a.status,
                ct.amount as cost,
                CONCAT(a.asc_standard, ' Analysis') as document_name
            FROM analyses a
            LEFT JOIN credit_transactions ct ON a.id = ct.analysis_id 
                AND ct.reason = 'analysis_charge'
            WHERE a.user_id = %s 
            ORDER BY a.completed_at DESC
            LIMIT 20
        """, (user_id,))
        
        analyses = []
        for row in cursor.fetchall():
            analyses.append({
                'id': row['id'],
                'title': row['document_name'] or f"{row['asc_standard']} Analysis",
                'asc_standard': row['asc_standard'] or 'Unknown',
                'created_at': row['completed_at'].isoformat() if row['completed_at'] else '',
                'status': row['status'],
                'cost': float(row['cost']) if row['cost'] else 0,
                'download_url': f"/api/download/{row['id']}"
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'analyses': analyses
        }), 200
        
    except Exception as e:
        logger.error(f"Analysis history error: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch analysis history'}), 500

@app.route('/api/save-analysis', methods=['POST'])
def save_analysis():
    """Save completed analysis to database"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
            
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
            
        user_id = payload['user_id']
        data = request.get_json()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Insert analysis record (match existing schema)
        cursor.execute("""
            INSERT INTO analyses (id, user_id, asc_standard, status, completed_at, words_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                completed_at = EXCLUDED.completed_at,
                words_count = EXCLUDED.words_count
        """, (
            data.get('analysis_id'),
            user_id,
            data.get('asc_standard'),
            data.get('status'),
            data.get('completed_at'),
            data.get('total_words', 0)
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Save analysis error: {e}")
        return jsonify({'success': False, 'error': 'Failed to save analysis'}), 500

@app.route('/api/submit-rerun-request', methods=['POST'])
def submit_rerun_request():
    """Submit rerun request via email"""
    try:
        data = request.get_json()
        
        # Create email content
        subject = f"Memo Rerun Request - {data.get('memoId', 'Unknown')}"
        
        html_content = f"""
        <h2>New Memo Rerun Request</h2>
        <p><strong>Memo ID:</strong> {data.get('memoId', 'Not provided')}</p>
        <p><strong>Request Type:</strong> {data.get('requestType', 'Not specified')}</p>
        <p><strong>Urgency:</strong> {data.get('urgency', 'Standard')}</p>
        <p><strong>Change Details:</strong></p>
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 4px; margin: 1rem 0;">
            {data.get('changeDetails', 'No details provided').replace(chr(10), '<br>')}
        </div>
        <hr>
        <p><em>Action Required: Review request and apply $200 rerun credit to user account</em></p>
        """
        
        # Send notification email
        from shared.postmark_client import send_notification_email
        success = send_notification_email(
            subject=subject,
            html_content=html_content,
            memo_id=data.get('memoId', 'unknown')
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Rerun request submitted successfully'}), 200
        else:
            return jsonify({'success': False, 'error': 'Failed to send notification'}), 500
            
    except Exception as e:
        logger.error(f"Rerun request submission error: {e}")
        return jsonify({'success': False, 'error': 'Failed to submit rerun request'}), 500

@app.route('/api/user/update-profile', methods=['PUT'])
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        if not first_name or not last_name:
            return jsonify({'error': 'First name and last name are required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Update user profile
        cursor.execute("""
            UPDATE users 
            SET first_name = %s, last_name = %s 
            WHERE id = %s
        """, (first_name, last_name, user_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User {user_id} updated profile: {first_name} {last_name}")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'first_name': first_name,
            'last_name': last_name
        }), 200
        
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        return jsonify({'success': False, 'error': 'Failed to update profile'}), 500

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port, debug=True)