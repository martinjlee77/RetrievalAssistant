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
        Handle multiple file upload and extract combined text content.
        
        Args:
            label: Label for the file uploader widget
            
        Returns:
            Tuple of (combined_extracted_text, comma_separated_filenames) or (None, None) if no files or error
        """
        uploaded_files = st.file_uploader(
            label,
            type=['pdf', 'docx'],
            help="Upload up to 5 contract documents (PDF or Word). All documents will be combined for analysis.",
            accept_multiple_files=True
        )
        
        if not uploaded_files:
            return None, None
            
        # Limit to 5 files for practical processing
        if len(uploaded_files) > 5:
            st.warning("⚠️ Maximum 5 files allowed. Using first 5 files only.")
            uploaded_files = uploaded_files[:5]
            
        try:
            combined_text = ""
            processed_filenames = []
            
            for uploaded_file in uploaded_files:
                # Extract text using existing extractor
                extraction_result = self.extractor.extract_text(uploaded_file)
                
                # Check for extraction errors
                if extraction_result.get('error'):
                    st.error(f"❌ Document extraction failed for {uploaded_file.name}: {extraction_result['error']}")
                    continue
                
                # Get the text from the extraction result
                extracted_text = extraction_result.get('text', '')
                
                if not extracted_text or len(extracted_text.strip()) < 50:
                    st.warning(f"⚠️ {uploaded_file.name} appears to be empty or extraction failed - skipping")
                    continue
                
                # Add document separator and content
                if combined_text:
                    combined_text += "\n\n" + "="*80 + "\n"
                    combined_text += f"DOCUMENT: {uploaded_file.name}\n"
                    combined_text += "="*80 + "\n\n"
                else:
                    combined_text += f"DOCUMENT: {uploaded_file.name}\n"
                    combined_text += "="*80 + "\n\n"
                
                combined_text += extracted_text
                processed_filenames.append(uploaded_file.name)
                
                # Keep logging but remove UI clutter
                logger.info(f"Successfully processed document: {uploaded_file.name}")
            
            if not combined_text:
                st.error("❌ No documents could be processed successfully")
                return None, None
                
            filenames_str = ", ".join(processed_filenames)
            # Removed "Combined X documents" message to reduce UI clutter
            
            return combined_text, filenames_str
            
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
        # Simplified - removed collapsible section to reduce UI clutter
        # Document info is shown in the file upload area instead
        pass