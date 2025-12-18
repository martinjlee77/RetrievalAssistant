import sqlite3

def add_totals_columns():
    conn = sqlite3.connect("close_data.db")
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE monthly_close ADD COLUMN qbo_total_debits REAL DEFAULT 0.0")
        cursor.execute("ALTER TABLE monthly_close ADD COLUMN qbo_total_credits REAL DEFAULT 0.0")
        print("✅ Added columns: qbo_total_debits, qbo_total_credits")
    except sqlite3.OperationalError:
        print("⚠️ Columns already exist.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_totals_columns()