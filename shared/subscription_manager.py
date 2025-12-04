"""
Subscription Manager Service for VeritasLogic
Handles word allowance tracking, rollover logic, and usage management
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import os
import logging

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manages subscription word allowances, usage tracking, and rollover logic
    """
    
    def __init__(self, conn=None):
        """
        Initialize subscription manager
        
        Args:
            conn: Optional database connection. If None, creates new connection.
        """
        self.conn = conn
        self.owns_connection = False
        
        if self.conn is None:
            self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
            self.owns_connection = True
    
    def __del__(self):
        """Close connection if we own it"""
        if self.owns_connection and self.conn:
            self.conn.close()
    
    def get_org_subscription(self, org_id):
        """
        Get active subscription for organization
        
        Args:
            org_id (int): Organization ID
            
        Returns:
            dict: Subscription details or None if no active subscription
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    si.*,
                    sp.plan_key,
                    sp.name as plan_name,
                    sp.price_monthly,
                    sp.word_allowance,
                    sp.seats
                FROM subscription_instances si
                JOIN subscription_plans sp ON si.plan_id = sp.id
                WHERE si.org_id = %s 
                AND si.status IN ('active', 'trial', 'past_due', 'cancelled')
                ORDER BY 
                    CASE si.status 
                        WHEN 'active' THEN 1 
                        WHEN 'trial' THEN 2 
                        WHEN 'past_due' THEN 3 
                        WHEN 'cancelled' THEN 4 
                    END,
                    si.created_at DESC
                LIMIT 1
            """, (org_id,))
            return cur.fetchone()
    
    def get_current_usage(self, org_id):
        """
        Get current month's usage for organization
        
        Args:
            org_id (int): Organization ID
            
        Returns:
            dict: Usage stats with available words, used words, rollover
        """
        subscription = self.get_org_subscription(org_id)
        if not subscription:
            return {
                'has_subscription': False,
                'word_allowance': 0,
                'rollover_words': 0,
                'words_used': 0,
                'words_available': 0,
                'status': 'no_subscription'
            }
        
        # Get or create current month's usage record
        current_month_start = date.today().replace(day=1)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get current month usage
            cur.execute("""
                SELECT * FROM subscription_usage
                WHERE org_id = %s 
                AND subscription_id = %s
                AND month_start = %s
            """, (org_id, subscription['id'], current_month_start))
            
            usage = cur.fetchone()
            
            # If no usage record for this month, create it
            if not usage:
                usage = self._create_usage_record(
                    org_id, 
                    subscription['id'], 
                    subscription['word_allowance'],
                    current_month_start
                )
                if self.owns_connection:
                    self.conn.commit()
            
            # Calculate total rollover from ledger
            cur.execute("""
                SELECT COALESCE(SUM(amount_remaining), 0) as total_rollover
                FROM rollover_ledger
                WHERE org_id = %s
                AND expires_at > NOW()
            """, (org_id,))
            
            rollover_result = cur.fetchone()
            rollover_words = rollover_result['total_rollover'] if rollover_result else 0
            
            # Calculate available words
            total_allowance = usage['word_allowance'] + rollover_words
            words_used = usage['words_used']
            words_available = max(0, total_allowance - words_used)
            
            return {
                'has_subscription': True,
                'subscription_status': subscription['status'],
                'plan_name': subscription['plan_name'],
                'plan_key': subscription['plan_key'],
                'word_allowance': usage['word_allowance'],
                'rollover_words': rollover_words,
                'words_used': words_used,
                'words_available': words_available,
                'current_period_end': subscription['current_period_end'],
                'cancel_at_period_end': subscription['cancel_at_period_end'],
                'is_trial': subscription['status'] == 'trial',
                'trial_end_date': subscription['trial_end_date']
            }
    
    def check_word_allowance(self, org_id, words_needed):
        """
        Check if organization has enough words for an analysis
        
        Args:
            org_id (int): Organization ID
            words_needed (int): Number of words required
            
        Returns:
            dict: {'allowed': bool, 'reason': str, 'words_available': int, 'upgrade_needed': bool}
        """
        usage = self.get_current_usage(org_id)
        
        if not usage['has_subscription']:
            return {
                'allowed': False,
                'reason': 'No active subscription. Start your 14-day free trial to continue.',
                'words_available': 0,
                'upgrade_needed': True,
                'suggested_action': 'start_trial'
            }
        
        # Check if subscription is cancelled and period has expired
        if usage['subscription_status'] == 'cancelled':
            period_end = usage.get('current_period_end')
            if period_end:
                # Handle both datetime and date objects
                if hasattr(period_end, 'date'):
                    period_end_date = period_end.date()
                else:
                    period_end_date = period_end
                
                if date.today() > period_end_date:
                    return {
                        'allowed': False,
                        'reason': 'Your subscription has expired. Please resubscribe to continue using the platform.',
                        'words_available': 0,
                        'upgrade_needed': True,
                        'suggested_action': 'resubscribe'
                    }
            # If within the cancelled period, allow usage with remaining words
            logger.info(f"Cancelled subscription for org {org_id} still within access period")
        
        if usage['subscription_status'] == 'past_due':
            return {
                'allowed': False,
                'reason': 'Subscription payment past due. Please update your payment method.',
                'words_available': 0,
                'upgrade_needed': False,
                'suggested_action': 'update_payment'
            }
        
        if words_needed > usage['words_available']:
            return {
                'allowed': False,
                'reason': f"Insufficient word allowance. You have {usage['words_available']:,} words available, but need {words_needed:,} words.",
                'words_available': usage['words_available'],
                'words_needed': words_needed,
                'upgrade_needed': True,
                'suggested_action': 'upgrade_plan',
                'current_plan': usage['plan_key']
            }
        
        return {
            'allowed': True,
            'reason': 'Sufficient allowance available',
            'words_available': usage['words_available'],
            'words_needed': words_needed,
            'words_remaining_after': usage['words_available'] - words_needed
        }
    
    def deduct_words(self, org_id, words_used, analysis_id):
        """
        Deduct words from organization's allowance (current month + rollover)
        
        Args:
            org_id (int): Organization ID
            words_used (int): Number of words to deduct
            analysis_id (int): Analysis ID for audit trail
            
        Returns:
            dict: Deduction result with breakdown
        """
        subscription = self.get_org_subscription(org_id)
        if not subscription:
            raise ValueError("No active subscription found")
        
        current_month_start = date.today().replace(day=1)
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get current usage
                cur.execute("""
                    SELECT * FROM subscription_usage
                    WHERE org_id = %s 
                    AND subscription_id = %s
                    AND month_start = %s
                    FOR UPDATE
                """, (org_id, subscription['id'], current_month_start))
                
                usage = cur.fetchone()
                if not usage:
                    raise ValueError("Usage record not found")
                
                # Strategy: Deduct from current month allowance first, then rollover
                remaining_to_deduct = words_used
                words_from_allowance = 0
                words_from_rollover = 0
                
                # Step 1: Deduct from current month allowance
                current_month_available = usage['word_allowance'] - usage['words_used']
                
                if current_month_available > 0:
                    words_from_allowance = min(remaining_to_deduct, current_month_available)
                    remaining_to_deduct -= words_from_allowance
                
                # Step 2: Deduct from rollover (FIFO - oldest expiring first)
                if remaining_to_deduct > 0:
                    cur.execute("""
                        SELECT * FROM rollover_ledger
                        WHERE org_id = %s
                        AND amount_remaining > 0
                        AND expires_at > NOW()
                        ORDER BY expires_at ASC
                        FOR UPDATE
                    """, (org_id,))
                    
                    rollover_entries = cur.fetchall()
                    
                    for entry in rollover_entries:
                        if remaining_to_deduct <= 0:
                            break
                        
                        deduct_from_entry = min(remaining_to_deduct, entry['amount_remaining'])
                        
                        # Update rollover ledger entry
                        cur.execute("""
                            UPDATE rollover_ledger
                            SET amount_remaining = amount_remaining - %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (deduct_from_entry, entry['id']))
                        
                        words_from_rollover += deduct_from_entry
                        remaining_to_deduct -= deduct_from_entry
                
                if remaining_to_deduct > 0:
                    if self.owns_connection:
                        self.conn.rollback()
                    raise ValueError(f"Insufficient words. Short by {remaining_to_deduct} words.")
                
                # Update usage record - ONLY track words from base allowance
                # Rollover consumption is already tracked in rollover_ledger
                cur.execute("""
                    UPDATE subscription_usage
                    SET words_used = words_used + %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (words_from_allowance, usage['id']))
                
                # Log the deduction in analyses table (already done in analysis_worker)
                
                if self.owns_connection:
                    self.conn.commit()
                
                logger.info(f"Deducted {words_used} words from org {org_id}: {words_from_allowance} from allowance, {words_from_rollover} from rollover")
                
                return {
                    'success': True,
                    'words_deducted': words_used,
                    'from_allowance': words_from_allowance,
                    'from_rollover': words_from_rollover,
                    'analysis_id': analysis_id
                }
        except Exception as e:
            if self.owns_connection:
                self.conn.rollback()
            logger.error(f"Error deducting words for org {org_id}: {e}")
            raise
    
    def _create_usage_record(self, org_id, subscription_id, word_allowance, month_start):
        """
        Create usage record for a new month
        
        Args:
            org_id (int): Organization ID
            subscription_id (int): Subscription instance ID
            word_allowance (int): Monthly word allowance
            month_start (date): First day of month
            
        Returns:
            dict: Created usage record
        """
        # Calculate month end (last day of month)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO subscription_usage (
                    org_id, subscription_id, month_start, month_end,
                    word_allowance, words_used
                )
                VALUES (%s, %s, %s, %s, %s, 0)
                RETURNING *
            """, (org_id, subscription_id, month_start, month_end, word_allowance))
            
            return cur.fetchone()
    
    def reset_monthly_allowance(self, org_id):
        """
        Reset monthly word allowance and calculate rollover
        Called by scheduled job at month end
        
        Args:
            org_id (int): Organization ID
            
        Returns:
            dict: Reset details with rollover amount
        """
        subscription = self.get_org_subscription(org_id)
        if not subscription:
            logger.warning(f"No active subscription for org {org_id} - skipping reset")
            return {'success': False, 'reason': 'no_subscription'}
        
        # Get last month's usage
        last_month_start = (date.today().replace(day=1) - relativedelta(months=1))
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM subscription_usage
                WHERE org_id = %s
                AND subscription_id = %s
                AND month_start = %s
            """, (org_id, subscription['id'], last_month_start))
            
            last_month_usage = cur.fetchone()
            
            if last_month_usage:
                # Calculate unused words from last month
                unused_words = max(0, last_month_usage['word_allowance'] - last_month_usage['words_used'])
                
                if unused_words > 0:
                    # Add to rollover ledger with 12-month expiration
                    expires_at = datetime.now() + relativedelta(months=12)
                    
                    cur.execute("""
                        INSERT INTO rollover_ledger (
                            org_id, subscription_id, grant_month,
                            amount_granted, amount_remaining, expires_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        org_id, subscription['id'], last_month_start,
                        unused_words, unused_words, expires_at
                    ))
                    
                    logger.info(f"Added {unused_words} words to rollover for org {org_id}, expires {expires_at}")
            
            # Clean up expired rollover entries
            cur.execute("""
                DELETE FROM rollover_ledger
                WHERE org_id = %s
                AND expires_at < NOW()
            """, (org_id,))
            
            expired_count = cur.rowcount
            
            # Create new month's usage record
            current_month_start = date.today().replace(day=1)
            new_usage = self._create_usage_record(
                org_id,
                subscription['id'],
                subscription['word_allowance'],
                current_month_start
            )
            
            if self.owns_connection:
                self.conn.commit()
            
            unused_words = 0
            if last_month_usage:
                unused_words = max(0, last_month_usage['word_allowance'] - last_month_usage['words_used'])
            
            return {
                'success': True,
                'org_id': org_id,
                'unused_words_rolled_over': unused_words,
                'expired_entries_removed': expired_count,
                'new_month_allowance': subscription['word_allowance']
            }
    
    def create_trial_subscription(self, org_id, plan_key='professional', stripe_subscription_id=None, payment_method_id=None, customer_email=None):
        """
        Create a new trial subscription for organization
        
        Args:
            org_id (int): Organization ID
            plan_key (str): Plan to trial (default: professional)
            stripe_subscription_id (str): Stripe subscription ID if created externally
            payment_method_id (str): Stripe payment method ID to attach
            customer_email (str): Customer email for Stripe customer creation
            
        Returns:
            dict: Created subscription details
        """
        import stripe
        import os
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get plan details
            cur.execute("""
                SELECT * FROM subscription_plans
                WHERE plan_key = %s AND is_active = true
            """, (plan_key,))
            
            plan = cur.fetchone()
            if not plan:
                raise ValueError(f"Plan {plan_key} not found")
            
            # Check for existing active subscription
            cur.execute("""
                SELECT * FROM subscription_instances
                WHERE org_id = %s
                AND status IN ('active', 'trial', 'past_due')
            """, (org_id,))
            
            if cur.fetchone():
                raise ValueError("Organization already has an active subscription")
            
            # Create Stripe customer and subscription if payment method provided
            stripe_customer_id = None
            if payment_method_id and customer_email:
                try:
                    # Create Stripe customer
                    customer = stripe.Customer.create(
                        email=customer_email,
                        payment_method=payment_method_id,
                        invoice_settings={'default_payment_method': payment_method_id},
                        metadata={'org_id': org_id}
                    )
                    stripe_customer_id = customer.id
                    logger.info(f"Created Stripe customer {stripe_customer_id} for org {org_id}")
                    
                    # Create Stripe subscription with trial
                    subscription = stripe.Subscription.create(
                        customer=stripe_customer_id,
                        items=[{'price': plan['stripe_price_id']}],
                        trial_period_days=14,
                        metadata={
                            'org_id': org_id,
                            'plan_key': plan_key
                        }
                    )
                    stripe_subscription_id = subscription.id
                    logger.info(f"Created Stripe subscription {stripe_subscription_id} with 14-day trial")
                    
                    # Store stripe_customer_id in organizations table
                    cur.execute("""
                        UPDATE organizations 
                        SET stripe_customer_id = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (stripe_customer_id, org_id))
                    
                except stripe.error.StripeError as e:
                    logger.error(f"Stripe error creating customer/subscription: {e}")
                    raise ValueError(f"Payment setup failed: {str(e)}")
            
            # Create trial subscription
            trial_start = datetime.now()
            trial_end = trial_start + timedelta(days=14)
            
            cur.execute("""
                INSERT INTO subscription_instances (
                    org_id, plan_id, stripe_subscription_id, status,
                    trial_start_date, trial_end_date,
                    current_period_start, current_period_end,
                    cancel_at_period_end
                )
                VALUES (%s, %s, %s, 'trial', %s, %s, %s, %s, false)
                RETURNING *
            """, (
                org_id, plan['id'], stripe_subscription_id,
                trial_start, trial_end, trial_start, trial_end
            ))
            
            subscription = cur.fetchone()
            
            # Create initial usage record with trial allowance (9K words)
            from shared.pricing_config import TRIAL_CONFIG
            trial_allowance = TRIAL_CONFIG['word_allowance']
            
            current_month_start = date.today().replace(day=1)
            self._create_usage_record(
                org_id,
                subscription['id'],
                trial_allowance,
                current_month_start
            )
            
            if self.owns_connection:
                self.conn.commit()
            
            logger.info(f"Created trial subscription for org {org_id}: {trial_allowance} words")
            
            return {
                'success': True,
                'subscription_id': subscription['id'],
                'status': 'trial',
                'trial_end_date': trial_end,
                'word_allowance': trial_allowance
            }
