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
    
    def calculate_pricing_from_word_count(self, total_words: int, file_count: int) -> Dict[str, Any]:
        """
        Calculate pricing based on word count without extracting files
        Used when files have already been extracted separately
        
        Args:
            total_words: Total word count across all files
            file_count: Number of files
            
        Returns:
            Dict containing tier info, price, and billing summary
        """
        if total_words == 0:
            return {
                'success': False,
                'error': 'No text available for pricing',
                'total_words': 0,
                'tier_info': None,
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
            'file_count': file_count,
            'billing_summary': self._format_billing_summary(tier_info, total_words, estimated_total_pages, file_count)
        }
        
        if tier_info.get('contact_support'):
            logger.info(f"Pricing calculated: {total_words} words, {tier_info['name']} - contact support required")
        else:
            logger.info(f"Pricing calculated: {total_words} words, {tier_info['name']} tier, ${tier_info['price']}")
        
        return result
    
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
    
    def _create_scanned_pdf_message(self, filename: str, reasons) -> str:
        """Create filename-aware scanned PDF message using DocumentExtractor's method"""
        return self.document_extractor._get_scanned_pdf_message(reasons=reasons, filename=filename)
    
    def check_subscription_allowance(self, org_id: int, total_words: int, file_count: int) -> Dict[str, Any]:
        """
        Check if organization has sufficient word allowance for analysis (subscription-based)
        
        Args:
            org_id: Organization ID
            total_words: Total word count across all files
            file_count: Number of files
            
        Returns:
            Dict containing allowance check result, usage info, and UI messaging
        """
        if total_words == 0:
            return {
                'success': False,
                'allowed': False,
                'error': 'No text available for analysis',
                'total_words': 0
            }
        
        # Get subscription allowance check
        subscription_manager = SubscriptionManager()
        allowance_check = subscription_manager.check_word_allowance(org_id, total_words)
        usage_info = subscription_manager.get_current_usage(org_id)
        
        # Calculate estimated pages for user display
        estimated_total_pages = max(1, round(total_words / 300))
        
        # Build result with allowance metadata
        result = {
            'success': True,
            'allowed': allowance_check['allowed'],
            'total_words': total_words,
            'estimated_total_pages': estimated_total_pages,
            'file_count': file_count,
            'words_available': allowance_check['words_available'],
            'usage_info': usage_info,
            'allowance_check': allowance_check
        }
        
        # Add tailored UI messaging based on subscription status
        if allowance_check['allowed']:
            # Sufficient allowance - show confirmation
            words_remaining = allowance_check.get('words_remaining_after', 0)
            result['ui_message'] = {
                'type': 'success',
                'title': '✅ Sufficient Word Allowance',
                'content': f"""
**This analysis will use {total_words:,} words** ({estimated_total_pages} pages across {file_count} file{'s' if file_count != 1 else ''})

- **Available:** {allowance_check['words_available']:,} words
- **After analysis:** {words_remaining:,} words remaining
- **Plan:** {usage_info.get('plan_name', 'N/A')}
"""
            }
        else:
            # Insufficient allowance - show upgrade message
            suggested_action = allowance_check.get('suggested_action', 'upgrade_plan')
            
            if suggested_action == 'update_payment':
                # Past due account
                result['ui_message'] = {
                    'type': 'error',
                    'title': '⚠️ Payment Required',
                    'content': f"""
Your subscription payment is past due. Please update your payment method to continue using VeritasLogic.

**Analysis requires:** {total_words:,} words ({estimated_total_pages} pages)

[Update Payment Method in Dashboard](#)
""",
                    'action': 'update_payment',
                    'action_url': '/dashboard#billing'
                }
            elif suggested_action == 'start_trial':
                # No subscription
                result['ui_message'] = {
                    'type': 'info',
                    'title': '🎉 Start Your Free Trial',
                    'content': f"""
**This analysis requires {total_words:,} words** ({estimated_total_pages} pages)

Start your 14-day free trial with {usage_info.get('word_allowance', 9000):,} words to analyze this contract.

[Start Free Trial](#)
""",
                    'action': 'start_trial',
                    'action_url': '/signup.html'
                }
            else:
                # Insufficient words - need upgrade
                is_trial = usage_info.get('is_trial', False)
                current_plan = usage_info.get('plan_key', 'professional')
                
                if is_trial:
                    # Trial user - celebratory tone
                    result['ui_message'] = {
                        'type': 'warning',
                        'title': '🎉 Great Choice!',
                        'content': f"""
**This contract requires {total_words:,} words** ({estimated_total_pages} pages across {file_count} file{'s' if file_count != 1 else ''})

You have **{allowance_check['words_available']:,} words** remaining in your trial.

Continue with a paid plan to analyze this contract and get your full monthly allowance.

- **Professional Plan:** 30,000 words/month - $295/month
- **Team Plan:** 75,000 words/month - $595/month  
- **Enterprise Plan:** 180,000 words/month - $1,195/month
""",
                        'action': 'upgrade_plan',
                        'action_url': '/dashboard#billing',
                        'cta_text': 'Continue with Professional Plan'
                    }
                else:
                    # Paid user - firm but helpful
                    result['ui_message'] = {
                        'type': 'error',
                        'title': '⚠️ Insufficient Word Allowance',
                        'content': f"""
**This contract requires {total_words:,} words** ({estimated_total_pages} pages across {file_count} file{'s' if file_count != 1 else ''})

You have **{allowance_check['words_available']:,} words** remaining this month.

**Current Plan:** {usage_info.get('plan_name', 'N/A')}

**Options:**
- Upgrade to a higher plan with more words per month
- Contact our team at [support@veritaslogic.ai](mailto:support@veritaslogic.ai) for custom enterprise pricing
""",
                        'action': 'upgrade_plan',
                        'action_url': '/dashboard#billing',
                        'cta_text': 'Upgrade Plan'
                    }
        
        # Log allowance decision for support visibility
        if allowance_check['allowed']:
            logger.info(
                f"Allowance check PASSED for org {org_id}: {total_words} words needed, "
                f"{allowance_check['words_available']} available, {allowance_check.get('words_remaining_after', 0)} remaining after"
            )
        else:
            logger.warning(
                f"Allowance check FAILED for org {org_id}: {total_words} words needed, "
                f"{allowance_check['words_available']} available, reason: {allowance_check['reason']}"
            )
        
        return result

# Global instance for use across the application
preflight_pricing = PreflightPricing()