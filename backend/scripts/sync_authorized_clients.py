import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.models import Lead, ActivityLog
from sqlalchemy import func

def sync_clients(csv_path: str, dry_run: bool = True):
    db = SessionLocal()
    print(f"{' [DRY RUN]' if dry_run else ''} Starting sync from {csv_path}")
    
    try:
        # 1. Load CSV Data
        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found at {csv_path}")
            return

        csv_clients = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Basic cleaning
                name = row['Name'].strip()
                if not name: continue
                
                # Split name (assuming 'First Last' or 'LAST, FIRST')
                if ',' in name:
                    last, first = name.split(',', 1)
                else:
                    parts = name.split()
                    first = parts[0]
                    last = ' '.join(parts[1:]) if len(parts) > 1 else ""
                
                dob_str = row['DOB'].strip()
                try:
                    dob = datetime.strptime(dob_str, '%m/%d/%Y').date() if dob_str else None
                except ValueError:
                    dob = None
                
                soc_str = row.get('SOC', '').strip()
                try:
                    soc = datetime.strptime(soc_str, '%m/%d/%Y').date() if soc_str else None
                except ValueError:
                    soc = None

                csv_clients.append({
                    'first_name': first.strip(),
                    'last_name': last.strip(),
                    'dob': dob,
                    'chart_id': row.get('Chart ID', '').strip(),
                    'supervisor': row.get('Supervisor', '').strip(),
                    'location': row.get('Location', '').strip(),
                    'soc': soc
                })

        print(f"Loaded {len(csv_clients)} clients from CSV.")

        # 2. De-duplication Logic
        print("\n--- Phase 1: De-duplication (DB Cleanup) ---")
        all_leads = db.query(Lead).filter(Lead.deleted_at == None).all()
        leads_by_key = {}
        for lead in all_leads:
            key = (lead.first_name.lower().strip(), lead.last_name.lower().strip(), lead.dob)
            if key not in leads_by_key:
                leads_by_key[key] = []
            leads_by_key[key].append(lead)
        
        duplicates_removed = 0
        for key, leads in leads_by_key.items():
            if len(leads) > 1:
                # Keep the one with the highest ID (latest)
                leads.sort(key=lambda l: l.id, reverse=True)
                keep = leads[0]
                to_delete = leads[1:]
                
                print(f"Duplicate found for {key[0]} {key[1]} ({key[2]}): Keeping ID {keep.id}, deleting { [l.id for l in to_delete] }")
                for l in to_delete:
                    if not dry_run:
                        l.deleted_at = datetime.utcnow()
                        l.deleted_by = "system_dedup"
                        
                        # Log activity
                        log = ActivityLog(
                            username="system",
                            action_type="DELETE",
                            entity_type="Lead",
                            entity_id=l.id,
                            entity_name=f"{l.first_name} {l.last_name}",
                            description=f"Auto-deleted duplicate lead during sync. Kept ID {keep.id}."
                        )
                        db.add(log)
                    duplicates_removed += 1

        # 3. Synchronization Logic
        print("\n--- Phase 2: Create or Update from CSV ---")
        updates_made = 0
        leads_created = 0
        found_lead_ids = set()
        
        for client in csv_clients:
            # Flexible matching: Try name + DOB, or Name alone if DOB missing in DB
            match = None
            
            # 1. Try exact match (First Last + DOB)
            match = db.query(Lead).filter(
                func.lower(Lead.first_name) == client['first_name'].lower(),
                func.lower(Lead.last_name) == client['last_name'].lower(),
                Lead.dob == client['dob'],
                Lead.deleted_at == None
            ).first()
            
            # 2. Try swapped match (Last First + DOB)
            if not match:
                match = db.query(Lead).filter(
                    func.lower(Lead.first_name) == client['last_name'].lower(),
                    func.lower(Lead.last_name) == client['first_name'].lower(),
                    Lead.dob == client['dob'],
                    Lead.deleted_at == None
                ).first()
            
            # 3. Try match without DOB if DB has no DOB
            if not match:
                potential_matches = db.query(Lead).filter(
                    Lead.deleted_at == None,
                    Lead.dob == None
                ).filter(
                    (
                        (func.lower(Lead.first_name) == client['first_name'].lower()) & 
                        (func.lower(Lead.last_name) == client['last_name'].lower())
                    ) | (
                        (func.lower(Lead.first_name) == client['last_name'].lower()) & 
                        (func.lower(Lead.last_name) == client['first_name'].lower())
                    )
                ).all()
                if len(potential_matches) == 1:
                    match = potential_matches[0]
            
            if match:
                found_lead_ids.add(match.id)
                needs_update = not match.authorization_received or match.care_status != "Care Start" or not match.active_client or (match.dob is None and client['dob'] is not None)
                
                if needs_update:
                    print(f"Updating status for ID {match.id}: {match.first_name} {match.last_name} -> AUTHORIZED")
                    if not dry_run:
                        match.authorization_received = True
                        match.care_status = "Care Start"
                        match.active_client = True
                        if match.dob is None:
                            match.dob = client['dob']
                        
                        # Log activity
                        log = ActivityLog(
                            username="system",
                            action_type="UPDATE",
                            entity_type="Lead",
                            entity_id=match.id,
                            entity_name=f"{match.first_name} {match.last_name}",
                            description="Auto-authorized and synchronized via client export."
                        )
                        db.add(log)
                    updates_made += 1
            else:
                # Auto-create lead
                print(f"CREATING NEW lead for: {client['first_name']} {client['last_name']} ({client['dob']})")
                if not dry_run:
                    new_lead = Lead(
                        first_name=client['first_name'],
                        last_name=client['last_name'],
                        dob=client['dob'],
                        custom_user_id=client['chart_id'],
                        staff_name=client.get('supervisor', 'System'),
                        source="Imported from Client Export",
                        phone="000-000-0000",
                        street=client.get('location', 'Unknown'),
                        active_client=True,
                        authorization_received=True,
                        care_status="Care Start",
                        priority="Medium",
                        created_by="system",
                        soc_date=client.get('soc')
                    )
                    db.add(new_lead)
                    db.flush() 
                    found_lead_ids.add(new_lead.id)
                    
                    log = ActivityLog(
                        username="system",
                        action_type="CREATE",
                        entity_type="Lead",
                        entity_id=new_lead.id,
                        entity_name=f"{new_lead.first_name} {new_lead.last_name}",
                        description="Auto-created lead from client export import."
                    )
                    db.add(log)
                leads_created += 1

        # 4. Inactive Logic
        print("\n--- Phase 3: Marking missing records as Inactive ---")
        inactives_marked = 0
        confirmed_leads = db.query(Lead).filter(
            Lead.active_client == True,
            Lead.authorization_received == True,
            Lead.deleted_at == None
        ).all()
        
        for lead in confirmed_leads:
            if lead.id not in found_lead_ids:
                print(f"Marking ID {lead.id} as INACTIVE: {lead.first_name} {lead.last_name} (Missing from export)")
                if not dry_run:
                    lead.active_client = False
                    log = ActivityLog(
                        username="system",
                        action_type="UPDATE",
                        entity_type="Lead",
                        entity_id=lead.id,
                        entity_name=f"{lead.first_name} {lead.last_name}",
                        description="Marked as Inactive: Missing from latest client export."
                    )
                    db.add(log)
                inactives_marked += 1

        if not dry_run:
            db.commit()
            print("\nSync completed successfully.")
        else:
            print("\nDry run completed. No changes were made.")

        print(f"Summary:")
        print(f"- Duplicates removed: {duplicates_removed}")
        print(f"- Leads created: {leads_created}")
        print(f"- Existing leads updated to Authorized: {updates_made}")
        print(f"- Leads marked inactive: {inactives_marked}")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    csv_file = "clients_export (6).csv"
    is_dry = "--commit" not in sys.argv
    sync_clients(csv_file, dry_run=is_dry)
