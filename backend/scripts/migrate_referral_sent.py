import sys
import os

# Add the backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Lead

def migrate_status():
    db = SessionLocal()
    try:
        print("Starting migration: 'Referral Sent' -> 'Initial Referral Sent'")
        
        # Update leads where last_contact_status is 'Referral Sent'
        leads_to_update = db.query(Lead).filter(Lead.last_contact_status == "Referral Sent").all()
        print(f"Found {len(leads_to_update)} leads with status 'Referral Sent'")
        
        already_updated = db.query(Lead).filter(Lead.last_contact_status == "Initial Referral Sent").count()
        print(f"Number of leads already with status 'Initial Referral Sent': {already_updated}")
        
        for lead in leads_to_update:
            lead.last_contact_status = "Initial Referral Sent"
        
        db.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"An error occurred during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_status()
