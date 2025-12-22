"""
Database migration script to add email and is_approved columns to existing users table.
This script safely adds new columns without losing existing data.
"""

import sqlite3
from datetime import datetime

DB_PATH = "leads.db"

def migrate_database():
    """Add email and is_approved columns to users table"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration...")
        print("=" * 50)
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add email column if it doesn't exist
        if 'email' not in columns:
            print("Adding 'email' column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN email VARCHAR(255) DEFAULT NULL
            """)
            
            # Update existing users with placeholder emails
            cursor.execute("SELECT id, username FROM users")
            users = cursor.fetchall()
            
            for user_id, username in users:
                placeholder_email = f"{username}@placeholder.local"
                cursor.execute(
                    "UPDATE users SET email = ? WHERE id = ?",
                    (placeholder_email, user_id)
                )
            
            print(f"✓ Added email column and updated {len(users)} existing users")
        else:
            print("✓ Email column already exists")
        
        # Add is_approved column if it doesn't exist
        if 'is_approved' not in columns:
            print("Adding 'is_approved' column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN is_approved BOOLEAN DEFAULT 0 NOT NULL
            """)
            
            # Approve all existing users (they were created before the approval system)
            cursor.execute("UPDATE users SET is_approved = 1")
            affected = cursor.rowcount
            
            print(f"✓ Added is_approved column and approved {affected} existing users")
        else:
            print("✓ is_approved column already exists")
        
        # Commit changes
        conn.commit()
        
        print("=" * 50)
        print("✓ Migration completed successfully!")
        print("=" * 50)
        
        # Show current users
        cursor.execute("SELECT id, username, email, is_approved FROM users")
        users = cursor.fetchall()
        
        print("\nCurrent users:")
        print("-" * 50)
        for user_id, username, email, is_approved in users:
            status = "✓ Approved" if is_approved else "⏳ Pending"
            print(f"ID: {user_id}, Username: {username}, Email: {email}, Status: {status}")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
