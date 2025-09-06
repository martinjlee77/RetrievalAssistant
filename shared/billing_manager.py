"""
Billing Manager for VeritasLogic Analysis Platform
Handles credit deduction and analysis recording
"""

import requests
import logging
from typing import Dict, Any, Optional
import streamlit as st

logger = logging.getLogger(__name__)

class BillingManager:
    """Manages billing operations for completed analyses"""
    
    def __init__(self):
        self.backend_url = "http://localhost:3000/api"
    
    def record_analysis_billing(
        self,
        asc_standard: str,
        cost_estimate: Dict[str, Any],
        user_token: str,
        words_count: int,
        is_free_analysis: bool = False
    ) -> bool:
        """
        Record analysis billing in the backend database
        
        Args:
            asc_standard: The ASC standard analyzed
            cost_estimate: Cost estimation details
            user_token: User authentication token
            words_count: Number of words in analyzed document
            is_free_analysis: Whether this used a free analysis slot
            
        Returns:
            True if billing recorded successfully, False otherwise
        """
        try:
            # Calculate actual cost (for now, use estimated cost)
            # In a real system, you might track actual API usage
            actual_cost = cost_estimate['estimated_cost']
            billed_cost = min(actual_cost, cost_estimate['cost_cap'])  # Apply cap
            
            billing_data = {
                'asc_standard': asc_standard,
                'words_count': words_count,
                'estimate_cap_credits': cost_estimate['cost_cap'],
                'actual_credits': actual_cost,
                'billed_credits': billed_cost,
                'is_free_analysis': is_free_analysis
            }
            
            response = requests.post(
                f"{self.backend_url}/user/record-analysis",
                headers={'Authorization': f'Bearer {user_token}'},
                json=billing_data,
                timeout=10
            )
            
            if response.ok:
                logger.info(f"Successfully recorded billing for {asc_standard} analysis: ${billed_cost}")
                return True
            else:
                logger.error(f"Failed to record billing: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error recording analysis billing: {e}")
            return False
    
    def show_billing_success_message(
        self, 
        cost_estimate: Dict[str, Any], 
        is_free_analysis: bool = False
    ):
        """Show billing confirmation message to user"""
        if is_free_analysis:
            st.success("🎁 **Analysis completed using one of your free analyses!**")
        else:
            billed_amount = min(cost_estimate['estimated_cost'], cost_estimate['cost_cap'])
            st.success(f"💳 **Analysis completed - Charged ${billed_amount:.2f} to your account**")
            
            # Show cost breakdown
            if billed_amount < cost_estimate['estimated_cost']:
                st.info(f"ℹ️ Cost was capped at ${billed_amount:.2f} (115% of estimate)")

# Global instance
billing_manager = BillingManager()