"""
Database migration script to add user_id column to users table.
This script safely adds the user_id column without losing existing data.
"""

import sqlite3
from datetime import datetime

DB_PATH = "leads.db"

def migrate_database():
    """Add user_id column to users table"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration...")
        print("=" * 50)
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add user_id column if it doesn't exist
        if 'user_id' not in columns:
            print("Adding 'user_id' column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN user_id VARCHAR(50) DEFAULT NULL
            """)
            
            # Create unique index on user_id
            try:
                cursor.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_user_id 
                    ON users(user_id)
                """)
                print("✓ Created unique index on user_id")
            except sqlite3.OperationalError as e:
                print(f"Note: Index creation: {e}")
            
            print("✓ Added user_id column")
        else:
            print("✓ user_id column already exists")
        
        # Commit changes
        conn.commit()
        
        print("=" * 50)
        print("✓ Migration completed successfully!")
        print("=" * 50)
        
        # Show current users
        cursor.execute("SELECT id, username, email, user_id FROM users")
        users = cursor.fetchall()
        
        print("\nCurrent users:")
        print("-" * 50)
        for user_id, username, email, uid in users:
            uid_display = uid if uid else "NULL"
            print(f"ID: {user_id}, Username: {username}, Email: {email}, User ID: {uid_display}")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()


