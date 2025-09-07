"""
Centralized Pricing Configuration for VeritasLogic Analysis Platform
Easy to update pricing without touching code
"""

# Tiered Pricing Structure - Update prices here only
PRICING_TIERS = {
    1: {
        "name": "Simple",
        "price": 3.00,
        "max_words": 2000,
        "description": "Basic contracts and simple agreements"
    },
    2: {
        "name": "Standard", 
        "price": 6.00,
        "max_words": 5000,
        "description": "Standard business contracts"
    },
    3: {
        "name": "Complex",
        "price": 10.00,
        "max_words": 10000,
        "description": "Complex agreements with multiple terms"
    },
    4: {
        "name": "Very Complex",
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
    {"amount": 200, "display": "Add $200 Credits"}
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

# Credit Settings
CREDIT_EXPIRATION_MONTHS = 12
FREE_ANALYSES_PER_USER = 3

def get_price_tier(word_count):
    """
    Determine pricing tier based on document word count
    
    Args:
        word_count (int): Number of words in document
        
    Returns:
        dict: Tier information with tier number, name, price, description
    """
    for tier_num, tier_info in PRICING_TIERS.items():
        if word_count <= tier_info['max_words']:
            return {
                'tier': tier_num,
                'name': tier_info['name'],
                'price': tier_info['price'],
                'description': tier_info['description'],
                'word_count': word_count
            }
    
    # Fallback to highest tier
    return {
        'tier': 5,
        'name': PRICING_TIERS[5]['name'],
        'price': PRICING_TIERS[5]['price'],
        'description': PRICING_TIERS[5]['description'],
        'word_count': word_count
    }

def is_business_email(email):
    """
    Determine if email is from a business domain
    
    Args:
        email (str): Email address to check
        
    Returns:
        bool: True if business email, False if personal
    """
    if not email or '@' not in email:
        return False
        
    domain = email.split('@')[1].lower()
    
    # Check against known personal providers
    if domain in PERSONAL_EMAIL_PROVIDERS:
        return False
    
    # Auto-approve government and education domains
    if domain.endswith(('.gov', '.edu', '.mil')):
        return True
    
    # Most other domains are likely business domains
    return True

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