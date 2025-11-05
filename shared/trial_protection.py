"""
Trial Abuse Prevention System
Protects against trial abuse through reCAPTCHA, rate limiting, and domain checks
"""

import os
import time
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# reCAPTCHA Enterprise Configuration
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY')
RECAPTCHA_SITE_KEY = os.getenv('RECAPTCHA_SITE_KEY')
GOOGLE_CLOUD_API_KEY = os.getenv('GOOGLE_CLOUD_API_KEY')
GOOGLE_CLOUD_PROJECT_ID = 'gen-lang-client-0926483167'
RECAPTCHA_ENTERPRISE_API_URL = f'https://recaptchaenterprise.googleapis.com/v1/projects/{GOOGLE_CLOUD_PROJECT_ID}/assessments'

# Rate Limiting Configuration
RATE_LIMIT_WINDOW_MINUTES = 60
MAX_SIGNUP_ATTEMPTS_PER_IP = 3
MAX_SIGNUP_ATTEMPTS_PER_DOMAIN = 2

def verify_recaptcha(token, remote_ip=None):
    """
    Verify reCAPTCHA Enterprise token with Google Cloud API
    
    Args:
        token (str): reCAPTCHA Enterprise token from frontend
        remote_ip (str, optional): User's IP address
        
    Returns:
        tuple: (success: bool, score: float, error_message: str)
    """
    if not GOOGLE_CLOUD_API_KEY:
        logger.warning("GOOGLE_CLOUD_API_KEY not configured - skipping verification")
        return True, 1.0, None  # Allow in development
    
    if not token:
        return False, 0.0, "reCAPTCHA token missing"
    
    try:
        # Build Enterprise API request
        payload = {
            'event': {
                'token': token,
                'siteKey': RECAPTCHA_SITE_KEY,
                'expectedAction': 'signup'
            }
        }
        
        if remote_ip:
            payload['event']['userIpAddress'] = remote_ip
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Call Enterprise API with API key
        url = f'{RECAPTCHA_ENTERPRISE_API_URL}?key={GOOGLE_CLOUD_API_KEY}'
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        result = response.json()
        
        # DEBUG: Log full Google response
        logger.info(f"reCAPTCHA Enterprise API Response: {result}")
        
        # Parse Enterprise API response
        token_properties = result.get('tokenProperties', {})
        risk_analysis = result.get('riskAnalysis', {})
        
        valid = token_properties.get('valid', False)
        action = token_properties.get('action', 'N/A')
        hostname = token_properties.get('hostname', 'N/A')
        create_time = token_properties.get('createTime', 'N/A')
        invalid_reason = token_properties.get('invalidReason', None)
        
        score = risk_analysis.get('score', 0.0)
        reasons = risk_analysis.get('reasons', [])
        
        logger.info(f"reCAPTCHA Enterprise Details - valid={valid}, score={score}, hostname={hostname}, action={action}, create_time={create_time}, reasons={reasons}")
        
        if not valid:
            error_msg = f"reCAPTCHA token invalid: {invalid_reason or 'unknown reason'}"
            logger.warning(f"reCAPTCHA failed for IP {remote_ip}: {error_msg}")
            return False, score, error_msg
        
        # Check action matches
        if action != 'signup':
            logger.warning(f"reCAPTCHA action mismatch: expected 'signup', got '{action}'")
            return False, score, "Invalid reCAPTCHA action"
        
        # Enterprise scores range from 0.0 (bot) to 1.0 (human)
        # We require a minimum score of 0.5 for signup
        if score < 0.5:
            logger.warning(f"Low reCAPTCHA score {score} for IP {remote_ip}")
            return False, score, f"Suspicious activity detected (score: {score:.2f})"
        
        logger.info(f"reCAPTCHA Enterprise verified successfully: score={score:.2f}, IP={remote_ip}")
        return True, score, None
        
    except requests.Timeout:
        logger.error("reCAPTCHA Enterprise verification timeout")
        # Allow signup on timeout to avoid blocking legitimate users
        return True, 1.0, None
    except Exception as e:
        logger.error(f"reCAPTCHA Enterprise verification error: {e}")
        # Allow signup on error to avoid blocking legitimate users
        return True, 1.0, None


def check_rate_limit(conn, ip_address, email_domain):
    """
    Check if IP or domain has exceeded signup rate limits
    
    Args:
        conn: Database connection
        ip_address (str): User's IP address
        email_domain (str): Email domain from signup
        
    Returns:
        tuple: (allowed: bool, error_message: str, wait_minutes: int)
    """
    cursor = conn.cursor()
    cutoff_time = datetime.utcnow() - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
    
    # Check IP-based rate limit
    cursor.execute("""
        SELECT COUNT(*) FROM signup_attempts
        WHERE ip_address = %s AND attempted_at > %s
    """, (ip_address, cutoff_time))
    
    ip_attempts = cursor.fetchone()[0]
    
    if ip_attempts >= MAX_SIGNUP_ATTEMPTS_PER_IP:
        logger.warning(f"Rate limit exceeded for IP {ip_address}: {ip_attempts} attempts")
        return False, f"Too many signup attempts from your location. Please try again in {RATE_LIMIT_WINDOW_MINUTES} minutes.", RATE_LIMIT_WINDOW_MINUTES
    
    # Check domain-based rate limit
    cursor.execute("""
        SELECT COUNT(*) FROM signup_attempts
        WHERE email_domain = %s AND attempted_at > %s
    """, (email_domain, cutoff_time))
    
    domain_attempts = cursor.fetchone()[0]
    
    if domain_attempts >= MAX_SIGNUP_ATTEMPTS_PER_DOMAIN:
        logger.warning(f"Rate limit exceeded for domain {email_domain}: {domain_attempts} attempts")
        return False, f"Multiple signup attempts detected from your organization. Please contact support if you need assistance.", RATE_LIMIT_WINDOW_MINUTES
    
    return True, None, 0


def record_signup_attempt(conn, ip_address, email, email_domain, success, failure_reason=None):
    """
    Record a signup attempt for rate limiting and abuse tracking
    
    Args:
        conn: Database connection
        ip_address (str): User's IP address
        email (str): Email address used for signup
        email_domain (str): Domain from email
        success (bool): Whether signup succeeded
        failure_reason (str, optional): Reason for failure
    """
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO signup_attempts (
                ip_address, email, email_domain, success, failure_reason, attempted_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (ip_address, email, email_domain, success, failure_reason, datetime.utcnow()))
        
        conn.commit()
        logger.info(f"Recorded signup attempt: IP={ip_address}, domain={email_domain}, success={success}")
    except Exception as e:
        logger.error(f"Failed to record signup attempt: {e}")
        conn.rollback()


def check_domain_trial_eligibility(conn, email_domain):
    """
    Check if domain is eligible for a trial (one trial per domain)
    
    Args:
        conn: Database connection
        email_domain (str): Email domain to check
        
    Returns:
        tuple: (eligible: bool, error_message: str)
    """
    cursor = conn.cursor()
    
    # Check if domain already has an organization with a trial or paid subscription
    cursor.execute("""
        SELECT o.id, o.company_name, si.status, si.plan_key, si.trial
        FROM organizations o
        LEFT JOIN subscription_instances si ON o.id = si.org_id
        WHERE o.domain = %s
        ORDER BY si.created_at DESC
        LIMIT 1
    """, (email_domain,))
    
    result = cursor.fetchone()
    
    if not result:
        # No organization exists for this domain - eligible
        return True, None
    
    org_id, company_name, sub_status, plan_key, is_trial = result
    
    if sub_status and is_trial:
        # Domain already has an active trial
        logger.warning(f"Domain {email_domain} already has trial subscription")
        return False, f"Your organization ({company_name}) already has an active trial. Please contact your account administrator to add you as a user."
    
    if sub_status in ('active', 'past_due'):
        # Domain has paid subscription - existing users should join
        logger.info(f"Domain {email_domain} has existing paid subscription")
        return False, f"Your organization ({company_name}) already has an active subscription. Please contact your account administrator to add you as a user."
    
    # Domain exists but no active subscription - could be expired trial
    # Allow new trial if previous trial has ended
    cursor.execute("""
        SELECT trial, status, trial_ends_at
        FROM subscription_instances
        WHERE org_id = %s AND trial = true
        ORDER BY created_at DESC
        LIMIT 1
    """, (org_id,))
    
    past_trial = cursor.fetchone()
    
    if past_trial and past_trial[1] in ('active', 'trial'):
        # Active trial exists
        return False, f"Your organization already has an active trial. Please contact support if you need assistance."
    
    if past_trial and past_trial[2]:
        trial_end = past_trial[2]
        days_since_trial = (datetime.utcnow() - trial_end).days
        
        if days_since_trial < 90:
            # Trial ended less than 90 days ago - not eligible for new trial
            logger.warning(f"Domain {email_domain} trial ended {days_since_trial} days ago")
            return False, f"Your organization's trial ended recently. Please contact sales@veritaslogic.ai to discuss subscription options."
    
    # Domain exists but trial ended 90+ days ago - allow new trial
    return True, None


def cleanup_old_signup_attempts(conn):
    """
    Clean up signup attempts older than 7 days (housekeeping)
    
    Args:
        conn: Database connection
    """
    cursor = conn.cursor()
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    
    try:
        cursor.execute("""
            DELETE FROM signup_attempts WHERE attempted_at < %s
        """, (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old signup attempts")
    except Exception as e:
        logger.error(f"Failed to cleanup signup attempts: {e}")
        conn.rollback()
