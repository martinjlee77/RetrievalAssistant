"""
Centralized Pricing Configuration for VeritasLogic Analysis Platform
Easy to update pricing without touching code
"""

# Tiered Pricing Structure - Update prices here only
PRICING_TIERS = {
    1: {
        "name": "3K (≤10 pages)",
        "price": 129.00,
        "max_words": 3000,
        "description": "Same features in every tier. For very short packages.",
        "docs_per_run": 10,
        "reruns_included": 1,
        "rerun_window_days": 14
    },
    2: {
        "name": "9K (≤30 pages)",
        "price": 195.00,
        "max_words": 9000,
        "description": "Same features in every tier. For short packages.",
        "docs_per_run": 10,
        "reruns_included": 1,
        "rerun_window_days": 14
    },
    3: {
        "name": "15K (≤50 pages)",
        "price": 325.00,
        "max_words": 15000,
        "description": "Same features in every tier. For shorter packages.",
        "docs_per_run": 10,
        "reruns_included": 1,
        "rerun_window_days": 14
    },
    4: {
        "name": "30K (≤100 pages)",
        "price": 525.00,
        "max_words": 30000,
        "description": "Same features in every tier. For standard-length packages.",
        "docs_per_run": 10,
        "reruns_included": 1,
        "rerun_window_days": 14
    },
    5: {
        "name": "60K (≤200 pages)",
        "price": 850.00,
        "max_words": 60000,
        "description": "Same features in every tier. For long or complex packages.",
        "docs_per_run": 10,
        "reruns_included": 1,
        "rerun_window_days": 14
    }
}

# Credit Purchase Options
CREDIT_PACKAGES = [
    {"amount": 1000, "display": "Add $1,000 Credits"},
    {"amount": 2000, "display": "Add $2,000 Credits"}, 
    {"amount": 3000, "display": "Add $3,000 Credits"}
]

# Business Email Configuration
PERSONAL_EMAIL_PROVIDERS = [
    'gmail.com',
    'outlook.com', 
    'hotmail.com',
    'yahoo.com',
    'aol.com',
    'icloud.com',
    'protonmail.com',
    'mail.com'
]

# Pre-approved business domains (bypass MX validation)
APPROVED_BUSINESS_DOMAINS = [
    'veritaslogic.ai'
]

# Credit Settings
CREDIT_EXPIRATION_MONTHS = 12
NEW_USER_WELCOME_CREDITS = 200  # $200 First Memo Credit

def get_price_tier(word_count):
    """
    Determine pricing tier based on document word count
    
    Args:
        word_count (int): Number of words in document
        
    Returns:
        dict: Tier information with tier number, name, price, description, per_1k_rate
    """
    for tier_num, tier_info in PRICING_TIERS.items():
        if word_count <= tier_info['max_words']:
            return {
                'tier': tier_num,
                'name': tier_info['name'],
                'price': tier_info['price'],
                'description': tier_info['description'],
                'max_words': tier_info['max_words'],
                'docs_per_run': tier_info['docs_per_run'],
                'reruns_included': tier_info['reruns_included'],
                'rerun_window_days': tier_info['rerun_window_days'],
                'word_count': word_count
            }
    
    # Document exceeds maximum tier - contact support required
    return {
        'tier': None,
        'name': 'Contact Support Required',
        'price': None,
        'description': f'Document exceeds 60,000 words ({word_count:,} words). Please contact support for custom pricing.',
        'max_words': None,
        'docs_per_run': None,
        'reruns_included': None,
        'rerun_window_days': None,
        'contact_support': True,
        'word_count': word_count
    }

def is_business_email(email):
    """
    Determine if email is from a business domain with MX record validation
    
    Args:
        email (str): Email address to check
        
    Returns:
        bool: True if business email, False if personal
    """
    import socket
    import logging
    
    logger = logging.getLogger(__name__)
    
    if not email or '@' not in email:
        return False
        
    domain = email.split('@')[1].lower()
    
    # Reject known personal providers immediately
    if domain in PERSONAL_EMAIL_PROVIDERS:
        logger.info(f"Email {email} rejected: personal email provider {domain}")
        return False
    
    # Auto-approve government and education domains
    if domain.endswith(('.gov', '.edu', '.mil')):
        logger.info(f"Email {email} approved: government/education domain {domain}")
        return True
    
    # Auto-approve pre-approved business domains
    if domain in APPROVED_BUSINESS_DOMAINS:
        logger.info(f"Email {email} approved: pre-approved business domain {domain}")
        return True
    
    # Enhanced validation: Check for suspicious patterns
    if len(domain) < 4 or domain.count('.') == 0:
        logger.info(f"Email {email} rejected: suspicious domain pattern {domain}")
        return False
    
    # MX record validation
    try:
        mx_records = socket.getaddrinfo(domain, None)
        if mx_records:
            logger.info(f"Email {email} approved: valid business domain {domain} with MX records")
            return True
        else:
            logger.info(f"Email {email} rejected: no MX records found for {domain}")
            return False
    except (socket.gaierror, socket.error) as e:
        logger.warning(f"Email {email} rejected: MX lookup failed for {domain}: {e}")
        return False

def format_tier_display(tier_info):
    """
    Format tier information for display
    
    Args:
        tier_info (dict): Tier information from get_price_tier()
        
    Returns:
        str: Formatted display string
    """
    return f"Tier {tier_info['tier']}: {tier_info['name']} - ${tier_info['price']:.2f}"

def get_credit_packages():
    """
    Get available credit purchase packages
    
    Returns:
        list: Credit package options
    """
    return CREDIT_PACKAGES.copy()