import sqlite3

def add_rec_note_column():
    conn = sqlite3.connect("close_data.db")
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE monthly_balances ADD COLUMN rec_note TEXT DEFAULT ''")
        print("✅ Added column: rec_note")
    except sqlite3.OperationalError:
        print("⚠️ Column 'rec_note' already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_rec_note_column()