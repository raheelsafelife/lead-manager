"""
Migration: Safe Revert AWS Statuses
Restores "Initial Call" for all non-referral leads (active_client=False)
that were accidentally updated to "Initial Referral Sent".
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

def safe_revert():
    print("Starting safe status reversal for regular leads...")
    db = SessionLocal()
    try:
        # Restore "Initial Call" for non-referrals
        # We target "Initial Referral Sent" because that's what the previous script wrote.
        count = db.query(models.Lead).filter(
            models.Lead.last_contact_status == "Initial Referral Sent",
            models.Lead.active_client == False
        ).update(
            {"last_contact_status": "Initial Call"},
            synchronize_session=False
        )
        print(f"Successfully restored {count} regular leads to 'Initial Call'")

        db.commit()
        print("Cleanup completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    safe_revert()
