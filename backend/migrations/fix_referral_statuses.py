"""
Migration: Standardize Referral Statuses
Unifies "Referral Sent" and "Initial Call" into "Initial Referral Sent"
"""
import sys
import os
from pathlib import Path

# Add backend to Python path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from app.db import SessionLocal
from app import models

def migrate_statuses():
    print("Starting status migration...")
    db = SessionLocal()
    try:
        # 1. Update "Referral Sent" -> "Initial Referral Sent"
        count1 = db.query(models.Lead).filter(models.Lead.last_contact_status == "Referral Sent").update(
            {"last_contact_status": "Initial Referral Sent"},
            synchronize_session=False
        )
        print(f"Updated {count1} leads from 'Referral Sent' to 'Initial Referral Sent'")

        # 2. Update "Initial Call", "Intro Call", "Follow Up", "Active" -> "Initial Referral Sent"
        legacy_statuses = ["Initial Call", "Intro Call", "Follow Up", "Active"]
        count2 = db.query(models.Lead).filter(models.Lead.last_contact_status.in_(legacy_statuses)).update(
            {"last_contact_status": "Initial Referral Sent"},
            synchronize_session=False
        )
        print(f"Updated {count2} leads from {legacy_statuses} to 'Initial Referral Sent'")

        db.commit()
        print("Migration completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_statuses()
