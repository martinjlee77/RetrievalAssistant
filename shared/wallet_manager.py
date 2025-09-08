"""
Wallet Management System for VeritasLogic Analysis Platform
Handles credit top-ups, balance checking, and payment processing
"""

import streamlit as st
import requests
import logging
from typing import Dict, Any, List, Optional
from .pricing_config import get_credit_packages

logger = logging.getLogger(__name__)

class WalletManager:
    """Manages user wallet operations and credit transactions"""
    
    def __init__(self):
        self.backend_url = "http://127.0.0.1:3000/api"
    
    def get_user_balance(self, user_token: str) -> Dict[str, Any]:
        """
        Get current user wallet balance
        
        Args:
            user_token: User authentication token
            
        Returns:
            Dict containing balance info and status
        """
        try:
            response = requests.get(
                f"{self.backend_url}/user/wallet-balance",
                headers={'Authorization': f'Bearer {user_token}'},
                timeout=10
            )
            
            if response.ok:
                data = response.json()
                return {
                    'success': True,
                    'balance': data.get('balance', 0.0),
                    'last_updated': data.get('last_updated'),
                    'pending_charges': data.get('pending_charges', 0.0)
                }
            else:
                logger.error(f"Failed to get wallet balance: {response.status_code}")
                return {
                    'success': False,
                    'error': 'Failed to retrieve wallet balance',
                    'balance': 0.0
                }
                
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return {
                'success': False,
                'error': 'Network error retrieving balance',
                'balance': 0.0
            }
    
    def show_wallet_top_up_options(self, current_balance: float, required_amount: float = None) -> Optional[float]:
        """
        Display wallet top-up options with both fixed and custom amounts
        
        Args:
            current_balance: User's current credit balance
            required_amount: Amount needed for pending analysis
            
        Returns:
            Selected top-up amount or None if no selection made
        """
        st.subheader("💳 Add Credits to Your Account")
        
        # Show current balance and requirement
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Balance", f"\${current_balance:.2f}")
        
        if required_amount:
            with col2:
                needed = max(0, required_amount - current_balance)
                st.metric("Amount Needed", f"\${needed:.2f}")
        
        # Get credit packages
        credit_packages = get_credit_packages()
        
        # Fixed amount options
        st.write("**Quick Top-Up Options:**")
        fixed_cols = st.columns(len(credit_packages))
        
        selected_fixed_amount = None
        for i, package in enumerate(credit_packages):
            with fixed_cols[i]:
                if st.button(f"\${package['amount']}", key=f"credit_{package['amount']}", use_container_width=True):
                    selected_fixed_amount = package['amount']
        
        # Custom amount option
        st.write("**Or Enter Custom Amount ($):**")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            custom_amount = st.number_input(
                label="Custom Amount ($)",
                min_value=10.0,
                max_value=2000.0,
                step=5.0,
                value=max(10.0, required_amount - current_balance) if required_amount else 50.0,
                key="custom_credit_amount"
            )
        
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing  
            if st.button("Add Custom", key="add_custom_credits", use_container_width=True):
                return custom_amount
        
        return selected_fixed_amount
    
    def process_credit_purchase(self, user_token: str, amount: float) -> Dict[str, Any]:
        """
        Process credit purchase transaction
        
        Args:
            user_token: User authentication token
            amount: Amount of credits to purchase
            
        Returns:
            Dict containing transaction result
        """
        try:
            purchase_data = {
                'credit_amount': amount,
                'payment_method': 'wallet_topup',  # Simplified for now
                'source': 'streamlit_app'
            }
            
            response = requests.post(
                f"{self.backend_url}/user/purchase-credits",
                headers={'Authorization': f'Bearer {user_token}'},
                json=purchase_data,
                timeout=15
            )
            
            if response.ok:
                data = response.json()
                logger.info(f"Successfully purchased ${amount} credits")
                return {
                    'success': True,
                    'transaction_id': data.get('transaction_id'),
                    'new_balance': data.get('new_balance', 0.0),
                    'amount_added': amount,
                    'message': f"✅ Successfully added \${amount:.2f} to your wallet!"
                }
            else:
                logger.error(f"Credit purchase failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'Purchase failed: {response.text}',
                    'message': f"❌ Failed to add credits. Please try again."
                }
                
        except Exception as e:
            logger.error(f"Error processing credit purchase: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': "❌ Network error during purchase. Please try again."
            }
    
    def charge_for_analysis(self, user_token: str, amount: float, analysis_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Charge user's wallet for analysis
        
        Args:
            user_token: User authentication token
            amount: Amount to charge
            analysis_details: Details about the analysis being charged for
            
        Returns:
            Dict containing charge result
        """
        try:
            charge_data = {
                'charge_amount': amount,
                'analysis_type': analysis_details.get('asc_standard', 'unknown'),
                'word_count': analysis_details.get('total_words', 0),
                'tier': analysis_details.get('tier', 1),
                'charge_reason': 'analysis_start'
            }
            
            response = requests.post(
                f"{self.backend_url}/user/charge-wallet",
                headers={'Authorization': f'Bearer {user_token}'},
                json=charge_data,
                timeout=10
            )
            
            if response.ok:
                data = response.json()
                logger.info(f"Successfully charged ${amount} for analysis")
                return {
                    'success': True,
                    'transaction_id': data.get('transaction_id'),
                    'remaining_balance': data.get('remaining_balance', 0.0),
                    'charge_amount': amount
                }
            else:
                logger.error(f"Wallet charge failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'Charge failed: {response.text}'
                }
                
        except Exception as e:
            logger.error(f"Error charging wallet: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance for use across the application
wallet_manager = WalletManager()