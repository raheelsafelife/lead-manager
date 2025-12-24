import sqlite3
import os

DB_PATH = "leads.db"

def clean_leads():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print(f"Cleaning database: {DB_PATH}")
        print("=" * 50)

        # 1. Clear email_reminders (depends on leads)
        cursor.execute("DELETE FROM email_reminders")
        print(f"[OK] Removed all records from 'email_reminders' ({cursor.rowcount} rows)")

        # 2. Clear activity_logs (audit trail related to leads)
        cursor.execute("DELETE FROM activity_logs")
        print(f"[OK] Removed all records from 'activity_logs' ({cursor.rowcount} rows)")

        # 3. Clear leads
        cursor.execute("DELETE FROM leads")
        print(f"[OK] Removed all records from 'leads' ({cursor.rowcount} rows)")

        # Reset SQLite sequences (so IDs start from 1 again)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('leads', 'email_reminders', 'activity_logs')")
        
        conn.commit()
        print("=" * 50)
        print("[SUCCESS] Database cleaned successfully! All leads and logs are gone.")
        print("[SUCCESS] User accounts and configuration (Agencies, CCUs, etc.) were preserved.")

    except Exception as e:
        print(f"[ERROR] Error cleaning database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # Check if we should clear other tables too
    # For now, just leads and logs as requested.
    clean_leads()
