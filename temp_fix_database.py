#!/usr/bin/env python3
"""
Temporary script to fix Railway database schema
Run this once to add the missing verified_at column
"""

import os
import psycopg2

def fix_database():
    """Add missing verified_at column to Railway database"""
    
    # Use Railway's DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found. Make sure you're running this in Railway or with DATABASE_URL set.")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Add missing column
        cursor.execute("""
            ALTER TABLE email_verification_tokens 
            ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;
        """)
        
        # Verify column exists
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'email_verification_tokens' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("✅ Current email_verification_tokens columns:")
        for col_name, data_type in columns:
            print(f"   - {col_name}: {data_type}")
        
        conn.commit()
        conn.close()
        
        print("✅ Database fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database fix failed: {e}")
        return False

if __name__ == "__main__":
    fix_database()