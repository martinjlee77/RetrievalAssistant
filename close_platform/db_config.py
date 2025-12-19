import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def init_close_tables():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS close_accounts (
        account_number TEXT PRIMARY KEY,
        account_name TEXT NOT NULL,
        category TEXT,
        permanent_link TEXT DEFAULT '',
        is_active BOOLEAN DEFAULT TRUE
    );
    """)
    
    cursor.execute("""
    ALTER TABLE close_accounts ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS close_checklist_template (
        id SERIAL PRIMARY KEY,
        phase TEXT,
        task_name TEXT,
        day_due INTEGER,
        default_owner TEXT
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS close_monthly_close (
        month_id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'Open',
        is_locked BOOLEAN DEFAULT FALSE,
        variance_threshold_pct REAL DEFAULT 10.0,
        variance_threshold_amt REAL DEFAULT 5000.0,
        qbo_total_debits REAL DEFAULT 0.0,
        qbo_total_credits REAL DEFAULT 0.0,
        qbo_net_income REAL DEFAULT 0.0,
        last_synced_at TIMESTAMP
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS close_monthly_balances (
        id SERIAL PRIMARY KEY,
        month_id TEXT REFERENCES close_monthly_close(month_id),
        account_number TEXT REFERENCES close_accounts(account_number),
        qbo_balance REAL DEFAULT 0.0,
        expected_balance REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Open',
        variance_note TEXT DEFAULT '',
        rec_note TEXT DEFAULT ''
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS close_monthly_tasks (
        id SERIAL PRIMARY KEY,
        month_id TEXT REFERENCES close_monthly_close(month_id),
        task_name TEXT,
        phase TEXT,
        day_due INTEGER,
        owner TEXT,
        instructions_link TEXT DEFAULT '',
        status TEXT DEFAULT 'Pending'
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS close_qbo_tokens (
        id SERIAL PRIMARY KEY,
        realm_id TEXT,
        access_token TEXT,
        refresh_token TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()
    return True
