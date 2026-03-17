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
        
        print(f"Found {len(logs)} recovery logs.")
        
        reverted = 0
        deleted = 0
        
        for log in logs:
            lead = db.query(Lead).filter(Lead.id == log.entity_id).first()
            if not lead:
                continue
                
            # Extract the old status from the log description
            # E.g. "Authorization removed: Not present in CSV export. Previous status='Care Start'"
            desc = log.description
            old_status = None
            if "Previous status=" in desc:
                parts = desc.split("Previous status=")
                if len(parts) > 1:
                    old_status = parts[1].strip("'\" ")
            
            # Restore authorization
            lead.authorization_received = True
            if old_status and old_status != 'None':
                lead.care_status = old_status
            
            # Revert active_client based on status
            if old_status in ["Care Start", "Hold", "Not Start"]:
                lead.active_client = True
            
            print(f"Recovering ID {lead.id}: {lead.first_name} {lead.last_name} -> {old_status}")
            
            # If it was active, move to delete box
            if old_status == "Care Start" or old_status == "Active":
                lead.deleted_at = datetime.now(pytz.utc)
                print(f"  -> Moving to Delete Box")
                deleted += 1
            
            db.add(ActivityLog(
                username="system_recovery",
                action_type="UPDATE",
                entity_type="Lead",
                entity_id=lead.id,
                entity_name=f"{lead.first_name} {lead.last_name}",
                description=f"Reverted accidental auth removal. Restored to status={old_status}"
            ))
            
            reverted += 1
            
        print(f"\nSummary:")
        print(f"  Total Reverted: {reverted}")
        print(f"  Total Deleted:  {deleted}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    recover()
