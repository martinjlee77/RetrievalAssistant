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
import time
from datetime import datetime, timedelta, date, timezone
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
from shared.trial_protection import (
    verify_recaptcha,
    check_rate_limit,
    record_signup_attempt,
    check_domain_trial_eligibility,
    cleanup_old_signup_attempts
)

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
# DEPRECATED: Credit system replaced with subscription model
# INITIAL_SIGNUP_CREDITS = Decimal(os.getenv('INITIAL_SIGNUP_CREDITS', '295.00'))
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

@app.route('/demo.html')
def serve_demo():
    return send_from_directory('veritaslogic_multipage_website', 'demo.html')

@app.route('/appsource')
def serve_appsource():
    return send_from_directory('veritaslogic_multipage_website', 'appsource.html')

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
            'exp': datetime.utcnow() + timedelta(hours=12),  # Extended for long-running memo reviews
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
    
    # Determine the Streamlit page to open based on analysis_id
    page_path = ""
    analysis_id = request.args.get('analysis_id')
    logger.info(f"Processing /analysis request with analysis_id={analysis_id}")
    
    if analysis_id:
        try:
            # Query database to get asc_standard and analysis_type for this analysis
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT asc_standard, COALESCE(analysis_type, 'standard') as analysis_type FROM analyses WHERE analysis_id = %s",
                (int(analysis_id),)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            logger.info(f"Database query result for analysis_id {analysis_id}: {result}")
            
            if result:
                asc_standard = result['asc_standard']
                analysis_type = result['analysis_type']
                logger.info(f"Found asc_standard: {asc_standard}, analysis_type: {analysis_type}")
                
                # Check if this is a review - redirect to memo_review page
                if analysis_type == 'review':
                    page_path = "/memo_review"
                    logger.info(f"Redirecting to memo_review page for review analysis")
                else:
                    # Map ASC standards to Streamlit page file names (used in URLs)
                    page_mapping = {
                        'ASC 606': 'asc606_page',
                        'ASC 340-40': 'asc340_page',
                        'ASC 842': 'asc842_page',
                        'ASC 718': 'asc718_page',
                        'ASC 805': 'asc805_page',
                    }
                    page_name = page_mapping.get(asc_standard)
                    logger.info(f"Mapped to page_name: {page_name}")
                    
                    if page_name:
                        page_path = f"/{page_name}"
                        logger.info(f"Set page_path: {page_path}")
            else:
                logger.warning(f"No analysis found for analysis_id {analysis_id}")
        except Exception as e:
            logger.error(f"Error determining page for analysis_id {analysis_id}: {e}")
    
    # Build redirect URL with automatic token refresh
    if token:
        # Validate token before redirecting
        payload = verify_token(token)
        if 'error' not in payload:
            # Token is valid, use it
            if analysis_id and page_path:
                redirect_url = f"{STREAMLIT_URL}{page_path}?auth_token={token}&analysis_id={analysis_id}"
            else:
                redirect_url = f"{STREAMLIT_URL}?auth_token={token}"
        else:
            # Token is expired/invalid, try to refresh it
            logger.info(f"Token validation failed: {payload.get('error', 'Unknown error')}, attempting refresh")
            refreshed_token = attempt_token_refresh(request)
            if refreshed_token:
                logger.info("Token refresh successful, redirecting with new token")
                if analysis_id and page_path:
                    redirect_url = f"{STREAMLIT_URL}{page_path}?auth_token={refreshed_token}&analysis_id={analysis_id}"
                else:
                    redirect_url = f"{STREAMLIT_URL}?auth_token={refreshed_token}"
            else:
                logger.info("Token refresh failed, redirecting without token")
                if analysis_id and page_path:
                    redirect_url = f"{STREAMLIT_URL}{page_path}?analysis_id={analysis_id}"
                else:
                    redirect_url = STREAMLIT_URL
    else:
        # No token found, try refresh anyway (user might be logged in via dashboard session)
        logger.info("No token found, attempting refresh from dashboard session")
        refreshed_token = attempt_token_refresh(request)
        if refreshed_token:
            logger.info("Dashboard session refresh successful, redirecting with new token")
            if analysis_id and page_path:
                redirect_url = f"{STREAMLIT_URL}{page_path}?auth_token={refreshed_token}&analysis_id={analysis_id}"
            else:
                redirect_url = f"{STREAMLIT_URL}?auth_token={refreshed_token}"
        else:
            logger.info("No valid session found, redirecting without token")
            if analysis_id and page_path:
                redirect_url = f"{STREAMLIT_URL}{page_path}?analysis_id={analysis_id}"
            else:
                redirect_url = STREAMLIT_URL
    
    logger.info(f"Final redirect URL: {redirect_url}")
    
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

def generate_service_token(user_id, email):
    """
    Generate a long-lived service token for background workers
    
    Service tokens are used by background workers to make authenticated API calls
    without relying on the user's short-lived access token.
    
    Args:
        user_id: User ID
        email: User email
        
    Returns:
        str: JWT service token valid for 24 hours
    """
    service_token = jwt.encode({
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'purpose': 'service',
        'domain': 'veritaslogic.ai',
        'issued_at': datetime.utcnow().isoformat()
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return service_token

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

@app.route('/api/check-domain', methods=['POST'])
def check_domain():
    """Check if an organization exists for the given email domain"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email or '@' not in email:
            return jsonify({'error': 'Valid email required'}), 400
        
        # Validate business email
        if not is_business_email(email):
            return jsonify({
                'error': 'Only business email addresses are accepted',
                'is_business_email': False
            }), 400
        
        # Extract domain
        email_domain = email.split('@')[1].lower()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if organization exists for this domain (no PII exposure)
        cursor.execute("""
            SELECT o.id, o.name, COUNT(u.id) as user_count
            FROM organizations o
            LEFT JOIN users u ON u.org_id = o.id
            WHERE o.domain = %s
            GROUP BY o.id, o.name
        """, (email_domain,))
        
        org = cursor.fetchone()
        conn.close()
        
        if org:
            user_count_text = f"{org['user_count']} existing member(s)" if org['user_count'] > 0 else "your organization"
            return jsonify({
                'success': True,
                'organization_exists': True,
                'organization_name': org['name'],
                'requires_payment': False,
                'message': f"You'll be joining {user_count_text} at {org['name']}. No credit card needed."
            })
        else:
            return jsonify({
                'success': True,
                'organization_exists': False,
                'requires_payment': True,
                'message': 'You\'ll create a new organization. Credit card required to activate your 14-day trial.'
            })
    
    except Exception as e:
        logger.error(f"Error checking domain: {e}")
        return jsonify({'error': 'Failed to check domain'}), 500

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
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
        
        # Extract domain from email for organization
        email_domain = email.split('@')[1].lower()
        
        # Get user's IP address for rate limiting
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in user_ip:
            user_ip = user_ip.split(',')[0].strip()
        
        # TRIAL ABUSE PREVENTION STEP 1: Verify reCAPTCHA token
        recaptcha_secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
        
        if recaptcha_secret_key:
            # reCAPTCHA is configured - token is REQUIRED
            recaptcha_token = data.get('recaptcha_token')
            if not recaptcha_token:
                record_signup_attempt(conn, user_ip, email, email_domain, False, "Missing reCAPTCHA token")
                conn.close()
                logger.warning(f"Signup blocked - no reCAPTCHA token provided: {email}")
                return jsonify({
                    'error': 'Security verification required. Please refresh the page and try again.'
                }), 400
            
            recaptcha_success, recaptcha_score, recaptcha_error = verify_recaptcha(recaptcha_token, user_ip)
            if not recaptcha_success:
                record_signup_attempt(conn, user_ip, email, email_domain, False, f"reCAPTCHA failed: {recaptcha_error}")
                conn.close()
                return jsonify({
                    'error': 'Security verification failed. Please refresh the page and try again.'
                }), 400
            logger.info(f"reCAPTCHA verified for {email}: score={recaptcha_score:.2f}")
        else:
            # Development mode - reCAPTCHA not configured, allow signup
            logger.info(f"reCAPTCHA not configured - allowing signup in development mode: {email}")
        
        # TRIAL ABUSE PREVENTION STEP 2: Check rate limits
        rate_allowed, rate_error, wait_minutes = check_rate_limit(conn, user_ip, email_domain)
        if not rate_allowed:
            record_signup_attempt(conn, user_ip, email, email_domain, False, rate_error)
            conn.close()
            return jsonify({'error': rate_error}), 429
        
        # TRIAL ABUSE PREVENTION STEP 3: Check domain trial eligibility
        # Only check for new organizations (not existing users joining their org)
        cursor.execute("SELECT id FROM organizations WHERE domain = %s", (email_domain,))
        org_exists = cursor.fetchone()
        
        if not org_exists:
            trial_eligible, trial_error = check_domain_trial_eligibility(conn, email_domain)
            if not trial_eligible:
                record_signup_attempt(conn, user_ip, email, email_domain, False, trial_error)
                conn.close()
                return jsonify({'error': trial_error}), 403
        
        # Hash password before storing
        password_hash = hash_password(password)
        
        # Get marketing opt-in preference (defaults to False if not provided)
        marketing_opt_in = data.get('marketing_opt_in', False)
        
        # Extract source and UTM parameters for attribution tracking
        signup_source = sanitize_string(data.get('source', 'direct'), 100)
        landing_page = sanitize_string(data.get('landing_page', ''), 500)
        
        utm_tracking = {}
        if data.get('utm_source'):
            utm_tracking['utm_source'] = sanitize_string(data.get('utm_source', ''), 100)
        if data.get('utm_medium'):
            utm_tracking['utm_medium'] = sanitize_string(data.get('utm_medium', ''), 100)
        if data.get('utm_campaign'):
            utm_tracking['utm_campaign'] = sanitize_string(data.get('utm_campaign', ''), 100)
        if data.get('plan'):
            utm_tracking['selected_plan'] = sanitize_string(data.get('plan', ''), 50)
        
        # Add source to utm_tracking for org settings
        if signup_source and signup_source != 'direct':
            utm_tracking['source'] = signup_source
        
        # Check if organization already exists for this domain
        cursor.execute("""
            SELECT id FROM organizations WHERE domain = %s
        """, (email_domain,))
        
        org_result = cursor.fetchone()
        is_new_org = False  # Track if we're creating a new organization
        
        if org_result:
            # Organization exists - add user to existing org and update attribution if provided
            org_id = org_result['id']
            is_new_org = False
            logger.info(f"Adding user {email} to existing organization (domain: {email_domain})")
            
            # If UTM parameters provided, append to existing org settings
            if utm_tracking:
                cursor.execute("""
                    SELECT settings FROM organizations WHERE id = %s
                """, (org_id,))
                current_settings = cursor.fetchone()['settings'] or {}
                
                # Append attribution to signups array
                if 'signups' not in current_settings:
                    current_settings['signups'] = []
                
                current_settings['signups'].append({
                    'email': email,
                    'timestamp': datetime.utcnow().isoformat(),
                    **utm_tracking
                })
                
                cursor.execute("""
                    UPDATE organizations 
                    SET settings = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(current_settings), org_id))
                
                logger.info(f"Appended signup attribution for {email}: {utm_tracking}")
        else:
            # Create new organization with UTM tracking in settings
            is_new_org = True
            org_settings = {}
            if utm_tracking:
                org_settings['attribution'] = utm_tracking
                org_settings['signups'] = [{
                    'email': email,
                    'timestamp': datetime.utcnow().isoformat(),
                    **utm_tracking
                }]
                logger.info(f"Tracking signup attribution: {utm_tracking}")
            
            cursor.execute("""
                INSERT INTO organizations (name, domain, settings)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (company_name, email_domain, json.dumps(org_settings)))
            
            org_id = cursor.fetchone()['id']
            logger.info(f"Created new organization for {company_name} (domain: {email_domain})")
        
        # Create user with org_id (first user in org becomes owner)
        cursor.execute("""
            SELECT COUNT(*) as user_count FROM users WHERE org_id = %s
        """, (org_id,))
        
        user_count = cursor.fetchone()['user_count']
        user_role = 'owner' if user_count == 0 else 'member'
        
        cursor.execute("""
            INSERT INTO users (email, first_name, last_name, job_title, org_id, role,
                             password_hash, terms_accepted_at, email_verified, marketing_opt_in)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), FALSE, %s)
            RETURNING id
        """, (email, first_name, last_name, job_title, org_id, user_role, password_hash, marketing_opt_in))
        
        user_id = cursor.fetchone()['id']
        
        # Record lead source for attribution tracking (for Microsoft AppSource, etc.)
        cursor.execute("""
            INSERT INTO lead_sources (
                user_id, source, utm_source, utm_medium, utm_campaign, landing_page, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id,
            signup_source,
            utm_tracking.get('utm_source'),
            utm_tracking.get('utm_medium'),
            utm_tracking.get('utm_campaign'),
            landing_page
        ))
        logger.info(f"Lead source tracked for {email}: source={signup_source}")
        
        # Generate verification token
        verification_token = generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
        
        # Store verification token
        cursor.execute("""
            INSERT INTO email_verification_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user_id, verification_token, expires_at))
        
        # Create trial subscription for organization (only if creating new org as owner)
        trial_info = None
        if user_role == 'owner' and is_new_org:
            # Check if org already has a subscription
            cursor.execute("""
                SELECT id FROM subscription_instances 
                WHERE org_id = %s AND status IN ('active', 'trial', 'past_due')
            """, (org_id,))
            
            if not cursor.fetchone():
                # Create trial subscription with payment method
                from shared.subscription_manager import SubscriptionManager
                sub_mgr = SubscriptionManager(conn)
                
                # Get payment_method_id from signup data (required for new org trials)
                payment_method_id = data.get('payment_method_id')
                
                if not payment_method_id:
                    conn.rollback()
                    conn.close()
                    logger.error(f"Signup blocked - payment method required for new org trial: {email}")
                    return jsonify({
                        'error': 'Payment method is required to activate your trial. Please refresh and try again.'
                    }), 400
                
                try:
                    trial_result = sub_mgr.create_trial_subscription(
                        org_id, 
                        plan_key='professional',
                        payment_method_id=payment_method_id,
                        customer_email=email
                    )
                    trial_info = trial_result
                    logger.info(f"Created 14-day trial subscription for org {org_id}: {trial_result['word_allowance']} words, payment method attached")
                except Exception as trial_error:
                    logger.error(f"Failed to create trial subscription: {trial_error}")
                    # Don't block signup if trial creation fails
                    conn.rollback()
                    raise
        
        conn.commit()
        
        # Record successful signup attempt for rate limiting tracking
        record_signup_attempt(conn, user_ip, email, email_domain, True)
        
        # Cleanup old signup attempts (housekeeping)
        cleanup_old_signup_attempts(conn)
        
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
        try:
            admin_notified = postmark_client.send_new_signup_notification(
                user_email=email,
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                job_title=job_title,
                awarded_credits=0  # Deprecated field - now using trial subscriptions
            )
            if admin_notified:
                logger.info(f"Admin notified of new signup: {email} (trial subscription created)")
            else:
                logger.warning(f"Failed to send admin notification for new signup: {email}")
        except Exception as notify_error:
            logger.warning(f"Admin notification skipped: {notify_error}")
        
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


@app.route('/api/recaptcha-config', methods=['GET'])
def get_recaptcha_config():
    """Provide reCAPTCHA site key for frontend"""
    recaptcha_site_key = os.getenv('RECAPTCHA_SITE_KEY')
    if recaptcha_site_key:
        return jsonify({'site_key': recaptcha_site_key}), 200
    else:
        return jsonify({'site_key': None}), 200


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
            SELECT u.id, u.email, u.first_name, u.last_name, u.job_title, u.org_id,
                   u.password_hash, u.created_at, u.email_verified, u.research_assistant_access,
                   o.name as company_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.id
            WHERE u.email = %s
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
            'exp': datetime.utcnow() + timedelta(hours=12),  # Extended for long-running memo reviews
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
                'company_name': user['company_name'] or '',
                'job_title': user['job_title'] or '',
                'org_id': user['org_id'],
                'credits_balance': 0,  # Legacy field - subscriptions now manage usage
                'free_analyses_remaining': 0,  # Legacy field removed
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
            'exp': datetime.utcnow() + timedelta(hours=12),  # Extended for long-running memo reviews
            'purpose': 'access',
            'domain': 'veritaslogic.ai',
            'issued_at': datetime.utcnow().isoformat()
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': new_access_token,
            'expires_in': 43200  # 12 hours in seconds
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
            SELECT u.id, u.email, u.first_name, u.last_name, u.job_title, u.org_id,
                   u.email_verified, u.created_at,
                   o.name as company_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.id
            WHERE u.id = %s AND u.email_verified = true
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
                'company_name': user['company_name'] or '',
                'job_title': user['job_title'] or '',
                'org_id': user['org_id'],
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
        
        # Get user data with organization and owner info
        cursor.execute("""
            SELECT u.id, u.email, u.first_name, u.last_name, u.job_title, u.org_id, u.role,
                   u.created_at, u.email_verified, u.research_assistant_access,
                   o.name as company_name,
                   (SELECT email FROM users WHERE org_id = u.org_id AND role = 'owner' LIMIT 1) as owner_email
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.id
            WHERE u.id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Get recent analyses (billed_credits removed - subscription system now)
        cursor.execute("""
            SELECT asc_standard, completed_at
            FROM analyses 
            WHERE user_id = %s AND status = 'completed'
            ORDER BY completed_at DESC 
            LIMIT 10
        """, (user_id,))
        
        recent_analyses = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'company_name': user['company_name'] or '',
                'job_title': user['job_title'] or '',
                'org_id': user['org_id'],
                'role': user['role'],
                'owner_email': user['owner_email'],
                'member_since': user['created_at'].isoformat(),
                'email_verified': bool(user['email_verified']),
                'research_assistant_access': bool(user['research_assistant_access'])
            },
            'recent_analyses': [
                {
                    'asc_standard': analysis['asc_standard'],
                    'completed_at': analysis['completed_at'].isoformat()
                }
                for analysis in recent_analyses
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/user/check-credits', methods=['POST'])
def check_user_credits():
    """
    Check if user has sufficient word allowance for analysis
    MIGRATED: Now uses subscription-based word allowances instead of credits
    """
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
        
        # Accept both 'words_needed' (new) and 'required_credits' (legacy) for backwards compatibility
        words_needed = data.get('words_needed') or data.get('required_credits', 0)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.email_verified, u.org_id, o.id as org_id_check
                FROM users u
                LEFT JOIN organizations o ON u.org_id = o.id
                WHERE u.id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Check email verification first
            if not user['email_verified']:
                return jsonify({
                    'can_proceed': False,
                    'error': 'Email verification required',
                    'message': 'Please verify your email address before running analyses.',
                    'email_verified': False
                }), 403
            
            # Get subscription allowance using SubscriptionManager
            from shared.subscription_manager import SubscriptionManager
            sub_mgr = SubscriptionManager(conn)
            
            allowance_check = sub_mgr.check_word_allowance(user['org_id'], words_needed)
            
            # Get current usage for additional context
            usage = sub_mgr.get_current_usage(user['org_id'])
            
            return jsonify({
                'can_proceed': allowance_check['allowed'],
                'words_available': allowance_check.get('words_available', 0),
                'words_needed': words_needed,
                'subscription': {
                    'has_subscription': usage['has_subscription'],
                    'status': usage.get('subscription_status'),
                    'plan_name': usage.get('plan_name'),
                    'word_allowance': usage.get('word_allowance', 0),
                    'rollover_words': usage.get('rollover_words', 0),
                    'words_used': usage.get('words_used', 0),
                    'is_trial': usage.get('is_trial', False),
                    'trial_end_date': usage.get('trial_end_date').isoformat() if usage.get('trial_end_date') else None
                },
                'upgrade_needed': allowance_check.get('upgrade_needed', False),
                'suggested_action': allowance_check.get('suggested_action'),
                'message': allowance_check.get('reason')
            }), 200
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Check allowance error: {e}")
        return jsonify({'error': 'Failed to check word allowance'}), 500

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
        analysis_type = sanitize_string(data.get('analysis_type', 'standard'), 50)
        source_memo_filename = sanitize_string(data.get('source_memo_filename', ''), 500) if data.get('source_memo_filename') else None
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            # Verify email and get org
            cursor.execute("SELECT email_verified, org_id FROM users WHERE id = %s", (user_id,))
            user_check = cursor.fetchone()
            if not user_check or not user_check['email_verified']:
                return jsonify({'error': 'Email verification required'}), 403
            
            # Check subscription allowance
            from shared.subscription_manager import SubscriptionManager
            sub_mgr = SubscriptionManager(conn)
            allowance_check = sub_mgr.check_word_allowance(user_check['org_id'], words_count)
            
            if not allowance_check['allowed']:
                return jsonify({
                    'error': 'Insufficient word allowance',
                    'message': allowance_check['reason'],
                    'upgrade_needed': allowance_check.get('upgrade_needed', False),
                    'suggested_action': allowance_check.get('suggested_action')
                }), 402
            
            # Insert pending analysis record (subscription-based, no upfront charging)
            import uuid
            memo_uuid = str(uuid.uuid4())[:8]
            
            cursor.execute("""
                INSERT INTO analyses (user_id, org_id, asc_standard, words_count, tier_name, 
                                    status, memo_uuid, started_at, file_count, analysis_type, source_memo_filename)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)
                RETURNING analysis_id
            """, (user_id, user_check['org_id'], asc_standard, words_count,
                  tier_name, 'processing', memo_uuid, file_count, analysis_type, source_memo_filename))
            
            result = cursor.fetchone()
            db_analysis_id = result['analysis_id']
            
            conn.commit()
            
            # Generate long-lived service token for background worker
            # This prevents token expiration issues during long-running analyses
            service_token = generate_service_token(user_id, payload['email'])
            
            return jsonify({
                'message': 'Analysis record created',
                'analysis_id': db_analysis_id,
                'memo_uuid': memo_uuid,
                'service_token': service_token
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
        org_id = data.get('org_id')  # For subscription word deduction
        total_words = data.get('total_words')  # For subscription word deduction
        
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
            
            # Subscription-based word deduction (new system)
            if success and org_id and total_words:
                try:
                    from shared.subscription_manager import SubscriptionManager
                    subscription_manager = SubscriptionManager(conn)
                    
                    # Deduct words from subscription allowance
                    deduction_result = subscription_manager.deduct_words(
                        org_id=org_id,
                        words_used=total_words,
                        analysis_id=db_analysis_id
                    )
                    
                    logger.info(
                        f"✓ Word deduction successful for org {org_id}: {total_words} words, "
                        f"breakdown: {deduction_result['from_allowance']} from allowance, "
                        f"{deduction_result['from_rollover']} from rollover"
                    )
                    balance_after = 0  # Not used in subscription system, but keep for response consistency
                    
                except Exception as e:
                    # Log error but don't fail the analysis save
                    logger.error(f"Word deduction failed for org {org_id}, analysis {db_analysis_id}: {str(e)}")
                    # Rollback to preserve transaction consistency
                    conn.rollback()
                    raise e
            
            # Legacy credit-based billing (for backwards compatibility during migration)
            elif success and cost_charged and cost_charged > 0:
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
                balance_after = current_balance if 'balance_after' not in locals() else balance_after
                logger.info(f"No billing applied (success={success}, org_id={org_id}, total_words={total_words})")
            
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
                       final_charged_credits, analysis_type, source_memo_filename
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
                'file_count': analysis['file_count'],
                'analysis_type': analysis['analysis_type'] or 'standard',
                'source_memo_filename': analysis['source_memo_filename']
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
    """Get user's most recent completed analysis for a specific ASC standard (within 24 hours)
    
    Special case: If asc_standard is 'review', returns most recent memo review analysis
    """
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
            # Special case: 'review' returns most recent memo review analysis (any ASC standard)
            if asc_standard.lower() == 'review':
                cursor.execute("""
                    SELECT analysis_id, memo_uuid, status, memo_content, completed_at, 
                           asc_standard, words_count, tier_name, file_count, final_charged_credits,
                           analysis_type, source_memo_filename
                    FROM analyses 
                    WHERE user_id = %s
                    AND analysis_type = 'review'
                    AND status = 'completed'
                    AND completed_at > NOW() - INTERVAL '24 hours'
                    ORDER BY completed_at DESC
                    LIMIT 1
                """, (user_id,))
            else:
                # Normalize ASC standard format (handle 'asc606' and 'ASC 606')
                asc_standard_clean = sanitize_string(asc_standard, 50).upper().replace(' ', '')
                # Convert 'ASC606' to 'ASC 606' format for database match
                if asc_standard_clean.startswith('ASC') and len(asc_standard_clean) > 3:
                    asc_standard_db = f"ASC {asc_standard_clean[3:]}"
                else:
                    asc_standard_db = asc_standard
                
                # Query most recent completed analysis for this user and ASC standard
                # Only return analyses completed within the last 24 hours
                # Use ILIKE for case-insensitive match
                cursor.execute("""
                    SELECT analysis_id, memo_uuid, status, memo_content, completed_at, 
                           asc_standard, words_count, tier_name, file_count, final_charged_credits,
                           analysis_type, source_memo_filename
                    FROM analyses 
                    WHERE user_id = %s
                    AND asc_standard ILIKE %s
                    AND status = 'completed'
                    AND completed_at > NOW() - INTERVAL '24 hours'
                    ORDER BY completed_at DESC
                    LIMIT 1
                """, (user_id, asc_standard_db))
            
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
                'credits_charged': float(analysis['final_charged_credits']) if analysis['final_charged_credits'] else 0,
                'analysis_type': analysis.get('analysis_type', 'standard'),
                'source_memo_filename': analysis.get('source_memo_filename')
            }
            
            return jsonify(response), 200
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Get recent analysis error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Failed to retrieve recent analysis'}), 500

@app.route('/api/analysis/complete', methods=['POST'])
def complete_analysis():
    """
    Unified endpoint for analysis completion - handles recording and word deduction atomically
    MIGRATED: Now uses subscription-based word allowances instead of credits
    """
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
        file_count = max(0, int(data.get('file_count', 0)))
        tier_name = sanitize_string(data.get('tier_name', ''), 100)
        idempotency_key = sanitize_string(data.get('idempotency_key', ''), 100)
        started_at = data.get('started_at')
        duration_seconds = max(0, int(data.get('duration_seconds', 0)))
        success = data.get('success', False)  # CRITICAL: Only deduct words if True
        error_message = sanitize_string(data.get('error_message', ''), 500) if data.get('error_message') else None
        
        # Generate customer-facing memo UUID
        import uuid
        memo_uuid = str(uuid.uuid4())[:8]
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        try:
            veritaslogic_logger.info(f"BACKEND: Starting analysis completion for user {user_id}")
            logger.info(f"Starting analysis completion for user {user_id}")
            
            # Verify email and get org_id
            cursor.execute("SELECT email, email_verified, org_id FROM users WHERE id = %s", (user_id,))
            user_check = cursor.fetchone()
            if not user_check or not user_check['email_verified']:
                logger.warning(f"Unverified user {user_id} attempted to complete analysis")
                return jsonify({
                    'error': 'Email verification required',
                    'message': 'Please verify your email address before running analyses.'
                }), 403
            
            user_email = user_check['email']
            org_id = user_check['org_id']
            
            # Check idempotency - prevent duplicate word deductions
            if idempotency_key:
                veritaslogic_logger.info(f"BACKEND: Checking idempotency for key: {idempotency_key}")
                logger.info(f"Checking idempotency for key: {idempotency_key}")
                cursor.execute("""
                    SELECT analysis_id, memo_uuid, words_charged FROM analyses 
                    WHERE user_id = %s AND memo_uuid = %s
                """, (user_id, idempotency_key))
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"Found existing analysis (idempotent): {existing['analysis_id']}")
                    return jsonify({
                        'message': 'Analysis already recorded (idempotent)',
                        'analysis_id': existing['analysis_id'],
                        'memo_uuid': existing['memo_uuid'],
                        'words_charged': existing['words_charged'] or 0,
                        'is_duplicate': True
                    }), 200
            
            # Set status based on success flag
            analysis_status = 'completed' if success else 'failed'
            logger.info(f"Inserting analysis record for user {user_id} with status: {analysis_status}")
            
            # Insert analysis record with new subscription schema
            cursor.execute("""
                INSERT INTO analyses (user_id, org_id, asc_standard, words_count, tier_name, 
                                    status, memo_uuid, started_at, completed_at, 
                                    duration_seconds, file_count, error_message, words_charged)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s)
                RETURNING analysis_id
            """, (user_id, org_id, asc_standard, words_count, tier_name, 
                  analysis_status, memo_uuid, started_at, duration_seconds, 
                  file_count, error_message, 0))
            
            analysis_id = cursor.fetchone()['analysis_id']
            logger.info(f"Analysis record created with ID: {analysis_id}, status: {analysis_status}")
            
            words_charged = 0
            deduction_details = None
            
            # CRITICAL: Only deduct words if analysis succeeded
            if success:
                # Deduct words from subscription allowance
                from shared.subscription_manager import SubscriptionManager
                sub_mgr = SubscriptionManager(conn)
                
                try:
                    deduction_result = sub_mgr.deduct_words(org_id, words_count, analysis_id)
                    words_charged = deduction_result['words_deducted']
                    deduction_details = deduction_result
                    
                    # Update analysis record with actual words charged
                    cursor.execute("""
                        UPDATE analyses 
                        SET words_charged = %s
                        WHERE analysis_id = %s
                    """, (words_charged, analysis_id))
                    
                    logger.info(f"Successfully deducted {words_charged} words from org {org_id}: {deduction_result['from_allowance']} from allowance, {deduction_result['from_rollover']} from rollover")
                    
                except ValueError as ve:
                    # Insufficient words - this shouldn't happen if pre-flight check passed
                    logger.error(f"Word deduction failed for analysis {analysis_id}: {ve}")
                    conn.rollback()
                    return jsonify({
                        'error': 'Insufficient word allowance',
                        'message': str(ve),
                        'suggestion': 'Please upgrade your subscription to continue.'
                    }), 402
            else:
                # Failed analysis - no word deduction
                logger.info(f"Analysis failed - no words charged. Error: {error_message}")
            
            # Commit transaction
            logger.info(f"Committing transaction for analysis {analysis_id}")
            conn.commit()
            logger.info(f"Transaction committed successfully")
            
            # Get updated subscription usage for response
            from shared.subscription_manager import SubscriptionManager
            sub_mgr = SubscriptionManager(conn)
            usage = sub_mgr.get_current_usage(org_id)
            
            logger.info(f"Analysis completed for user {user_id}: {asc_standard}, memo: {memo_uuid}, words charged: {words_charged}")
            
            return jsonify({
                'message': 'Analysis completed successfully',
                'analysis_id': analysis_id,
                'memo_uuid': memo_uuid,
                'words_charged': words_charged,
                'subscription_usage': {
                    'words_available': usage.get('words_available', 0),
                    'words_used': usage.get('words_used', 0),
                    'word_allowance': usage.get('word_allowance', 0),
                    'rollover_words': usage.get('rollover_words', 0)
                },
                'deduction_breakdown': deduction_details if deduction_details else None
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
        logger.exception(f"ANALYSIS COMPLETION ERROR - Failed for user {user_id if 'user_id' in locals() else 'unknown'}")
        logger.error(f"Error Type: {error_type}")
        logger.error(f"Error Details: {error_msg}")
        if 'asc_standard' in locals():
            logger.error(f"ASC Standard: {asc_standard}, Words: {words_count}")
        
        # Send critical error alert to support team
        try:
            postmark = PostmarkClient()
            email_for_alert = user_email if 'user_email' in locals() else f"User ID {user_id if 'user_id' in locals() else 'unknown'}"
            postmark.send_billing_error_alert(
                user_id=user_id if 'user_id' in locals() else 0,
                user_email=email_for_alert,
                asc_standard=asc_standard if 'asc_standard' in locals() else 'unknown',
                error_type=error_type,
                error_details=error_msg,
                words_count=words_count if 'words_count' in locals() else 0,
                credits_to_charge=0
            )
            logger.info("Analysis error alert sent to support team")
        except Exception as alert_error:
            logger.error(f"Failed to send error alert: {sanitize_for_log(alert_error)}")
        
        return jsonify({
            'error': 'Analysis completion failed',
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

@app.route('/api/stripe/public-key', methods=['GET'])
def get_stripe_public_key():
    """Get Stripe publishable key for signup flow"""
    return jsonify({'public_key': STRIPE_PUBLISHABLE_KEY}), 200

@app.route('/api/signup/create-setup-intent', methods=['POST'])
def create_signup_setup_intent():
    """Create a Setup Intent for collecting payment method during signup"""
    try:
        data = request.get_json()
        email = data.get('email', '')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Create Setup Intent with Stripe
        setup_intent = stripe.SetupIntent.create(
            payment_method_types=['card'],
            metadata={
                'signup_email': email,
                'purpose': 'trial_signup'
            }
        )
        
        logger.info(f"Created Setup Intent for signup: {email}")
        
        return jsonify({
            'client_secret': setup_intent.client_secret
        }), 200
        
    except Exception as e:
        logger.error(f"Setup Intent creation error: {e}")
        return jsonify({'error': 'Failed to initialize payment method collection'}), 500

@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe Checkout session for direct plan purchase"""
    try:
        from shared.pricing_config import SUBSCRIPTION_PLANS
        
        data = request.get_json()
        plan_key = data.get('plan')
        
        if not plan_key:
            return jsonify({'error': 'Plan is required'}), 400
        
        # Validate plan exists
        if plan_key not in SUBSCRIPTION_PLANS:
            return jsonify({'error': 'Invalid plan selected'}), 400
        
        plan = SUBSCRIPTION_PLANS[plan_key]
        
        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': plan['stripe_price_id'],
                'quantity': 1,
            }],
            success_url=f"{WEBSITE_URL}/checkout-success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{WEBSITE_URL}/pricing.html",
            allow_promotion_codes=True,
            billing_address_collection='required',
            customer_email=data.get('email'),
            metadata={
                'plan_key': plan_key,
                'signup_type': 'direct_purchase'
            },
            subscription_data={
                'metadata': {
                    'plan_key': plan_key,
                    'signup_type': 'direct_purchase'
                }
            }
        )
        
        logger.info(f"Created Stripe Checkout session for {plan_key} plan: {checkout_session.id}")
        
        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }), 200
        
    except stripe.StripeError as se:
        logger.error(f"Stripe error creating checkout session: {se}")
        return jsonify({
            'error': 'Payment processing error',
            'message': 'Unable to create checkout session. Please try again.'
        }), 500
    except Exception as e:
        logger.error(f"Create checkout session error: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@app.route('/api/process-checkout-success', methods=['POST'])
def process_checkout_success():
    """Process successful Stripe Checkout and create user account (idempotent)"""
    conn = None
    cursor = None
    try:
        from shared.pricing_config import SUBSCRIPTION_PLANS
        from shared.subscription_manager import SubscriptionManager
        import secrets as secret_gen
        
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status != 'paid':
            return jsonify({'error': 'Payment not completed'}), 400
        
        # Get plan details from metadata
        plan_key = session.metadata.get('plan_key')
        if not plan_key or plan_key not in SUBSCRIPTION_PLANS:
            return jsonify({'error': 'Invalid plan'}), 400
        
        plan = SUBSCRIPTION_PLANS[plan_key]
        customer_email = session.customer_details.email
        customer_name = session.customer_details.name or customer_email.split('@')[0]
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # IDEMPOTENCY: Check if this session was already processed
        cursor.execute("""
            SELECT u.id, u.email FROM users u
            JOIN organizations o ON u.org_id = o.id
            WHERE o.stripe_customer_id = %s AND u.email = %s
        """, (session.customer, customer_email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Session already processed - return success (idempotent)
            logger.info(f"Session {session_id} already processed for {customer_email}")
            return jsonify({
                'success': True,
                'message': 'Account already created',
                'email': customer_email,
                'already_processed': True
            }), 200
        
        # Check if email is already used (edge case: different checkout)
        cursor.execute("SELECT id FROM users WHERE email = %s", (customer_email,))
        email_conflict = cursor.fetchone()
        
        if email_conflict:
            logger.warning(f"Email {customer_email} already exists with different checkout")
            return jsonify({'error': 'An account with this email already exists. Please login.'}), 400
        
        # Generate random password for the user
        temp_password = secret_gen.token_urlsafe(16)
        password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Extract company name from email domain
        company_domain = customer_email.split('@')[1]
        company_name = company_domain.split('.')[0].title()
        
        # Create organization with Stripe customer ID
        cursor.execute("""
            INSERT INTO organizations (name, stripe_customer_id, created_at)
            VALUES (%s, %s, NOW())
            RETURNING id
        """, (company_name, session.customer))
        org_id = cursor.fetchone()['id']
        
        # Create user
        cursor.execute("""
            INSERT INTO users (email, password_hash, name, company, email_verified, org_id, created_at)
            VALUES (%s, %s, %s, %s, true, %s, NOW())
            RETURNING id
        """, (customer_email, password_hash, customer_name, company_name, org_id))
        user_id = cursor.fetchone()['id']
        
        # Create subscription using SubscriptionManager
        sub_manager = SubscriptionManager(conn)
        subscription = sub_manager.create_subscription(
            org_id=org_id,
            plan_key=plan_key,
            stripe_customer_id=session.customer,
            stripe_subscription_id=session.subscription,
            trial_days=0
        )
        
        conn.commit()
        
        # Send welcome email with credentials
        email_sent = False
        try:
            postmark = PostmarkClient()
            email_sent = postmark.send_purchase_welcome_email(
                to_email=customer_email,
                customer_name=customer_name,
                plan_name=plan['name'],
                temp_password=temp_password,
                login_url=f"{WEBSITE_URL}/login.html"
            )
            if email_sent:
                logger.info(f"Sent welcome email to {customer_email}")
        except Exception as email_error:
            logger.error(f"Failed to send welcome email: {email_error}")
        
        # If email failed, store temp password for support retrieval
        if not email_sent:
            cursor.execute("""
                UPDATE users
                SET notes = %s
                WHERE id = %s
            """, (f"URGENT: Welcome email failed to send. Temp password: {temp_password}. Send manually or via password reset.", user_id))
            conn.commit()
            logger.error(f"CRITICAL: Welcome email failed for {customer_email}. Password stored in user notes for support.")
        
        logger.info(f"Successfully created account for {customer_email} with {plan_key} plan")
        
        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'email': customer_email,
            'email_sent': email_sent
        }), 200
        
    except stripe.StripeError as se:
        logger.error(f"Stripe error processing checkout: {se}")
        return jsonify({'error': 'Failed to verify payment'}), 500
    except Exception as e:
        logger.error(f"Process checkout success error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'error': 'Failed to create account. Please contact support.'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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

@app.route('/api/purchase-credits', methods=['POST', 'GET'])
def purchase_credits():
    """DEPRECATED: Credit purchases removed. Platform now uses subscription model."""
    return jsonify({
        'error': 'Credit purchases are no longer available',
        'message': 'VeritasLogic now uses a subscription-based model. Start your 14-day free trial to continue.',
        'action_required': 'start_subscription_trial',
        'learn_more': '/pricing'
    }), 410

@app.route('/api/purchase-credits-legacy', methods=['POST'])
def purchase_credits_legacy():
    """Legacy endpoint - redirects to Stripe payment flow"""
    return jsonify({
        'error': 'This endpoint is deprecated. Use /api/stripe/create-payment-intent for payments.',
        'redirect': '/api/stripe/create-payment-intent'
    }), 400

@app.route('/api/user/wallet-balance', methods=['GET'])
def get_wallet_balance():
    """DEPRECATED: Wallet balance endpoint - platform now uses subscription word allowances"""
    logger.warning(f"Deprecated endpoint /api/user/wallet-balance called")
    return jsonify({
        'error': 'Wallet balance system has been replaced',
        'message': 'VeritasLogic now uses subscription-based word allowances. Check your subscription status instead.',
        'action_required': 'check_subscription_status',
        'balance': 0  # Legacy compatibility
    }), 410

@app.route('/api/user/purchase-credits', methods=['POST'])
def user_purchase_credits():
    """DEPRECATED: Platform now uses subscription model"""
    logger.warning(f"Deprecated endpoint /api/user/purchase-credits called")
    return jsonify({
        'success': False,
        'error': 'Credit purchases are no longer available',
        'message': 'VeritasLogic now uses subscriptions. Start your 14-day free trial.',
        'action_required': 'start_subscription_trial'
    }), 410

@app.route('/api/user/purchase-credits-legacy', methods=['POST'])
def user_purchase_credits_legacy():
    """DEPRECATED: User credit purchase endpoint (matches wallet manager calls)"""
    logger.warning(f"Deprecated endpoint /api/user/purchase-credits-legacy called")
    return jsonify({
        'success': False,
        'error': 'Credit purchases are no longer available',
        'message': 'VeritasLogic now uses subscriptions. Upgrade your subscription plan for more word allowance.',
        'action_required': 'upgrade_subscription'
    }), 410

@app.route('/api/user/charge-wallet', methods=['POST'])
def charge_wallet():
    """DEPRECATED: Wallet charging removed - subscription system now tracks word usage automatically"""
    logger.warning(f"Deprecated endpoint /api/user/charge-wallet called")
    return jsonify({
        'success': False,
        'error': 'Wallet charging is no longer used',
        'message': 'Word usage is automatically tracked with your subscription. No manual charging needed.',
        'action_required': 'none'
    }), 410

@app.route('/api/user/auto-credit', methods=['POST'])
def auto_credit_wallet():
    """DEPRECATED: Auto-credit removed (subscription model doesn't charge for failed analyses)"""
    logger.warning(f"Deprecated endpoint /api/user/auto-credit called")
    return jsonify({
        'success': False,
        'error': 'Auto-credit is no longer needed',
        'message': 'Subscriptions only deduct words from successful analyses. Failed analyses are free.',
        'note': 'No action required - your word allowance was not affected.'
    }), 410

@app.route('/api/user/auto-credit-legacy', methods=['POST'])
def auto_credit_wallet_legacy():
    """DEPRECATED LEGACY: Auto-credit user's wallet for failed analysis"""
    logger.warning(f"Deprecated endpoint /api/user/auto-credit-legacy called")
    return jsonify({
        'success': False,
        'error': 'Auto-credit is no longer needed',
        'message': 'Subscriptions only deduct words from successful analyses. Failed analyses are free.',
        'note': 'No action required - your word allowance was not affected.'
    }), 410

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

@app.route('/api/demo/register', methods=['POST'])
def demo_registration():
    """Handle demo registration form submissions via Postmark"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'company', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Extract form data
        name = sanitize_string(data.get('name'), 100)
        email = sanitize_string(data.get('email'), 100)
        company = sanitize_string(data.get('company'), 100)
        role = sanitize_string(data.get('role'), 100)
        
        # Send email using PostmarkClient
        postmark = PostmarkClient()
        success = postmark.send_demo_registration(
            name=name,
            email=email,
            company=company,
            role=role
        )
        
        if not success:
            raise Exception("Failed to send demo registration email")
        
        logger.info(f"Demo registration: {name} from {company} ({email})")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Check your email for the invite.'
        }), 200
        
    except Exception as e:
        logger.error(f"Demo registration error: {sanitize_for_log(e)}")
        return jsonify({'error': 'Failed to register. Please try again or email support@veritaslogic.ai'}), 500

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
        
        # Get total words used (subscription model)
        # For subscription model, "total spent" is replaced with word usage
        cursor.execute("""
            SELECT COALESCE(SUM(words_count), 0) as total_words_used
            FROM analyses 
            WHERE user_id = %s AND status = 'completed'
        """, (user_id,))
        result = cursor.fetchone()
        total_words_used = result['total_words_used'] if result else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_analyses': int(total_analyses),
                'analyses_this_month': int(month_analyses),
                'total_spent': 0  # Deprecated for subscription model
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
        # Only show completed analyses with actual memo content (not failed/processing/empty ones)
        cursor.execute("""
            SELECT 
                a.analysis_id,
                COALESCE(a.memo_uuid, 'unknown') as id,
                a.asc_standard,
                a.completed_at,
                a.status,
                0 as cost,
                a.words_count,
                a.file_count,
                a.tier_name,
                COALESCE(a.analysis_type, 'standard') as analysis_type,
                CONCAT(a.asc_standard, ' Analysis') as document_name
            FROM analyses a
            WHERE a.user_id = %s 
                AND a.status = 'completed'
                AND a.completed_at IS NOT NULL
                AND a.memo_content IS NOT NULL
                AND LENGTH(a.memo_content) > 100
            ORDER BY a.completed_at DESC
            LIMIT 20
        """, (user_id,))
        
        analyses = []
        for row in cursor.fetchall():
            analysis_type = row['analysis_type'] or 'standard'
            analyses.append({
                'id': row['id'],
                'analysis_id': row['analysis_id'],
                'title': row['document_name'] or f"{row['asc_standard']} Analysis",
                'asc_standard': row['asc_standard'] or 'Unknown',
                'analysis_type': analysis_type,
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
            SELECT u.id, u.email, u.first_name, u.last_name, u.org_id,
                   u.preferences, u.created_at,
                   o.name as company_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.id
            WHERE u.id = %s
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
                'company_name': user['company_name'] or '',
                'org_id': user['org_id'],
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

# ==========================================
# STRIPE WEBHOOK HANDLERS
# ==========================================

def create_usage_record(subscription_id, org_id, plan_key, period_start_dt, period_end_dt, conn, words_used=0):
    """
    Create subscription_usage record based on Stripe billing period (not calendar month).
    Preserves words_used for mid-period updates.
    
    Args:
        subscription_id: Database subscription_instances.id
        org_id: Organization ID
        plan_key: Plan identifier (professional, team, enterprise)
        period_start_dt: Stripe current_period_start as datetime
        period_end_dt: Stripe current_period_end as datetime
        conn: Database connection
        words_used: Existing word usage to preserve (default 0 for new periods)
    """
    from shared.pricing_config import SUBSCRIPTION_PLANS
    
    cursor = conn.cursor()
    
    # Get plan details
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        logger.error(f"Plan {plan_key} not found in SUBSCRIPTION_PLANS")
        return
    
    word_allowance = plan['word_allowance']
    
    # Convert Stripe period to dates for storage
    month_start = period_start_dt.date()
    month_end = period_end_dt.date()
    
    # Check if usage record already exists for this period
    cursor.execute("""
        SELECT id, words_used FROM subscription_usage
        WHERE subscription_id = %s AND month_start = %s
    """, (subscription_id, month_start))
    
    existing = cursor.fetchone()
    
    if existing:
        # Update existing record (plan change during period)
        cursor.execute("""
            UPDATE subscription_usage
            SET word_allowance = %s,
                month_end = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (word_allowance, month_end, existing['id']))
        logger.info(f"Updated usage record for org {org_id}: {word_allowance} words, preserved {existing['words_used']} used")
    else:
        # Create new record (new billing period)
        cursor.execute("""
            INSERT INTO subscription_usage
            (subscription_id, org_id, month_start, month_end, 
             word_allowance, words_used, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (subscription_id, org_id, month_start, month_end, word_allowance, words_used))
        logger.info(f"Created usage record for org {org_id}: {word_allowance} words, period {month_start} to {month_end}")


@app.route('/api/webhooks/stripe', methods=['POST'])
def stripe_subscription_webhook():
    """
    Handle Stripe webhook events for subscription management.
    Supports: subscription.created/updated/deleted, invoice.payment_succeeded/failed,
    checkout.session.completed with idempotency protection.
    """
    import stripe
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return jsonify({'error': 'Webhook not configured'}), 500
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    event_type = event['type']
    event_id = event['id']
    
    logger.info(f"Received Stripe webhook: {event_type} ({event_id})")
    
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed for webhook processing")
        return jsonify({'error': 'Database unavailable'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check for idempotency - have we already processed this event?
        cursor.execute("""
            SELECT id FROM stripe_webhook_events
            WHERE event_id = %s
        """, (event_id,))
        
        if cursor.fetchone():
            logger.info(f"Event {event_id} already processed (idempotent)")
            return jsonify({'received': True, 'status': 'already_processed'}), 200
        
        # Record event for idempotency
        cursor.execute("""
            INSERT INTO stripe_webhook_events (event_id, event_type, processed_at)
            VALUES (%s, %s, NOW())
        """, (event_id, event_type))
        
        # Route to appropriate handler
        if event_type == 'checkout.session.completed':
            handle_checkout_completed(event, conn)
        
        elif event_type == 'customer.subscription.created':
            handle_subscription_created(event, conn)
        
        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(event, conn)
        
        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(event, conn)
        
        elif event_type == 'invoice.payment_succeeded':
            handle_payment_succeeded(event, conn)
        
        elif event_type == 'invoice.payment_failed':
            handle_payment_failed(event, conn)
        
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
        
        conn.commit()
        
        return jsonify({'received': True, 'status': 'processed'}), 200
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': 'Processing failed'}), 500
    finally:
        conn.close()


def handle_checkout_completed(event, conn):
    """Handle successful checkout session completion"""
    session = event['data']['object']
    
    signup_type = session['metadata'].get('signup_type')
    
    # For direct purchases, the account is created in the success endpoint
    # The webhook will receive the subscription.created event separately
    if signup_type == 'direct_purchase':
        logger.info(f"Checkout completed for direct purchase (session {session['id']}). Account creation handled by success endpoint.")
        return
    
    # For trial signups or upgrades with existing org
    org_id = session['metadata'].get('org_id')
    plan_key = session['metadata'].get('plan_key')
    stripe_subscription_id = session.get('subscription')
    customer_id = session.get('customer')
    
    if not org_id or not plan_key:
        logger.error(f"Missing metadata in checkout session: {session['id']}")
        return
    
    logger.info(f"Checkout completed for org {org_id}, plan {plan_key}")
    
    cursor = conn.cursor()
    
    # Update organization with customer ID
    cursor.execute("""
        UPDATE organizations
        SET stripe_customer_id = %s, updated_at = NOW()
        WHERE id = %s
    """, (customer_id, org_id))
    
    # The actual subscription will be created via subscription.created event
    logger.info(f"Updated org {org_id} with Stripe customer {customer_id}")


def handle_subscription_created(event, conn):
    """Handle new subscription creation"""
    subscription = event['data']['object']
    
    stripe_sub_id = subscription['id']
    customer_id = subscription['customer']
    status = subscription['status']
    plan_key = subscription['metadata'].get('plan_key', 'professional')
    
    current_period_start = datetime.fromtimestamp(subscription['current_period_start'], tz=timezone.utc)
    current_period_end = datetime.fromtimestamp(subscription['current_period_end'], tz=timezone.utc)
    
    cursor = conn.cursor()
    
    # Find organization by customer ID
    cursor.execute("""
        SELECT id FROM organizations
        WHERE stripe_customer_id = %s
    """, (customer_id,))
    
    org = cursor.fetchone()
    
    if not org:
        logger.error(f"No organization found for Stripe customer {customer_id}")
        return
    
    org_id = org['id']
    
    logger.info(f"Creating subscription for org {org_id}: {plan_key}, status: {status}")
    
    # Look up plan ID from plan_key
    cursor.execute("""
        SELECT id FROM subscription_plans
        WHERE plan_key = %s AND is_active = true
    """, (plan_key,))
    
    plan = cursor.fetchone()
    if not plan:
        logger.error(f"Plan {plan_key} not found")
        return
    
    plan_id = plan['id']
    
    # Cancel any existing trial subscriptions for this org
    cursor.execute("""
        UPDATE subscription_instances
        SET status = 'cancelled', updated_at = NOW()
        WHERE org_id = %s AND status = 'trialing'
    """, (org_id,))
    
    # Create new subscription instance
    cursor.execute("""
        INSERT INTO subscription_instances (
            org_id, plan_id, stripe_subscription_id, status,
            current_period_start, current_period_end
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (org_id, stripe_subscription_id) 
        DO UPDATE SET
            status = EXCLUDED.status,
            current_period_start = EXCLUDED.current_period_start,
            current_period_end = EXCLUDED.current_period_end,
            updated_at = NOW()
        RETURNING id
    """, (org_id, plan_id, stripe_sub_id, status, current_period_start, current_period_end))
    
    sub_instance = cursor.fetchone()
    subscription_id = sub_instance['id']
    
    logger.info(f"Subscription created for org {org_id}")
    
    # Create subscription_usage record for this billing period
    create_usage_record(subscription_id, org_id, plan_key, 
                       current_period_start, current_period_end, conn, words_used=0)
    
    # Send upgrade confirmation email to user
    try:
        # Get user info for this organization
        cursor.execute("""
            SELECT email, name FROM users WHERE org_id = %s LIMIT 1
        """, (org_id,))
        user = cursor.fetchone()
        
        if user:
            # Get plan details for email
            from shared.pricing_config import SUBSCRIPTION_PLANS
            plan_info = SUBSCRIPTION_PLANS.get(plan_key, {})
            plan_name = plan_info.get('name', plan_key.title())
            word_allowance = plan_info.get('word_allowance', 150000)
            monthly_words = f"{word_allowance:,}"
            
            postmark = PostmarkClient()
            email_sent = postmark.send_upgrade_confirmation_email(
                to_email=user['email'],
                customer_name=user['name'] or 'Valued Customer',
                plan_name=plan_name,
                monthly_words=monthly_words,
                login_url=f"{os.getenv('WEBSITE_URL', 'https://veritaslogic.ai')}/login.html"
            )
            
            if email_sent:
                logger.info(f"Upgrade confirmation email sent to {user['email']}")
            else:
                logger.warning(f"Failed to send upgrade confirmation email to {user['email']}")
            
            # Send admin notification to support@
            try:
                admin_email_sent = postmark.send_admin_upgrade_notification(
                    customer_email=user['email'],
                    customer_name=user['name'] or 'Unknown',
                    plan_name=plan_name,
                    monthly_price=plan_info.get('price_monthly', 295.00)
                )
                if admin_email_sent:
                    logger.info(f"Admin upgrade notification sent for {user['email']}")
            except Exception as admin_email_error:
                logger.error(f"Failed to send admin upgrade notification: {admin_email_error}")
        else:
            logger.warning(f"No user found for org {org_id} - skipping upgrade email")
    except Exception as email_error:
        logger.error(f"Error sending upgrade confirmation email: {email_error}")


def handle_subscription_updated(event, conn):
    """Handle subscription updates (plan changes, renewals, cancellations)"""
    subscription = event['data']['object']
    
    stripe_sub_id = subscription['id']
    status = subscription['status']
    plan_key = subscription['metadata'].get('plan_key')
    cancel_at_period_end = bool(subscription.get('cancel_at_period_end', False))
    
    current_period_start = datetime.fromtimestamp(subscription['current_period_start'], tz=timezone.utc)
    current_period_end = datetime.fromtimestamp(subscription['current_period_end'], tz=timezone.utc)
    
    cursor = conn.cursor()
    
    logger.info(f"Updating subscription {stripe_sub_id}: status={status}, cancel_at_period_end={cancel_at_period_end}")
    
    # Look up plan ID if plan_key provided
    plan_id = None
    if plan_key:
        cursor.execute("""
            SELECT id FROM subscription_plans
            WHERE plan_key = %s AND is_active = true
        """, (plan_key,))
        
        plan = cursor.fetchone()
        if plan:
            plan_id = plan['id']
    
    # Update subscription instance including cancel_at_period_end
    if plan_id:
        cursor.execute("""
            UPDATE subscription_instances
            SET status = %s,
                current_period_start = %s,
                current_period_end = %s,
                plan_id = %s,
                cancel_at_period_end = %s,
                updated_at = NOW()
            WHERE stripe_subscription_id = %s
        """, (status, current_period_start, current_period_end, plan_id, cancel_at_period_end, stripe_sub_id))
    else:
        cursor.execute("""
            UPDATE subscription_instances
            SET status = %s,
                current_period_start = %s,
                current_period_end = %s,
                cancel_at_period_end = %s,
                updated_at = NOW()
            WHERE stripe_subscription_id = %s
        """, (status, current_period_start, current_period_end, cancel_at_period_end, stripe_sub_id))
    
    if cursor.rowcount == 0:
        logger.warning(f"No subscription found for Stripe subscription {stripe_sub_id}")
        # Fallback: create it using subscription.created logic
        handle_subscription_created(event, conn)
        return
    
    logger.info(f"Subscription {stripe_sub_id} updated")
    
    # Get subscription_id and org_id
    cursor.execute("""
        SELECT id, org_id FROM subscription_instances
        WHERE stripe_subscription_id = %s
    """, (stripe_sub_id,))
    
    sub_inst = cursor.fetchone()
    if not sub_inst:
        logger.error(f"Failed to find subscription_instance after update")
        return
    
    subscription_id = sub_inst['id']
    org_id = sub_inst['org_id']
    
    # Handle usage record creation/update
    if plan_key:
        # Plan change or renewal - update/create usage record
        create_usage_record(subscription_id, org_id, plan_key,
                           current_period_start, current_period_end, conn)


def handle_subscription_deleted(event, conn):
    """Handle subscription cancellation (immediate or at period end)"""
    subscription = event['data']['object']
    
    stripe_sub_id = subscription['id']
    
    cursor = conn.cursor()
    
    logger.info(f"Cancelling subscription {stripe_sub_id}")
    
    # When subscription is fully deleted, set status to cancelled and clear cancel_at_period_end
    cursor.execute("""
        UPDATE subscription_instances
        SET status = 'cancelled', 
            cancel_at_period_end = false,
            updated_at = NOW()
        WHERE stripe_subscription_id = %s
    """, (stripe_sub_id,))
    
    logger.info(f"Subscription {stripe_sub_id} cancelled")


def handle_payment_succeeded(event, conn):
    """Handle successful invoice payment"""
    invoice = event['data']['object']
    
    stripe_sub_id = invoice.get('subscription')
    amount_paid = invoice.get('amount_paid', 0) / 100  # Convert cents to dollars
    
    if not stripe_sub_id:
        logger.info("Invoice payment succeeded but no subscription ID found")
        return
    
    cursor = conn.cursor()
    
    logger.info(f"Payment succeeded for subscription {stripe_sub_id}: ${amount_paid:.2f}")
    
    # Update subscription status to active if it was past_due
    cursor.execute("""
        UPDATE subscription_instances
        SET status = 'active', updated_at = NOW()
        WHERE stripe_subscription_id = %s AND status = 'past_due'
    """, (stripe_sub_id,))
    
    if cursor.rowcount > 0:
        logger.info(f"Subscription {stripe_sub_id} reactivated after payment")


def handle_payment_failed(event, conn):
    """Handle failed invoice payment"""
    invoice = event['data']['object']
    
    stripe_sub_id = invoice.get('subscription')
    
    if not stripe_sub_id:
        logger.info("Invoice payment failed but no subscription ID found")
        return
    
    cursor = conn.cursor()
    
    logger.warning(f"Payment failed for subscription {stripe_sub_id}")
    
    # Update subscription status to past_due
    cursor.execute("""
        UPDATE subscription_instances
        SET status = 'past_due', updated_at = NOW()
        WHERE stripe_subscription_id = %s
    """, (stripe_sub_id,))
    
    logger.info(f"Subscription {stripe_sub_id} marked as past_due")


# ==========================================
# SUBSCRIPTION API ENDPOINTS
# ==========================================

@app.route('/api/subscription/plans', methods=['GET'])
def get_subscription_plans():
    """Get all available subscription plans"""
    try:
        from shared.pricing_config import get_plan_comparison
        
        plans = get_plan_comparison()
        
        return jsonify({
            'plans': plans,
            'trial_config': {
                'duration_days': 14,
                'word_allowance': 9000,
                'requires_payment_method': True
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get subscription plans error: {e}")
        return jsonify({'error': 'Failed to get subscription plans'}), 500


@app.route('/api/subscription/usage', methods=['GET'])
def get_subscription_usage():
    """Get current subscription usage for user's organization"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT org_id FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user or not user['org_id']:
                return jsonify({'error': 'User organization not found'}), 404
            
            from shared.subscription_manager import SubscriptionManager
            sub_mgr = SubscriptionManager(conn)
            
            usage = sub_mgr.get_current_usage(user['org_id'])
            
            return jsonify(usage), 200
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Get subscription usage error: {e}")
        return jsonify({'error': 'Failed to get subscription usage'}), 500


@app.route('/api/subscription/check-allowance', methods=['POST'])
def check_subscription_allowance():
    """Check if user has sufficient word allowance for analysis (preflight check)"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        data = request.get_json()
        words_needed = int(data.get('words_needed', 0))
        
        if words_needed <= 0:
            return jsonify({'error': 'Invalid words_needed parameter'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT org_id FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user or not user['org_id']:
                return jsonify({'error': 'User organization not found'}), 404
            
            org_id = user['org_id']
            
            from shared.subscription_manager import SubscriptionManager
            sub_mgr = SubscriptionManager(conn)
            
            allowance_check = sub_mgr.check_word_allowance(org_id, words_needed)
            usage_info = sub_mgr.get_current_usage(org_id)
            
            can_proceed = allowance_check['allowed']
            suggested_action = allowance_check.get('suggested_action', 'upgrade_plan')
            
            if usage_info.get('is_trial'):
                segment = 'trial'
            elif usage_info.get('subscription_status') == 'past_due':
                segment = 'past_due'
            elif usage_info.get('has_subscription'):
                segment = 'paid'
            else:
                segment = 'none'
            
            result = {
                'can_proceed': can_proceed,
                'segment': segment,
                'status': usage_info.get('subscription_status', 'no_subscription'),
                'words_available': allowance_check['words_available'],
                'words_remaining_after': allowance_check.get('words_remaining_after', 0),
                'show_warning': can_proceed and usage_info.get('words_available', 0) < 5000,
                'renewal_date': usage_info.get('current_period_end').strftime('%B %d, %Y') if usage_info.get('current_period_end') else 'Unknown',
                'org_id': org_id,
                'upgrade_link': 'https://www.veritaslogic.ai/dashboard',
                'total_words': words_needed
            }
            
            if not can_proceed:
                result['error_message'] = allowance_check['reason']
            
            logger.info(f"Allowance check for org {org_id}: {words_needed} words, can_proceed={can_proceed}, segment={segment}")
            
            return jsonify(result), 200
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Check subscription allowance error: {e}")
        return jsonify({'error': 'Failed to check subscription allowance'}), 500


@app.route('/api/subscription/status', methods=['GET'])
def get_subscription_status():
    """Get current subscription status for user's organization"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT org_id FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user or not user['org_id']:
                return jsonify({'error': 'User organization not found'}), 404
            
            # Get active subscription
            cursor.execute("""
                SELECT 
                    si.id,
                    si.status,
                    si.trial_start_date,
                    si.trial_end_date,
                    si.current_period_start,
                    si.current_period_end,
                    si.cancel_at_period_end,
                    si.stripe_subscription_id,
                    sp.name as plan_name,
                    sp.plan_key,
                    sp.price_monthly as plan_price,
                    sp.word_allowance
                FROM subscription_instances si
                JOIN subscription_plans sp ON si.plan_id = sp.id
                WHERE si.org_id = %s 
                    AND si.status IN ('trial', 'active', 'past_due', 'canceled')
                ORDER BY si.created_at DESC
                LIMIT 1
            """, (user['org_id'],))
            
            subscription = cursor.fetchone()
            
            if not subscription:
                return jsonify({
                    'success': False,
                    'error': 'No subscription found'
                }), 404
            
            # Get current usage - use subscription_id to get the correct record
            # This handles mid-period upgrades where month_start differs from calendar month
            cursor.execute("""
                SELECT words_used, word_allowance
                FROM subscription_usage
                WHERE subscription_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (subscription['id'],))
            
            usage = cursor.fetchone()
            words_used = usage['words_used'] if usage else 0
            word_allowance = usage['word_allowance'] if usage else subscription['word_allowance']
            
            return jsonify({
                'success': True,
                'subscription': {
                    'status': subscription['status'],
                    'plan_name': subscription['plan_name'],
                    'plan_key': subscription['plan_key'],
                    'plan_price': float(subscription['plan_price']) if subscription['plan_price'] else 0,
                    'word_allowance': word_allowance,
                    'words_used': words_used,
                    'trial_start_date': subscription['trial_start_date'].isoformat() if subscription['trial_start_date'] else None,
                    'trial_end_date': subscription['trial_end_date'].isoformat() if subscription['trial_end_date'] else None,
                    'current_period_start': subscription['current_period_start'].isoformat() if subscription['current_period_start'] else None,
                    'current_period_end': subscription['current_period_end'].isoformat() if subscription['current_period_end'] else None,
                    'cancel_at_period_end': subscription['cancel_at_period_end'],
                    'has_payment_method': bool(subscription['stripe_subscription_id'])
                }
            }), 200
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Get subscription status error: {e}")
        return jsonify({'error': 'Failed to get subscription status'}), 500


@app.route('/api/subscription/activate-trial', methods=['POST'])
def activate_trial():
    """
    Activate trial subscription for organization
    NOTE: Trials are automatically created during signup
    This endpoint is for manual activation if needed
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT org_id, role FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user or not user['org_id']:
                return jsonify({'error': 'User organization not found'}), 404
            
            if user['role'] != 'owner':
                return jsonify({'error': 'Only organization owners can activate trials'}), 403
            
            from shared.subscription_manager import SubscriptionManager
            sub_mgr = SubscriptionManager(conn)
            
            trial_result = sub_mgr.create_trial_subscription(user['org_id'], plan_key='professional')
            
            return jsonify({
                'message': 'Trial activated successfully',
                'trial': trial_result
            }), 200
            
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Activate trial error: {e}")
        return jsonify({'error': 'Failed to activate trial'}), 500


@app.route('/api/subscription/upgrade', methods=['POST'])
def create_upgrade_checkout():
    """Create Stripe checkout session for subscription upgrade"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        data = request.get_json()
        
        plan_key = sanitize_string(data.get('plan_key', ''), 50)
        
        if not plan_key or plan_key not in ['professional', 'team', 'enterprise']:
            return jsonify({'error': 'Valid plan_key required (professional, team, or enterprise)'}), 400
        
        # Import stripe at function level so exception handler can reference it
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.org_id, u.email, u.role, o.stripe_customer_id, o.name as org_name
                FROM users u
                JOIN organizations o ON u.org_id = o.id
                WHERE u.id = %s
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user or not user['org_id']:
                return jsonify({'error': 'User organization not found'}), 404
            
            if user['role'] != 'owner':
                return jsonify({'error': 'Only organization owners can upgrade subscriptions'}), 403
            
            # Check if organization already has a subscription (active, trialing, past_due, etc.)
            cursor.execute("""
                SELECT id, status FROM subscription_instances
                WHERE org_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (user['org_id'],))
            existing_subscription = cursor.fetchone()
            
            # If org has any subscription, no trial (immediate billing)
            # If no subscription, give 14-day trial (new customer)
            has_existing_subscription = existing_subscription is not None
            trial_days = 0 if has_existing_subscription else 14
            
            logger.info(f"Org {user['org_id']} upgrade: existing_sub={has_existing_subscription}, trial_days={trial_days}")
            
            # Get plan details
            from shared.pricing_config import get_plan_by_key
            plan = get_plan_by_key(plan_key)
            
            if not plan:
                return jsonify({'error': f'Plan {plan_key} not found'}), 404
            
            # Get or create Stripe customer
            if user['stripe_customer_id']:
                customer_id = user['stripe_customer_id']
            else:
                # Create Stripe customer
                customer = stripe.Customer.create(
                    email=user['email'],
                    name=user['org_name'],
                    metadata={
                        'org_id': user['org_id'],
                        'user_id': user_id
                    }
                )
                customer_id = customer.id
                
                # Save customer ID
                cursor.execute("""
                    UPDATE organizations
                    SET stripe_customer_id = %s
                    WHERE id = %s
                """, (customer_id, user['org_id']))
                conn.commit()
            
            # Create Stripe checkout session
            # NOTE: Stripe price IDs will be set up in Task 6
            stripe_price_id = plan.get('stripe_price_id')
            
            if not stripe_price_id:
                return jsonify({
                    'error': 'Stripe integration not configured',
                    'message': f'Please contact support to set up {plan["name"]} subscription'
                }), 503
            
            # Build subscription_data - only include trial_period_days if > 0 (Stripe minimum is 1)
            subscription_data = {
                'metadata': {
                    'org_id': user['org_id'],
                    'plan_key': plan_key
                }
            }
            if trial_days > 0:
                subscription_data['trial_period_days'] = trial_days
            
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{
                    'price': stripe_price_id,
                    'quantity': 1
                }],
                success_url=f"{WEBSITE_URL}/subscription-success.html?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{WEBSITE_URL}/subscription-cancel.html",
                metadata={
                    'org_id': user['org_id'],
                    'user_id': user_id,
                    'plan_key': plan_key
                },
                subscription_data=subscription_data
            )
            
            logger.info(f"Created Stripe checkout session for org {user['org_id']}: {checkout_session.id}")
            
            return jsonify({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id,
                'plan': {
                    'key': plan_key,
                    'name': plan['name'],
                    'price_monthly': plan['price_monthly'],
                    'word_allowance': plan['word_allowance']
                }
            }), 200
            
        finally:
            conn.close()
        
    except stripe.StripeError as se:
        logger.error(f"Stripe error creating checkout session: {se}")
        return jsonify({
            'error': 'Payment processing error',
            'message': 'Unable to create checkout session. Please try again.'
        }), 500
    except Exception as e:
        logger.error(f"Create upgrade checkout error: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500


@app.route('/api/subscription/verify-upgrade', methods=['POST'])
def verify_and_process_upgrade():
    """Verify Stripe checkout session and immediately process subscription upgrade"""
    from shared.pricing_config import SUBSCRIPTION_PLANS
    
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        # Retrieve the checkout session from Stripe
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.StripeError as se:
            logger.error(f"Failed to retrieve Stripe session {session_id}: {se}")
            return jsonify({'error': 'Invalid checkout session'}), 400
        
        # Verify payment was successful
        if session.payment_status != 'paid':
            return jsonify({'error': 'Payment not completed'}), 400
        
        # Extract metadata
        org_id = session.metadata.get('org_id')
        plan_key = session.metadata.get('plan_key')
        stripe_subscription_id = session.subscription
        customer_id = session.customer
        
        if not org_id or not plan_key or not stripe_subscription_id:
            logger.error(f"Missing metadata in session {session_id}")
            return jsonify({'error': 'Invalid session metadata'}), 400
        
        # Get subscription details from Stripe
        try:
            stripe_sub_obj = stripe.Subscription.retrieve(stripe_subscription_id)
            stripe_sub = stripe_sub_obj.to_dict()
        except stripe.StripeError as se:
            logger.error(f"Failed to retrieve subscription {stripe_subscription_id}: {se}")
            return jsonify({'error': 'Failed to retrieve subscription'}), 500
        
        # Get plan details
        plan = SUBSCRIPTION_PLANS.get(plan_key)
        if not plan:
            return jsonify({'error': 'Invalid plan'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Get plan_id from subscription_plans table
            cursor.execute("""
                SELECT id FROM subscription_plans WHERE plan_key = %s
            """, (plan_key,))
            plan_row = cursor.fetchone()
            if not plan_row:
                return jsonify({'error': 'Plan not found in database'}), 400
            plan_id = plan_row['id']
            
            # Find and cancel existing active/trial subscription (always cancel, even if usage missing)
            cursor.execute("""
                SELECT si.id, sp.plan_key
                FROM subscription_instances si
                JOIN subscription_plans sp ON si.plan_id = sp.id
                WHERE si.org_id = %s AND si.status IN ('active', 'trial')
                ORDER BY si.created_at DESC
                LIMIT 1
            """, (org_id,))
            
            old_sub = cursor.fetchone()
            old_sub_id = old_sub['id'] if old_sub else None
            old_plan_key = old_sub['plan_key'] if old_sub else None
            
            # Get usage data for rollover calculation (separate query, won't block cancellation)
            rollover_words = 0
            if old_sub_id and plan_key == 'team' and old_plan_key == 'professional':
                cursor.execute("""
                    SELECT word_allowance, words_used
                    FROM subscription_usage
                    WHERE subscription_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (old_sub_id,))
                
                old_usage = cursor.fetchone()
                if old_usage:
                    prev_allowance = old_usage['word_allowance']
                    prev_used = old_usage['words_used']
                    rollover_words = max(0, prev_allowance - prev_used)
                    logger.info(f"Pro→Team rollover: {rollover_words} words will carry over (used {prev_used}/{prev_allowance})")
            
            # Always cancel old subscription (prevents duplicate active subscriptions)
            if old_sub_id:
                cursor.execute("""
                    UPDATE subscription_instances
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE id = %s
                """, (old_sub_id,))
                logger.info(f"Cancelled old subscription {old_sub_id}")
            
            # PRESERVE historical usage data - do NOT delete old usage records
            
            # Create new subscription instance
            # Safely extract period timestamps with null checks
            period_start_ts = stripe_sub.get('current_period_start')
            period_end_ts = stripe_sub.get('current_period_end')
            
            if not period_start_ts or not period_end_ts:
                logger.warning(f"Missing period timestamps for subscription {stripe_subscription_id}: start={period_start_ts}, end={period_end_ts}")
                # Use start_date as fallback or current time
                period_start_ts = stripe_sub.get('start_date') or int(time.time())
                period_end_ts = period_start_ts + (30 * 24 * 60 * 60)  # Add 30 days
            
            current_period_start = datetime.fromtimestamp(period_start_ts, tz=timezone.utc)
            current_period_end = datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
            
            cursor.execute("""
                INSERT INTO subscription_instances 
                (org_id, plan_id, stripe_subscription_id, status, 
                 current_period_start, current_period_end, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (org_id, plan_id, stripe_subscription_id, stripe_sub.get('status', 'active'),
                  current_period_start, current_period_end))
            
            new_sub_id = cursor.fetchone()['id']
            
            # Create usage record aligned with Stripe billing period (matches create_usage_record logic)
            base_allowance = plan['word_allowance']
            total_allowance = base_allowance + rollover_words
            month_start = current_period_start.date()
            month_end = current_period_end.date()
            
            cursor.execute("""
                INSERT INTO subscription_usage
                (subscription_id, org_id, month_start, month_end, 
                 word_allowance, words_used, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 0, NOW(), NOW())
            """, (new_sub_id, org_id, month_start, month_end, total_allowance))
            
            # Update organization with Stripe customer ID
            cursor.execute("""
                UPDATE organizations
                SET stripe_customer_id = %s, updated_at = NOW()
                WHERE id = %s
            """, (customer_id, org_id))
            
            conn.commit()
            
            logger.info(f"✅ Subscription upgraded: org={org_id}, plan={plan_key}, sub_id={new_sub_id}")
            
            return jsonify({
                'success': True,
                'message': 'Subscription upgraded successfully',
                'plan': {
                    'name': plan['name'],
                    'word_allowance': plan['word_allowance']
                }
            }), 200
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Verify upgrade error: {e}")
        return jsonify({'error': 'Failed to process upgrade'}), 500


@app.route('/api/subscription/cancel', methods=['POST'])
def cancel_subscription():
    """Cancel user's subscription (remains active until end of billing period)"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.org_id, u.email, u.role
                FROM users u
                WHERE u.id = %s
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user or not user['org_id']:
                return jsonify({'error': 'User organization not found'}), 404
            
            if user['role'] != 'owner':
                return jsonify({'error': 'Only organization owners can cancel subscriptions'}), 403
            
            # Get subscription
            cursor.execute("""
                SELECT si.id, si.stripe_subscription_id, si.status
                FROM subscription_instances si
                WHERE si.org_id = %s AND si.status IN ('active', 'trial')
                ORDER BY si.created_at DESC
                LIMIT 1
            """, (user['org_id'],))
            subscription = cursor.fetchone()
            
            if not subscription:
                return jsonify({'error': 'No active subscription found'}), 404
            
            # Cancel in Stripe if it's a paid subscription
            if subscription['stripe_subscription_id']:
                import stripe
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                
                try:
                    stripe.Subscription.modify(
                        subscription['stripe_subscription_id'],
                        cancel_at_period_end=True
                    )
                    logger.info(f"Canceled Stripe subscription {subscription['stripe_subscription_id']}")
                except stripe.StripeError as se:
                    logger.error(f"Stripe cancellation error: {se}")
                    return jsonify({'error': 'Failed to cancel subscription with payment provider'}), 500
            
            # Update database
            cursor.execute("""
                UPDATE subscription_instances
                SET cancel_at_period_end = true, updated_at = NOW()
                WHERE id = %s
            """, (subscription['id'],))
            conn.commit()
            
            logger.info(f"Canceled subscription for org {user['org_id']}")
            
            return jsonify({
                'success': True,
                'message': 'Subscription canceled. Access continues until end of billing period.'
            }), 200
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Cancel subscription error: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500


@app.route('/api/subscription/customer-portal', methods=['POST'])
def create_customer_portal_session():
    """Create Stripe Customer Portal session for payment method and billing management"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if user is organization owner
            cursor.execute("""
                SELECT u.role, u.org_id
                FROM users u
                WHERE u.id = %s
            """, (user_id,))
            user_result = cursor.fetchone()
            
            if not user_result:
                return jsonify({'error': 'User not found'}), 404
            
            if user_result['role'] != 'owner':
                # Get owner email for error message
                cursor.execute("""
                    SELECT email
                    FROM users
                    WHERE org_id = %s AND role = 'owner'
                    LIMIT 1
                """, (user_result['org_id'],))
                owner_result = cursor.fetchone()
                owner_email = owner_result['email'] if owner_result else 'your organization owner'
                
                logger.info(f"Permission denied: User {user_id} (role: {user_result['role']}) attempted to access customer portal for org {user_result['org_id']}")
                
                return jsonify({
                    'error': 'permission_denied',
                    'message': 'Only organization owners can access billing portal',
                    'owner_email': owner_email
                }), 403
            
            # Get user's organization and Stripe customer ID
            cursor.execute("""
                SELECT o.stripe_customer_id
                FROM users u
                JOIN organizations o ON u.org_id = o.id
                WHERE u.id = %s
            """, (user_id,))
            result = cursor.fetchone()
            
            if not result or not result['stripe_customer_id']:
                return jsonify({'error': 'No billing account found'}), 404
            
            stripe_customer_id = result['stripe_customer_id']
            
            # Create Stripe Customer Portal session
            import stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=f"{WEBSITE_URL}/dashboard.html"
            )
            
            logger.info(f"Created Customer Portal session for customer {stripe_customer_id}")
            
            return jsonify({
                'success': True,
                'url': session.url
            }), 200
            
        finally:
            conn.close()
        
    except stripe.StripeError as se:
        logger.error(f"Stripe error creating customer portal session: {se}")
        return jsonify({
            'error': 'Unable to access billing portal',
            'message': str(se)
        }), 500
    except Exception as e:
        logger.error(f"Create customer portal session error: {e}")
        return jsonify({'error': 'Failed to create billing portal session'}), 500


@app.route('/api/subscription/invoices', methods=['GET'])
def get_customer_invoices():
    """Get customer's invoice history from Stripe"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        payload = verify_token(token)
        if 'error' in payload:
            return jsonify({'error': payload['error']}), 401
        
        user_id = payload['user_id']
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if user is organization owner
            cursor.execute("""
                SELECT u.role, u.org_id
                FROM users u
                WHERE u.id = %s
            """, (user_id,))
            user_result = cursor.fetchone()
            
            if not user_result:
                return jsonify({'error': 'User not found'}), 404
            
            if user_result['role'] != 'owner':
                # Get owner email for error message
                cursor.execute("""
                    SELECT email
                    FROM users
                    WHERE org_id = %s AND role = 'owner'
                    LIMIT 1
                """, (user_result['org_id'],))
                owner_result = cursor.fetchone()
                owner_email = owner_result['email'] if owner_result else 'your organization owner'
                
                logger.info(f"Permission denied: User {user_id} (role: {user_result['role']}) attempted to view invoices for org {user_result['org_id']}")
                
                return jsonify({
                    'error': 'permission_denied',
                    'message': 'Only organization owners can view invoice history',
                    'owner_email': owner_email
                }), 403
            
            # Get user's organization and Stripe customer ID
            cursor.execute("""
                SELECT o.stripe_customer_id
                FROM users u
                JOIN organizations o ON u.org_id = o.id
                WHERE u.id = %s
            """, (user_id,))
            result = cursor.fetchone()
            
            if not result or not result['stripe_customer_id']:
                return jsonify({
                    'success': True,
                    'invoices': []
                }), 200
            
            stripe_customer_id = result['stripe_customer_id']
            
            # Fetch invoices from Stripe
            import stripe
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            
            invoices = stripe.Invoice.list(
                customer=stripe_customer_id,
                limit=50
            )
            
            # Format invoice data for frontend
            invoice_list = []
            for invoice in invoices.data:
                invoice_list.append({
                    'id': invoice.id,
                    'number': invoice.number,
                    'amount_due': invoice.amount_due / 100,  # Convert from cents
                    'amount_paid': invoice.amount_paid / 100,
                    'currency': invoice.currency.upper(),
                    'status': invoice.status,
                    'created': invoice.created,
                    'due_date': invoice.due_date,
                    'invoice_pdf': invoice.invoice_pdf,
                    'hosted_invoice_url': invoice.hosted_invoice_url,
                    'description': invoice.lines.data[0].description if invoice.lines.data else 'Subscription'
                })
            
            logger.info(f"Retrieved {len(invoice_list)} invoices for customer {stripe_customer_id}")
            
            return jsonify({
                'success': True,
                'invoices': invoice_list
            }), 200
            
        finally:
            conn.close()
        
    except stripe.StripeError as se:
        logger.error(f"Stripe error fetching invoices: {se}")
        return jsonify({
            'error': 'Unable to fetch invoice history',
            'message': str(se)
        }), 500
    except Exception as e:
        logger.error(f"Get customer invoices error: {e}")
        return jsonify({'error': 'Failed to retrieve invoices'}), 500


@app.route('/api/leads/appsource', methods=['POST'])
def track_appsource_lead():
    """Track lead from Microsoft AppSource (handles both anonymous visits and identified leads)"""
    try:
        data = request.get_json()
        
        # Extract UTM parameters and lead info
        email = sanitize_email(data.get('email', ''))
        source = sanitize_string(data.get('source', 'appsource'), 50)
        campaign = sanitize_string(data.get('campaign', ''), 100)
        medium = sanitize_string(data.get('medium', ''), 50)
        utm_source = sanitize_string(data.get('utm_source', ''), 100)
        utm_campaign = sanitize_string(data.get('utm_campaign', ''), 100)
        utm_medium = sanitize_string(data.get('utm_medium', ''), 100)
        utm_content = sanitize_string(data.get('utm_content', ''), 100)
        utm_term = sanitize_string(data.get('utm_term', ''), 100)
        referrer = sanitize_string(data.get('referrer', ''), 500)
        landing_page = sanitize_string(data.get('page_url', ''), 500)
        
        # Email is optional for anonymous page visit tracking
        
        conn = get_db_connection()
        if not conn:
            # Fallback to logging if DB unavailable
            logger.warning("Database unavailable for lead tracking - logging only")
            logger.info(f"AppSource page visit: utm_source={utm_source}, utm_medium={utm_medium}, utm_campaign={utm_campaign}, email={email or 'anonymous'}")
            return jsonify({'success': True, 'message': 'Visit logged'}), 200
        
        try:
            cursor = conn.cursor()
            
            # Check if user exists (if email provided)
            user_id = None
            if email:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                user_row = cursor.fetchone()
                if user_row:
                    user_id = user_row['id']
            
            # Insert lead record (works for both anonymous and identified visits)
            cursor.execute("""
                INSERT INTO lead_sources (
                    user_id, source, campaign, medium, utm_source, utm_campaign,
                    utm_medium, utm_content, utm_term, referrer, landing_page, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (user_id, source, campaign, medium, utm_source, utm_campaign,
                  utm_medium, utm_content, utm_term, referrer, landing_page))
            
            conn.commit()
            
            logger.info(f"AppSource lead tracked: utm_source={utm_source}, utm_medium={utm_medium}, utm_campaign={utm_campaign}, email={email or 'anonymous'}, user_id={user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Visit tracked successfully'
            }), 200
            
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Track AppSource lead error: {e}")
        return jsonify({'error': 'Failed to track lead'}), 500


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port, debug=True)
