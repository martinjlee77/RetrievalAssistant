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
    
    def send_new_signup_notification(self, user_email: str, first_name: str, last_name: str, 
                                     company_name: str, job_title: str, awarded_credits: float) -> bool:
        """
        Send new signup notification to admin for monitoring
        
        Args:
            user_email: User's email address
            first_name: User's first name
            last_name: User's last name
            company_name: User's company name
            job_title: User's job title
            awarded_credits: Amount of credits awarded
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Postmark-Server-Token': self.api_key
            }
            
            email_domain = user_email.split('@')[1] if '@' in user_email else 'unknown'
            
            email_data = {
                'From': self.from_email,
                'To': 'support@veritaslogic.ai',
                'Subject': f'🎉 New User Signup - {company_name}',
                'HtmlBody': f"""
                <h2>🎉 New User Signup</h2>
                <p><strong>User Details:</strong></p>
                <ul>
                    <li><strong>Name:</strong> {first_name} {last_name}</li>
                    <li><strong>Email:</strong> {user_email}</li>
                    <li><strong>Domain:</strong> {email_domain}</li>
                    <li><strong>Company:</strong> {company_name}</li>
                    <li><strong>Job Title:</strong> {job_title}</li>
                </ul>
                <p><strong>Initial Credits Awarded:</strong> ${awarded_credits:.2f}</p>
                <p><em>Monitor for potential abuse (multiple signups from same domain)</em></p>
                """,
                'TextBody': f"""
New User Signup

User Details:
- Name: {first_name} {last_name}
- Email: {user_email}
- Domain: {email_domain}
- Company: {company_name}
- Job Title: {job_title}

Initial Credits Awarded: ${awarded_credits:.2f}

Monitor for potential abuse (multiple signups from same domain)
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"New signup notification sent to support for {user_email}")
                return True
            else:
                logger.error(f"Failed to send signup notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending signup notification: {e}")
            return False
    
    def send_billing_error_alert(self, user_id: int, user_email: str, asc_standard: str, 
                                 error_type: str, error_details: str, words_count: int, 
                                 credits_to_charge: float) -> bool:
        """
        Send critical billing error alert to support
        
        Args:
            user_id: User ID
            user_email: User's email
            asc_standard: ASC standard being analyzed
            error_type: Type of error (e.g., DatabaseError)
            error_details: Detailed error message
            words_count: Number of words in analysis
            credits_to_charge: Credits that should have been charged
            
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
                'To': 'support@veritaslogic.ai',
                'Subject': f'[CRITICAL] Billing Error - User {user_id}',
                'HtmlBody': f"""
                <h2>🚨 CRITICAL BILLING ERROR</h2>
                <p><strong style="color: red;">Analysis completed but billing failed!</strong></p>
                
                <p><strong>User Details:</strong></p>
                <ul>
                    <li><strong>User ID:</strong> {user_id}</li>
                    <li><strong>Email:</strong> {user_email}</li>
                </ul>
                
                <p><strong>Analysis Details:</strong></p>
                <ul>
                    <li><strong>ASC Standard:</strong> {asc_standard}</li>
                    <li><strong>Word Count:</strong> {words_count:,}</li>
                    <li><strong>Credits to Charge:</strong> ${credits_to_charge:.2f}</li>
                </ul>
                
                <p><strong>Error Details:</strong></p>
                <ul>
                    <li><strong>Error Type:</strong> {error_type}</li>
                    <li><strong>Error Message:</strong> {error_details}</li>
                </ul>
                
                <p><strong style="color: red;">ACTION REQUIRED:</strong></p>
                <ul>
                    <li>User received analysis without being charged</li>
                    <li>Manually charge user ${credits_to_charge:.2f} or provide as free analysis</li>
                    <li>Check database and system logs for root cause</li>
                </ul>
                """,
                'TextBody': f"""
CRITICAL BILLING ERROR

Analysis completed but billing failed!

User Details:
- User ID: {user_id}
- Email: {user_email}

Analysis Details:
- ASC Standard: {asc_standard}
- Word Count: {words_count:,}
- Credits to Charge: ${credits_to_charge:.2f}

Error Details:
- Error Type: {error_type}
- Error Message: {error_details}

ACTION REQUIRED:
- User received analysis without being charged
- Manually charge user ${credits_to_charge:.2f} or provide as free analysis
- Check database and system logs for root cause
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Billing error alert sent to support for user {user_id}")
                return True
            else:
                logger.error(f"Failed to send billing error alert: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending billing error alert: {e}")
            return False
    
    def send_payment_success_notification(self, user_email: str, amount: float, 
                                         credits_added: float, payment_id: str) -> bool:
        """
        Send payment success notification to support for revenue tracking
        
        Args:
            user_email: User's email
            amount: Payment amount in dollars
            credits_added: Credits added to account
            payment_id: Stripe payment ID
            
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
                'To': 'support@veritaslogic.ai',
                'Subject': f'[PAYMENT] ${amount:.2f} - {user_email}',
                'HtmlBody': f"""
                <h2>💰 Payment Received</h2>
                
                <p><strong>Customer:</strong> {user_email}</p>
                <p><strong>Amount:</strong> ${amount:.2f}</p>
                <p><strong>Credits Added:</strong> ${credits_added:.2f}</p>
                <p><strong>Payment ID:</strong> {payment_id}</p>
                
                <p><em>Revenue tracking - No action required</em></p>
                """,
                'TextBody': f"""
Payment Received

Customer: {user_email}
Amount: ${amount:.2f}
Credits Added: ${credits_added:.2f}
Payment ID: {payment_id}

Revenue tracking - No action required
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Payment success notification sent to support for {user_email}")
                return True
            else:
                logger.error(f"Failed to send payment success notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending payment success notification: {e}")
            return False
    
    def send_payment_failure_alert(self, user_email: str, amount: float, 
                                   error_message: str, payment_intent_id: str = None) -> bool:
        """
        Send payment failure alert to support
        
        Args:
            user_email: User's email
            amount: Attempted payment amount
            error_message: Stripe error message
            payment_intent_id: Stripe payment intent ID (optional)
            
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
                'To': 'support@veritaslogic.ai',
                'Subject': f'[PAYMENT FAILED] ${amount:.2f} - {user_email}',
                'HtmlBody': f"""
                <h2>❌ Payment Failed</h2>
                
                <p><strong>Customer:</strong> {user_email}</p>
                <p><strong>Attempted Amount:</strong> ${amount:.2f}</p>
                <p><strong>Error:</strong> {error_message}</p>
                {f'<p><strong>Payment Intent ID:</strong> {payment_intent_id}</p>' if payment_intent_id else ''}
                
                <p><strong>Possible Actions:</strong></p>
                <ul>
                    <li>User may try again with different card</li>
                    <li>Check if card was declined or insufficient funds</li>
                    <li>Contact user if pattern of failures</li>
                </ul>
                """,
                'TextBody': f"""
Payment Failed

Customer: {user_email}
Attempted Amount: ${amount:.2f}
Error: {error_message}
{f'Payment Intent ID: {payment_intent_id}' if payment_intent_id else ''}

Possible Actions:
- User may try again with different card
- Check if card was declined or insufficient funds
- Contact user if pattern of failures
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Payment failure alert sent to support for {user_email}")
                return True
            else:
                logger.error(f"Failed to send payment failure alert: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending payment failure alert: {e}")
            return False
    
    def send_database_error_alert(self, operation: str, error_type: str, 
                                  error_details: str, affected_user: str = None) -> bool:
        """
        Send database error alert to support for critical system failures
        
        Args:
            operation: Database operation that failed (e.g., "user signup", "credit charge")
            error_type: Type of error
            error_details: Detailed error message
            affected_user: User email if applicable
            
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
                'To': 'support@veritaslogic.ai',
                'Subject': f'[SYSTEM ERROR] Database Failure - {operation}',
                'HtmlBody': f"""
                <h2>⚠️ Database Error</h2>
                
                <p><strong>Operation:</strong> {operation}</p>
                <p><strong>Error Type:</strong> {error_type}</p>
                {f'<p><strong>Affected User:</strong> {affected_user}</p>' if affected_user else ''}
                
                <p><strong>Error Details:</strong></p>
                <pre>{error_details}</pre>
                
                <p><strong>Action Required:</strong></p>
                <ul>
                    <li>Check database connection and status</li>
                    <li>Review recent schema changes</li>
                    <li>Check Railway/production logs</li>
                </ul>
                """,
                'TextBody': f"""
Database Error

Operation: {operation}
Error Type: {error_type}
{f'Affected User: {affected_user}' if affected_user else ''}

Error Details:
{error_details}

Action Required:
- Check database connection and status
- Review recent schema changes
- Check Railway/production logs
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Database error alert sent to support for {operation}")
                return True
            else:
                logger.error(f"Failed to send database error alert: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending database error alert: {e}")
            return False
    
    def send_demo_registration(self, name: str, email: str, company: str, role: str) -> bool:
        """
        Send demo registration notification to support
        
        Args:
            name: Registrant's full name
            email: Registrant's email
            company: Registrant's company
            role: Registrant's role
            
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
                'To': 'support@veritaslogic.ai',
                'Subject': f'Demo Registration - {name} from {company}',
                'HtmlBody': f"""
                <h2>🎯 New Demo Registration - October 29, 2025</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Company:</strong> {company}</p>
                <p><strong>Role:</strong> {role}</p>
                <hr>
                <p><em>Send calendar invite and Microsoft Teams link to {email}</em></p>
                """,
                'TextBody': f"""
New Demo Registration - October 29, 2025

Name: {name}
Email: {email}
Company: {company}
Role: {role}

Send calendar invite and Microsoft Teams link to {email}
                """
            }
            
            response = requests.post(
                f'{self.api_url}/email',
                json=email_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Demo registration notification sent for {email}")
                return True
            else:
                logger.error(f"Failed to send demo registration: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending demo registration: {e}")
            return False