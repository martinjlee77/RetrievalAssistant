"""
Document Text Extraction Utility
Handles PDF and Word document text extraction for contract analysis
"""

import io
import logging
import re
from typing import Optional, Dict, Any, List
import PyPDF2
import pdfplumber
import docx
from docx import Document
try:
    import fitz  # PyMuPDF - preferred for text extraction
except ImportError:
    fitz = None

class DocumentExtractor:
    """Extract text from various document formats"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_text(self, uploaded_file) -> Dict[str, Any]:
        """
        Extract text from uploaded file
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            Dict containing extracted text and metadata
        """
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        try:
            # Check file size first - enforce 50MB limit
            uploaded_file.seek(0)  # Reset file pointer
            file_content = uploaded_file.read()
            file_size_mb = len(file_content) / (1024 * 1024)  # Convert to MB
            
            if len(file_content) < 100:  # Less than 100 bytes is likely empty/corrupted
                raise ValueError(f"File appears to be empty or corrupted (size: {len(file_content)} bytes)")
            
            if file_size_mb > 50:  # 50MB limit
                raise ValueError(f"File size ({file_size_mb:.1f}MB) exceeds 50MB limit. Please upload a smaller file.")
            
            # Reset file pointer for actual extraction
            uploaded_file.seek(0)
            
            if file_extension == 'pdf':
                extraction_result = self._extract_pdf_text(uploaded_file)
            elif file_extension in ['docx']:
                extraction_result = self._extract_word_text(uploaded_file)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")

            # Check if extraction yielded meaningful text
            extracted_text = extraction_result.get('text', '').strip()
            if len(extracted_text) < 50:  # Less than 50 characters is likely failed extraction
                raise ValueError("File processed but no meaningful text extracted (may be image-only PDF or corrupted)")

            # Enhanced word counting with proper tokenization
            word_count = self._count_words(extracted_text)
            extraction_result['word_count'] = word_count
            extraction_result['file_size_mb'] = round(file_size_mb, 2)
            
            # Add page estimate for user context (≈300 words/page)
            extraction_result['estimated_pages'] = max(1, round(word_count / 300))

            return extraction_result
                
        except Exception as e:
            self.logger.error(f"Error extracting text from {uploaded_file.name}: {str(e)}")
            return {
                'text': '',
                'error': str(e),
                'pages': 0,
                'word_count': 0,
                'extraction_method': 'error',
                'file_size_mb': 0,
                'estimated_pages': 0
            }
    
    def _count_words(self, text: str) -> int:
        """
        Enhanced word counting with proper tokenization
        Numbers count as words, whitespace/punctuation split
        """
        if not text or not text.strip():
            return 0
        
        # Split by whitespace and punctuation, filter empty strings
        words = re.findall(r'\b\w+\b', text)
        return len(words)
    
    def _extract_pdf_text(self, uploaded_file) -> Dict[str, Any]:
        """Extract text from PDF file using multiple methods"""
        text = ""
        pages = 0
        extraction_method = "none"
        
        try:
            # Method 1: Try pdfplumber first (better for complex layouts)
            pdf_bytes = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages = len(pdf.pages)
                text_parts = []
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                if text_parts:
                    text = "\n\n".join(text_parts)
                    extraction_method = "pdfplumber"
                    
        except Exception as e:
            self.logger.warning(f"pdfplumber failed: {str(e)}, trying PyPDF2")
            
        # Method 2: Fallback to PyPDF2 if pdfplumber fails
        if not text.strip():
            try:
                uploaded_file.seek(0)  # Reset file pointer
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                pages = len(pdf_reader.pages)
                text_parts = []
                
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                if text_parts:
                    text = "\n\n".join(text_parts)
                    extraction_method = "PyPDF2"
                    
            except Exception as e:
                self.logger.error(f"PyPDF2 also failed: {str(e)}")
                text = ""
        
        # Clean up the text
        text = self._clean_text(text)
        
        return {
            'text': text,
            'pages': pages,
            'word_count': self._count_words(text) if text else 0,
            'extraction_method': extraction_method,
            'is_likely_scanned': False,  # Will enhance this later
            'error': None if text else "No text could be extracted from PDF"
        }
    
    def _extract_word_text(self, uploaded_file) -> Dict[str, Any]:
        """Extract text from Word document"""
        try:
            doc = Document(uploaded_file)
            text_parts = []
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))
            
            text = "\n\n".join(text_parts)
            text = self._clean_text(text)
            
            return {
                'text': text,
                'pages': len(doc.paragraphs) // 50,  # Rough estimate
                'word_count': self._count_words(text) if text else 0,
                'extraction_method': 'python-docx',
                'is_likely_scanned': False,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Word extraction failed: {str(e)}")
            return {
                'text': '',
                'pages': 0,
                'word_count': 0,
                'extraction_method': 'error',
                'error': str(e)
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Only keep non-empty lines
                cleaned_lines.append(line)
        
        # Join lines and normalize spacing
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text.strip()
    
    def validate_extraction(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of text extraction"""
        validation_result = {
            'is_valid': True,
            'quality_score': 100,
            'issues': [],
            'recommendations': []
        }
        
        text = extraction_result.get('text', '')
        word_count = extraction_result.get('word_count', 0)
        error = extraction_result.get('error')
        
        # Check for extraction errors
        if error:
            validation_result['is_valid'] = False
            validation_result['quality_score'] = 0
            validation_result['issues'].append(f"Extraction error: {error}")
            validation_result['recommendations'].append("Try converting the document to a different format")
            return validation_result
        
        # Check for minimum text length
        if word_count < 100:
            validation_result['quality_score'] -= 50
            validation_result['issues'].append("Document appears to contain very little text")
            validation_result['recommendations'].append("Verify the document contains readable text content")
        
        # Check for garbled text (common with scanned PDFs)
        if text and self._detect_garbled_text(text):
            validation_result['quality_score'] -= 30
            validation_result['issues'].append("Text may be garbled or from scanned document")
            validation_result['recommendations'].append("Consider using OCR software if document is scanned")
        
        # Check for reasonable contract content
        contract_keywords = ['agreement', 'contract', 'party', 'parties', 'terms', 'conditions', 'payment', 'service', 'goods']
        found_keywords = sum(1 for keyword in contract_keywords if keyword.lower() in text.lower())
        
        if found_keywords < 3:
            validation_result['quality_score'] -= 20
            validation_result['issues'].append("Document may not contain typical contract language")
            validation_result['recommendations'].append("Verify this is a contract document suitable for ASC 606 analysis")
        
        # Final validation
        if validation_result['quality_score'] < 50:
            validation_result['is_valid'] = False
        
        return validation_result
    
    def _detect_garbled_text(self, text: str) -> bool:
        """Detect if text appears to be garbled (e.g., from poor OCR)"""
        if not text:
            return False
        
        # Check for excessive special characters
        special_char_count = sum(1 for char in text if not char.isalnum() and not char.isspace())
        total_chars = len(text)
        
        if total_chars > 0 and (special_char_count / total_chars) > 0.3:
            return True
        
        # Check for very short words (common in garbled text)
        words = text.split()
        if len(words) > 10:
            very_short_words = sum(1 for word in words if len(word) <= 2)
            if (very_short_words / len(words)) > 0.5:
                return True
        
        return False