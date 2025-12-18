import sqlite3

def add_token_table():
    conn = sqlite3.connect("close_data.db")
    cursor = conn.cursor()

    # Create table for QBO Auth Tokens
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qbo_tokens (
        id INTEGER PRIMARY KEY,
        realm_id TEXT,
        access_token TEXT,
        refresh_token TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("Database schema updated with qbo_tokens table.")

if __name__ == "__main__":
    add_token_table()