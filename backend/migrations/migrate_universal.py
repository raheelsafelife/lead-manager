"""
Universal Migration Script: Ensures the database schema matches models.py
This script is idempotent and safe to run multiple times.
"""
import sqlite3
import os
import sys
from pathlib import Path

# Set database path
DB_PATH = "leads.db"
if not os.path.exists(DB_PATH):
    # Try alternate location if running from internal directory
    DB_PATH = "../leads.db"
    if not os.path.exists(DB_PATH):
        # Default to root-relative path if possible
        root_path = Path(__file__).parent.parent.parent
        DB_PATH = str(root_path / "leads.db")

def migrate():
    print(f"🚀 Starting Universal Migration on: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # --- USERS TABLE ---
        print("\nChecking 'users' table...")
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [info[1] for info in cursor.fetchall()]
        
        user_updates = [
            ('email', 'VARCHAR(255)'),
            ('is_approved', 'BOOLEAN DEFAULT 0'),
            ('password_reset_requested', 'BOOLEAN DEFAULT 0'),
            ('user_id', 'VARCHAR(50)')
        ]
        
        for col_name, col_type in user_updates:
            if col_name not in user_cols:
                print(f"  + Adding {col_name}...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        
        # --- LEADS TABLE ---
        print("\nChecking 'leads' table...")
        cursor.execute("PRAGMA table_info(leads)")
        lead_cols = [info[1] for info in cursor.fetchall()]
        
        lead_updates = [
            # Identity & Ownership
            ('owner_id', 'INTEGER'),
            ('created_by', 'VARCHAR(100)'),
            ('updated_by', 'VARCHAR(100)'),
            ('custom_user_id', 'VARCHAR(50)'),
            
            # Form Metadata
            ('event_name', 'VARCHAR(150)'),
            ('word_of_mouth_type', 'VARCHAR(50)'),
            ('other_source_type', 'VARCHAR(150)'),
            ('active_client', 'BOOLEAN DEFAULT 0'),
            ('referral_type', 'VARCHAR(50)'),
            
            # Relationships
            ('agency_id', 'INTEGER'),
            ('agency_suboption_id', 'INTEGER'),
            ('ccu_id', 'INTEGER'),
            ('mco_id', 'INTEGER'),
            
            # Status & Dates
            ('authorization_received', 'BOOLEAN DEFAULT 0'),
            ('care_status', 'VARCHAR(50)'),
            ('soc_date', 'DATE'),
            ('dob', 'DATE'),
            ('priority', 'VARCHAR(50) DEFAULT "Medium"'),
            
            # Contact Info
            ('street', 'VARCHAR(255)'),
            ('city', 'VARCHAR(100)'),
            ('state', 'VARCHAR(2)'),
            ('zip_code', 'VARCHAR(20)'),
            ('email', 'VARCHAR(255)'),
            ('ssn', 'VARCHAR(50)'),
            
            # Emergency Contact
            ('e_contact_name', 'VARCHAR(150)'),
            ('e_contact_relation', 'VARCHAR(100)'),
            ('e_contact_phone', 'VARCHAR(50)'),
            
            # SafeLife CCP Specific
            ('relation_to_client', 'VARCHAR(100)'),
            ('medicaid_status', 'VARCHAR(10)'),
            ('address', 'TEXT'),
            
            # Soft Delete
            ('deleted_at', 'DATETIME'),
            ('deleted_by', 'VARCHAR(100)')
        ]
        
        for col_name, col_type in lead_updates:
            if col_name not in lead_cols:
                print(f"  + Adding {col_name} ({col_type})...")
                cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")

        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
