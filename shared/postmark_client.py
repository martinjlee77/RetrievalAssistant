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
        self.from_email = 'admin@veritaslogic.ai'  # Use established verified email address
        
        # Debug: Log masked token info for troubleshooting
        if self.api_key:
            masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
            logger.info(f"PostmarkClient initialized with token: {masked_key} (length: {len(self.api_key)})")
        else:
            logger.error("POSTMARK_API_KEY environment variable not found!")
        
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
            
    def send_password_reset_email(self, user_email: str, user_name: str, reset_token: str) -> bool:
        """
        Send password reset email to user
        
        Args:
            user_email: User's email address
            user_name: User's first name
            reset_token: Password reset token
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Postmark-Server-Token': self.api_key
            }
            
            # Create the reset link
            reset_link = f"https://veritaslogic.ai/reset-password.html?token={reset_token}"
            
            email_data = {
                'From': self.from_email,
                'To': user_email,
                'Subject': 'Reset Your VeritasLogic Password',
                'HtmlBody': f"""
                <h2>🔐 Password Reset Request</h2>
                <p>Hello {user_name},</p>
                <p>We received a request to reset your password for your VeritasLogic account.</p>
                
                <p><strong>Click the link below to reset your password:</strong></p>
                <p><a href="{reset_link}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Reset My Password</a></p>
                
                <p><strong>Or copy and paste this link into your browser:</strong><br>
                {reset_link}</p>
                
                <p><strong>Important security notes:</strong></p>
                <ul>
                    <li>This link will expire in 1 hour for your security</li>
                    <li>If you didn't request this reset, you can safely ignore this email</li>
                    <li>Never share this link with anyone</li>
                </ul>
                
                <p>If you have any questions, reply to this email and we'll help.</p>
                <p><em>- The VeritasLogic Team</em></p>
                """,
                'TextBody': f"""
Password Reset Request

Hello {user_name},

We received a request to reset your password for your VeritasLogic account.

Click the link below to reset your password:
{reset_link}

Important security notes:
- This link will expire in 1 hour for your security
- If you didn't request this reset, you can safely ignore this email
- Never share this link with anyone

If you have any questions, reply to this email and we'll help.

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
                logger.info(f"Password reset email sent successfully to {user_email}")
                return True
            else:
                logger.error(f"Failed to send password reset email: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False
            
    def send_email_verification(self, user_email: str, user_name: str, verification_token: str) -> bool:
        """
        Send email verification email to user
        
        Args:
            user_email: User's email address
            user_name: User's first name
            verification_token: Email verification token
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Postmark-Server-Token': self.api_key
            }
            
            # Create the verification link
            verification_link = f"https://veritaslogic.ai/verify-email.html?token={verification_token}"
            
            email_data = {
                'From': self.from_email,
                'To': user_email,
                'Subject': 'Verify Your VeritasLogic Email Address',
                'HtmlBody': f"""
                <h2>🔒 Welcome to VeritasLogic!</h2>
                <p>Hello {user_name},</p>
                <p>Thank you for signing up for VeritasLogic. To complete your registration and start using our platform, please verify your email address.</p>
                
                <p><strong>Click the link below to verify your email:</strong></p>
                <p><a href="{verification_link}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Verify My Email</a></p>
                
                <p><strong>Or copy and paste this link into your browser:</strong><br>
                {verification_link}</p>
                
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This link will expire in 24 hours</li>
                    <li>You must verify your email before you can log in</li>
                    <li>If you didn't create an account, please ignore this email</li>
                </ul>
                
                <p>Once verified, you'll have access to our AI-powered accounting analysis platform.</p>
                <p>If you have any questions, reply to this email and we'll help.</p>
                <p><em>- The VeritasLogic Team</em></p>
                """,
                'TextBody': f"""
Welcome to VeritasLogic!

Hello {user_name},

Thank you for signing up for VeritasLogic. To complete your registration and start using our platform, please verify your email address.

Click the link below to verify your email:
{verification_link}

Important:
- This link will expire in 24 hours
- You must verify your email before you can log in
- If you didn't create an account, please ignore this email

Once verified, you'll have access to our AI-powered accounting analysis platform.

If you have any questions, reply to this email and we'll help.

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
                logger.info(f"Email verification sent successfully to {user_email}")
                return True
            else:
                logger.error(f"Failed to send email verification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email verification: {e}")
            return False