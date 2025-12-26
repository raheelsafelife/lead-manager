"""
Add agencies table and agency_id to leads table
"""

import sqlite3
from datetime import datetime

DB_PATH = "leads.db"

def migrate_database():
    """Create agencies table and add agency_id to leads"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration for Agencies...")
        print("=" * 50)
        
        # 1. Create agencies table
        print("Creating 'agencies' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL UNIQUE,
                created_at DATETIME NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                updated_at DATETIME,
                updated_by VARCHAR(100)
            )
        """)
        print("✓ 'agencies' table created (or already exists)")
        
        # 2. Create index on agency name
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_agencies_name ON agencies (name)")
        print("✓ Index on agency name created")
        
        # 3. Add agency_id to leads table
        # Check if column already exists
        cursor.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'agency_id' not in columns:
            print("Adding 'agency_id' column to leads table...")
            cursor.execute("""
                ALTER TABLE leads 
                ADD COLUMN agency_id INTEGER REFERENCES agencies(id)
            """)
            print("✓ Added agency_id column")
        else:
            print("✓ agency_id column already exists")
        
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
