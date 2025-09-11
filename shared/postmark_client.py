"""
Postmark Email Client for VeritasLogic Platform
Handles rerun notifications and other email functionality
"""

import os
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PostmarkClient:
    def __init__(self):
        self.api_key = os.getenv('POSTMARK_API_KEY')
        self.api_url = 'https://api.postmarkapp.com'
        self.from_email = 'noreply@veritaslogic.ai'  # Update with your verified domain
        
    def send_rerun_notification(self, memo_id: str, user_email: str, user_name: str, 
                               requested_changes: str) -> bool:
        """
        Send rerun request notification to admin
        
        Args:
            memo_id: Original memo ID
            user_email: User's email
            user_name: User's name
            requested_changes: What the user wants changed
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Postmark-Server-Token': self.api_key
            }
            
            email_data = {
                'From': self.from_email,
                'To': 'admin@veritaslogic.ai',  # Your admin email
                'Subject': f'Memo Rerun Request - {memo_id}',
                'HtmlBody': f"""
                <h2>📝 New Memo Rerun Request</h2>
                <p><strong>Original Memo ID:</strong> {memo_id}</p>
                <p><strong>Customer:</strong> {user_name} ({user_email})</p>
                <p><strong>Requested Changes:</strong></p>
                <blockquote>{requested_changes}</blockquote>
                <p><em>Please review and process this rerun request within 14 days.</em></p>
                """,
                'TextBody': f"""
New Memo Rerun Request

Original Memo ID: {memo_id}
Customer: {user_name} ({user_email})
Requested Changes: {requested_changes}

Please review and process this rerun request within 14 days.
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Rerun notification sent successfully for memo {memo_id}")
                return True
            else:
                logger.error(f"Failed to send rerun notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending rerun notification: {e}")
            return False
            
    def send_rerun_confirmation(self, user_email: str, memo_id: str, 
                               estimated_completion: str = "1-2 business days") -> bool:
        """
        Send confirmation to user that rerun request was received
        
        Args:
            user_email: User's email
            memo_id: Original memo ID
            estimated_completion: When rerun will be completed
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Postmark-Server-Token': self.api_key
            }
            
            email_data = {
                'From': self.from_email,
                'To': user_email,
                'Subject': f'Rerun Request Received - Memo {memo_id}',
                'HtmlBody': f"""
                <h2>✅ Rerun Request Received</h2>
                <p>We've received your request to rerun memo <strong>{memo_id}</strong>.</p>
                <p><strong>What happens next:</strong></p>
                <ul>
                    <li>Our team will review your requested changes</li>
                    <li>The updated memo will be processed within {estimated_completion}</li>
                    <li>You'll receive an email when your updated memo is ready</li>
                </ul>
                <p>Questions? Reply to this email and we'll help.</p>
                <p><em>- The VeritasLogic Team</em></p>
                """,
                'TextBody': f"""
Rerun Request Received - Memo {memo_id}

We've received your request to rerun memo {memo_id}.

What happens next:
- Our team will review your requested changes
- The updated memo will be processed within {estimated_completion}
- You'll receive an email when your updated memo is ready

Questions? Reply to this email and we'll help.

- The VeritasLogic Team
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Rerun confirmation sent to {user_email} for memo {memo_id}")
                return True
            else:
                logger.error(f"Failed to send rerun confirmation: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending rerun confirmation: {e}")
            return False