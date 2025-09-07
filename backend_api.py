"""
VeritasLogic Backend API
Handles user registration, authentication, and billing
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory, redirect, url_for
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
from shared.pricing_config import is_business_email

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='veritaslogic_multipage_website', static_url_path='')
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Serve static files (HTML, CSS, JS)
@app.route('/')
def serve_index():
    return send_from_directory('veritaslogic_multipage_website', 'index.html')

@app.route('/analysis')
def serve_streamlit():
    """Serve Streamlit app - production ready"""
    # Get the current host from the request
    host = request.headers.get('Host', 'localhost:5000')
    # Replace port 5000 with 8501 for Streamlit
    streamlit_url = f"http://{host.replace(':5000', ':8501')}"
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>VeritasLogic Analysis Platform</title>
        <style>
            body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
            iframe {{ width: 100%; height: 100vh; border: none; }}
            .loading {{ 
                position: absolute; 
                top: 50%; 
                left: 50%; 
                transform: translate(-50%, -50%);
                text-align: center;
                color: #666;
                z-index: 1000;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
        </style>
        <script>
            let loadTimeout;
            function showAnalysisPlatform() {{
                const loading = document.getElementById('loading');
                const iframe = document.getElementById('streamlit-frame');
                
                // Show loading initially
                loading.style.display = 'block';
                
                // Try to load Streamlit
                iframe.src = '{streamlit_url}';
                
                // Hide loading when iframe loads
                iframe.onload = function() {{
                    setTimeout(() => {{
                        loading.style.display = 'none';
                    }}, 1000);
                }};
                
                // Fallback: hide loading after 10 seconds regardless
                loadTimeout = setTimeout(() => {{
                    loading.style.display = 'none';
                }}, 10000);
            }}
            
            // Start loading when page loads
            window.onload = showAnalysisPlatform;
        </script>
    </head>
    <body>
        <div class="loading" id="loading">
            <h3>Loading Analysis Platform...</h3>
            <p>Starting your multi-standard ASC analysis tools...</p>
        </div>
        <iframe id="streamlit-frame" width="100%" height="100%" frameborder="0"></iframe>
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
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, 'verified', NOW(), 3)
            RETURNING id
        """, (email, first_name, last_name, company_name, job_title, password_hash))
        
        user_id = cursor.fetchone()['id']
        
        # Add trial credits transaction
        cursor.execute("""
            INSERT INTO credit_transactions (user_id, amount, reason)
            VALUES (%s, 3, 'trial_grant')
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
    """Purchase credits (simplified - no payment processing)"""
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
        
        if not amount or amount not in [50, 100, 200]:
            return jsonify({'error': 'Invalid credit amount. Must be 50, 100, or 200'}), 400
        
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
        
        # Record credit purchase transaction with expiration
        from shared.pricing_config import CREDIT_EXPIRATION_MONTHS
        cursor.execute("""
            INSERT INTO credit_transactions (user_id, amount, reason, expires_at)
            VALUES (%s, %s, 'credit_purchase', NOW() + INTERVAL '%s months')
        """, (user_id, amount, CREDIT_EXPIRATION_MONTHS))
        
        # Get updated balance
        cursor.execute("""
            SELECT credits_balance FROM users WHERE id = %s
        """, (user_id,))
        
        new_balance = cursor.fetchone()['credits_balance']
        
        conn.commit()
        conn.close()
        
        logger.info(f"User {user_id} purchased ${amount} credits. New balance: ${new_balance}")
        
        return jsonify({
            'message': f'Successfully added ${amount} to your account!',
            'amount_purchased': amount,
            'new_balance': float(new_balance),
            'expires_months': CREDIT_EXPIRATION_MONTHS
        }), 200
        
    except Exception as e:
        logger.error(f"Purchase credits error: {e}")
        return jsonify({'error': 'Failed to purchase credits'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)