"""
Migration: Targeted Status Standardization
Updates "Referral Sent" and legacy referral statuses to "Initial Referral Sent"
ONLY for active referrals (active_client=True).
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

def migrate_referrals():
    print("Starting targeted status standardization for REFERRALS ONLY...")
    db = SessionLocal()
    try:
        # Target "Referral Sent" and "Initial Call" for ACTIVE referrals
        legacy_statuses = ["Referral Sent", "Initial Call", "Intro Call", "Follow Up"]
        
        count = db.query(models.Lead).filter(
            models.Lead.last_contact_status.in_(legacy_statuses),
            models.Lead.active_client == True
        ).update(
            {"last_contact_status": "Initial Referral Sent"},
            synchronize_session=False
        )
        print(f"Successfully updated {count} active referrals to 'Initial Referral Sent'")

        db.commit()
        print("Standardization completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during standardization: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_referrals()
