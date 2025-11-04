"""
Centralized Pricing Configuration for VeritasLogic Analysis Platform
Easy to update pricing without touching code
"""

# ==========================================
# SUBSCRIPTION PLANS
# ==========================================
SUBSCRIPTION_PLANS = {
    'professional': {
        'plan_key': 'professional',
        'name': 'Professional',
        'description': 'For individual controllers and technical accounting professionals',
        'price_monthly': 295.00,
        'word_allowance': 30000,
        'seats': 1,
        'features': [
            'All ASC standards (606, 842, 718, 805, 340-40)',
            'Research Assistant with RAG-powered citations',
            'DOCX and PDF memo export',
            'Priority email support',
            'Professional-grade analysis quality'
        ],
        'ideal_for': 'Individual controllers and technical accounting professionals',
        'stripe_product_id': 'prod_TMZYA0436dZmL1',
        'stripe_price_id': 'price_1SPqP82M206TZw8PqqOL6uAu',
    },
    'team': {
        'plan_key': 'team',
        'name': 'Team',
        'description': 'For accounting teams and small firms with shared usage',
        'price_monthly': 595.00,
        'word_allowance': 75000,
        'seats': 3,
        'features': [
            'All ASC standards (606, 842, 718, 805, 340-40)',
            'Research Assistant with RAG-powered citations',
            'DOCX and PDF memo export',
            'Priority email support',
            'Multi-user organization with pooled usage',
            'Audit logs and user management',
            'Shared analysis history across team'
        ],
        'ideal_for': 'Accounting teams and small firms',
        'stripe_product_id': 'prod_TMZYrJj8yswA2r',
        'stripe_price_id': 'price_1SPqP82M206TZw8PDTLc5DTU',
    },
    'enterprise': {
        'plan_key': 'enterprise',
        'name': 'Enterprise',
        'description': 'For large enterprises and Big 4 firms with custom SLA and dedicated support',
        'price_monthly': 1195.00,
        'word_allowance': 180000,
        'seats': 999,  # Effectively unlimited
        'features': [
            'All ASC standards (606, 842, 718, 805, 340-40)',
            'Research Assistant with RAG-powered citations',
            'DOCX and PDF memo export',
            'Dedicated customer success manager',
            'Custom SLA with guaranteed response times',
            'Azure OpenAI deployment option (data residency)',
            'Unlimited internal viewers',
            'Advanced security and compliance features',
            'SSO integration (coming soon)'
        ],
        'ideal_for': 'Large enterprises and Big 4 accounting firms',
        'stripe_product_id': 'prod_TMZY36SH65ts7H',
        'stripe_price_id': 'price_1SPqP92M206TZw8P1uY9VdzR',
    }
}

# Trial Configuration
TRIAL_CONFIG = {
    'duration_days': 14,
    'word_allowance': 9000,  # Enough for 1-2 typical analyses
    'requires_payment_method': True,
    'cancellation_policy': 'Cancel anytime during trial - no charge if canceled before trial ends'
}

# Rollover Policy
ROLLOVER_CONFIG = {
    'enabled': True,
    'expiration_months': 12,  # Unused words expire after 12 months
    'description': 'Unused monthly word allowance carries forward for 12 months'
}

# ==========================================
# LEGACY COMPATIBILITY (DEPRECATED)
# ==========================================
# Keep these exports for backward compatibility during migration
# TODO: Remove after backend_api.py migrated to subscription model

PRICING_TIERS = {
    # Deprecated: Kept for backward compatibility only
    # New code should use SUBSCRIPTION_PLANS instead
}

CREDIT_PACKAGES = [
    # Deprecated: Kept for backward compatibility only
    # Subscriptions don't use credit packages
]

CREDIT_EXPIRATION_MONTHS = 12  # Still used for rollover
NEW_USER_WELCOME_CREDITS = 0  # Deprecated: Trial uses word allowance instead

def get_price_tier(word_count):
    """
    DEPRECATED: Use subscription model instead
    This function is kept for backward compatibility only
    """
    raise NotImplementedError(
        "get_price_tier() is deprecated. "
        "Platform now uses subscription-based pricing. "
        "Use subscription_manager.check_word_allowance() instead."
    )

def get_credit_packages():
    """
    DEPRECATED: Use subscription plans instead
    """
    return []  # Return empty list for now

# ==========================================
# HELPER FUNCTIONS - SUBSCRIPTION PLANS
# ==========================================

def get_all_plans():
    """
    Get all subscription plans
    
    Returns:
        dict: All subscription plans keyed by plan_key
    """
    return SUBSCRIPTION_PLANS.copy()

def get_plan_by_key(plan_key):
    """
    Get subscription plan details by plan_key
    
    Args:
        plan_key (str): Plan key (professional, team, enterprise)
        
    Returns:
        dict: Plan details or None if not found
    """
    return SUBSCRIPTION_PLANS.get(plan_key)

def get_plan_comparison():
    """
    Get plans formatted for comparison table
    
    Returns:
        list: Plans sorted by price with formatted comparison data
    """
    plans = []
    for key in ['professional', 'team', 'enterprise']:
        plan = SUBSCRIPTION_PLANS[key].copy()
        plan['price_display'] = f"${plan['price_monthly']:.0f}/mo"
        plan['word_allowance_display'] = f"{plan['word_allowance']:,} words/mo"
        plan['seats_display'] = f"{plan['seats']} user{'s' if plan['seats'] > 1 else ''}"
        plans.append(plan)
    return plans

# ==========================================
# BUSINESS EMAIL VALIDATION
# ==========================================

# Personal email providers to reject for trial signup
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

