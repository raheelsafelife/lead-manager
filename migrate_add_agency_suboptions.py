"""
Add agency_suboptions table and agency_suboption_id to leads table
"""

import sqlite3
from datetime import datetime

DB_PATH = "leads.db"

def migrate_database():
    """Create agency_suboptions table and add agency_suboption_id to leads"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration for Agency Suboptions...")
        print("=" * 50)
        
        # 1. Create agency_suboptions table
        print("Creating 'agency_suboptions' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agency_suboptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL,
                agency_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                updated_at DATETIME,
                updated_by VARCHAR(100),
                FOREIGN KEY (agency_id) REFERENCES agencies(id)
            )
        """)
        print("✓ 'agency_suboptions' table created (or already exists)")
        
        # 2. Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_agency_suboptions_name ON agency_suboptions (name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_agency_suboptions_agency_id ON agency_suboptions (agency_id)")
        print("✓ Indexes created")
        
        # 3. Add agency_suboption_id to leads table
        cursor.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'agency_suboption_id' not in columns:
            print("Adding 'agency_suboption_id' column to leads table...")
            cursor.execute("""
                ALTER TABLE leads 
                ADD COLUMN agency_suboption_id INTEGER REFERENCES agency_suboptions(id)
            """)
            print("✓ Added agency_suboption_id column")
        else:
            print("✓ agency_suboption_id column already exists")
        
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
