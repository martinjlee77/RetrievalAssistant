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
    
    def upload_and_process(self, label: str = "Upload Contract Document") -> Tuple[Optional[str], Optional[str]]:
        """
        Handle file upload and extract text content.
        
        Args:
            label: Label for the file uploader widget
            
        Returns:
            Tuple of (extracted_text, filename) or (None, None) if no file or error
        """
        uploaded_file = st.file_uploader(
            label,
            type=['pdf', 'docx'],
            help="Upload a PDF or Word document for analysis"
        )
        
        if uploaded_file is None:
            return None, None
            
        try:
            # Extract text using existing extractor (pass the uploaded file directly)
            extraction_result = self.extractor.extract_text(uploaded_file)
            
            # Check for extraction errors
            if extraction_result.get('error'):
                st.error(f"Document extraction failed: {extraction_result['error']}")
                return None, None
            
            # Get the text from the extraction result
            extracted_text = extraction_result.get('text', '')
            
            if not extracted_text or len(extracted_text.strip()) < 100:
                st.error("Document appears to be empty or text extraction failed.")
                return None, None
                
            st.success(f"✅ Successfully processed {uploaded_file.name}")
            logger.info(f"Successfully processed document: {uploaded_file.name}")
            
            return extracted_text, uploaded_file.name
            
        except Exception as e:
            st.error(f"Error processing document: {str(e)}")
            logger.error(f"Document processing error: {str(e)}")
            return None, None
    
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
        with st.expander("📄 Document Information", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Filename:** {filename}")
                st.write(f"**Character Count:** {len(text):,}")
                
            with col2:
                word_count = len(text.split())
                st.write(f"**Word Count:** {word_count:,}")
                
                # Estimate reading time
                reading_time = max(1, word_count // 200)  # 200 WPM average
                st.write(f"**Est. Reading Time:** {reading_time} min")
            
            # Show first few lines as preview
            lines = text.split('\n')[:10]
            preview = '\n'.join(line.strip() for line in lines if line.strip())[:500]
            st.text_area("Document Preview", preview, height=100, disabled=True)