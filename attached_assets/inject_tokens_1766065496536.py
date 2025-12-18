import sqlite3

# --- PASTE VALUES FROM INTUIT PLAYGROUND BELOW ---
REALM_ID = "9130352978475756" 
ACCESS_TOKEN = "eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwieC5vcmciOiJIMCJ9" 
REFRESH_TOKEN = "RT1-144-H0-1773589494oeqce4juri8lb18zg5ey" 

def inject():
    conn = sqlite3.connect("close_data.db")
    cursor = conn.cursor()

    # 1. Create the table if it doesn't exist (Fixes your error)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qbo_tokens (
        id INTEGER PRIMARY KEY,
        realm_id TEXT,
        access_token TEXT,
        refresh_token TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Clear old tokens
    cursor.execute("DELETE FROM qbo_tokens")

    # 3. Insert new manual tokens
    cursor.execute("""
        INSERT INTO qbo_tokens (realm_id, access_token, refresh_token)
        VALUES (?, ?, ?)
    """, (REALM_ID, ACCESS_TOKEN, REFRESH_TOKEN))

    conn.commit()
    conn.close()
    print("✅ Table created & tokens injected successfully.")

if __name__ == "__main__":
    inject()