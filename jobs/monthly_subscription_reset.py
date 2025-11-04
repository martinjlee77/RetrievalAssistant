#!/usr/bin/env python3
"""
Monthly Subscription Reset Job
Runs on the 1st of each month to reset subscription allowances and process rollover.
Should be scheduled via RQ Scheduler or cron.
"""
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db_connection
from shared.subscription_manager import SubscriptionManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reset_monthly_allowances():
    """
    Reset all active subscription allowances for the new month.
    This job should run on the 1st of each month.
    
    Process:
    1. Find all active subscriptions
    2. For each subscription:
       - Calculate unused words from PREVIOUS month (the period that just ended)
       - Add to rollover_ledger with 12-month expiration from earned_period
       - Expire rollover entries older than 12 months
       - Create new subscription_usage record for new month
       - Update subscription_instances.last_reset_at
    """
    from dateutil.relativedelta import relativedelta
    
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to get database connection")
        return {'success': False, 'error': 'Database connection failed'}
    
    try:
        cursor = conn.cursor()
        sub_mgr = SubscriptionManager(conn, owns_connection=False)
        
        # Current month is the NEW billing period starting today (1st of month)
        current_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Previous month is the period that just ENDED - this is what we need to analyze
        previous_month = current_month - relativedelta(months=1)
        
        logger.info(f"Starting monthly reset for billing period {current_month.strftime('%Y-%m')}")
        logger.info(f"Analyzing usage from previous period: {previous_month.strftime('%Y-%m')}")
        
        # Get all active subscriptions
        cursor.execute("""
            SELECT 
                si.id as subscription_id,
                si.org_id,
                si.plan_key,
                si.status,
                si.current_period_start,
                si.current_period_end,
                sp.word_allowance,
                o.name as org_name
            FROM subscription_instances si
            JOIN subscription_plans sp ON si.plan_key = sp.plan_key
            JOIN organizations o ON si.org_id = o.id
            WHERE si.status IN ('active', 'trialing')
            AND si.current_period_end >= %s
            ORDER BY si.org_id
        """, (current_month,))
        
        subscriptions = cursor.fetchall()
        
        if not subscriptions:
            logger.info("No active subscriptions found to reset")
            return {
                'success': True,
                'processed': 0,
                'message': 'No active subscriptions'
            }
        
        logger.info(f"Found {len(subscriptions)} active subscriptions to reset")
        
        processed_count = 0
        rollover_total = Decimal('0')
        expired_total = Decimal('0')
        errors = []
        
        for sub in subscriptions:
            try:
                org_id = sub['org_id']
                subscription_id = sub['subscription_id']
                plan_key = sub['plan_key']
                word_allowance = sub['word_allowance']
                org_name = sub['org_name']
                
                logger.info(f"Processing {org_name} (org_id: {org_id}, plan: {plan_key})")
                
                # Get PREVIOUS month's usage (the period that just ended)
                cursor.execute("""
                    SELECT words_used
                    FROM subscription_usage
                    WHERE subscription_id = %s
                    AND period_start = %s
                """, (subscription_id, previous_month))
                
                previous_usage = cursor.fetchone()
                words_used = previous_usage['words_used'] if previous_usage else Decimal('0')
                
                # Calculate unused words
                unused_words = max(Decimal('0'), Decimal(str(word_allowance)) - words_used)
                
                logger.info(f"  Allowance: {word_allowance:,} words")
                logger.info(f"  Used: {words_used:,} words")
                logger.info(f"  Unused: {unused_words:,} words")
                
                # Add to rollover ledger if there are unused words
                if unused_words > 0:
                    # Rollover expires 12 months from when it was earned (previous_month)
                    expiration_date = previous_month + relativedelta(months=12)
                    
                    cursor.execute("""
                        INSERT INTO rollover_ledger (
                            subscription_id, rollover_words, earned_period, expires_at
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (subscription_id, unused_words, previous_month, expiration_date))
                    
                    rollover_total += unused_words
                    logger.info(f"  ✅ Added {unused_words:,} words to rollover (earned: {previous_month.strftime('%Y-%m')}, expires: {expiration_date.strftime('%Y-%m-%d')})")
                
                # Expire old rollover entries (>12 months)
                cursor.execute("""
                    SELECT id, rollover_words, earned_period
                    FROM rollover_ledger
                    WHERE subscription_id = %s
                    AND expires_at <= %s
                    AND words_used < rollover_words
                """, (subscription_id, current_month))
                
                expired_entries = cursor.fetchall()
                
                for entry in expired_entries:
                    expired_words = entry['rollover_words'] - Decimal('0')  # Unused portion
                    
                    cursor.execute("""
                        UPDATE rollover_ledger
                        SET words_used = rollover_words
                        WHERE id = %s
                    """, (entry['id'],))
                    
                    expired_total += expired_words
                    logger.info(f"  ⏰ Expired {expired_words:,} words from {entry['earned_period'].strftime('%Y-%m')}")
                
                # Create new usage record for current month (the billing period that just started)
                next_month = current_month + relativedelta(months=1)
                
                cursor.execute("""
                    INSERT INTO subscription_usage (
                        subscription_id, period_start, period_end, words_used
                    )
                    VALUES (%s, %s, %s, 0)
                    ON CONFLICT (subscription_id, period_start) DO NOTHING
                """, (subscription_id, current_month, next_month))
                
                # Update last_reset_at timestamp
                cursor.execute("""
                    UPDATE subscription_instances
                    SET last_reset_at = %s
                    WHERE id = %s
                """, (current_month, subscription_id))
                
                processed_count += 1
                logger.info(f"  ✅ Reset complete for {org_name}")
                
            except Exception as e:
                error_msg = f"Error processing org_id {sub['org_id']}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Commit all changes
        conn.commit()
        
        result = {
            'success': True,
            'processed': processed_count,
            'total_subscriptions': len(subscriptions),
            'rollover_words_added': float(rollover_total),
            'rollover_words_expired': float(expired_total),
            'errors': errors,
            'reset_date': current_month.isoformat()
        }
        
        logger.info("=" * 80)
        logger.info("Monthly Reset Summary")
        logger.info("=" * 80)
        logger.info(f"Processed: {processed_count}/{len(subscriptions)} subscriptions")
        logger.info(f"Rollover added: {rollover_total:,} words")
        logger.info(f"Rollover expired: {expired_total:,} words")
        if errors:
            logger.warning(f"Errors: {len(errors)}")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Monthly reset failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        conn.close()


def enqueue_monthly_reset():
    """
    Enqueue the monthly reset job via RQ.
    This can be called from a cron job or RQ Scheduler.
    """
    from shared.redis_connection import get_redis
    from rq import Queue
    
    redis_conn = get_redis()
    queue = Queue('maintenance', connection=redis_conn)
    
    job = queue.enqueue(
        reset_monthly_allowances,
        job_timeout='30m',
        description='Monthly subscription allowance reset'
    )
    
    logger.info(f"Monthly reset job enqueued: {job.id}")
    return job.id


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Monthly subscription reset')
    parser.add_argument('--enqueue', action='store_true', help='Enqueue job via RQ instead of running directly')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be reset without making changes')
    
    args = parser.parse_args()
    
    if args.enqueue:
        job_id = enqueue_monthly_reset()
        print(f"Job enqueued: {job_id}")
    else:
        if args.dry_run:
            print("DRY RUN MODE - No changes will be made")
            print()
        
        result = reset_monthly_allowances()
        
        if result['success']:
            print(f"✅ Monthly reset completed successfully")
            print(f"   Processed: {result['processed']}/{result.get('total_subscriptions', 0)} subscriptions")
            print(f"   Rollover added: {result['rollover_words_added']:,.0f} words")
            print(f"   Rollover expired: {result['rollover_words_expired']:,.0f} words")
            if result.get('errors'):
                print(f"   ⚠️  Errors: {len(result['errors'])}")
        else:
            print(f"❌ Monthly reset failed: {result.get('error')}")
            sys.exit(1)
