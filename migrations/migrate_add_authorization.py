"""
Migration script to add authorization tracking fields to leads table.
Adds: authorization_received, care_status, soc_date
"""

import sqlite3

def migrate():
    conn = sqlite3.connect('leads.db')
    cursor = conn.cursor()
    
    # Check which columns already exist
    cursor.execute("PRAGMA table_info(leads)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Add authorization_received column if not exists
    if 'authorization_received' not in existing_columns:
        print("Adding authorization_received column...")
        cursor.execute("""
            ALTER TABLE leads 
            ADD COLUMN authorization_received BOOLEAN NOT NULL DEFAULT 0
        """)
        print(" authorization_received column added")
    else:
        print("⏭authorization_received column already exists")
    
    # Add care_status column if not exists
    if 'care_status' not in existing_columns:
        print("Adding care_status column...")
        cursor.execute("""
            ALTER TABLE leads 
            ADD COLUMN care_status VARCHAR(50) NULL
        """)
        print(" care_status column added")
    else:
        print("⏭ care_status column already exists")
    
    # Add soc_date column if not exists
    if 'soc_date' not in existing_columns:
        print("Adding soc_date column...")
        cursor.execute("""
            ALTER TABLE leads 
            ADD COLUMN soc_date DATE NULL
        """)
        print("soc_date column added")
    else:
        print("⏭soc_date column already exists")
    
    conn.commit()
    conn.close()
    print("\n Migration completed successfully!")

if __name__ == "__main__":
    migrate()
