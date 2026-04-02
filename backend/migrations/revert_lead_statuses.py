"""
Migration: Revert Lead Statuses in View Leads
Changes "Initial Referral Sent" back to "Initial Call" ONLY for non-referrals (active_client=False)
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

def revert_lead_statuses():
    print("Starting status reversal for View Leads (non-referrals)...")
    db = SessionLocal()
    try:
        # Update "Initial Referral Sent" -> "Initial Call" for non-active clients
        count = db.query(models.Lead).filter(
            models.Lead.last_contact_status == "Initial Referral Sent",
            models.Lead.active_client == False
        ).update(
            {"last_contact_status": "Initial Call"},
            synchronize_session=False
        )
        print(f"Successfully reverted {count} leads back to 'Initial Call'")

        db.commit()
        print("Reversal completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during reversal: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    revert_lead_statuses()
