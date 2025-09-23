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
import json
import uuid
import requests
from shared.pricing_config import is_business_email
from shared.postmark_client import PostmarkClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

# Environment configuration
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
STREAMLIT_URL = os.getenv('STREAMLIT_URL', 'https://tas.veritaslogic.ai')
DEVELOPMENT_URLS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "http://localhost:5000",
    "http://127.0.0.1:5000"
]

# Configure allowed origins for CORS
ALLOWED_ORIGINS = [
    WEBSITE_URL,
    STREAMLIT_URL,
    # Allow all VeritasLogic subdomains in production
    "https://*.veritaslogic.ai"
] + DEVELOPMENT_URLS

app = Flask(__name__, static_folder='veritaslogic_multipage_website', static_url_path='')

# Enhanced CORS configuration for subdomain support
CORS(app, 
     origins=ALLOWED_ORIGINS,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True,  # Important for cookie sharing
     expose_headers=["Content-Type", "Authorization"])

# Serve static files (HTML, CSS, JS)
@app.route('/')
def serve_index():
    return send_from_directory('veritaslogic_multipage_website', 'index.html')

@app.route('/analysis')
def serve_streamlit_app():
    """Redirect to Streamlit app with seamless authentication"""
    
    # Check if user is authenticated
    auth_header = request.headers.get('Authorization')
    token = None
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    
    # Also check cookies
    if not token:
        token = request.cookies.get('vl_auth_token')
    
    # Build redirect URL
    if token:
        # Validate token before redirecting
        payload = verify_token(token)
        if 'error' not in payload:
            redirect_url = f"{STREAMLIT_URL}?auth_token={token}"
        else:
            redirect_url = STREAMLIT_URL
    else:
        redirect_url = STREAMLIT_URL
    
    # Build enhanced HTML response with error handling and status checking
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VeritasLogic Analysis Platform</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Inter', Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .launch-container {{
                text-align: center;
                background: rgba(255,255,255,0.1);
                padding: 3rem;
                border-radius: 20px;
                backdrop-filter: blur(10px);
                max-width: 600px;
                min-height: 400px;
                position: relative;
            }}
            .status-indicator {{
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
                background: #4ade80;
                animation: pulse 2s infinite;
            }}
            .status-checking {{ background: #fbbf24; }}
            .status-error {{ background: #ef4444; animation: none; }}
            
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            
            .spinner {{
                border: 4px solid rgba(255,255,255,0.3);
                border-top: 4px solid white;
                border-radius: 50%;
                width: 60px;
                height: 60px;
                animation: spin 1s linear infinite;
                margin: 0 auto 2rem;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            .progress-bar {{
                width: 100%;
                height: 8px;
                background: rgba(255,255,255,0.2);
                border-radius: 4px;
                margin: 2rem 0;
                overflow: hidden;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #4ade80, #22d3ee);
                border-radius: 4px;
                width: 0%;
                transition: width 0.3s ease;
            }}
            
            .btn {{
                background: white;
                color: #667eea;
                padding: 1rem 2rem;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                margin: 1rem 0.5rem;
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }}
            .btn:hover {{ 
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            }}
            .btn:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }}
            .alt-btn {{
                background: transparent;
                color: white;
                border: 2px solid white;
            }}
            .error-message {{
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.5);
                padding: 1rem;
                border-radius: 10px;
                margin: 2rem 0;
                display: none;
            }}
            .success-message {{
                background: rgba(74, 222, 128, 0.2);
                border: 1px solid rgba(74, 222, 128, 0.5);
                padding: 1rem;
                border-radius: 10px;
                margin: 2rem 0;
                display: none;
            }}
            .loading-steps {{
                text-align: left;
                margin: 2rem 0;
                font-size: 14px;
            }}
            .step {{
                padding: 0.5rem 0;
                opacity: 0.6;
                transition: opacity 0.3s ease;
            }}
            .step.active {{ opacity: 1; font-weight: 500; }}
            .step.complete {{ opacity: 0.8; }}
            .step.complete::before {{
                content: '✓ ';
                color: #4ade80;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="launch-container">
            <div id="loadingState">
                <div class="spinner"></div>
                <h1>🚀 Launching Analysis Platform</h1>
                <p><span class="status-indicator status-checking" id="statusIndicator"></span>Connecting to your analysis platform...</p>
                
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                
                <div class="loading-steps">
                    <div class="step" id="step1">🔒 Verifying authentication</div>
                    <div class="step" id="step2">🔗 Connecting to analysis platform</div>
                    <div class="step" id="step3">📊 Loading ASC standards (606, 842, 718, 805, 340-40)</div>
                    <div class="step" id="step4">🤖 Initializing Research Assistant</div>
                </div>
                
                <p style="font-size: 14px; opacity: 0.8;">
                    Your complete technical accounting analysis suite
                </p>
            </div>
            
            <div id="successState" style="display: none;">
                <div class="success-message">
                    <h2>✅ Platform Ready!</h2>
                    <p>Your analysis platform is ready. Opening now...</p>
                </div>
                <button class="btn" onclick="openStreamlit()">
                    Open Analysis Platform
                </button>
            </div>
            
            <div id="errorState" style="display: none;">
                <div class="error-message">
                    <h2>⚠️ Connection Issue</h2>
                    <p id="errorMessage">Unable to connect to the analysis platform. Please try again.</p>
                </div>
                <button class="btn" onclick="retryConnection()">
                    Retry Connection
                </button>
                <br>
                <button class="alt-btn btn" onclick="goBack()">
                    Back to Dashboard
                </button>
            </div>
        </div>
        
        <script>
            const steps = ['step1', 'step2', 'step3', 'step4'];
            let currentStep = 0;
            let connectionAttempts = 0;
            const maxAttempts = 3;
            const redirectUrl = '{redirect_url}';
            
            function updateProgress(percentage) {{
                document.getElementById('progressFill').style.width = percentage + '%';
            }}
            
            function activateStep(stepIndex) {{
                if (stepIndex > 0) {{
                    document.getElementById(steps[stepIndex - 1]).classList.add('complete');
                    document.getElementById(steps[stepIndex - 1]).classList.remove('active');
                }}
                if (stepIndex < steps.length) {{
                    document.getElementById(steps[stepIndex]).classList.add('active');
                }}
            }}
            
            function showError(message) {{
                document.getElementById('loadingState').style.display = 'none';
                document.getElementById('errorState').style.display = 'block';
                document.getElementById('errorMessage').textContent = message;
                document.getElementById('statusIndicator').className = 'status-indicator status-error';
            }}
            
            function showSuccess() {{
                document.getElementById('loadingState').style.display = 'none';
                document.getElementById('successState').style.display = 'block';
                document.getElementById('statusIndicator').className = 'status-indicator';
            }}
            
            async function checkPlatformStatus() {{
                try {{
                    // Try to reach the Streamlit platform
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 5000);
                    
                    const response = await fetch(redirectUrl, {{
                        method: 'HEAD',
                        mode: 'no-cors',
                        signal: controller.signal
                    }});
                    
                    clearTimeout(timeoutId);
                    return true;
                }} catch (error) {{
                    return false;
                }}
            }}
            
            async function launchSequence() {{
                connectionAttempts++;
                
                // Step 1: Authentication
                activateStep(0);
                updateProgress(20);
                await new Promise(resolve => setTimeout(resolve, 800));
                
                // Step 2: Platform connection
                activateStep(1);
                updateProgress(40);
                
                const platformAvailable = await checkPlatformStatus();
                
                if (!platformAvailable && connectionAttempts < maxAttempts) {{
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    updateProgress(50);
                    return launchSequence(); // Retry
                }}
                
                if (!platformAvailable) {{
                    showError('Analysis platform is temporarily unavailable. Please try again in a few moments.');
                    return;
                }}
                
                // Step 3: Loading standards
                activateStep(2);
                updateProgress(70);
                await new Promise(resolve => setTimeout(resolve, 800));
                
                // Step 4: Research Assistant
                activateStep(3);
                updateProgress(90);
                await new Promise(resolve => setTimeout(resolve, 800));
                
                // Complete
                activateStep(4);
                updateProgress(100);
                await new Promise(resolve => setTimeout(resolve, 500));
                
                showSuccess();
                setTimeout(openStreamlit, 1500);
            }}
            
            function openStreamlit() {{
                window.location.href = redirectUrl;
            }}
            
            function retryConnection() {{
                connectionAttempts = 0;
                currentStep = 0;
                document.getElementById('errorState').style.display = 'none';
                document.getElementById('loadingState').style.display = 'block';
                document.getElementById('statusIndicator').className = 'status-indicator status-checking';
                
                // Reset progress and steps
                updateProgress(0);
                steps.forEach(step => {{
                    document.getElementById(step).classList.remove('active', 'complete');
                }});
                
                setTimeout(launchSequence, 500);
            }}
            
            function goBack() {{
                window.location.href = '/dashboard.html';
            }}
            
            // Start the launch sequence
            setTimeout(launchSequence, 1000);
        </script>
    </body>
    </html>
    """
    
    return html_content

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

def generate_verification_token():
    """Generate a secure email verification token"""
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
        
        # Create unverified account that requires email verification
        cursor.execute("""
            INSERT INTO users (email, first_name, last_name, company_name, job_title, 
                             password_hash, terms_accepted_at, email_verified)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), FALSE)
            RETURNING id
        """, (email, first_name, last_name, company_name, job_title, password_hash))
        
        user_id = cursor.fetchone()['id']
        
        # Generate verification token
        verification_token = generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
        
        # Store verification token
        cursor.execute("""
            INSERT INTO email_verification_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user_id, verification_token, expires_at))
        
        conn.commit()
        conn.close()
        
        # Send verification email
        postmark_client = PostmarkClient()
        email_sent = postmark_client.send_email_verification(
            user_email=email,
            user_name=first_name,
            verification_token=verification_token
        )
        
        if email_sent:
            logger.info(f"Email verification sent successfully to {email}")
        else:
            logger.error(f"Failed to send email verification to {email}")
        
        logger.info(f"User {email} registered successfully - pending email verification")
        
        return jsonify({
            'message': 'Registration successful! Please check your email and click the verification link to complete your account setup.',
            'user_id': user_id,
            'verification_required': True
        }), 201
            
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """Handle enterprise user login with password authentication"""
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
                   credits_balance, password_hash, created_at, email_verified
            FROM users 
            WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if email is verified
        if not user['email_verified']:
            return jsonify({
                'error': 'Please verify your email address before logging in. Check your inbox for a verification email.',
                'verification_required': True
            }), 403
        
        # All users are now enterprise users - password required
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        if not user['password_hash']:
            return jsonify({'error': 'User account is corrupted. Please contact support'}), 500
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid password'}), 401
        
        # Generate login token with domain information for cross-subdomain auth
        login_token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(days=7),
            'purpose': 'authentication',
            'domain': 'veritaslogic.ai',  # Allow token to work across subdomains
            'issued_at': datetime.utcnow().isoformat()
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        # Create response with enhanced user data for cross-subdomain sharing
        response_data = {
            'message': 'Login successful',
            'token': login_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'company_name': user['company_name'],
                'job_title': user['job_title'],
                'credits_balance': float(user['credits_balance'] or 0),
                'free_analyses_remaining': 0,  # Legacy field removed, always 0 for enterprise
                'email_verified': bool(user['email_verified'])
            },
            'redirect_urls': {
                'dashboard': f"{WEBSITE_URL}/dashboard.html",
                'streamlit': STREAMLIT_URL
            }
        }
        
        # Create response and optionally set cross-domain cookies for better UX
        response = jsonify(response_data)
        
        # In production, set secure cookies for *.veritaslogic.ai
        if not request.host.startswith('localhost') and not request.host.startswith('127.0.0.1'):
            response.set_cookie(
                'vl_auth_token', 
                login_token, 
                domain='.veritaslogic.ai',  # Works across all subdomains
                secure=True,  # HTTPS only
                httponly=False,  # Allow JS access for Streamlit
                samesite='Lax',  # Cross-site requests allowed
                max_age=7*24*60*60  # 7 days
            )
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/validate-token', methods=['POST'])
def validate_cross_domain_token():
    """Validate authentication token for cross-subdomain access"""
    try:
        data = request.get_json()
        token = data.get('token') if data else None
        
        # Also check Authorization header as fallback
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '')
        
        # Also check cookies for seamless cross-subdomain experience
        if not token:
            token = request.cookies.get('vl_auth_token')
        
        if not token:
            return jsonify({'valid': False, 'error': 'No token provided'}), 400
        
        # Verify token
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'valid': False, 'error': payload['error']}), 401
        
        # Get fresh user data to ensure account is still active and verified
        user_id = payload['user_id']
        conn = get_db_connection()
        if not conn:
            return jsonify({'valid': False, 'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, first_name, last_name, company_name, job_title, 
                   credits_balance, email_verified, created_at
            FROM users 
            WHERE id = %s AND email_verified = true
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'valid': False, 'error': 'User not found or not verified'}), 404
        
        # Return validation success with fresh user data
        return jsonify({
            'valid': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'company_name': user['company_name'],
                'job_title': user['job_title'],
                'credits_balance': float(user['credits_balance'] or 0),
                'email_verified': bool(user['email_verified']),
                'member_since': user['created_at'].isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({'valid': False, 'error': 'Token validation failed'}), 500

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
        
        # Check if user exists
        cursor.execute("""
            SELECT id, first_name
            FROM users 
            WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        
        if not user:
            # Return success even if user doesn't exist for security
            return jsonify({
                'message': 'If an account with that email exists, you will receive a password reset email.'
            }), 200
        
        # All users are now enterprise users - can reset passwords
        
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
        
        # Send password reset email
        postmark_client = PostmarkClient()
        email_sent = postmark_client.send_password_reset_email(
            user_email=email,
            user_name=user['first_name'],
            reset_token=reset_token
        )
        
        if email_sent:
            logger.info(f"Password reset email sent successfully to {email}")
        else:
            logger.error(f"Failed to send password reset email to {email}")
        
        # Always return success message for security (don't reveal if email failed)
        # Token should NEVER be returned in API response for security
        return jsonify({
            'message': 'If an account with that email exists, you will receive a password reset email.'
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
        
        # Update user password
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s
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

@app.route('/api/resend-verification', methods=['POST'])
def resend_verification():
    """Resend email verification for authenticated user"""
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
        
        # Get user data and check if already verified
        cursor.execute("""
            SELECT email, first_name, email_verified
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        if user['email_verified']:
            conn.close()
            return jsonify({'error': 'Email is already verified'}), 400
        
        # Check for rate limiting (max 3 requests per hour per user)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM email_verification_tokens 
            WHERE user_id = %s 
              AND created_at > NOW() - INTERVAL '1 hour'
        """, (user_id,))
        
        recent_requests = cursor.fetchone()
        if recent_requests['count'] >= 3:
            conn.close()
            return jsonify({'error': 'Too many verification requests. Please wait before requesting another.'}), 429
        
        # Invalidate old tokens
        cursor.execute("""
            DELETE FROM email_verification_tokens 
            WHERE user_id = %s
        """, (user_id,))
        
        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        cursor.execute("""
            INSERT INTO email_verification_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user_id, verification_token, expires_at))
        
        conn.commit()
        conn.close()
        
        # Send verification email
        postmark_client = PostmarkClient()
        email_sent = postmark_client.send_email_verification(
            user_email=user['email'],
            user_name=user['first_name'],
            verification_token=verification_token
        )
        
        if email_sent:
            logger.info(f"Verification email resent successfully to {user['email']}")
            return jsonify({
                'message': 'Verification email sent! Please check your inbox and click the verification link.'
            }), 200
        else:
            logger.error(f"Failed to resend verification email to {user['email']}")
            return jsonify({'error': 'Failed to send verification email. Please try again later.'}), 500
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        return jsonify({'error': 'Failed to resend verification email'}), 500

@app.route('/api/verify-email', methods=['POST'])
def verify_email():
    """Handle email verification with token"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        
        if not token:
            return jsonify({'error': 'Verification token is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Find valid verification token
        cursor.execute("""
            SELECT evt.user_id, u.email, u.first_name
            FROM email_verification_tokens evt
            JOIN users u ON evt.user_id = u.id
            WHERE evt.token = %s 
              AND evt.expires_at > NOW()
              AND evt.verified_at IS NULL
        """, (token,))
        
        verification_request = cursor.fetchone()
        
        if not verification_request:
            conn.close()
            return jsonify({'error': 'Invalid or expired verification token'}), 400
        
        user_id = verification_request['user_id']
        user_email = verification_request['email']
        
        # Mark user as verified
        cursor.execute("""
            UPDATE users 
            SET email_verified = TRUE
            WHERE id = %s
        """, (user_id,))
        
        # Mark token as used
        cursor.execute("""
            UPDATE email_verification_tokens 
            SET verified_at = NOW()
            WHERE token = %s
        """, (token,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Email verification successful for user {user_email}")
        
        return jsonify({
            'message': 'Email verified successfully! You can now log in to your account.'
        }), 200
        
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        return jsonify({'error': 'Email verification failed'}), 500

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
            SELECT password_hash
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # All users are now enterprise users - verify current password required
        if not current_password:
            return jsonify({'error': 'Current password is required'}), 400
        
        if not user['password_hash'] or not verify_password(current_password, user['password_hash']):
            conn.close()
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update password
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s
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
                   credits_balance, created_at, email_verified
            FROM users 
            WHERE id = %s
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
                'credits_balance': float(user['credits_balance'] or 0),
                'free_analyses_remaining': 0,  # Legacy field removed, always 0 for enterprise
                'member_since': user['created_at'].isoformat(),
                'email_verified': bool(user['email_verified'])
            },
            'recent_analyses': [
                {
                    'asc_standard': analysis['asc_standard'],
                    'cost': float(analysis['billed_credits'] or 0),
                    'completed_at': analysis['completed_at'].isoformat()
                }
                for analysis in recent_analyses
            ],
            'transactions': [
                {
                    'amount': float(transaction['amount'] or 0),
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
            SELECT credits_balance
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        can_proceed = (user['credits_balance'] >= required_credits)
        
        return jsonify({
            'can_proceed': can_proceed,
            'credits_balance': float(user['credits_balance'] or 0),
            'free_analyses_remaining': 0,  # Legacy field removed, always 0 for enterprise
            'is_free_analysis': False  # No free analyses in enterprise model
        }), 200
        
    except Exception as e:
        logger.error(f"Check credits error: {e}")
        return jsonify({'error': 'Failed to check credits'}), 500

@app.route('/api/analysis/complete', methods=['POST'])
def complete_analysis():
    """Unified endpoint for analysis completion - handles both recording and billing atomically"""
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
        
        # Extract and validate input data
        asc_standard = sanitize_string(data.get('asc_standard', ''), 50)
        words_count = max(0, int(data.get('words_count', 0)))
        api_cost = Decimal(str(data.get('api_cost', 0)))  # What OpenAI actually charged
        file_count = max(0, int(data.get('file_count', 0)))
        tier_name = sanitize_string(data.get('tier_name', ''), 100)
        is_free_analysis = data.get('is_free_analysis', False)
        idempotency_key = sanitize_string(data.get('idempotency_key', ''), 100)
        started_at = data.get('started_at')
        duration_seconds = max(0, int(data.get('duration_seconds', 0)))
        
        # Server-side cost calculation (no more client-provided billing amounts)
        from shared.pricing_config import get_price_tier
        tier_info = get_price_tier(words_count)
        final_charged_credits = Decimal(str(tier_info['price']))
        
        # Generate customer-facing memo UUID
        import uuid
        memo_uuid = str(uuid.uuid4())[:8]
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            # Check idempotency - prevent duplicate charges
            if idempotency_key:
                cursor.execute("""
                    SELECT analysis_id, memo_uuid FROM credit_transactions 
                    WHERE user_id = %s AND reason = 'analysis_charge' 
                    AND metadata->>'idempotency_key' = %s
                """, (user_id, idempotency_key))
                existing = cursor.fetchone()
                if existing:
                    return jsonify({
                        'message': 'Analysis already recorded (idempotent)',
                        'analysis_id': existing['analysis_id'],
                        'memo_uuid': existing['memo_uuid'],
                        'final_charged_credits': float(final_charged_credits),
                        'is_duplicate': True
                    }), 200
            
            # Insert analysis record with all required fields (including billed_credits for backward compatibility)
            cursor.execute("""
                INSERT INTO analyses (user_id, asc_standard, words_count, est_api_cost, 
                                    final_charged_credits, billed_credits, tier_name, status, memo_uuid,
                                    started_at, completed_at, duration_seconds, file_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'completed', %s, %s, NOW(), %s, %s)
                RETURNING id
            """, (user_id, asc_standard, words_count, api_cost, final_charged_credits, 
                  final_charged_credits, tier_name, memo_uuid, started_at, duration_seconds, file_count))
            
            analysis_id = cursor.fetchone()['id']
            
            # Get current balance for balance_after calculation
            cursor.execute("SELECT credits_balance FROM users WHERE id = %s", (user_id,))
            current_balance = cursor.fetchone()['credits_balance']
            
            if is_free_analysis:
                # No free analyses in enterprise model - this is for backward compatibility only
                pass  # No database update needed since free_analyses_remaining field was removed
                
                balance_after = current_balance  # No credit charge for free analysis
                
                # Record credit transaction for tracking (zero amount)
                cursor.execute("""
                    INSERT INTO credit_transactions (user_id, analysis_id, amount, reason, 
                                                   balance_after, memo_uuid, metadata, created_at)
                    VALUES (%s, %s, %s, 'analysis_charge', %s, %s, %s, NOW())
                """, (user_id, analysis_id, 0, balance_after, memo_uuid, 
                      json.dumps({'idempotency_key': idempotency_key, 'est_api_cost': float(api_cost)}) if idempotency_key else json.dumps({'est_api_cost': float(api_cost)})))
                
            else:
                # Calculate new balance after charge
                balance_after = max(current_balance - final_charged_credits, 0)
                
                # Deduct from credits balance
                cursor.execute("""
                    UPDATE users 
                    SET credits_balance = %s
                    WHERE id = %s
                """, (balance_after, user_id))
                
                # Record credit transaction with full audit trail
                cursor.execute("""
                    INSERT INTO credit_transactions (user_id, analysis_id, amount, reason,
                                                   balance_after, memo_uuid, metadata, created_at)
                    VALUES (%s, %s, %s, 'analysis_charge', %s, %s, %s, NOW())
                """, (user_id, analysis_id, -final_charged_credits, balance_after, memo_uuid,
                      json.dumps({'idempotency_key': idempotency_key, 'est_api_cost': float(api_cost)}) if idempotency_key else json.dumps({'est_api_cost': float(api_cost)})))
            
            conn.commit()
            
            logger.info(f"Analysis completed for user {user_id}: {asc_standard}, memo: {memo_uuid}, cost: {final_charged_credits}")
            
            return jsonify({
                'message': 'Analysis completed successfully',
                'analysis_id': analysis_id,  # Database primary key
                'memo_uuid': memo_uuid,      # Customer-facing ID
                'final_charged_credits': float(final_charged_credits),
                'balance_remaining': float(balance_after),
                'is_free_analysis': is_free_analysis
            }), 200
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Complete analysis error: {e}")
        return jsonify({'error': 'Failed to complete analysis'}), 500

# Legacy endpoint - deprecated but maintained for backwards compatibility
@app.route('/api/user/record-analysis', methods=['POST'])
def record_analysis():
    """DEPRECATED: Use /api/analysis/complete instead - Proxy to new unified endpoint"""
    logger.warning("DEPRECATED ENDPOINT: /api/user/record-analysis called. Use /api/analysis/complete")
    
    try:
        # Transform legacy request format to new unified format
        data = request.get_json()
        
        # Map legacy fields to new format
        transformed_data = {
            'asc_standard': data.get('asc_standard'),
            'words_count': data.get('words_count', 0),
            'est_api_cost': data.get('est_api_cost', 0),  # Use new column name
            'file_count': 1,  # Default for legacy requests
            'tier_name': data.get('tier_name', 'Tier 2'),  # Use actual tier_name instead of price_tier
            'is_free_analysis': data.get('is_free_analysis', False),
            'idempotency_key': f"legacy_{int(datetime.now().timestamp()*1000)}_{data.get('asc_standard', 'unknown')}",
            'started_at': datetime.now().isoformat(),
            'duration_seconds': 0  # Legacy requests don't have timing
        }
        
        # Replace request data for proxy
        request_backup = request.get_json
        request.get_json = lambda: transformed_data
        
        # Call the new unified endpoint
        response = complete_analysis()
        
        # Restore original request
        request.get_json = request_backup
        
        return response
        
    except Exception as e:
        logger.error(f"Legacy record analysis proxy error: {e}")
        return jsonify({'error': 'Failed to record analysis via legacy endpoint'}), 500

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
                'balance': float(result['credits_balance'] or 0)
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
        
        current_balance = float(result['credits_balance'] or 0)
        
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
        new_balance = float(result['credits_balance'] or 0)
        
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

@app.route('/api/contact', methods=['POST'])
def contact_form():
    """Handle unified contact form submissions via Postmark"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['inquiry_type', 'name', 'email', 'company', 'role', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Send email using direct Postmark API (more reliable)
        api_key = os.getenv('POSTMARK_API_KEY')
        if not api_key:
            raise Exception("POSTMARK_API_KEY not configured")
            
        # Prepare email content based on inquiry type
        inquiry_type = data.get('inquiry_type')
        name = data.get('name')
        email = data.get('email')
        company = data.get('company')
        role = data.get('role')
        message = data.get('message')
        
        # Get optional conditional fields
        monthly_volume = data.get('monthly_volume', '')
        team_size = data.get('team_size', '')
        implementation_timeframe = data.get('implementation_timeframe', '')
        
        # Create subject line based on inquiry type
        subject_map = {
            'professional-services': 'Professional Services Inquiry',
            'enterprise-sales': 'Enterprise Sales Inquiry',
            'demo-request': 'Demo Request',
            'technical-support': 'Technical Support Request',
            'general-inquiry': 'General Inquiry'
        }
        subject = subject_map.get(inquiry_type, 'Contact Form Submission')
        
        # Create email body
        email_body = f"""
New contact form submission from VeritasLogic.ai

Contact Information:
- Name: {name}
- Email: {email}
- Company: {company}
- Role: {role}
- Inquiry Type: {inquiry_type.replace('-', ' ').title()}

"""
        
        # Add conditional fields if present
        if monthly_volume:
            email_body += f"- Expected Monthly Volume: {monthly_volume}\n"
        if team_size:
            email_body += f"- Team Size: {team_size}\n"
        if implementation_timeframe:
            email_body += f"- Implementation Timeframe: {implementation_timeframe}\n"
        
        email_body += f"""
Message:
{message}

---
Sent from VeritasLogic.ai contact form
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        # Send email via direct Postmark API
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Postmark-Server-Token': api_key
        }
        
        email_data = {
            'From': 'support@veritaslogic.ai',
            'To': 'support@veritaslogic.ai',
            'Subject': f'[VeritasLogic] {subject} - {company}',
            'TextBody': email_body,
            'ReplyTo': email
        }
        
        response = requests.post(
            'https://api.postmarkapp.com/email',
            json=email_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Postmark API error: {response.status_code} - {response.text}")
        
        logger.info(f"Contact form submitted: {inquiry_type} from {email} ({company})")
        
        return jsonify({
            'success': True,
            'message': 'Your message has been sent successfully! We\'ll respond within 4 hours during business days.'
        }), 200
        
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return jsonify({
            'error': 'Failed to send message. Please try again or email us directly at hello@veritaslogic.ai'
        }), 500

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
                COALESCE(a.memo_uuid, a.id::text) as id,
                a.asc_standard,
                a.completed_at,
                a.status,
                a.final_charged_credits as cost,
                a.words_count,
                a.file_count,
                a.tier_name,
                CONCAT(a.asc_standard, ' Analysis') as document_name
            FROM analyses a
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
                'words_count': int(row['words_count']) if row['words_count'] else 0,
                'file_count': int(row['file_count']) if row['file_count'] else 0,
                'tier_name': row['tier_name'] or 'Unknown'
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
    """DEPRECATED: Save completed analysis to database - Use /api/analysis/complete instead"""
    logger.warning("DEPRECATED ENDPOINT: /api/save-analysis called. Use /api/analysis/complete")
    return jsonify({'error': 'Endpoint deprecated. Use /api/analysis/complete'}), 410

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
