"""
Shared Document Processing Module

This module handles PDF and DOCX parsing for all accounting standards.
Clean, simple interface that any ASC module can use.

Author: Accounting Platform Team
"""

import streamlit as st
import tempfile
import os
from typing import Optional, Tuple
import logging

# Import existing document processing functionality
from utils.document_extractor import DocumentExtractor

logger = logging.getLogger(__name__)

class SharedDocumentProcessor:
    """
    Simple, clean document processor for all accounting standards.
    Handles file upload and text extraction with clear error handling.
    """
    
    def __init__(self):
        self.extractor = DocumentExtractor()
    
    # File upload functionality moved to individual ASC pages
    # Each page now has standard-specific help text and file processing
    
    def validate_document_content(self, text: str, min_length: int = 500) -> bool:
        """
        Basic validation that document contains sufficient content for analysis.
        
        Args:
            text: Extracted document text
            min_length: Minimum character length for valid document
            
        Returns:
            True if document passes validation
        """
        if not text or len(text.strip()) < min_length:
            return False
            
        # Check for common contract indicators
        contract_indicators = [
            'agreement', 'contract', 'party', 'parties', 
            'services', 'payment', 'term', 'consideration'
        ]
        
        text_lower = text.lower()
        found_indicators = sum(1 for indicator in contract_indicators if indicator in text_lower)
        
        return found_indicators >= 3  # At least 3 contract-related terms
    
    def display_document_info(self, text: str, filename: str) -> None:
        """
        Display useful information about the processed document.
        
        Args:
            text: Extracted document text
            filename: Original filename
        """
        # Simplified - removed collapsible section to reduce UI clutter
        # Document info is shown in the file upload area instead
        pass