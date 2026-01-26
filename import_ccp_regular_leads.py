import sys
from pathlib import Path
import csv
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.db import SessionLocal
import app.models as models
from app.crud import crud_leads

CSV_FILE = "CCP Regular Leads - Sheet1.csv"

def parse_dob(dob_str):
    if not dob_str or dob_str.lower() == 'nan':
        return None
    for fmt in ('%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%m/%d/%y'):
        try:
            return datetime.strptime(dob_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

def import_data():
    print(f"Starting import from {CSV_FILE}...")
    db = SessionLocal()
    
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            count = 0
            for row in reader:
                first_name = (row.get('First Name') or "").strip()
                last_name = (row.get('Last Name') or "").strip()
                
                if not first_name and not last_name:
                    continue
                
                status_raw = (row.get('Status') or "").strip()
                # Categorize as active_client if status is "Referral Sent"
                is_referral = "referral sent" in status_raw.lower()
                
                phone = (row.get('Phone') or "").strip()
                existing = crud_leads.check_duplicate_lead(db, first_name, last_name, phone)
                if existing:
                    print(f"Skipping duplicate: {first_name} {last_name}")
                    continue
                
                lead_data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone,
                    "dob": parse_dob(row.get('DOB')),
                    "source": "CCP Regular",
                    "staff_name": "system",
                    "created_by": "system",
                    "active_client": is_referral,
                    "medicaid_no": row.get('Medicaid #'),
                    "address": row.get('Address'),
                    "city": row.get('City'),
                    "zip_code": row.get('ZIP Code'),
                    "comments": row.get('Comment') or row.get('Status'),
                    "priority": row.get('Priority') or "Medium",
                    "last_contact_status": "Referral Sent" if is_referral else "Initial Call"
                }
                
                mco_name = row.get('MCO')
                if mco_name:
                    agency = db.query(models.Agency).filter(models.Agency.name.ilike(f"%{mco_name}%")).first()
                    if agency:
                        lead_data["agency_id"] = agency.id
                
                ccu_name_raw = row.get('Fi')
                if ccu_name_raw:
                    ccu_base = ccu_name_raw.split('(')[0].strip()
                    ccu = db.query(models.CCU).filter(models.CCU.name.ilike(f"%{ccu_base}%")).first()
                    if ccu:
                        lead_data["ccu_id"] = ccu.id

                lead = models.Lead(**lead_data)
                db.add(lead)
                count += 1
                
            db.commit()
            print(f"Successfully imported {count} leads/referrals.")

    except Exception as e:
        db.rollback()
        print(f"Error during import: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_data()
