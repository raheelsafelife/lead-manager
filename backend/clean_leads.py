
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# The script is now in the 'backend' folder.
# We can import app directly as long as 'backend' is in sys.path or we are running from it.
# Inside Docker, PYTHONPATH is set to /app/backend.

from app.db import SessionLocal
import app.models as models

def get_priority_score(lead):
    """
    Priority hierarchy:
    1. Auth Received (authorization_received == True) -> Score 2
    2. Mark Referral (active_client == True) -> Score 1
    3. Lead (Default) -> Score 0
    """
    if lead.authorization_received:
        return 2
    if lead.active_client:
        return 1
    return 0

def clean_leads(apply_changes=False):
    db = SessionLocal()
    try:
        # Fetch all non-deleted leads
        leads = db.query(models.Lead).filter(models.Lead.deleted_at == None).all()
        print(f"Total active leads found: {len(leads)}")

        # Group leads by first_name, last_name, phone
        groups = defaultdict(list)
        for lead in leads:
            key = (
                (lead.first_name or "").strip().lower(),
                (lead.last_name or "").strip().lower(),
                (lead.phone or "").strip()
            )
            groups[key].append(lead)

        to_delete = []
        kept_count = 0
        
        for key, group in groups.items():
            if len(group) <= 1:
                kept_count += 1
                continue

            # Sort by priority score (desc) and updated_at (desc)
            # We want the highest priority first, then the most recently updated
            sorted_group = sorted(
                group,
                key=lambda x: (get_priority_score(x), x.updated_at or datetime.min),
                reverse=True
            )

            keep = sorted_group[0]
            others = sorted_group[1:]
            
            print(f"\nDuplicate group found: {key}")
            print(f"  KEEP: ID {keep.id} | Score {get_priority_score(keep)} | Updated {keep.updated_at}")
            
            for other in others:
                print(f"  DELETE: ID {other.id} | Score {get_priority_score(other)} | Updated {other.updated_at}")
                to_delete.append(other)
            
            kept_count += 1

        print(f"\nSummary:")
        print(f"Total Groups: {len(groups)}")
        print(f"Leads to Keep: {kept_count}")
        print(f"Leads to Delete: {len(to_delete)}")

        if not to_delete:
            print("No redundant leads found.")
            return

        if apply_changes:
            print("\nApplying changes...")
            for lead in to_delete:
                lead.deleted_at = datetime.utcnow()
                lead.deleted_by = "system_cleanup"
            db.commit()
            print("Changes committed to database.")
        else:
            print("\nDRY RUN: No changes applied. Use --apply to mark leads as deleted.")

    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean redundant leads from the database.")
    parser.add_argument("--apply", action="store_true", help="Apply changes (soft delete duplicates)")
    
    args = parser.parse_args()
    
    clean_leads(apply_changes=args.apply)
