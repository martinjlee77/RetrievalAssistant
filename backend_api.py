"""
VeritasLogic Backend API
Handles user registration, authentication, and billing
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import jwt
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from postmarker.core import PostmarkClient
from shared.pricing_config import is_business_email

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'veritaslogic-secret-key-change-in-production')

# Postmark Configuration
POSTMARK_API_KEY = os.environ.get('POSTMARK_API_KEY', 'e073a56a-79c1-4045-9dd1-c8d82f40ba24')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@veritaslogic.ai')

# Initialize Postmark client
try:
    postmark_client = PostmarkClient(server_token=POSTMARK_API_KEY)
except Exception as e:
    logger.warning(f"Postmark client initialization failed: {e}")
    postmark_client = None

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
def generate_verification_token(user_id, email):
    """Generate JWT token for email verification"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=24),  # 24-hour expiry
        'iat': datetime.utcnow(),
        'purpose': 'email_verification'
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token'}

def send_verification_email(email, first_name, verification_token):
    """Send email verification using Postmark"""
    if not postmark_client:
        logger.error("Postmark client not initialized")
        return False
        
    try:
        verification_url = f"https://a45dfa8e-cff4-4d5e-842f-dc8d14b3b2d2-00-3khkzanf4tnm3.picard.replit.dev:8000/verify.html?token={verification_token}"
        
        html_body = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #f8f9fa; padding: 20px; text-align: center;">
                <h1 style="color: #2c3e50;">Welcome to VeritasLogic.ai</h1>
            </div>
            <div style="padding: 30px;">
                <h2>Hi {first_name},</h2>
                <p>Thank you for signing up for VeritasLogic! Click the button below to verify your email address and get started with your 3 free analyses.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background: #007bff; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;
                              font-weight: bold;">
                        Verify My Email
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    This link expires in 24 hours. If you didn't create this account, you can safely ignore this email.
                </p>
                
                <p style="color: #666; font-size: 14px;">
                    If the button doesn't work, copy and paste this link: {verification_url}
                </p>
            </div>
            <div style="background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px;">
                © 2025 VeritasLogic.ai - Professional Accounting Analysis Platform
            </div>
        </div>
        '''
        
        text_body = f'''
        Welcome to VeritasLogic.ai!
        
        Hi {first_name},
        
        Thank you for signing up for VeritasLogic! Please verify your email address by clicking the link below:
        
        {verification_url}
        
        This link expires in 24 hours. If you didn't create this account, you can safely ignore this email.
        
        © 2025 VeritasLogic.ai - Professional Accounting Analysis Platform
        '''
        
        response = postmark_client.emails.send(
            From=FROM_EMAIL,
            To=email,
            Subject='Verify Your VeritasLogic Account',
            HtmlBody=html_body,
            TextBody=text_body
        )
        
        logger.info(f"Verification email sent to {email} via Postmark. MessageID: {response['MessageID']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email via Postmark: {e}")
        return False

# API Routes
@app.route('/api/signup', methods=['POST'])
def signup():
    """Handle user registration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'first_name', 'last_name', 'company_name', 'job_title', 'terms_accepted']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        if not data.get('terms_accepted'):
            return jsonify({'error': 'Terms and conditions must be accepted'}), 400
        
        email = data['email'].lower().strip()
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        company_name = data['company_name'].strip()
        job_title = data['job_title'].strip()
        
        # Check if user already exists
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Email already registered'}), 409
        
        # Check if business email for auto-approval
        is_business = is_business_email(email)
        
        if is_business:
            # Business email - auto-approve without verification
            cursor.execute("""
                INSERT INTO users (email, first_name, last_name, company_name, job_title, 
                                 status, verified_at, free_analyses_remaining)
                VALUES (%s, %s, %s, %s, %s, 'verified', NOW(), 3)
                RETURNING id
            """, (email, first_name, last_name, company_name, job_title))
            
            user_id = cursor.fetchone()['id']
            
            # Add trial credits transaction
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, reason)
                VALUES (%s, 3, 'trial_grant')
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Business email {email} auto-approved during signup")
            
            return jsonify({
                'message': 'Registration successful! Your business email has been automatically verified. You can now log in.',
                'user_id': user_id,
                'auto_verified': True
            }), 201
            
        else:
            # Personal email - require verification
            verification_token = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO users (email, first_name, last_name, company_name, job_title, 
                                 status, verification_token, free_analyses_remaining)
                VALUES (%s, %s, %s, %s, %s, 'pending', %s, 3)
                RETURNING id
            """, (email, first_name, last_name, company_name, job_title, verification_token))
            
            user_id = cursor.fetchone()['id']
            
            # Add trial credits transaction
            cursor.execute("""
                INSERT INTO credit_transactions (user_id, amount, reason)
                VALUES (%s, 3, 'trial_grant')
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            # Send verification email
            email_sent = send_verification_email(email, first_name, verification_token)
            
            if email_sent:
                return jsonify({
                    'message': 'Registration successful! Please check your email to verify your account.',
                    'user_id': user_id,
                    'verification_required': True
                }), 201
            else:
                return jsonify({
                    'message': 'Registration successful, but failed to send verification email. Please contact support.',
                    'user_id': user_id,
                    'verification_required': True
                }), 201
            
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/verify/<token>')
def verify_email(token):
    """Handle email verification"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Find user by verification token
        cursor.execute("""
            SELECT id, email, first_name, status 
            FROM users 
            WHERE verification_token = %s AND status = 'pending'
        """, (token,))
        
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'Invalid or expired verification token'}), 400
        
        # Mark user as verified
        cursor.execute("""
            UPDATE users 
            SET status = 'verified', verified_at = NOW(), verification_token = NULL
            WHERE id = %s
        """, (user['id'],))
        
        conn.commit()
        conn.close()
        
        logger.info(f"User {user['email']} verified successfully")
        
        return jsonify({
            'message': 'Email verified successfully! You can now log in.',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, first_name, last_name, company_name, job_title, 
                   status, credits_balance, free_analyses_remaining
            FROM users 
            WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user['status'] != 'verified':
            return jsonify({'error': 'Please verify your email first'}), 403
        
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
    app.run(host='0.0.0.0', port=3000, debug=True)