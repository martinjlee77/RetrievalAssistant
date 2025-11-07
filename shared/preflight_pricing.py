"""
Preflight Pricing System for VeritasLogic Analysis Platform
Handles multi-file word counting and subscription allowance checking before analysis
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from utils.document_extractor import DocumentExtractor
from shared.pricing_config import get_price_tier
from shared.subscription_manager import SubscriptionManager

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
                        # Create filename-aware message for scanned PDFs
                        reasons = extraction_result.get('detection_reasons', [])
                        filename_msg = self._create_scanned_pdf_message(uploaded_file.name, reasons)
                        errors.append(filename_msg)
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
            all_scanned = all(isinstance(error, str) and error.startswith('🔍 **Scanned/Image-Based PDF Detected') for error in errors)
            
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
                    'error': 'No text could be extracted from any files. ' + '\n\n'.join(errors),
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
        
        if tier_info.get('contact_support'):
            logger.info(f"Preflight pricing complete: {total_words} words, {tier_info['name']} - contact support required")
        else:
            logger.info(f"Preflight pricing complete: {total_words} words, {tier_info['name']} tier, ${tier_info['price']}")
        return result
    
    def _format_billing_summary(self, tier_info: Dict[str, Any], total_words: int, estimated_pages: int, file_count: int) -> str:
        
        """Format billing summary for user display"""
        # Handle contact support case for oversized documents
        if tier_info.get('contact_support'):
            return f"""
**DOCUMENT TOO LARGE FOR STANDARD PRICING**

- Word count: **{total_words:,} words across {file_count} file{'s' if file_count != 1 else ''}** (~{estimated_pages} pages)
- This exceeds our maximum tier of 60,000 words

**Next Steps:** Please contact support at support@veritaslogic.ai for custom enterprise pricing on documents of this size.

        """.strip()
        
        # Standard pricing display
        return f"""
**COST FOR THIS ANALYSIS IS \\${int(tier_info['price'])}** based on the following factors:

- Word count: **{total_words:,} words across {file_count} file{'s' if file_count != 1 else ''}**, ~{estimated_pages} pages (at 300 words/page)
- Pricing tier: **{tier_info['name']}**

        """.strip()
    
    def _create_scanned_pdf_message(self, filename: str, reasons) -> str:
        """Create filename-aware scanned PDF message using DocumentExtractor's method"""
        return self.document_extractor._get_scanned_pdf_message(reasons=reasons, filename=filename)
    
    def check_subscription_allowance(self, user_token: str, total_words: int) -> Dict[str, Any]:
        """
        Check if user has sufficient word allowance for analysis (subscription-based)
        
        Args:
            user_token: User authentication token
            total_words: Total word count across all files
            
        Returns:
            Dict containing allowance check result, usage info, and UI messaging
        """
        if total_words == 0:
            return {
                'can_proceed': False,
                'error_message': 'No text available for analysis',
                'total_words': 0
            }
        
        # Get subscription allowance check via API
        import requests
        from shared.auth_utils import WEBSITE_URL
        
        try:
            response = requests.post(
                f'{WEBSITE_URL}/api/subscription/check-allowance',
                headers={'Authorization': f'Bearer {user_token}'},
                json={'words_needed': total_words},
                timeout=10
            )
            
            if not response.ok:
                logger.error(f"Allowance check failed: {response.status_code} - {response.text}")
                return {
                    'can_proceed': False,
                    'error_message': 'Failed to check word allowance. Please try again.',
                    'total_words': total_words
                }
            
            allowance_data = response.json()
            
        except Exception as e:
            logger.error(f"Allowance check error: {str(e)}")
            return {
                'can_proceed': False,
                'error_message': 'Network error checking word allowance. Please try again.',
                'total_words': total_words
            }
        
        # Extract allowance data from API response
        can_proceed = allowance_data.get('can_proceed', False)
        segment = allowance_data.get('segment', 'unknown')  # trial, paid, past_due, none
        status = allowance_data.get('status', 'unknown')
        words_available = allowance_data.get('words_available', 0)
        words_remaining_after = allowance_data.get('words_remaining_after', 0)
        show_warning = allowance_data.get('show_warning', False)
        renewal_date = allowance_data.get('renewal_date', 'Unknown')
        org_id = allowance_data.get('org_id')
        upgrade_link = allowance_data.get('upgrade_link', '/dashboard')
        
        # Build standard result structure
        result = {
            'can_proceed': can_proceed,
            'total_words': total_words,
            'segment': segment,
            'status': status,
            'words_available': words_available,
            'words_remaining_after': words_remaining_after,
            'show_warning': show_warning,
            'renewal_date': renewal_date,
            'org_id': org_id,
            'upgrade_link': upgrade_link
        }
        
        # Add error message if blocked
        if not can_proceed:
            if segment == 'past_due':
                # STRICT ENFORCEMENT: Completely block past-due users
                result['error_message'] = (
                    f"Your subscription payment failed. Please update your payment method to continue. "
                    f"Visit your dashboard to resolve this issue."
                )
                logger.warning(f"BLOCKED past-due user (org {org_id}): Cannot proceed with {total_words} word analysis")
            elif segment == 'none':
                result['error_message'] = (
                    f"No active subscription found. Start your 14-day free trial to analyze this contract."
                )
            else:
                # Insufficient word allowance
                result['error_message'] = (
                    f"Insufficient word allowance. You have {words_available:,} words available, "
                    f"but this analysis requires {total_words:,} words."
                )
                logger.warning(f"Insufficient allowance for org {org_id}: {total_words} needed, {words_available} available")
        else:
            # Log successful allowance check
            logger.info(
                f"Allowance check PASSED for org {org_id}: {total_words} words needed, "
                f"{words_available:,} available, {words_remaining_after:,} remaining after, segment={segment}"
            )
        
        return result

# Global instance for use across the application
preflight_pricing = PreflightPricing()