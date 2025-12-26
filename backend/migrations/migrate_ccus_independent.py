"""
Make CCUs independent from Agencies - remove agency_id foreign key
"""

import sqlite3
from datetime import datetime

DB_PATH = "leads.db"

def migrate_database():
    """Remove agency_id from CCUs table to make them independent"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration to make CCUs independent...")
        print("=" * 50)
        
        # SQLite doesn't support DROP COLUMN directly, so we need to:
        # 1. Create new table without agency_id
        # 2. Copy data
        # 3. Drop old table
        # 4. Rename new table
        
        print("Creating new ccus table without agency_id...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ccus_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL UNIQUE,
                created_at DATETIME NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                updated_at DATETIME,
                updated_by VARCHAR(100)
            )
        """)
        print("✓ New ccus table structure created")
        
        # Copy data from old table (only unique CCU names)
        print("Migrating existing CCU data...")
        cursor.execute("""
            INSERT OR IGNORE INTO ccus_new (id, name, created_at, created_by, updated_at, updated_by)
            SELECT 
                MIN(id) as id,
                name,
                MIN(created_at) as created_at,
                MIN(created_by) as created_by,
                MAX(updated_at) as updated_at,
                MAX(updated_by) as updated_by
            FROM ccus
            GROUP BY name
        """)
        print("✓ Data migrated (duplicates removed)")
        
        # Update leads table to use new CCU IDs
        print("Updating leads table references...")
        cursor.execute("""
            UPDATE leads 
            SET ccu_id = (
                SELECT MIN(id) 
                FROM ccus 
                WHERE ccus.name = (SELECT name FROM ccus WHERE id = leads.ccu_id)
            )
            WHERE ccu_id IS NOT NULL
        """)
        print("✓ Lead references updated")
        
        # Drop old table
        print("Removing old ccus table...")
        cursor.execute("DROP TABLE IF EXISTS ccus")
        print("✓ Old table removed")
        
        # Rename new table
        print("Renaming new table...")
        cursor.execute("ALTER TABLE ccus_new RENAME TO ccus")
        print("✓ Table renamed")
        
        # Create index
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_ccus_name ON ccus (name)")
        print("✓ Index created")
        
        conn.commit()
        
        print("=" * 50)
        print("✓ Migration completed successfully!")
        print("✓ CCUs are now independent from Agencies")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
