"""
Migrate database to add new lead tracking fields and rename active_hh to active_client
"""

import sqlite3

DB_PATH = "leads.db"

def migrate_database():
    """Add new fields and rename active_hh column"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting database migration...")
        print("=" * 60)
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(leads)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        # Add event_name if not exists
        if 'event_name' not in columns:
            print("Adding 'event_name' column...")
            cursor.execute("ALTER TABLE leads ADD COLUMN event_name VARCHAR(150) DEFAULT NULL")
            print("✓ Added event_name column")
        else:
            print("✓ event_name column already exists")
        
        # Add word_of_mouth_type if not exists
        if 'word_of_mouth_type' not in columns:
            print("Adding 'word_of_mouth_type' column...")
            cursor.execute("ALTER TABLE leads ADD COLUMN word_of_mouth_type VARCHAR(50) DEFAULT NULL")
            print("✓ Added word_of_mouth_type column")
        else:
            print("✓ word_of_mouth_type column already exists")
        
        # Add other_source_type if not exists
        if 'other_source_type' not in columns:
            print("Adding 'other_source_type' column...")
            cursor.execute("ALTER TABLE leads ADD COLUMN other_source_type VARCHAR(150) DEFAULT NULL")
            print("✓ Added other_source_type column")
        else:
            print("✓ other_source_type column already exists")
        
        # Rename active_hh to active_client
        if 'active_hh' in columns and 'active_client' not in columns:
            print("Renaming 'active_hh' to 'active_client'...")
            
            # SQLite doesn't support RENAME COLUMN directly in older versions
            # We need to use ALTER TABLE ... RENAME COLUMN (supported in SQLite 3.25+)
            try:
                cursor.execute("ALTER TABLE leads RENAME COLUMN active_hh TO active_client")
                print("✓ Renamed active_hh to active_client")
            except Exception as e:
                print(f"Note: Could not rename column directly: {e}")
                print("Trying alternative method...")
                
                # Alternative: Add new column and copy data
                cursor.execute("ALTER TABLE leads ADD COLUMN active_client BOOLEAN DEFAULT 0 NOT NULL")
                cursor.execute("UPDATE leads SET active_client = active_hh")
                print("✓ Created active_client and copied data from active_hh")
                print("Note: Old active_hh column still exists but is no longer used")
        elif 'active_client' in columns:
            print("✓ active_client column already exists")
        else:
            print("✓ active_hh already renamed or active_client exists")
        
        conn.commit()
        
        print("=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        
        # Show sample of updated schema
        cursor.execute("PRAGMA table_info(leads)")
        print("\nUpdated Lead table columns:")
        for col in cursor.fetchall():
            print(f"  - {col[1]} ({col[2]})")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
