"""
Simplified Tiered Pricing System for VeritasLogic Analysis Platform
Fixed pricing based on document word count - No complex calculations
"""

import logging
from typing import Dict, Any
from .pricing_config import get_price_tier, format_tier_display

logger = logging.getLogger(__name__)

class CostEstimator:
    """Simple tiered pricing for ASC analyses based on document length"""
    
    def __init__(self):
        pass
    
    def estimate_analysis_cost(
        self, 
        asc_standard: str, 
        document_text: str, 
        additional_context: str = ""
    ) -> Dict[str, Any]:
        """
        Calculate tier-based pricing for an ASC analysis
        
        Args:
            asc_standard: The ASC standard (e.g., 'ASC 606') - no longer affects pricing
            document_text: The main document content
            additional_context: Additional context provided by user
            
        Returns:
            Dict containing tier pricing information
        """
        try:
            # Combine all text and count words
            full_text = f"{document_text} {additional_context}".strip()
            word_count = len(full_text.split())
            
            # Get tier information based on word count
            tier_info = get_price_tier(word_count)
            
            # Handle contact support case for oversized documents
            if tier_info.get('contact_support'):
                return {
                    'estimated_cost': None,
                    'cost_cap': None,
                    'tier': None,
                    'tier_name': tier_info['name'],
                    'tier_description': tier_info['description'],
                    'word_count': word_count,
                    'asc_standard': asc_standard,
                    'billing_model': 'contact_support_required',
                    'contact_support': True
                }
            
            return {
                'estimated_cost': tier_info['price'],
                'cost_cap': tier_info['price'],  # Fixed price, no cap needed
                'tier': tier_info['tier'],
                'tier_name': tier_info['name'],
                'tier_description': tier_info['description'],
                'word_count': word_count,
                'asc_standard': asc_standard,
                'billing_model': 'fixed_tier_pricing'
            }
            
        except Exception as e:
            logger.error(f"Tier pricing error: {e}")  # Still log the error for debugging
            return {
                'error': "An error occurred while calculating the price. Please contact support for assistance.",
                'estimated_cost': None,
                'cost_cap': None,
                'tier': None,
                'tier_name': None,
                'tier_description': None,
                'word_count': None,
                'asc_standard': asc_standard,
                'billing_model': None
            }
    
    def format_cost_display(self, cost_estimate: Dict[str, Any]) -> str:
        """Format tier pricing for user display"""
        # Handle contact support case for oversized documents
        if cost_estimate.get('contact_support'):
            word_count = cost_estimate['word_count']
            description = cost_estimate['tier_description']
            return f"""
        **📞 {cost_estimate['tier_name']}**
        
        - **Document Length:** {word_count:,} words
        - **Analysis Type:** {cost_estimate['asc_standard']}
        - **Required Action:** {description}
        
        *Please contact support@veritaslogic.ai for custom enterprise pricing*
        """
        
        # Standard pricing display
        tier = cost_estimate['tier']
        name = cost_estimate['tier_name']
        price = cost_estimate['estimated_cost']
        word_count = cost_estimate['word_count']
        description = cost_estimate['tier_description']
        
        return f"""
        **💰 Tier {tier}: {name} - ${price:.2f}**
        
        - **Document Length:** {word_count:,} words
        - **Analysis Type:** {cost_estimate['asc_standard']}
        - **Tier Description:** {description}
        
        *Fixed price - No estimates or caps needed*
        """

# Global instance for use across the application
cost_estimator = CostEstimator()