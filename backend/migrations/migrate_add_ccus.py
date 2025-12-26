"""
Add CCUs table that belongs to Payors (Agencies)
"""

import sqlite3
from datetime import datetime

DB_PATH = "leads.db"

def migrate_database():
    """Create CCUs table"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration for CCUs...")
        print("=" * 50)
        
        # 1. Create CCUs table
        print("Creating 'ccus' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ccus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL,
                agency_id INTEGER NOT NULL REFERENCES agencies(id),
                created_at DATETIME NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                updated_at DATETIME,
                updated_by VARCHAR(100),
                UNIQUE(name, agency_id)
            )
        """)
        print("✓ 'ccus' table created (or already exists)")
        
        # 2. Create index on CCU name and agency_id
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_ccus_name ON ccus (name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_ccus_agency_id ON ccus (agency_id)")
        print("✓ Indexes on CCU name and agency_id created")
        
        # 3. Add ccu_id to leads table
        # Check if column already exists
        cursor.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'ccu_id' not in columns:
            print("Adding 'ccu_id' column to leads table...")
            cursor.execute("""
                ALTER TABLE leads 
                ADD COLUMN ccu_id INTEGER REFERENCES ccus(id)
            """)
            print("✓ Added ccu_id column")
        else:
            print("✓ ccu_id column already exists")
        
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
