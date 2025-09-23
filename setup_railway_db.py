#!/usr/bin/env python3
"""
VeritasLogic Railway Database Setup Script

This script creates all necessary database tables for the VeritasLogic platform
on your Railway PostgreSQL database. Run this once after adding PostgreSQL to Railway.

Usage:
    python setup_railway_db.py

Requirements:
    - Railway PostgreSQL service added and running
    - DATABASE_URL environment variable set (automatically provided by Railway)
"""

import os
import sys
import psycopg2
from pathlib import Path

def get_db_connection():
    """Get database connection using Railway environment variables"""
    try:
        # Railway automatically provides DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            print("❌ ERROR: DATABASE_URL environment variable not found!")
            print("Make sure you've added PostgreSQL to your Railway project.")
            return None
        
        print(f"🔗 Connecting to Railway PostgreSQL database...")
        conn = psycopg2.connect(database_url)
        print("✅ Database connection successful!")
        return conn
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def run_sql_script():
    """Run the SQL setup script"""
    
    # Get database connection
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        # Read the SQL script
        sql_file = Path("setup_railway_database.sql")
        if not sql_file.exists():
            print(f"❌ SQL script not found: {sql_file}")
            print("Make sure setup_railway_database.sql is in the same directory.")
            return False
        
        print("📄 Reading SQL setup script...")
        sql_content = sql_file.read_text()
        
        # Execute the SQL script
        print("🔨 Creating database tables...")
        cursor = conn.cursor()
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Database setup completed successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        if tables:
            print(f"📊 Created tables:")
            for table in tables:
                print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Your VeritasLogic database is ready!")
        print("Your Flask and Streamlit apps can now connect to the database.")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def main():
    """Main function"""
    print("=== VeritasLogic Railway Database Setup ===\n")
    
    # Check if DATABASE_URL is available
    if not os.environ.get('DATABASE_URL'):
        print("❌ DATABASE_URL not found in environment variables.")
        print("\nTo run this script:")
        print("1. Make sure you've added PostgreSQL to your Railway project")
        print("2. Run this script from Railway (it has DATABASE_URL automatically)")
        print("3. Or run locally with: railway run python setup_railway_db.py")
        sys.exit(1)
    
    # Run the setup
    success = run_sql_script()
    
    if success:
        print("\n✅ Database setup complete! Your apps are ready to use the database.")
        sys.exit(0)
    else:
        print("\n❌ Database setup failed. Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()