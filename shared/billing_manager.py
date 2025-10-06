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
        self.backend_url = "http://127.0.0.1:3000/api"
    
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
            
            # Log billing record start
            logger.info(f"💰 Recording billing: {asc_standard} - {words_count} words - ${billed_cost:.2f}")
            
            billing_data = {
                'asc_standard': asc_standard,
                'words_count': words_count,
                'estimate_cap_credits': cost_estimate['cost_cap'],
                'est_api_cost': actual_cost,  # Renamed from actual_credits
                'billed_credits': billed_cost,
                'is_free_analysis': is_free_analysis
                # Removed price_tier - using tier_name instead
            }
            
            response = requests.post(
                f"{self.backend_url}/user/record-analysis",
                headers={'Authorization': f'Bearer {user_token}'},
                json=billing_data,
                timeout=10
            )
            
            if response.ok:
                logger.info(f"✓ Billing recorded successfully: {asc_standard} - ${billed_cost:.2f} charged")
                return True
            else:
                logger.error(f"✗ Billing record failed (status {response.status_code}): {asc_standard} - ${billed_cost:.2f}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error recording analysis billing: {asc_standard} - {str(e)}")
            return False
    
    def auto_credit_on_failure(self, user_token: str, cost_amount: float, analysis_id: str = None) -> bool:
        """
        Automatically credit user's wallet when analysis fails after payment
        
        Args:
            user_token: User authentication token
            cost_amount: Amount to credit back to wallet
            analysis_id: Optional analysis identifier for tracking
            
        Returns:
            True if credit was successful, False otherwise
        """
        try:
            credit_data = {
                'credit_amount': cost_amount,
                'reason': 'analysis_failure_refund',
                'analysis_id': analysis_id or 'unknown',
                'automatic': True
            }
            
            response = requests.post(
                f"{self.backend_url}/user/auto-credit",
                headers={'Authorization': f'Bearer {user_token}'},
                json=credit_data,
                timeout=10
            )
            
            if response.ok:
                logger.info(f"Successfully auto-credited ${cost_amount} for failed analysis")
                return True
            else:
                logger.error(f"Failed to auto-credit: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error auto-crediting on failure: {e}")
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
            st.success(f"💳 **Analysis completed - Charged \\${billed_amount:.2f} to your account**")
            
            # Show cost breakdown
            if billed_amount < cost_estimate['estimated_cost']:
                st.info(f"ℹ️ Cost was capped at ${billed_amount:.2f} (115% of estimate)")

# Global instance
billing_manager = BillingManager()