import sys
import os
from pathlib import Path
from datetime import datetime
import pytz

backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

data_db = Path("/app/data/leads.db")
if data_db.exists():
    os.environ["DATABASE_URL"] = f"sqlite:///{data_db}"

from sqlalchemy import func
from app.db import SessionLocal
from app.models import Lead, ActivityLog

def recover():
    db = SessionLocal()
    try:
        # Find the logs from the "system_import" cleanup we just ran
        # looking for "Authorization removed: Not present in CSV export"
        logs = db.query(ActivityLog).filter(
            ActivityLog.action_type == "UPDATE",
            ActivityLog.description.like("Authorization removed: Not present in CSV%")
        ).all()
        
        # Also check for any manual DELETES from today just in case
        today = datetime.now(pytz.utc).date()
        manual_deletes = db.query(ActivityLog).filter(
            ActivityLog.action_type == "DELETE",
            func.date(ActivityLog.timestamp) == today
        ).all()
        
        reverted = 0
        deleted = 0
        
        if manual_deletes:
            print(f"Found {len(manual_deletes)} manual deletes from today.")
            for log in manual_deletes:
                lead = db.query(Lead).filter(Lead.id == log.entity_id).first()
                if lead and not lead.authorization_received:
                    lead.authorization_received = True
                    print(f"  RE-AUTHORIZED Deleted Lead: {lead.first_name} {lead.last_name} (ID: {lead.id})")
                    reverted += 1
        
        print(f"Processing {len(logs)} recovery logs from sync cleanup...")
        
        
        for log in logs:
            lead = db.query(Lead).filter(Lead.id == log.entity_id).first()
            if not lead:
                continue
                
            # Extract the old status from the log description
            desc = log.description
            old_status = None
            if "Previous status=" in desc:
                parts = desc.split("Previous status=")
                if len(parts) > 1:
                    old_status = parts[1].strip("'\" ")
            
            # 1. Restore authorization and status
            lead.authorization_received = True
            if old_status and old_status != 'None':
                lead.care_status = old_status
            
            # 2. Revert active_client based on status
            if old_status in ["Care Start", "Hold", "Not Start", "Transfer Received"]:
                lead.active_client = True
            
            # 3. MOVE TO RECYCLE BIN (Soft Delete) - The user wants ALL of these in the recycle bin
            lead.deleted_at = datetime.now(pytz.utc)
            
            print(f"Recovering & Deleting ID {lead.id}: {lead.first_name} {lead.last_name} -> {old_status}")
            
            db.add(ActivityLog(
                username="system_recovery",
                action_type="UPDATE",
                entity_type="Lead",
                entity_id=lead.id,
                entity_name=f"{lead.first_name} {lead.last_name}",
                description=f"Recovered auth (status={old_status}) and moved to Recycle Bin per user request."
            ))
            
            reverted += 1
            deleted += 1
        
        db.commit()
        print(f"\nSummary:")
        print(f"  Total Reverted & Moved to Recycle Bin: {reverted}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    recover()
