"""
Preflight Pricing System for VeritasLogic Analysis Platform
Handles multi-file word counting, tier determination, and pricing before analysis
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from utils.document_extractor import DocumentExtractor
from .pricing_config import get_price_tier

logger = logging.getLogger(__name__)

class PreflightPricing:
    """Handles preflight document processing and pricing calculation"""
    
    def __init__(self):
        self.document_extractor = DocumentExtractor()
    
    def process_files_for_pricing(self, uploaded_files) -> Dict[str, Any]:
        """
        Process multiple uploaded files to calculate total words and pricing
        
        Args:
            uploaded_files: List of Streamlit uploaded file objects
            
        Returns:
            Dict containing total word count, tier info, price, and file details
        """
        if not uploaded_files:
            return {
                'success': False,
                'error': 'No files provided',
                'total_words': 0,
                'tier_info': None,
                'file_details': []
            }
        
        # Process all uploaded files (no limit - charge for all contracts)
        logger.info(f"Processing {len(uploaded_files)} uploaded files")
        
        file_details = []
        total_words = 0
        errors = []
        
        # Process each file
        for i, uploaded_file in enumerate(uploaded_files, 1):
            try:
                # Reset file pointer
                uploaded_file.seek(0)
                
                # Extract text and metadata
                extraction_result = self.document_extractor.extract_text(uploaded_file)
                
                if extraction_result.get('error'):
                    # Handle scanned PDF detection with detailed user message
                    if extraction_result.get('error') == 'scanned_pdf_detected':
                        # Use the detailed user message instead of the error code
                        user_friendly_msg = extraction_result.get('user_message', 'Scanned PDF detected')
                        errors.append(user_friendly_msg)
                        logger.error(f"File {i} ({uploaded_file.name}): scanned_pdf_detected")
                    else:
                        # Handle other errors normally
                        error_msg = f"File {i} ({uploaded_file.name}): {extraction_result['error']}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                    continue
                
                file_word_count = extraction_result.get('word_count', 0)
                total_words += file_word_count
                
                # Store file details
                file_details.append({
                    'filename': uploaded_file.name,
                    'file_number': i,
                    'word_count': file_word_count,
                    'estimated_pages': extraction_result.get('estimated_pages', 1),
                    'file_size_mb': extraction_result.get('file_size_mb', 0),
                    'extraction_method': extraction_result.get('extraction_method', 'unknown'),
                    'is_likely_scanned': extraction_result.get('is_likely_scanned', False),
                    'text_content': extraction_result.get('text', '')  # Store extracted text
                })
                
                logger.info(f"Processed file {i}: {uploaded_file.name} - {file_word_count} words")
                
            except Exception as e:
                error_msg = f"File {i} ({uploaded_file.name}): Failed to process - {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        # Check if we have any successful extractions
        if total_words == 0:
            # Special handling for all-scanned-PDFs case to trigger clean UI
            all_scanned = all(error.startswith('🔍 **Scanned/Image-Based PDF Detected**') for error in errors)
            
            if all_scanned and len(errors) == 1:
                # Single scanned PDF - use clean expandable UI
                return {
                    'success': False,
                    'error': 'scanned_pdf_detected',
                    'user_message': errors[0],  # The detailed message
                    'total_words': 0,
                    'tier_info': None,
                    'file_details': file_details
                }
            else:
                # Multiple files or mixed error types - use generic handler
                return {
                    'success': False,
                    'error': 'No text could be extracted from any files. ' + '; '.join(errors),
                    'total_words': 0,
                    'tier_info': None,
                    'file_details': file_details
                }
        
        # Get tier information based on total words
        tier_info = get_price_tier(total_words)
        
        # Calculate estimated pages for user display
        estimated_total_pages = max(1, round(total_words / 300))
        
        result = {
            'success': True,
            'total_words': total_words,
            'estimated_total_pages': estimated_total_pages,
            'tier_info': tier_info,
            'file_count': len(file_details),
            'file_details': file_details,
            'processing_errors': errors if errors else None,
            'billing_summary': self._format_billing_summary(tier_info, total_words, estimated_total_pages, len(file_details))
        }
        
        logger.info(f"Preflight pricing complete: {total_words} words, {tier_info['name']} tier, ${tier_info['price']}")
        return result
    
    def _format_billing_summary(self, tier_info: Dict[str, Any], total_words: int, estimated_pages: int, file_count: int) -> str:
        
        """Format billing summary for user display"""
        return f"""
**COST FOR THIS ANALYSIS: \\${int(tier_info['price'])}** based on the following factors:

- Document analysis: {total_words:,} words across {file_count} file{'s' if file_count != 1 else ''}
- Pricing tier: {tier_info['name']} (up to {tier_info['max_words']:,} words)
- Just FYI, estimated pages: ~{estimated_pages} pages (at 300 words/page)

        """.strip()
    
    def check_sufficient_credits(self, required_price: float, user_credits: float) -> Dict[str, Any]:
        """
        Check if user has sufficient credits for the analysis
        
        Args:
            required_price: Price required for the analysis
            user_credits: User's current credit balance
            
        Returns:
            Dict with can_proceed, shortfall amount, and user message
        """
        if user_credits >= required_price:
            return {
                'can_proceed': True,
                'credits_sufficient': True,
                'current_credits': user_credits,
                'required_credits': required_price,
                'credits_remaining': user_credits - required_price,
                'message': f"**SUFFICIENT CREDITS AVAILABLE:** \\${user_credits:.0f} available, \\${required_price:.0f} needed for this analysis."
            }
        else:
            shortfall = required_price - user_credits
            return {
                'can_proceed': False,
                'credits_sufficient': False,
                'current_credits': user_credits,
                'required_credits': required_price,
                'shortfall_amount': shortfall,
                'message': f"⚠️ INSUFFICIENT CREDITS: You have \\${user_credits:.0f} but need \\${required_price:.0f}. Please add at least \\${shortfall:.0f} to your account using the button below."
            }

# Global instance for use across the application
preflight_pricing = PreflightPricing()