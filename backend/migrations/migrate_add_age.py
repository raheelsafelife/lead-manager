import sqlite3
import os

def migrate():
    db_path = "leads.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'age' not in columns:
            print("Adding 'age' column to leads table...")
            cursor.execute("ALTER TABLE leads ADD COLUMN age INTEGER")
            conn.commit()
            print("Successfully added 'age' column.")
        else:
            print("'age' column already exists.")
            
        # Data migration: Rename source
        print("Migrating source names from 'External Referral' to 'Direct Through CCU'...")
        cursor.execute("UPDATE leads SET source = 'Direct Through CCU' WHERE source = 'External Referral'")
        conn.commit()
        print(f"Source names updated. Rows affected: {cursor.rowcount}")
            
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
