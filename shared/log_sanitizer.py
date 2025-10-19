"""
Log sanitization utility for removing PII and sensitive data from error messages.

This module provides utilities to sanitize log messages by removing or masking
personally identifiable information (PII) and sensitive customer data before logging.
"""

import re
from typing import Any


def sanitize_for_log(message: Any, max_length: int = 200) -> str:
    """
    Sanitize a message for safe logging by removing PII and sensitive data.
    
    This function:
    - Converts the message to string
    - Truncates very long messages (likely contract text)
    - Masks sensitive patterns (SSN, EIN, bank accounts, credit cards, emails, phones)
    - Preserves error type and short context for debugging
    
    Args:
        message: The message to sanitize (can be string, Exception, or any object)
        max_length: Maximum length of sanitized message (default: 200 chars)
    
    Returns:
        Sanitized string safe for logging
        
    Examples:
        >>> sanitize_for_log("Error processing SSN: 123-45-6789")
        'Error processing SSN: XXX-XX-XXXX'
        
        >>> sanitize_for_log("Failed for user@example.com")
        'Failed for [EMAIL]'
    """
    # Convert to string
    if isinstance(message, Exception):
        text = str(message)
    else:
        text = str(message)
    
    # Truncate very long messages (likely contains contract text)
    if len(text) > max_length:
        text = text[:max_length] + "... [truncated]"
    
    # Pattern matching and replacement for common PII
    sanitized = text
    
    # SSN patterns (XXX-XX-XXXX or XXXXXXXXX)
    sanitized = re.sub(
        r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        'XXX-XX-XXXX',
        sanitized
    )
    
    # EIN patterns (XX-XXXXXXX)
    sanitized = re.sub(
        r'\b\d{2}[-\s]?\d{7}\b',
        'XX-XXXXXXX',
        sanitized
    )
    
    # Credit card numbers (13-19 digits, possibly with spaces/dashes)
    sanitized = re.sub(
        r'\b(?:\d[ -]*?){13,19}\b',
        '[CARD]',
        sanitized
    )
    
    # Bank account numbers (6-17 digits)
    sanitized = re.sub(
        r'\b\d{6,17}\b',
        '[ACCOUNT]',
        sanitized
    )
    
    # Email addresses
    sanitized = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]',
        sanitized
    )
    
    # Phone numbers (various formats)
    sanitized = re.sub(
        r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        '[PHONE]',
        sanitized
    )
    
    # IBAN patterns (basic - starts with 2 letters, then numbers)
    sanitized = re.sub(
        r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b',
        '[IBAN]',
        sanitized
    )
    
    return sanitized


def sanitize_exception_for_db(exception: Exception, max_length: int = 500) -> str:
    """
    Sanitize an exception message for safe storage in database error_message column.
    
    Similar to sanitize_for_log() but optimized for database storage.
    Returns error type + sanitized message suitable for support/debugging.
    
    Args:
        exception: The exception to sanitize
        max_length: Maximum length for database storage (default: 500)
    
    Returns:
        Sanitized error message string
        
    Example:
        >>> try:
        ...     raise ValueError("Invalid SSN: 123-45-6789")
        ... except Exception as e:
        ...     sanitize_exception_for_db(e)
        'ValueError: Invalid SSN: XXX-XX-XXXX'
    """
    error_type = type(exception).__name__
    error_message = sanitize_for_log(str(exception), max_length=max_length)
    
    return f"{error_type}: {error_message}"
