"""
Background Worker for Close Platform QBO Sync
Handles scheduled QuickBooks Online trial balance sync jobs
"""

import logging
import sys
import os
from datetime import datetime
import calendar

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from close_platform.db_config import get_connection
from close_platform import qbo_connector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sync_qbo_trial_balance(month_id: str) -> dict:
    """
    Sync trial balance from QuickBooks Online for a given month
    This function is called by the RQ worker
    
    Args:
        month_id: Month in YYYY-MM format
        
    Returns:
        Dict with sync results
    """
    logger.info(f"Starting QBO sync for month: {month_id}")
    
    try:
        client = qbo_connector.get_active_client()
        if not client:
            return {
                'success': False,
                'error': 'QBO not connected. Please authenticate first.',
                'accounts_synced': 0,
                'new_accounts': 0
            }
        
        y, m = map(int, month_id.split('-'))
        last_day = calendar.monthrange(y, m)[1]
        end_date_str = f"{month_id}-{last_day}"
        
        qbo_data = qbo_connector.fetch_trial_balance(end_date_str)
        
        if not qbo_data:
            return {
                'success': False,
                'error': 'Failed to fetch data from QuickBooks',
                'accounts_synced': 0,
                'new_accounts': 0
            }
        
        conn = get_connection()
        cursor = conn.cursor()
        
        new_accounts_found = 0
        updated_balances = 0
        updated_names = 0
        deactivated_accounts = 0
        reactivated_accounts = 0
        
        qbo_account_nums = set(qbo_data.keys())
        
        for acct_num, details in qbo_data.items():
            name = details['name']
            bal = details['balance']
            
            cursor.execute("SELECT account_number, account_name, is_active FROM close_accounts WHERE account_number = %s", (acct_num,))
            existing = cursor.fetchone()
            
            if not existing:
                cat = 'BS' if int(acct_num) < 40000 else 'PL'
                cursor.execute(
                    "INSERT INTO close_accounts (account_number, account_name, category, permanent_link, is_active) VALUES (%s, %s, %s, '', TRUE)", 
                    (acct_num, name, cat)
                )
                new_accounts_found += 1
            else:
                if existing['account_name'] != name:
                    cursor.execute(
                        "UPDATE close_accounts SET account_name = %s WHERE account_number = %s",
                        (name, acct_num))
                    updated_names += 1
                if not existing.get('is_active', True):
                    cursor.execute(
                        "UPDATE close_accounts SET is_active = TRUE WHERE account_number = %s",
                        (acct_num,))
                    reactivated_accounts += 1
            
            cursor.execute(
                "SELECT id FROM close_monthly_balances WHERE month_id = %s AND account_number = %s", 
                (month_id, acct_num)
            )
            row = cursor.fetchone()
            
            if row:
                cursor.execute("UPDATE close_monthly_balances SET qbo_balance = %s WHERE id = %s", (bal, row['id']))
            else:
                cursor.execute(
                    "INSERT INTO close_monthly_balances (month_id, account_number, qbo_balance, status) VALUES (%s, %s, %s, 'Open')", 
                    (month_id, acct_num, bal)
                )
            updated_balances += 1
        
        cursor.execute("SELECT account_number FROM close_accounts WHERE is_active = TRUE")
        all_active = cursor.fetchall()
        for row in all_active:
            if row['account_number'] not in qbo_account_nums:
                cursor.execute(
                    "UPDATE close_accounts SET is_active = FALSE WHERE account_number = %s",
                    (row['account_number'],))
                deactivated_accounts += 1
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE close_monthly_close SET last_synced_at = %s WHERE month_id = %s", (now_str, month_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"QBO sync complete: {updated_balances} balances, {new_accounts_found} new, {updated_names} renamed, {deactivated_accounts} removed")
        
        return {
            'success': True,
            'accounts_synced': updated_balances,
            'new_accounts': new_accounts_found,
            'updated_names': updated_names,
            'deactivated_accounts': deactivated_accounts,
            'synced_at': now_str
        }
        
    except Exception as e:
        logger.error(f"QBO sync failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'accounts_synced': 0,
            'new_accounts': 0
        }


def sync_all_open_months() -> dict:
    """
    Sync trial balance for all open (non-locked) months
    Useful for scheduled daily/weekly syncs
    
    Returns:
        Dict with results for each month
    """
    logger.info("Starting batch QBO sync for all open months")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT month_id FROM close_monthly_close WHERE is_locked = FALSE ORDER BY month_id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {
            'success': True,
            'message': 'No open months to sync',
            'months_synced': 0
        }
    
    results = {}
    for row in rows:
        month_id = row['month_id']
        results[month_id] = sync_qbo_trial_balance(month_id)
    
    successful = sum(1 for r in results.values() if r.get('success'))
    
    return {
        'success': True,
        'months_synced': successful,
        'total_months': len(results),
        'details': results
    }
