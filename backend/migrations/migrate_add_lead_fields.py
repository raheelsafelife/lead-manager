"""
Migration script to add ssn, email, and custom_user_id columns to leads table.
"""
import sqlite3
import os

DB_FILE = "leads.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found!")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(leads)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Add custom_user_id
        if 'custom_user_id' not in columns:
            print("Adding custom_user_id column...")
            cursor.execute("ALTER TABLE leads ADD COLUMN custom_user_id VARCHAR(50)")
        else:
            print("custom_user_id column already exists.")
            
        # Add ssn
        if 'ssn' not in columns:
            print("Adding ssn column...")
            cursor.execute("ALTER TABLE leads ADD COLUMN ssn VARCHAR(50)")
        else:
            print("ssn column already exists.")

        # Add email
        if 'email' not in columns:
            print("Adding email column...")
            cursor.execute("ALTER TABLE leads ADD COLUMN email VARCHAR(255)")
        else:
            print("email column already exists.")

        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
