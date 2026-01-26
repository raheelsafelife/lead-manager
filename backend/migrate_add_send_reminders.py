import sqlite3
import os

def migrate():
    # Try multiple common paths
    possible_paths = [
        "backend/leads.db",
        "data/leads.db",
        "leads.db",
        "/app/data/leads.db"
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "send_reminders" not in columns:
            print("Adding 'send_reminders' column to 'leads' table...")
            cursor.execute("ALTER TABLE leads ADD COLUMN send_reminders BOOLEAN NOT NULL DEFAULT 1")
            conn.commit()
            print("Migration successful: Added 'send_reminders' column.")
        else:
            print("Column 'send_reminders' already exists in 'leads' table.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
