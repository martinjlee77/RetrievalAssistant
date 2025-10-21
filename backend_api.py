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
from shared.log_sanitizer import sanitize_for_log, sanitize_exception_for_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DEPLOYMENT FIX: Enhanced logging for Gunicorn production environment
veritaslogic_logger = logging.getLogger('veritaslogic.backend')
veritaslogic_logger.setLevel(logging.INFO)
veritaslogic_logger.info("Enhanced VeritasLogic backend logging initialized")

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

# Environment configuration
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
STREAMLIT_URL = os.getenv('STREAMLIT_URL', 'https://tas.veritaslogic.ai')
INITIAL_SIGNUP_CREDITS = Decimal(os.getenv('INITIAL_SIGNUP_CREDITS', '295.00'))
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

app = Flask(__name__, static_folder='veritaslogic_multipage_website', static_url_path='/static')

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

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('veritaslogic_multipage_website', 'dashboard.html')

def attempt_token_refresh(request_obj):
    """
    Attempt to refresh an expired token using refresh token from cookies
    Returns new access token on success, None on failure
    """
    try:
        # Get refresh token from HTTP-only cookie
        refresh_token = request_obj.cookies.get('refresh_token')
        if not refresh_token:
            logger.info("No refresh token found in cookies")
            return None
        
        # Verify refresh token
        payload = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=['HS256'])
        
        # Ensure it's a refresh token
        if payload.get('purpose') != 'refresh':
            logger.warning("Found token but it's not a refresh token")
            return None
        
        # Generate new short-lived access token
        new_access_token = jwt.encode({
            'user_id': payload['user_id'],
            'email': payload['email'],
            'exp': datetime.utcnow() + timedelta(hours=4),  # Extended for large contracts
            'purpose': 'access',
            'domain': 'veritaslogic.ai',
            'issued_at': datetime.utcnow().isoformat()
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        logger.info(f"Successfully refreshed token for user {payload['email']}")
        return new_access_token
        
    except jwt.ExpiredSignatureError:
        logger.info("Refresh token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.info("Invalid refresh token")
        return None
    except Exception as e:
        logger.error(f"Token refresh error: {sanitize_for_log(e)}")
        return None

@app.route('/analysis')
def serve_streamlit_app():
    """Redirect to Streamlit app with seamless authentication and automatic token refresh"""
    
    # Check if user is authenticated
    auth_header = request.headers.get('Authorization')
    token = None
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    
    # Also check cookies
    if not token:
        token = request.cookies.get('vl_auth_token')
    
    # Preserve any query parameters from the incoming request (e.g., analysis_id=123)
    query_string = request.query_string.decode('utf-8')
    
    # Determine the Streamlit page to open based on analysis_id
    page_param = ""
    analysis_id = request.args.get('analysis_id')
    if analysis_id:
        try:
            # Query database to get asc_standard for this analysis
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT asc_standard FROM analyses WHERE id = %s",
                (int(analysis_id),)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                asc_standard = result['asc_standard']
                # Map ASC standards to Streamlit page titles (URL-encoded)
                page_mapping = {
                    'ASC 606': 'ASC%20606%3A%20Revenue%20Recognition',
                    'ASC 340-40': 'ASC%20340-40%3A%20Cost%20to%20Obtain',
                    'ASC 842': 'ASC%20842%3A%20Leases%20(Lessee)',
                    'ASC 718': 'ASC%20718%3A%20Stock%20Compensation',
                    'ASC 805': 'ASC%20805%3A%20Business%20Combinations',
                }
                page_title = page_mapping.get(asc_standard)
                if page_title:
                    page_param = f"&page={page_title}"
        except Exception as e:
            logger.error(f"Error determining page for analysis_id {analysis_id}: {e}")
    
    extra_params = f"&{query_string}{page_param}" if query_string else page_param
    
    # Build redirect URL with automatic token refresh
    if token:
        # Validate token before redirecting
        payload = verify_token(token)
        if 'error' not in payload:
            # Token is valid, use it
            redirect_url = f"{STREAMLIT_URL}?auth_token={token}{extra_params}"
        else:
            # Token is expired/invalid, try to refresh it
            logger.info(f"Token validation failed: {payload.get('error', 'Unknown error')}, attempting refresh")
            refreshed_token = attempt_token_refresh(request)
            if refreshed_token:
                logger.info("Token refresh successful, redirecting with new token")
                redirect_url = f"{STREAMLIT_URL}?auth_token={refreshed_token}{extra_params}"
            else:
                logger.info("Token refresh failed, redirecting without token")
                redirect_url = f"{STREAMLIT_URL}{extra_params}" if extra_params else STREAMLIT_URL
    else:
        # No token found, try refresh anyway (user might be logged in via dashboard session)
        logger.info("No token found, attempting refresh from dashboard session")
        refreshed_token = attempt_token_refresh(request)
        if refreshed_token:
            logger.info("Dashboard session refresh successful, redirecting with new token")
            redirect_url = f"{STREAMLIT_URL}?auth_token={refreshed_token}{extra_params}"
        else:
            logger.info("No valid session found, redirecting without token")
            redirect_url = f"{STREAMLIT_URL}{extra_params}" if extra_params else STREAMLIT_URL
    
    # Build enhanced HTML response with error handling and status checking
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VeritasLogic Analysis Platform</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Poppins', sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background: #36404A;
                color: white;
            }}
            .launch-container {{
                text-align: center;
                background: #212F3C;
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
                background: linear-gradient(90deg, #ffffff, #A88A57);
                border-radius: 4px;
                width: 0%;
                transition: width 0.3s ease;
            }}
            
            .btn {{
                background: white;
                color: #212F3C;
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
                <h1>Launching Analysis Platform</h1>
                <p><span class="status-indicator status-checking" id="statusIndicator"></span>Connecting to your analysis platform...</p>
                
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                
                <div class="loading-steps">
                    <div class="step" id="step1">Verifying authentication</div>
                    <div class="step" id="step2">Connecting to analysis platform</div>
                    <div class="step" id="step3">Loading ASC standards (606, 842, 718, 805, 340-40)</div>
                    <div class="step" id="step4">Initializing Research Assistant</div>
                </div>
                
                <p style="font-size: 14px; opacity: 0.8;">
                    Your AI-powered technical accounting analysis
                </p>
            </div>
            
            <div id="successState" style="display: none;">
                <div class="success-message">
                    <h2>✅ Platform Ready!</h2>
                    <p>Your analysis platform is ready. Opening now...</p>
                </div>
                <button class="btn" onclick="openStreamlit()">
                    Opening Analysis Platform
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
            const redirectUrl = {json.dumps(redirect_url)};
            
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
    """Serve static files with clean URL support (e.g., /about instead of /about.html)"""
    import os
    
    static_folder = 'veritaslogic_multipage_website'
    
    # Try serving the exact path first
    try:
        return send_from_directory(static_folder, path)
    except:
        pass
    
    # If not found and doesn't end with .html, try adding .html extension
    if not path.endswith('.html'):
        html_path = f'{path}.html'
        try:
            return send_from_directory(static_folder, html_path)
        except:
            pass
    
    # Return 404 if neither worked
    return "Page not found", 404

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'veritaslogic-secret-key-change-in-production')


# Database connection
def get_db_connection():
    """Get database connection using DATABASE_URL or individual environment variables"""
    try:
        # Try DATABASE_URL first (for Railway/production)
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(
                database_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            return conn
        
        # Fall back to individual variables (for Replit/development)
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
        logger.error(f"Database connection error: {sanitize_for_log(e)}")
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
        
        # Get marketing opt-in preference (defaults to False if not provided)
        marketing_opt_in = data.get('marketing_opt_in', False)
        
        # Create unverified account that requires email verification
        cursor.execute("""
            INSERT INTO users (email, first_name, last_name, company_name, job_title, 
                             password_hash, terms_accepted_at, email_verified, marketing_opt_in)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), FALSE, %s)
            RETURNING id
        """, (email, first_name, last_name, company_name, job_title, password_hash, marketing_opt_in))
        
        user_id = cursor.fetchone()['id']
        
        # Generate verification token
        verification_token = generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
        
        # Store verification token
        cursor.execute("""
            INSERT INTO email_verification_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user_id, verification_token, expires_at))
        
        # Award initial signup credits if configured and not already awarded
        if INITIAL_SIGNUP_CREDITS > 0:
            # Check if signup bonus already awarded (idempotency check)
            cursor.execute("""
                SELECT id FROM credit_transactions 
                WHERE user_id = %s AND reason = 'signup_bonus_v1'
            """, (user_id,))
            
            if not cursor.fetchone():
                # Award signup credits
                cursor.execute("""
                    UPDATE users 
                    SET credits_balance = credits_balance + %s
                    WHERE id = %s
                    RETURNING credits_balance
                """, (INITIAL_SIGNUP_CREDITS, user_id))
                
                new_balance = cursor.fetchone()['credits_balance']
                
                # Record the transaction for audit trail
                cursor.execute("""
                    INSERT INTO credit_transactions 
                    (user_id, amount, reason, balance_after, metadata)
                    VALUES (%s, %s, 'signup_bonus_v1', %s, %s)
                """, (user_id, INITIAL_SIGNUP_CREDITS, new_balance, 
                      json.dumps({'awarded_at': datetime.utcnow().isoformat()})))
                
                logger.info(f"Awarded ${INITIAL_SIGNUP_CREDITS} signup bonus to user {email}")
        
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
        
        # Send admin notification for new signup (don't block on failure)
        if INITIAL_SIGNUP_CREDITS > 0:
            admin_notified = postmark_client.send_new_signup_notification(
                user_email=email,
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                job_title=job_title,
                awarded_credits=float(INITIAL_SIGNUP_CREDITS)
            )
            if admin_notified:
                logger.info(f"Admin notified of new signup: {email}")
            else:
                logger.warning(f"Failed to send admin notification for new signup: {email}")
        
        logger.info(f"User {email} registered successfully - pending email verification")
        
        return jsonify({
            'message': 'Registration successful! Please check your email and click the verification link to complete your account setup.',
            'user_id': user_id,
            'verification_required': True
        }), 201
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"Signup error: {error_type} - {error_msg}")
        
        # Send database error alert for signup failures (critical operation)
        try:
            postmark = PostmarkClient()
            # Get user email if available in locals
            affected_user = email if 'email' in locals() else 'Unknown'
            postmark.send_database_error_alert(
                operation="user signup",
                error_type=error_type,
                error_details=error_msg,
                affected_user=affected_user
            )
            logger.info("Database error alert sent to support")
        except Exception as alert_error:
            logger.error(f"Failed to send database error alert: {alert_error}")
        
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
                   credits_balance, password_hash, created_at, email_verified, research_assistant_access
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
        # STRATEGIC FIX: Create short-lived access token + refresh token system
        access_token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=4),  # Extended for large contracts
            'purpose': 'access',
            'domain': 'veritaslogic.ai',
            'issued_at': datetime.utcnow().isoformat()
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        refresh_token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(days=7),  # Long-lived refresh token
            'purpose': 'refresh',
            'domain': 'veritaslogic.ai',
            'issued_at': datetime.utcnow().isoformat()
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        login_token = access_token  # For backward compatibility
        
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
                'email_verified': bool(user['email_verified']),
                'research_assistant_access': bool(user['research_assistant_access'])
            },
            'redirect_urls': {
                'dashboard': f"{WEBSITE_URL}/dashboard.html",
                'streamlit': STREAMLIT_URL
            }
        }
        
        # Create response and set refresh token cookie
        response = jsonify(response_data)
        
        # STRATEGIC FIX: Set refresh token cookie with proper cross-domain settings
        if not request.host.startswith('localhost') and not request.host.startswith('127.0.0.1'):
            # Production: Set for all .veritaslogic.ai subdomains
            response.set_cookie(
                'refresh_token',
                refresh_token,
                max_age=7*24*60*60,  # 7 days
                domain='.veritaslogic.ai',  # Works across all subdomains
                httponly=True,
                secure=True,
                samesite='None'  # Allow cross-site for subdomain access
            )
        else:
            # Development: Set for local testing
            response.set_cookie(
                'refresh_token',
                refresh_token,
                max_age=7*24*60*60,  # 7 days
                httponly=True,
                secure=False,  # Local development doesn't use HTTPS
                samesite='Lax'  # Local development
            )
        
        # In production, set secure cookies for *.veritaslogic.ai
        if not request.host.startswith('localhost') and not request.host.startswith('127.0.0.1'):
            response.set_cookie(
                'vl_auth_token', 
                login_token, 
                domain='.veritaslogic.ai',  # Works across all subdomains
                secure=True,  # HTTPS only
                httponly=False,  # Allow JS access for Streamlit
                samesite='Lax',  # Cross-site requests allowed
                max_age=10*60  # STRATEGIC FIX: 10 minutes instead of 7 days
            )
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Login error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/refresh-token', methods=['POST'])
def refresh_access_token():
    """Generate new access token using refresh token"""
    try:
        # Get refresh token from HTTP-only cookie
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            return jsonify({'error': 'Refresh token not found'}), 401
        
        # Verify refresh token
        payload = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=['HS256'])
        
        # Ensure it's a refresh token
        if payload.get('purpose') != 'refresh':
            return jsonify({'error': 'Invalid refresh token'}), 401
        
        # Generate new short-lived access token
        new_access_token = jwt.encode({
            'user_id': payload['user_id'],
            'email': payload['email'],
            'exp': datetime.utcnow() + timedelta(hours=4),  # Extended for large contracts
            'purpose': 'access',
            'domain': 'veritaslogic.ai',
            'issued_at': datetime.utcnow().isoformat()
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': new_access_token,
            'expires_in': 600  # 10 minutes in seconds
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@app.route('/api/auth/validate-token', methods=['GET', 'POST'])
def validate_cross_domain_token():
    """Validate authentication token for cross-subdomain access"""
    try:
        # Handle both GET and POST requests
        if request.method == 'POST':
            data = request.get_json()
            token = data.get('token') if data else None
        else:
            token = None
        
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
            conn.close()
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
        logger.error(f"Forgot password error: {sanitize_for_log(e)}")
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
            conn.close()
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
                   credits_balance, created_at, email_verified, research_assistant_access
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
                'email_verified': bool(user['email_verified']),
                'research_assistant_access': bool(user['research_assistant_access'])
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
            SELECT credits_balance, email_verified
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check email verification first
        if not user['email_verified']:
            return jsonify({
                'can_proceed': False,
                'error': 'Email verification required',
                'message': 'Please verify your email address before running analyses.',
                'credits_balance': float(user['credits_balance'] or 0),
                'email_verified': False
            }), 403
        
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

@app.route('/api/analysis/create', methods=['POST'])
def create_pending_analysis():
    """Create a pending analysis record before job submission (stores authoritative pricing)"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        data = request.get_json()
        
        # Extract and validate data (no client-side analysis_id)
        asc_standard = sanitize_string(data.get('asc_standard', ''), 50)
        words_count = max(0, int(data.get('words_count', 0)))
        tier_name = sanitize_string(data.get('tier_name', ''), 100)
        file_count = max(0, int(data.get('file_count', 0)))
        
        # SERVER-SIDE PRICING VALIDATION
        from shared.pricing_config import get_price_tier
        tier_info = get_price_tier(words_count)
        cost_to_charge = Decimal(str(tier_info['price']))
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            # Verify email
            cursor.execute("SELECT email_verified, credits_balance FROM users WHERE id = %s", (user_id,))
            user_check = cursor.fetchone()
            if not user_check or not user_check['email_verified']:
                return jsonify({'error': 'Email verification required'}), 403
            
            # Check sufficient credits
            if user_check['credits_balance'] < cost_to_charge:
                return jsonify({'error': 'Insufficient credits'}), 402
            
            # Insert pending analysis with authoritative pricing
            import uuid
            memo_uuid = str(uuid.uuid4())[:8]
            
            cursor.execute("""
                INSERT INTO analyses (user_id, asc_standard, words_count, est_api_cost,
                                    final_charged_credits, billed_credits, tier_name, status, memo_uuid,
                                    started_at, file_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                RETURNING analysis_id
            """, (user_id, asc_standard, words_count, 0,
                  cost_to_charge, cost_to_charge, tier_name, 'processing', memo_uuid, file_count))
            
            result = cursor.fetchone()
            db_analysis_id = result['analysis_id']
            
            conn.commit()
            
            return jsonify({
                'message': 'Analysis record created',
                'analysis_id': db_analysis_id,
                'memo_uuid': memo_uuid
            }), 200
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create pending analysis: {sanitize_for_log(e)}")
            raise
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Create pending analysis error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Failed to create analysis record'}), 500

@app.route('/api/analysis/save', methods=['POST'])
def save_worker_analysis():
    """Save completed analysis from background worker with memo content"""
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
        
        # Extract minimal data from worker (analysis_id is database INTEGER)
        try:
            analysis_id = int(data.get('analysis_id', 0))  # Database INTEGER id
        except (ValueError, TypeError):
            return jsonify({'error': 'analysis_id must be a valid integer'}), 400
            
        memo_content = data.get('memo_content', '')  # Full memo text
        api_cost = Decimal(str(data.get('api_cost', 0)))  # For logging only
        success = data.get('success', False)
        error_message = sanitize_string(data.get('error_message', ''), 500) if data.get('error_message') else None
        
        if not analysis_id or analysis_id <= 0:
            return jsonify({'error': 'Valid analysis_id required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            # CRITICAL: Retrieve AUTHORITATIVE pricing from existing analysis record
            # This record was created with server-validated pricing BEFORE job submission
            # Look up by analysis_id (database INTEGER) with user scoping for security
            cursor.execute("""
                SELECT analysis_id, user_id, memo_uuid, asc_standard, words_count, tier_name, 
                       file_count, final_charged_credits, billed_credits, status
                FROM analyses 
                WHERE analysis_id = %s
                AND user_id = %s
            """, (analysis_id, user_id))
            
            existing_record = cursor.fetchone()
            
            if not existing_record:
                logger.error(f"No pending analysis found for user {user_id}")
                return jsonify({'error': 'Analysis record not found'}), 404
            
            # Verify user owns this analysis
            if existing_record['user_id'] != user_id:
                logger.error(f"User {user_id} attempted to save analysis for user {existing_record['user_id']}")
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Check if already completed (idempotency)
            if existing_record['status'] in ['completed', 'failed']:
                logger.warning(f"Duplicate save attempt for analysis {existing_record['analysis_id']}")
                
                # Get current balance
                cursor.execute("SELECT credits_balance FROM users WHERE id = %s", (user_id,))
                current_balance = cursor.fetchone()['credits_balance']
                
                return jsonify({
                    'message': 'Analysis already saved (idempotent)',
                    'analysis_id': existing_record['analysis_id'],
                    'memo_uuid': existing_record['memo_uuid'],
                    'balance_remaining': float(current_balance)
                }), 200
            
            # Use AUTHORITATIVE pricing from database (created at job submission time)
            db_analysis_id = existing_record['analysis_id']
            memo_uuid = existing_record['memo_uuid']
            cost_charged = existing_record['final_charged_credits']  # Server-validated price
            asc_standard = existing_record['asc_standard']
            words_count = existing_record['words_count']
            tier_name = existing_record['tier_name']
            file_count = existing_record['file_count']
            
            analysis_status = 'completed' if success else 'failed'
            
            # Get current balance and verification status
            cursor.execute("SELECT email_verified, credits_balance FROM users WHERE id = %s", (user_id,))
            user_check = cursor.fetchone()
            
            # CRITICAL: If unverified, still persist failure status but don't charge
            if not user_check or not user_check['email_verified']:
                logger.warning(f"Unverified user {user_id} attempted to complete analysis")
                
                # Mark analysis as failed with clear error message
                cursor.execute("""
                    UPDATE analyses 
                    SET status = 'failed',
                        completed_at = NOW(),
                        error_message = 'Email verification required. Please verify your email and try again.'
                    WHERE analysis_id = %s AND user_id = %s
                """, (db_analysis_id, user_id))
                
                conn.commit()
                
                return jsonify({
                    'error': 'Email verification required',
                    'message': 'Analysis marked as failed. No credits charged.'
                }), 403
            
            current_balance = user_check['credits_balance']
            
            # Update analysis record with completion data
            cursor.execute("""
                UPDATE analyses 
                SET status = %s,
                    completed_at = NOW(),
                    est_api_cost = %s,
                    memo_content = %s,
                    error_message = %s,
                    final_charged_credits = %s,
                    billed_credits = %s
                WHERE analysis_id = %s AND user_id = %s
            """, (analysis_status, api_cost, 
                  memo_content if success else None,
                  error_message,
                  cost_charged if success else 0,
                  cost_charged if success else 0,
                  db_analysis_id, user_id))
            
            logger.info(f"Analysis updated: {db_analysis_id}, status: {analysis_status}")
            
            # Only charge credits if successful
            if success and cost_charged > 0:
                balance_after = max(current_balance - cost_charged, 0)
                
                # Deduct credits
                cursor.execute("""
                    UPDATE users 
                    SET credits_balance = %s
                    WHERE id = %s
                """, (balance_after, user_id))
                
                # Record transaction
                cursor.execute("""
                    INSERT INTO credit_transactions (user_id, analysis_id, amount, reason,
                                                   balance_after, memo_uuid, metadata, created_at)
                    VALUES (%s, %s, %s, 'analysis_charge', %s, %s, %s, NOW())
                """, (user_id, db_analysis_id, -cost_charged, balance_after, memo_uuid,
                      json.dumps({'est_api_cost': float(api_cost), 'worker_job': analysis_id})))
                
                logger.info(f"Credits charged: {cost_charged}, new balance: {balance_after}")
            else:
                balance_after = current_balance
                logger.info(f"No credits charged (success={success})")
            
            conn.commit()
            
            return jsonify({
                'message': 'Analysis saved successfully',
                'analysis_id': db_analysis_id,
                'memo_uuid': memo_uuid,
                'balance_remaining': float(balance_after)
            }), 200
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save analysis: {sanitize_for_log(e)}")
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Save analysis error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Failed to save analysis'}), 500

@app.route('/api/analysis/status/<int:analysis_id>', methods=['GET'])
def get_analysis_status(analysis_id):
    """Get analysis status and memo content for polling by analysis_id (database INTEGER)"""
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
        
        try:
            # Query analysis by analysis_id (database INTEGER) with user scoping for security
            cursor.execute("""
                SELECT analysis_id, memo_uuid, status, memo_content, error_message, 
                       completed_at, asc_standard, words_count, tier_name, file_count,
                       final_charged_credits
                FROM analyses 
                WHERE analysis_id = %s
                AND user_id = %s
            """, (analysis_id, user_id))
            
            analysis = cursor.fetchone()
            
            if not analysis:
                return jsonify({'error': 'Analysis not found'}), 404
            
            # Return status and memo if completed
            response = {
                'status': analysis['status'],
                'memo_uuid': analysis['memo_uuid'],
                'asc_standard': analysis['asc_standard'],
                'words_count': analysis['words_count'],
                'tier_name': analysis['tier_name'],
                'file_count': analysis['file_count']
            }
            
            if analysis['status'] == 'completed' and analysis['memo_content']:
                response['memo_content'] = analysis['memo_content']
                response['completed_at'] = analysis['completed_at'].isoformat() if analysis['completed_at'] else None
                response['credits_charged'] = float(analysis['final_charged_credits']) if analysis['final_charged_credits'] else 0
            elif analysis['status'] == 'failed' and analysis['error_message']:
                response['error_message'] = analysis['error_message']
                response['completed_at'] = analysis['completed_at'].isoformat() if analysis['completed_at'] else None
            
            return jsonify(response), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Get analysis status error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Failed to retrieve analysis status'}), 500

@app.route('/api/analysis/recent/<asc_standard>', methods=['GET'])
def get_recent_analysis(asc_standard):
    """Get user's most recent completed analysis for a specific ASC standard (within 24 hours)"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        # Validate ASC standard format
        asc_standard_clean = sanitize_string(asc_standard, 50)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            # Query most recent completed analysis for this user and ASC standard
            # Only return analyses completed within the last 24 hours
            cursor.execute("""
                SELECT analysis_id, memo_uuid, status, memo_content, completed_at, 
                       asc_standard, words_count, tier_name, file_count, final_charged_credits
                FROM analyses 
                WHERE user_id = %s
                AND asc_standard = %s
                AND status = 'completed'
                AND completed_at > NOW() - INTERVAL '24 hours'
                ORDER BY completed_at DESC
                LIMIT 1
            """, (user_id, asc_standard_clean))
            
            analysis = cursor.fetchone()
            
            if not analysis:
                return jsonify({'message': 'No recent analysis found'}), 404
            
            # Return the analysis data
            response = {
                'analysis_id': analysis['analysis_id'],
                'memo_uuid': analysis['memo_uuid'],
                'status': analysis['status'],
                'memo_content': analysis['memo_content'],
                'completed_at': analysis['completed_at'].isoformat() if analysis['completed_at'] else None,
                'asc_standard': analysis['asc_standard'],
                'words_count': analysis['words_count'],
                'tier_name': analysis['tier_name'],
                'file_count': analysis['file_count'],
                'credits_charged': float(analysis['final_charged_credits']) if analysis['final_charged_credits'] else 0
            }
            
            return jsonify(response), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Get recent analysis error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Failed to retrieve recent analysis'}), 500

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
        success = data.get('success', False)  # CRITICAL: Only charge if True
        error_message = sanitize_string(data.get('error_message', ''), 500) if data.get('error_message') else None
        
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
            # DEPLOYMENT FIX: Use enhanced logger for production visibility
            veritaslogic_logger.info(f"BACKEND: Starting analysis completion for user {user_id}")
            logger.info(f"Starting analysis completion for user {user_id}")
            
            # CRITICAL: Verify email before allowing credit spending
            cursor.execute("SELECT email, email_verified FROM users WHERE id = %s", (user_id,))
            user_check = cursor.fetchone()
            if not user_check or not user_check['email_verified']:
                logger.warning(f"Unverified user {user_id} attempted to run analysis")
                return jsonify({
                    'error': 'Email verification required',
                    'message': 'Please verify your email address before running analyses. Check your inbox for the verification link.'
                }), 403
            
            # Store user email for potential error notifications
            user_email = user_check['email']
            
            # Check idempotency - prevent duplicate charges
            if idempotency_key:
                veritaslogic_logger.info(f"BACKEND: Checking idempotency for key: {idempotency_key}")
                logger.info(f"Checking idempotency for key: {idempotency_key}")
                cursor.execute("""
                    SELECT analysis_id, memo_uuid FROM credit_transactions 
                    WHERE user_id = %s AND reason = 'analysis_charge' 
                    AND metadata->>'idempotency_key' = %s
                """, (user_id, idempotency_key))
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"Found existing analysis (idempotent): {existing['analysis_id']}")
                    return jsonify({
                        'message': 'Analysis already recorded (idempotent)',
                        'analysis_id': existing['analysis_id'],
                        'memo_uuid': existing['memo_uuid'],
                        'final_charged_credits': float(final_charged_credits),
                        'is_duplicate': True
                    }), 200
            
            # Insert analysis record with all required fields (including billed_credits for backward compatibility)
            # CRITICAL FIX: Set status based on success flag
            analysis_status = 'completed' if success else 'failed'
            logger.info(f"Inserting analysis record for user {user_id} with status: {analysis_status}")
            
            # Store error_message in metadata for now (until production DB has error_message column)
            # TODO: Add error_message column to production DB, then include it in INSERT
            cursor.execute("""
                INSERT INTO analyses (user_id, asc_standard, words_count, est_api_cost, 
                                    final_charged_credits, billed_credits, tier_name, status, memo_uuid,
                                    started_at, completed_at, duration_seconds, file_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
                RETURNING analysis_id
            """, (user_id, asc_standard, words_count, api_cost, 
                  final_charged_credits if success else 0,  # Only set charged amount if successful
                  final_charged_credits if success else 0,  # Only set billed amount if successful
                  tier_name, analysis_status, memo_uuid, started_at, duration_seconds, file_count))
            
            analysis_id = cursor.fetchone()['analysis_id']
            logger.info(f"Analysis record created with ID: {analysis_id}, status: {analysis_status}")
            
            # Get current balance for balance_after calculation
            logger.info(f"Getting current balance for user {user_id}")
            cursor.execute("SELECT credits_balance FROM users WHERE id = %s", (user_id,))
            current_balance = cursor.fetchone()['credits_balance']
            logger.info(f"Current balance: {current_balance}")
            
            # CRITICAL FIX: Only charge credits if analysis succeeded
            if not success:
                # Failed analysis - record but DON'T charge
                balance_after = current_balance  # Balance unchanged
                logger.info(f"Analysis failed - no credits charged. Balance remains: {current_balance}")
                
                # No credit transaction needed - analysis record already tracks failure with status='failed'
                # Error details stored in analysis metadata
                
            elif is_free_analysis:
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
                # Successful analysis - charge credits
                # Calculate new balance after charge
                balance_after = max(current_balance - final_charged_credits, 0)
                
                # Deduct from credits balance
                logger.info(f"Successful analysis - updating balance from {current_balance} to {balance_after}")
                cursor.execute("""
                    UPDATE users 
                    SET credits_balance = %s
                    WHERE id = %s
                """, (balance_after, user_id))
                logger.info(f"Balance updated successfully")
                
                # Record credit transaction with full audit trail
                logger.info(f"Recording credit transaction for analysis {analysis_id}")
                cursor.execute("""
                    INSERT INTO credit_transactions (user_id, analysis_id, amount, reason,
                                                   balance_after, memo_uuid, metadata, created_at)
                    VALUES (%s, %s, %s, 'analysis_charge', %s, %s, %s, NOW())
                """, (user_id, analysis_id, -final_charged_credits, balance_after, memo_uuid,
                      json.dumps({'idempotency_key': idempotency_key, 'est_api_cost': float(api_cost)}) if idempotency_key else json.dumps({'est_api_cost': float(api_cost)})))
                logger.info(f"Credit transaction recorded successfully")
            
            logger.info(f"Committing transaction for analysis {analysis_id}")
            conn.commit()
            logger.info(f"Transaction committed successfully")
            
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
            logger.error(f"Database transaction failed - rolling back: {sanitize_for_log(e)}")
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = sanitize_for_log(e, max_length=300)
        
        # Enhanced error logging with full context
        logger.exception(f"BILLING ERROR - Analysis completion failed for user {user_id}")
        logger.error(f"Error Type: {error_type}")
        logger.error(f"Error Details: {error_msg}")
        logger.error(f"ASC Standard: {asc_standard}, Words: {words_count}, Credits to charge: {final_charged_credits}")
        
        # Send critical billing error alert to support team
        try:
            postmark = PostmarkClient()
            # Get user email safely (might not be set if error occurred early)
            email_for_alert = user_email if 'user_email' in locals() else f"User ID {user_id}"
            postmark.send_billing_error_alert(
                user_id=user_id,
                user_email=email_for_alert,
                asc_standard=asc_standard,
                error_type=error_type,
                error_details=error_msg,
                words_count=words_count,
                credits_to_charge=float(final_charged_credits)
            )
            logger.info("Billing error alert sent to support team")
        except Exception as alert_error:
            logger.error(f"Failed to send billing error alert: {sanitize_for_log(alert_error)}")
        
        # Return detailed error for debugging (safe for production since it doesn't expose sensitive data)
        return jsonify({
            'error': 'Analysis billing failed',
            'details': f'{error_type}: {error_msg}',
            'message': 'The analysis could not be saved. Please contact support if this persists.'
        }), 500

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
        logger.info(f"Payment intent request data: {data}")
        
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            logger.error("No authorization token provided")
            return jsonify({'error': 'Authorization token required'}), 401
        
        # Verify token and get user
        payload = verify_token(token)
        if 'error' in payload:
            logger.error(f"Token verification failed: {payload['error']}")
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        amount = data.get('amount')
        logger.info(f"Received amount: {amount} (type: {type(amount)})")
        
        # Convert string amount to int if necessary
        if isinstance(amount, str):
            try:
                amount = int(amount)
                logger.info(f"Converted string amount to int: {amount}")
            except ValueError:
                logger.error(f"Could not convert amount to int: {amount}")
                return jsonify({'error': 'Invalid amount format'}), 400
        
        # Validate amount - allow preset packages OR custom amounts within range
        from shared.pricing_config import CREDIT_PACKAGES
        preset_amounts = [pkg['amount'] for pkg in CREDIT_PACKAGES]
        logger.info(f"Preset amounts: {preset_amounts}")
        
        # Allow preset packages OR custom amounts between $95-$3000 (matching frontend validation)
        if not amount:
            logger.error("No amount provided")
            return jsonify({'error': 'Amount is required'}), 400
        elif amount < 95 or amount > 3000:
            logger.error(f"Amount {amount} outside valid range $95-$3000")
            return jsonify({'error': 'Amount must be between $95 and $3,000'}), 400
        
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
        logger.error(f"Stripe error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Payment processing error'}), 500
    except Exception as e:
        logger.error(f"Create payment intent error: {sanitize_for_log(e)}")
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
            logger.error(f"Invalid payload: {sanitize_for_log(e)}")
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {sanitize_for_log(e)}")
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
                
                # Send database error alert for webhook DB failures (critical for revenue)
                try:
                    postmark = PostmarkClient()
                    user_email = payment_intent['metadata'].get('user_email', f"User ID {user_id}")
                    postmark.send_database_error_alert(
                        operation="stripe webhook payment processing",
                        error_type="DatabaseConnectionError",
                        error_details="Failed to connect to database during Stripe payment webhook processing",
                        affected_user=user_email
                    )
                    logger.info("Database error alert sent to support")
                except Exception as alert_error:
                    logger.error(f"Failed to send database error alert: {alert_error}")
                
                return jsonify({'error': 'Database error'}), 500
            
            cursor = conn.cursor()
            
            # Get current balance before update
            cursor.execute("SELECT credits_balance FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            if not result:
                logger.error(f"User {user_id} not found")
                conn.close()
                return jsonify({'error': 'User not found'}), 404
            
            current_balance = float(result['credits_balance'] or 0)
            new_balance = current_balance + float(credit_amount)
            
            logger.info(f"Balance update: ${current_balance} -> ${new_balance} (+ ${credit_amount})")
            
            # Update user's balance
            cursor.execute("""
                UPDATE users 
                SET credits_balance = %s
                WHERE id = %s
            """, (new_balance, user_id))
            
            rows_affected = cursor.rowcount
            logger.info(f"Updated {rows_affected} user records")
            
            # Record credit purchase transaction with balance_after
            from shared.pricing_config import CREDIT_EXPIRATION_MONTHS
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, reason, balance_after, expires_at, stripe_payment_id)
                VALUES (%s, %s, 'stripe_purchase', %s, NOW() + INTERVAL '%s months', %s)
            """, (user_id, credit_amount, new_balance, CREDIT_EXPIRATION_MONTHS, payment_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"=== WEBHOOK SUCCESS: User {user_id} credited ${credit_amount} ===")
            
            # Send payment success notification to support for revenue tracking
            try:
                postmark = PostmarkClient()
                user_email = payment_intent['metadata'].get('user_email', f"User ID {user_id}")
                postmark.send_payment_success_notification(
                    user_email=user_email,
                    amount=float(credit_amount),
                    credits_added=float(credit_amount),
                    payment_id=payment_id
                )
                logger.info("Payment success notification sent to support")
            except Exception as notif_error:
                logger.error(f"Failed to send payment success notification: {notif_error}")
            
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': 'Processing failed'}), 500
    
    # Handle payment failure
    elif event['type'] == 'payment_intent.payment_failed':
        logger.info("Processing payment_intent.payment_failed event")
        payment_intent = event['data']['object']
        
        try:
            user_email = payment_intent['metadata'].get('user_email', 'Unknown')
            credit_amount = Decimal(payment_intent['metadata'].get('credit_amount', '0'))
            payment_intent_id = payment_intent['id']
            error_message = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
            
            logger.warning(f"Payment failed for {user_email}, amount: ${credit_amount}, error: {error_message}")
            
            # Send payment failure alert to support
            try:
                postmark = PostmarkClient()
                postmark.send_payment_failure_alert(
                    user_email=user_email,
                    amount=float(credit_amount),
                    error_message=error_message,
                    payment_intent_id=payment_intent_id
                )
                logger.info("Payment failure alert sent to support")
            except Exception as notif_error:
                logger.error(f"Failed to send payment failure alert: {notif_error}")
                
        except Exception as e:
            logger.error(f"Error processing payment failure event: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
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
        # Include both analysis_id and memo_uuid for different use cases
        # Only show completed analyses (not failed/processing ones)
        cursor.execute("""
            SELECT 
                a.analysis_id,
                COALESCE(a.memo_uuid, 'unknown') as id,
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
                AND a.status = 'completed'
                AND a.completed_at IS NOT NULL
            ORDER BY a.completed_at DESC
            LIMIT 20
        """, (user_id,))
        
        analyses = []
        for row in cursor.fetchall():
            analyses.append({
                'id': row['id'],
                'analysis_id': row['analysis_id'],
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

@app.route('/api/user/preferences', methods=['GET', 'POST'])
def manage_user_preferences():
    """Get or update user preferences for cross-platform synchronization"""
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
        
        if request.method == 'GET':
            # Get user preferences
            cursor.execute("""
                SELECT preferences FROM users WHERE id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return jsonify({'error': 'User not found'}), 404
            
            preferences = result['preferences'] or {}
            
            # Default preferences structure for cross-platform sync
            default_preferences = {
                'theme': 'light',
                'notifications': {
                    'analysis_complete': True,
                    'platform_status': True,
                    'credit_alerts': True
                },
                'analysis_defaults': {
                    'preferred_standards': ['ASC 606', 'ASC 842'],
                    'auto_save': True,
                    'detailed_citations': True
                },
                'platform_settings': {
                    'default_redirect_delay': 2,
                    'auto_launch_platform': False,
                    'show_platform_status': True
                },
                'ui_preferences': {
                    'sidebar_collapsed': False,
                    'dashboard_cards_collapsed': {},
                    'recent_items_count': 10
                }
            }
            
            # Merge with user preferences
            if isinstance(preferences, dict):
                for key, value in default_preferences.items():
                    if key not in preferences:
                        preferences[key] = value
                    elif isinstance(value, dict) and isinstance(preferences[key], dict):
                        for subkey, subvalue in value.items():
                            if subkey not in preferences[key]:
                                preferences[key][subkey] = subvalue
            else:
                preferences = default_preferences
            
            return jsonify({
                'success': True,
                'preferences': preferences
            }), 200
            
        elif request.method == 'POST':
            # Update user preferences
            data = request.get_json()
            new_preferences = data.get('preferences', {})
            
            if not isinstance(new_preferences, dict):
                return jsonify({'error': 'Invalid preferences format'}), 400
            
            # Get current preferences
            cursor.execute("""
                SELECT preferences FROM users WHERE id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return jsonify({'error': 'User not found'}), 404
            
            current_preferences = result['preferences'] or {}
            
            # Merge preferences (deep merge for nested objects)
            def deep_merge(target, source):
                for key, value in source.items():
                    if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                        deep_merge(target[key], value)
                    else:
                        target[key] = value
                return target
            
            updated_preferences = deep_merge(current_preferences.copy(), new_preferences)
            
            # Update preferences in database
            cursor.execute("""
                UPDATE users 
                SET preferences = %s 
                WHERE id = %s
            """, (json.dumps(updated_preferences), user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"User {user_id} updated preferences")
            
            return jsonify({
                'success': True,
                'message': 'Preferences updated successfully',
                'preferences': updated_preferences
            }), 200
        
    except Exception as e:
        logger.error(f"Manage preferences error: {e}")
        return jsonify({'error': 'Failed to manage preferences'}), 500

@app.route('/api/user/session-sync', methods=['POST'])
def sync_user_session():
    """Synchronize user session data across platforms"""
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
        session_data = data.get('session_data', {})
        platform = data.get('platform', 'unknown')  # 'website' or 'streamlit'
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get current user data for cross-platform sync
        cursor.execute("""
            SELECT id, email, first_name, last_name, company_name, 
                   credits_balance, preferences, created_at
            FROM users 
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Build synchronized session data
        sync_response = {
            'success': True,
            'user_profile': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'company_name': user['company_name'],
                'credits_balance': float(user['credits_balance'] or 0),
                'member_since': user['created_at'].isoformat(),
                'preferences': user['preferences'] or {}
            },
            'platform_status': {
                'current_platform': platform,
                'last_sync': datetime.now().isoformat(),
                'session_valid': True
            },
            'cross_platform_data': session_data
        }
        
        logger.info(f"User {user_id} synchronized session from {platform}")
        
        return jsonify(sync_response), 200
        
    except Exception as e:
        logger.error(f"Session sync error: {e}")
        return jsonify({'error': 'Failed to sync session'}), 500

@app.route('/api/user/platform-activity', methods=['POST'])
def log_platform_activity():
    """Log user activity across platforms for unified tracking"""
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
        activity_type = data.get('activity_type')  # 'platform_switch', 'analysis_start', etc.
        platform = data.get('platform')  # 'website' or 'streamlit'
        metadata = data.get('metadata', {})
        
        if not activity_type or not platform:
            return jsonify({'error': 'Activity type and platform required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Log activity (you might want to create a dedicated activity table)
        # For now, we'll use the existing credit_transactions table with a special reason
        if activity_type in ['platform_switch', 'analysis_start', 'session_sync']:
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, reason, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (user_id, 0, f"{platform}_{activity_type}"))
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"User {user_id} activity logged: {activity_type} on {platform}")
        
        return jsonify({
            'success': True,
            'message': 'Activity logged successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Platform activity error: {e}")
        return jsonify({'error': 'Failed to log activity'}), 500

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port, debug=True)
