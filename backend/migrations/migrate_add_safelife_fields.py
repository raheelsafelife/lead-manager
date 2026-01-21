"""
Database migration to add fields for SafeLife CCP Form integration
Adds: relation_to_client, age, medicaid_status, address fields, ssn, email
"""
from sqlalchemy import text
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db import SessionLocal

def migrate_add_safelife_fields():
    """
    Add new fields to the leads table for SafeLife CCP Form:
    - relation_to_client: varchar (relationship of form submitter to client)
    - age: integer (client's age if birthdate unknown)
    - medicaid_status: varchar ("yes" or "no")
    - address: text (full address from form)
    - state: varchar (2-letter state code)
    - ssn: varchar (social security number) 
    - email: varchar (client's email address)
    """
    db = SessionLocal()
    
    try:
        # Check if fields already exist
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        # Add relation_to_client if not exists
        if 'relation_to_client' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN relation_to_client VARCHAR(100)"))
            print("[OK] Added column: relation_to_client")
        
        # Add age if not exists
        if 'age' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN age INTEGER"))
            print("[OK] Added column: age")
        
        # Add medicaid_status if not exists
        if 'medicaid_status' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN medicaid_status VARCHAR(10)"))
            print("[OK] Added column: medicaid_status")
        
        # Add address if not exists
        if 'address' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN address TEXT"))
            print("[OK] Added column: address")
        
        # Add street if not exists
        if 'street' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN street VARCHAR(255)"))
            print("[OK] Added column: street")
        
        # Add state if not exists
        if 'state' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN state VARCHAR(2)"))
            print("[OK] Added column: state")
        
        # Add ssn if not exists (already exists, but checking)
        if 'ssn' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN ssn VARCHAR(50)"))
            print("[OK] Added column: ssn")
        
        # Add email if not exists (already exists, but checking)
        if 'email' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN email VARCHAR(255)"))
            print("[OK] Added column: email")
        
        db.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        print("New fields added for SafeLife CCP Form integration")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Running migration: Add SafeLife CCP Form fields...")
    migrate_add_safelife_fields()
