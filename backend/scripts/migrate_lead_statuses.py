"""
Migration Script: Update Lead Contact Statuses
================================================
Maps old status values to new ones:
  "Intro Call"  -> "Initial Call"
  "Follow Up"   -> "Initial Call"

Run this script ONCE on the AWS server (outside Docker is fine).
It is idempotent — safe to run multiple times.

Usage:
  python3 scripts/migrate_lead_statuses.py
  python3 scripts/migrate_lead_statuses.py /custom/path/to/leads.db
"""
import sys
import os
import sqlite3
from pathlib import Path

STATUS_MAPPING = {
    "Intro Call": "Initial Call",
    "Follow Up": "Initial Call",
}

def find_db():
    """Locate the database file using the same priority as db.py"""
    # Priority 1: Docker persistent volume
    if os.path.exists("/app/data/leads.db"):
        return "/app/data/leads.db"
    # Priority 2: DATABASE_URL env var (sqlite only)
    env_url = os.getenv("DATABASE_URL", "")
    if env_url.startswith("sqlite:///"):
        path = env_url.replace("sqlite:///", "")
        if os.path.exists(path):
            return path
    # Priority 3: Local leads.db next to the backend folder
    local = Path(__file__).parent.parent / "leads.db"
    if local.exists():
        return str(local)
    return None


def migrate(db_path=None):
    if db_path is None:
        db_path = find_db()

    if db_path is None:
        print("❌ Could not locate leads.db. Pass the path as an argument:")
        print("   python3 scripts/migrate_lead_statuses.py /path/to/leads.db")
        sys.exit(1)

    print(f"[DB] Using: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        total_updated = 0

        for old_status, new_status in STATUS_MAPPING.items():
            cur.execute(
                "SELECT COUNT(*) FROM leads WHERE last_contact_status = ?",
                (old_status,)
            )
            count = cur.fetchone()[0]
            if count == 0:
                print(f"[SKIP] No leads with status '{old_status}' found.")
                continue

            cur.execute(
                "UPDATE leads SET last_contact_status = ? WHERE last_contact_status = ?",
                (new_status, old_status)
            )
            conn.commit()
            total_updated += count
            print(f"[OK]   Updated {count} lead(s) from '{old_status}' -> '{new_status}'")

        if total_updated == 0:
            print("\n✅ Nothing to migrate — all leads already have the new status values.")
        else:
            print(f"\n✅ Migration complete. {total_updated} lead(s) updated in total.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    custom_path = sys.argv[1] if len(sys.argv) > 1 else None
    migrate(custom_path)

