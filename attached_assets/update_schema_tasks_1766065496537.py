import sqlite3

def update_schema():
    conn = sqlite3.connect("close_data.db")
    cursor = conn.cursor()

    # 1. Add instructions_link to tasks
    try:
        cursor.execute("ALTER TABLE monthly_tasks ADD COLUMN instructions_link TEXT DEFAULT ''")
        print("✅ Added column: instructions_link")
    except sqlite3.OperationalError:
        print("⚠️ Column 'instructions_link' already exists.")

    # 2. Add last_synced_at to monthly metadata
    try:
        cursor.execute("ALTER TABLE monthly_close ADD COLUMN last_synced_at TEXT DEFAULT NULL")
        print("✅ Added column: last_synced_at")
    except sqlite3.OperationalError:
        print("⚠️ Column 'last_synced_at' already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_schema()