import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db import SessionLocal
import app.models as models

def parse_date(date_str):
    if not date_str or date_str == "--" or date_str.strip() == "":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()
    except ValueError:
        return None

def get_or_create_agency(db, name):
    if not name or name == "--":
        return None
    agency = db.query(models.Agency).filter(models.Agency.name == name).first()
    if not agency:
        agency = models.Agency(name=name, created_by="system")
        db.add(agency)
        db.commit()
        db.refresh(agency)
    return agency.id

def import_csv(file_path, default_status):
    db = SessionLocal()
    print(f"\nImporting {file_path}...")
    
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        added_count = 0
        updated_count = 0
        skipped_count = 0
        
        for row in reader:
            chart_id = row.get('Chart ID', '').strip('"')
            full_name = row.get('Name', '').strip('"')
            dob = parse_date(row.get('DOB', ''))
            status = row.get('Status', '').strip('"')
            supervisor = row.get('Supervisor', '').strip('"')
            payor_name = row.get('Payor', '').strip('"')
            soc_date = parse_date(row.get('SOC', ''))
            eoc = row.get('EOC', '').strip('"')
            
            # Split name
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            # Map status
            if status == "Canceled":
                final_status = "Terminated"
            else:
                final_status = default_status
            
            # Match by Name and DOB
            existing_lead = db.query(models.Lead).filter(
                models.Lead.first_name.ilike(first_name),
                models.Lead.last_name.ilike(last_name),
                models.Lead.dob == dob
            ).first()
            
            agency_id = get_or_create_agency(db, payor_name)
            
            comments = f"Imported from CSV. Chart ID: {chart_id}. EOC: {eoc}"
            
            if existing_lead:
                # Update existing lead
                existing_lead.care_status = final_status
                existing_lead.soc_date = soc_date
                existing_lead.staff_name = supervisor
                existing_lead.agency_id = agency_id
                existing_lead.custom_user_id = chart_id
                existing_lead.authorization_received = True
                if existing_lead.comments:
                    if chart_id not in existing_lead.comments:
                        existing_lead.comments += f"\n{comments}"
                else:
                    existing_lead.comments = comments
                updated_count += 1
            else:
                # Create new lead
                new_lead = models.Lead(
                    first_name=first_name,
                    last_name=last_name,
                    dob=dob,
                    care_status=final_status,
                    staff_name=supervisor,
                    agency_id=agency_id,
                    custom_user_id=chart_id,
                    soc_date=soc_date,
                    comments=comments,
                    authorization_received=True,
                    active_client=True if final_status == "Hold" else False,
                    source="External Referral", # Required field
                    phone="N/A", # Required field
                    last_contact_status="Referral Sent" # Logical start for authorized leads
                )
                db.add(new_lead)
                added_count += 1
        
        db.commit()
        print(f"Finished: {added_count} added, {updated_count} updated, {skipped_count} skipped.")
    
    db.close()

if __name__ == "__main__":
    # Get the backend root directory (parent of scripts/)
    backend_root = Path(__file__).parent.parent
    import_csv(str(backend_root / "data" / "terminated.csv"), "Terminated")
    import_csv(str(backend_root / "data" / "hold.csv"), "Hold")
