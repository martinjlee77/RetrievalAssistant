"""
Wallet Management System for VeritasLogic Analysis Platform
Handles credit top-ups, balance checking, and payment processing
"""

import streamlit as st
import requests
import logging
import os
from typing import Dict, Any, List, Optional
from .pricing_config import get_credit_packages
import pandas as pd

logger = logging.getLogger(__name__)

# Backend API configuration - Use environment variables for cross-deployment support
BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:3000/api')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')

class WalletManager:
    """Manages user wallet operations and credit transactions"""
    
    def __init__(self):
        self.backend_url = BACKEND_URL
    
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
    
    def show_wallet_top_up_options(self, current_balance: float, required_amount: float = None) -> None:
        """
        Display wallet top-up redirect to dashboard
        
        Args:
            current_balance: User's current credit balance
            required_amount: Amount needed for pending analysis
        """
        st.subheader(":primary[Add Credits to Your Account]")
        
        # Show current balance and requirement, col1 and col4 are added for better layout
        col1, col2, col3, col4 = st.columns([0.01,1,1,5])
        with col2:
            st.metric("Current Balance:", f"${current_balance:.0f}", border = True)
        
        if required_amount:
            with col3:
                needed = max(0, required_amount - current_balance)
                st.metric("Add'l Amount Needed:", f"${needed:.0f}", border = True)       
       
        # Create buttons row
        dashboard_url = f"{WEBSITE_URL}/dashboard.html#credits"
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            st.markdown(f"""
            <div style="text-align: left; margin: 20px 0;">
                <a href="{dashboard_url}" target="_blank">
                    <button style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        padding: 15px 30px;
                        font-size: 16px;
                        font-weight: bold;
                        border-radius: 8px;
                        cursor: pointer;
                        text-decoration: none;
                        display: inline-block;
                        transition: transform 0.2s;
                        width: 100%;
                    " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                        🔒 Add Credits
                    </button>
                </a>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Add refresh balance button that preserves form data
            if st.button("🔄 Refresh Balance", key="refresh_balance_btn", help="Update balance without losing your form data"):
                # Force a rerun to fetch fresh balance - this preserves all form state
                st.rerun()
        
        # Add helpful instruction
        st.info("💡 **Tip:** After adding credits in the dashboard, use the 'Refresh Balance' button to update your balance without losing your uploaded files or form data.")
        
        return None
    
    def process_credit_purchase(self, user_token: str, amount: float) -> Dict[str, Any]:
        """
        DEPRECATED: Credit purchases now handled through dashboard
        
        Args:
            user_token: User authentication token
            amount: Amount of credits to purchase
            
        Returns:
            Dict containing redirect instruction
        """
        return {
            'success': False,
            'redirect_required': True,
            'message': "Please use the secure dashboard to add credits to your account.",
            'dashboard_url': f"{WEBSITE_URL}/dashboard.html#credits"
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