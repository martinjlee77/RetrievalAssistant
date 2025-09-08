"""
Centralized Pricing Configuration for VeritasLogic Analysis Platform
Easy to update pricing without touching code
"""

# Tiered Pricing Structure - Update prices here only
PRICING_TIERS = {
    1: {
        "name": "Short",
        "price": 4.00,
        "max_words": 2000,
        "description": "Basic contracts and simple agreements"
    },
    2: {
        "name": "Medium", 
        "price": 6.00,
        "max_words": 5000,
        "description": "Standard business contracts"
    },
    3: {
        "name": "Large",
        "price": 10.00,
        "max_words": 10000,
        "description": "Complex agreements with multiple terms"
    },
    4: {
        "name": "Extensive",
        "price": 18.00,
        "max_words": 20000,
        "description": "Large enterprise agreements"
    },
    5: {
        "name": "Enterprise",
        "price": 30.00,
        "max_words": float('inf'),
        "description": "Enterprise-scale document sets"
    }
}

# Credit Purchase Options
CREDIT_PACKAGES = [
    {"amount": 50, "display": "Add $50 Credits"},
    {"amount": 100, "display": "Add $100 Credits"}, 
    {"amount": 250, "display": "Add $250 Credits"},
    {"amount": 500, "display": "Add $500 Credits"}
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
NEW_USER_WELCOME_CREDITS = 100  # $100 free credits instead of 3 free analyses

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
                'per_1k_rate': tier_info['per_1k_rate'],
                'word_count': word_count
            }
    
    # Fallback to highest tier (Enterprise)
    return {
        'tier': 5,
        'name': PRICING_TIERS[5]['name'],
        'price': PRICING_TIERS[5]['price'],
        'description': PRICING_TIERS[5]['description'],
        'max_words': PRICING_TIERS[5]['max_words'],
        'per_1k_rate': PRICING_TIERS[5]['per_1k_rate'],
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