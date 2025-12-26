"""
Add password_reset_requested field to users table
"""

import sqlite3

DB_PATH = "leads.db"

def migrate_database():
    """Add password_reset_requested column to users table"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration...")
        print("=" * 50)
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'password_reset_requested' not in columns:
            print("Adding 'password_reset_requested' column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN password_reset_requested BOOLEAN DEFAULT 0 NOT NULL
            """)
            
            affected = cursor.rowcount
            print(f"✓ Added password_reset_requested column")
        else:
            print("✓ password_reset_requested column already exists")
        
        conn.commit()
        
        print("=" * 50)
        print("✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
