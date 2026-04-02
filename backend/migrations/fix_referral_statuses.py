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

# SENSITIVE: If running on AWS (not in Docker), point to the data/ folder
if not os.path.exists("/app/data") and os.path.exists(current_dir.parent / "data" / "leads.db"):
    db_path = str(current_dir.parent / "data" / "leads.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    print(f"Detected production database at: {db_path}")

from app.db import SessionLocal
from app import models

def migrate_statuses():
    print("Starting status migration for active referrals only...")
    db = SessionLocal()
    try:
        # 1. Update "Referral Sent" -> "Initial Referral Sent" (Global fix for referrals)
        count1 = db.query(models.Lead).filter(
            models.Lead.last_contact_status == "Referral Sent",
            models.Lead.active_client == True
        ).update(
            {"last_contact_status": "Initial Referral Sent"},
            synchronize_session=False
        )
        print(f"Updated {count1} active referrals from 'Referral Sent' to 'Initial Referral Sent'")

        # 2. Update legacy statuses to Initial Referral Sent ONLY for active referrals
        legacy_statuses = ["Initial Call", "Intro Call", "Follow Up", "Active"]
        count2 = db.query(models.Lead).filter(
            models.Lead.last_contact_status.in_(legacy_statuses),
            models.Lead.active_client == True
        ).update(
            {"last_contact_status": "Initial Referral Sent"},
            synchronize_session=False
        )
        print(f"Updated {count2} active referrals from {legacy_statuses} to 'Initial Referral Sent'")

        db.commit()
        print("Migration completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_statuses()
