"""
Migration Script: Update Lead Contact Statuses
================================================
Maps old status values to new ones:
  "Intro Call"  -> "Initial Call"
  "Follow Up"   -> "Initial Call"

Run this script ONCE on the AWS database.
It is idempotent — safe to run multiple times.
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.models import Lead

STATUS_MAPPING = {
    "Intro Call": "Initial Call",
    "Follow Up": "Initial Call",
}


def migrate():
    db = SessionLocal()
    try:
        total_updated = 0

        for old_status, new_status in STATUS_MAPPING.items():
            leads_to_update = (
                db.query(Lead)
                .filter(Lead.last_contact_status == old_status)
                .all()
            )
            count = len(leads_to_update)
            if count == 0:
                print(f"[SKIP] No leads with status '{old_status}' found.")
                continue

            for lead in leads_to_update:
                lead.last_contact_status = new_status

            db.commit()
            total_updated += count
            print(f"[OK]   Updated {count} lead(s) from '{old_status}' -> '{new_status}'")

        if total_updated == 0:
            print("\n✅ Nothing to migrate — all leads already have the new status values.")
        else:
            print(f"\n✅ Migration complete. {total_updated} lead(s) updated in total.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
