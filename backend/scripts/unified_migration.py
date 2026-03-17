import sys
import os

# Add the backend directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Lead

def migrate_data():
    db = SessionLocal()
    try:
        print("Starting unified data migration...")
        
        # 1. Update any remaining 'Referral Sent' to 'Initial Referral Sent'
        status_to_update = db.query(Lead).filter(Lead.last_contact_status == "Referral Sent").all()
        print(f"Found {len(status_to_update)} leads with literal status 'Referral Sent'")
        for lead in status_to_update:
            lead.last_contact_status = "Initial Referral Sent"
            
        # 2. Update NULL referral types for active clients
        # We assume existing referrals without a type are 'Regular'
        from sqlalchemy import or_
        type_to_update = db.query(Lead).filter(
            Lead.active_client == True,
            or_(Lead.referral_type == None, Lead.referral_type == "")
        ).all()
        
        print(f"Found {len(type_to_update)} active clients with missing referral type.")
        for lead in type_to_update:
            lead.referral_type = "Regular"
            
        db.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"An error occurred during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
