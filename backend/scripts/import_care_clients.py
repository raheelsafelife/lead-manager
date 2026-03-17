"""
import_care_clients.py
─────────────────────
Imports clients from clients_export.csv into the Lead Manager authorization
page.

Rules
-----
- Dedup  : Compare by Chart-ID first, then Name+DOB, then Name alone.
           Never create a duplicate entry.
- Status mapping (CSV Status → internal care_status):
      Active     → care_status = "Care Start"     active_client = True
      Hold       → care_status = "Hold"            active_client = True
      Deceased   → care_status = "Deceased"        active_client = False
      everything else (Terminated, Canceled, Leave …)
                 → care_status = "Terminated"      active_client = False
- All imported / updated records get  authorization_received = True.

Usage (local)
-------------
  python backend/scripts/import_care_clients.py clients_export.csv          # dry-run
  python backend/scripts/import_care_clients.py clients_export.csv --commit # write to DB

Usage (AWS Docker - run inside the running dashboard container)
--------------------------------------------------------------
  # 1. Copy CSV into container
  docker cp clients_export.csv lead-manager-dashboard-1:/app/clients_export.csv

  # 2. Run inside container
  docker exec lead-manager-dashboard-1 \\
      python3 /app/backend/scripts/import_care_clients.py \\
      /app/clients_export.csv --commit
"""

import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# ── path setup ──────────────────────────────────────────────────────────────
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

# Honour AWS persistent-volume DB (Docker mounts /app/data)
data_db = Path("/app/data/leads.db")
if data_db.exists():
    os.environ["DATABASE_URL"] = f"sqlite:///{data_db}"

from sqlalchemy import func
from app.db import SessionLocal
from app.models import Lead, ActivityLog

# ── status mapping ───────────────────────────────────────────────────────────
STATUS_MAP = {
    "active":   ("Care Start",  True),
    "hold":     ("Hold",        True),
    "deceased": ("Deceased",    False),
}

def map_status(raw_status: str):
    """Return (care_status, active_client) for a given CSV Status value."""
    key = (raw_status or "").strip().lower()
    return STATUS_MAP.get(key, ("Terminated", False))  # default → terminated


# ── CSV parsing ──────────────────────────────────────────────────────────────
def parse_date(s: str):
    s = s.strip()
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def load_csv(csv_path: str):
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            name = raw.get("Name", "").strip()
            if not name:
                continue

            # Split "LAST, FIRST"  or  "First Last …"
            if "," in name:
                last, first = name.split(",", 1)
            else:
                parts = name.split()
                first = parts[0]
                last  = " ".join(parts[1:]) if len(parts) > 1 else ""

            rows.append({
                "chart_id":   raw.get("Chart ID", "").strip(),
                "first_name": first.strip(),
                "last_name":  last.strip(),
                "dob":        parse_date(raw.get("DOB", "")),
                "status":     raw.get("Status", "").strip(),
                "supervisor": raw.get("Supervisor", "").strip(),
                "location":   raw.get("Location", "").strip(),
                "payor":      raw.get("Payor", "").strip(),
                "soc":        parse_date(raw.get("SOC", "")),
                "eoc":        parse_date(raw.get("EOC", "")),
            })
    return rows


# ── matching helpers ─────────────────────────────────────────────────────────
def find_existing(db, client: dict):
    """
    Try three strategies in order:
      1. chart_id  (custom_user_id)
      2. first+last+DOB  (or swapped)
      3. first+last only (if DB has no DOB)
    Returns the first alive Lead that matches, or None.
    """
    base = db.query(Lead).filter(Lead.deleted_at == None)

    # 1. Chart ID
    if client["chart_id"]:
        m = base.filter(Lead.custom_user_id == client["chart_id"]).first()
        if m:
            return m

    fn = client["first_name"].lower()
    ln = client["last_name"].lower()

    # 2. Name + DOB
    if client["dob"]:
        m = base.filter(
            func.lower(Lead.first_name) == fn,
            func.lower(Lead.last_name)  == ln,
            Lead.dob == client["dob"],
        ).first()
        if m:
            return m
        # swapped
        m = base.filter(
            func.lower(Lead.first_name) == ln,
            func.lower(Lead.last_name)  == fn,
            Lead.dob == client["dob"],
        ).first()
        if m:
            return m

    # 3. Name only (when DB has no DOB)
    candidates = base.filter(
        Lead.dob == None
    ).filter(
        (
            (func.lower(Lead.first_name) == fn) &
            (func.lower(Lead.last_name)  == ln)
        ) | (
            (func.lower(Lead.first_name) == ln) &
            (func.lower(Lead.last_name)  == fn)
        )
    ).all()

    if len(candidates) == 1:
        return candidates[0]

    return None


# ── main sync ────────────────────────────────────────────────────────────────
def run_import(csv_path: str, dry_run: bool = True):
    db = SessionLocal()
    tag = "[DRY RUN]" if dry_run else "[COMMIT]"
    print(f"\n{tag} Importing from: {csv_path}\n")

    try:
        clients = load_csv(csv_path)
        print(f"Loaded {len(clients)} clients from CSV.\n")

        created  = 0
        updated  = 0
        skipped  = 0

        for c in clients:
            care_status, active_client = map_status(c["status"])
            display_name = f"{c['first_name']} {c['last_name']}".strip()
            chart_label  = f"[Chart {c['chart_id']}]" if c["chart_id"] else ""

            match = find_existing(db, c)

            if match:
                # ── UPDATE existing lead ──────────────────────────────────
                changed = []

                if not match.authorization_received:
                    match.authorization_received = True
                    changed.append("authorization_received=True")

                if match.care_status != care_status:
                    old = match.care_status
                    match.care_status = care_status
                    changed.append(f"care_status: {old!r} → {care_status!r}")

                if match.active_client != active_client:
                    match.active_client = active_client
                    changed.append(f"active_client={active_client}")

                if match.dob is None and c["dob"] is not None:
                    match.dob = c["dob"]
                    changed.append(f"dob={c['dob']}")

                if not match.custom_user_id and c["chart_id"]:
                    match.custom_user_id = c["chart_id"]
                    changed.append(f"chart_id={c['chart_id']}")

                if match.soc_date is None and c["soc"] is not None:
                    match.soc_date = c["soc"]
                    changed.append(f"soc_date={c['soc']}")

                if changed:
                    print(f"  UPDATE  ID {match.id:5d}  {display_name} {chart_label}")
                    for ch in changed:
                        print(f"            → {ch}")
                    if not dry_run:
                        log = ActivityLog(
                            username="system_import",
                            action_type="UPDATE",
                            entity_type="Lead",
                            entity_id=match.id,
                            entity_name=display_name,
                            description=(
                                f"Authorization import: {'; '.join(changed)}. "
                                f"CSV status={c['status']!r}"
                            ),
                        )
                        db.add(log)
                    updated += 1
                else:
                    print(f"  SKIP    ID {match.id:5d}  {display_name} {chart_label}  (no changes)")
                    skipped += 1

            else:
                # ── CREATE new lead ───────────────────────────────────────
                print(f"  CREATE  {display_name} {chart_label}  status={c['status']!r} → {care_status!r}")
                if not dry_run:
                    new_lead = Lead(
                        first_name           = c["first_name"],
                        last_name            = c["last_name"],
                        dob                  = c["dob"],
                        custom_user_id       = c["chart_id"] or None,
                        staff_name           = c["supervisor"] or "System Import",
                        source               = "Imported from Client Export",
                        phone                = "000-000-0000",
                        street               = c["location"] or None,
                        active_client        = active_client,
                        authorization_received = True,
                        care_status          = care_status,
                        priority             = "Not Called",
                        created_by           = "system_import",
                        soc_date             = c["soc"],
                    )
                    db.add(new_lead)
                    db.flush()

                    log = ActivityLog(
                        username    = "system_import",
                        action_type = "CREATE",
                        entity_type = "Lead",
                        entity_id   = new_lead.id,
                        entity_name = display_name,
                        description = (
                            f"Auto-created via CSV import. "
                            f"CSV status={c['status']!r} → {care_status!r}. "
                            f"Payor={c['payor']!r}."
                        ),
                    )
                    db.add(log)
                created += 1

        # ── commit ────────────────────────────────────────────────────────
        if not dry_run:
            db.commit()
            print("\n✅  Import committed to database.")
        else:
            print("\n⚠️   Dry-run only — no changes written. Re-run with --commit to apply.")

        print(f"\n─── Summary ───────────────────────────────")
        print(f"  Total CSV rows : {len(clients)}")
        print(f"  Created        : {created}")
        print(f"  Updated        : {updated}")
        print(f"  Skipped (same) : {skipped}")
        print(f"───────────────────────────────────────────\n")

    except Exception as exc:
        db.rollback()
        print(f"\n❌  Error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


# ── entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_care_clients.py <path/to/clients_export.csv> [--commit]")
        sys.exit(1)

    csv_file = sys.argv[1]
    commit   = "--commit" in sys.argv
    run_import(csv_file, dry_run=not commit)
