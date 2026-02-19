import pandas as pd
import os
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Lead, User, Event, CCU, MCO, Agency, ActivityLog
from app.crud.crud_users import hash_password

def str_to_date(date_str):
    if pd.isna(date_str) or not str(date_str).strip() or str(date_str).lower() == 'na':
        return None
    try:
        # Try common formats
        for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y', '%m/%d/%y'):
            try:
                return datetime.strptime(str(date_str).strip(), fmt).date()
            except ValueError:
                continue
        return None
    except:
        return None

def normalize_phone(phone):
    if pd.isna(phone):
        return ""
    res = re.sub(r'\D', '', str(phone))
    return res[-10:] if len(res) >= 10 else res

def get_or_create_user(db, username, display_name):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        print(f"Creating user: {username}")
        user = User(
            username=username,
            email=f"{username}@safelifehomehealth.com",
            hashed_password=hash_password("123456"),
            role="user",
            is_approved=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def fuzzy_match_ccu(db, csv_name):
    if pd.isna(csv_name) or not str(csv_name).strip():
        return None
    name = str(csv_name).strip().lower()
    
    mapping = {
        'lake county': 'Lake County Senior Social Services',
        'kenneth young': 'Kenneth Young Center',
        'will county': 'Senior Services of Will County',
        'dupage': 'DuPage County CS Programs',
        'south suburban': 'Catholic Charities SSSS',
        'southwest': 'Catholic Charities SWSS',
        'nenw': 'Catholic Charities OAS/NENW',
        'nwss': 'Catholic Charities NWSS',
        'ssss': 'Catholic Charities SSSS',
        'area 5': 'CCSI Case Coordination, LLC (Area 5)',
        'area 6': 'CCSI Case Coordination, LLC (Area 6)',
        'area 8': 'CCSI Case Coordination, LLC (Area 8)',
        'area 10': 'CCSI Case Coordination, LLC (Area 10)',
        'area 11': 'CCSI Case Coordination, LLC (Area 11)',
        'area 12': 'CCSI Case Coordination, LLC (Area 12)',
        'case coordination': 'CCSI Case Coordination',
        'premier': 'Premier Home Health Care',
        'path lights': 'Pathlights',
        'plows': 'Pathlights',
        'aurora': 'Senior Services Ass. Aurora',
        'elgin': 'Senior Services Ass. Elgin',
        'kendall': 'Senior Services Ass. Kendall',
        'grundy': 'Grundy County Health Department',
        'central': 'Catholic Charities NWSS',
        'chicago': 'CCSI Case Coordination',
    }
    
    for key, target in mapping.items():
        if key in name:
            matched = db.query(CCU).filter(CCU.name.ilike(f"%{target}%")).first()
            if matched: return matched.id

    ccus = db.query(CCU).all()
    for c in ccus:
        if c.name.lower() in name or name in c.name.lower():
            return c.id
    return None

def identify_staff(row_values):
    text = " ".join([str(v).lower() for v in row_values]).replace('.', '')
    if 'rahman gul' in text or ' rg ' in text or ' rg' in text or 'rg ' in text:
        return 'rahman_gul'
    if 'muneeza' in text or ' ms ' in text or ' ms' in text or 'ms ' in text:
        return 'muneeza'
    if 'rai faisal' in text or 'faisal' in text or 'rai' in text:
        return 'rai Faisal'
    return 'Safelife'

def upsert_lead(db, lead_data):
    phone = lead_data.get('phone')
    first_name = str(lead_data.get('first_name', '')).strip().lower()
    last_name = str(lead_data.get('last_name', '')).strip().lower()
    
    if not first_name: return None
    
    if phone:
        # Match by First Name and Phone (for husband/wife households)
        existing = db.query(Lead).filter(
            Lead.phone == phone,
            Lead.first_name.ilike(first_name)
        ).first()
    else:
        # Match by Full Name if phone is missing
        existing = db.query(Lead).filter(
            Lead.first_name.ilike(first_name),
            Lead.last_name.ilike(last_name)
        ).first()
    
    if existing:
        for key, value in lead_data.items():
            if key in ['phone', 'first_name', 'last_name']: continue
            # Allow False, but skip None/Empty/NaN
            if value is not None and str(value).strip() != '' and str(value).lower() != 'nan':
                if key == 'comments':
                    val_str = str(value).strip()
                    if not existing.comments:
                        existing.comments = val_str
                    elif val_str not in existing.comments:
                        existing.comments += f" | {val_str}"
                else:
                    setattr(existing, key, value)
        return existing
    else:
        # Default staff if missing
        if not lead_data.get('staff_name'): lead_data['staff_name'] = 'Safelife'
        if not lead_data.get('created_by'): lead_data['created_by'] = 'Safelife'
        if not lead_data.get('source'): lead_data['source'] = 'External Referral'
        
        # Ensure we have a phone string (even if empty) for the db constraint if needed
        if not lead_data.get('phone'): lead_data['phone'] = ''
        
        new_lead = Lead(**lead_data)
        db.add(new_lead)
        return new_lead

def import_data():
    db = SessionLocal()
    print("Starting Data Import...")

    try:
        idoa_id = db.query(Agency).filter(Agency.name.ilike("%IDOA%")).first().id
        mco_agency_id = db.query(Agency).filter(Agency.name.ilike("%MCO%")).first().id
        dors_id = db.query(Agency).filter(Agency.name.ilike("%DORS%")).first().id
    except Exception as e:
        print(f"Error getting agencies: {e}")
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # STEP 1: Process Event Sheet
    event_path = os.path.join(base_dir, "Untitled spreadsheet - Sheet1 (1).csv")
    if os.path.exists(event_path):
        print("Processing Events...")
        current_event = "General Event"
        with open(event_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:]:
                parts = line.strip().split(',')
                if '"' in line and any(x in line for x in ["Event", "Fest", "Dinner", "Day", "Convention", "Bazaar"]):
                    current_event = line.strip().strip('"').replace(',', '')
                    if not db.query(Event).filter(Event.event_name == current_event).first():
                        db.add(Event(event_name=current_event, created_by="Safelife"))
                        db.commit()
                    continue
                if len(parts) >= 8 and parts[1].strip():
                    name_parts = parts[1].strip().split(' ')
                    phone = normalize_phone(parts[7])
                    staff = identify_staff(parts)
                    upsert_lead(db, {
                        'first_name': name_parts[0],
                        'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else "",
                        'phone': phone,
                        'staff_name': staff,
                        'created_by': staff,
                        'source': "Event",
                        'event_name': current_event,
                        'active_client': False,
                        'relation_to_client': parts[2] if len(parts) > 2 else None,
                        'dob': str_to_date(parts[3]) if len(parts) > 3 else None,
                        'medicaid_no': parts[6] if len(parts) > 6 else None,
                        'address': parts[9] if len(parts) > 9 else None,
                        'city': parts[10] if len(parts) > 10 else None,
                        'zip_code': parts[11] if len(parts) > 11 else None,
                        'comments': parts[12] if len(parts) > 12 else None,
                        'last_contact_status': "Initial Call"
                    })
            db.commit()

    # STEP 2: Process Referrals
    ref_path = os.path.join(base_dir, "referal sent - Sheet1.csv")
    if os.path.exists(ref_path):
        print("Processing Referrals...")
        df = pd.read_csv(ref_path)
        for _, row in df.iterrows():
            phone = normalize_phone(row.get('Phone', ''))
            staff = identify_staff(row.values)
            ccu_id = fuzzy_match_ccu(db, row.get('CCU Details'))
            comments = str(row.get('Comment ', '')).lower()
            agency_id = idoa_id
            mco_id = None
            if 'bcbs' in comments: mco_id = db.query(MCO).filter(MCO.name.ilike("%BCBS%")).first().id
            elif 'aetna' in comments: mco_id = db.query(MCO).filter(MCO.name.ilike("%Aetna%")).first().id
            if mco_id: agency_id = mco_agency_id
            if 'dors' in comments: agency_id = dors_id

            upsert_lead(db, {
                'first_name': str(row.get('First Name', '')).strip(),
                'last_name': str(row.get('Last Name', '')).strip(),
                'phone': phone,
                'staff_name': staff,
                'created_by': staff,
                'active_client': True,
                'last_contact_status': "Referral Sent",
                'source': "External Referral",
                'dob': str_to_date(row.get('DOB')),
                'medicaid_no': str(row.get('Medicaid #', '')),
                'address': str(row.get('Address', '')),
                'zip_code': str(row.get('ZIP Code', '')),
                'comments': str(row.get('Comment ', '')),
                'ccu_id': ccu_id,
                'agency_id': agency_id,
                'mco_id': mco_id
            })
        db.commit()

    # STEP 3: Process Active Leads Sheet
    active_path = os.path.join(base_dir, "leads - Sheet1.csv")
    if os.path.exists(active_path):
        print("Processing Active Leads...")
        df = pd.read_csv(active_path)
        for _, row in df.iterrows():
            phone = normalize_phone(row.get('PHONE NUMBER', ''))
            assigned_staff = str(row.get('A', '')).lower()
            if 'muneeza' in assigned_staff: staff = 'muneeza'
            elif 'faisal' in assigned_staff: staff = 'rai Faisal'
            elif 'rahman' in assigned_staff: staff = 'rahman_gul'
            else: staff = identify_staff(row.values)

            is_active = str(row.get('Active HH?', '')).lower() in ['yes', 'y', 'true']
            
            upsert_lead(db, {
                'first_name': str(row.get('FIRST NAME', '')).strip(),
                'last_name': str(row.get('LAST NAME', '')).strip(),
                'phone': phone,
                'staff_name': staff,
                'active_client': is_active,
                'authorization_received': is_active,
                'last_contact_status': "Follow Up" if is_active else "Initial Call",
                'priority': "High" if 'high' in str(row.get('Priority', '')).lower() else "Medium",
                'medicaid_no': str(row.get('MEDICAID #', '')),
                'address': str(row.get('ADDRESS', '')),
                'comments': str(row.get('COMMENTS', ''))
            })
        db.commit()

    # STEP 4: Process Inactive Leads
    inactive_path = os.path.join(base_dir, "inactive - Sheet1.csv")
    if os.path.exists(inactive_path):
        print("Processing Inactive Leads (Overwrite)...")
        df = pd.read_csv(inactive_path)
        for _, row in df.iterrows():
            # MATCHING COLUMN NAMES FROM INACTIVE SHEET
            phone = normalize_phone(row.get('Phone', ''))
            if not phone: phone = normalize_phone(row.get('E - Contact Phone', ''))
            
            staff = identify_staff(row.values)
            upsert_lead(db, {
                'first_name': str(row.get('First Name', '')).strip(),
                'last_name': str(row.get('Last Name', '')).strip(),
                'phone': phone,
                'staff_name': staff,
                'created_by': staff,
                'source': "External Referral",
                'active_client': False,
                'last_contact_status': "Inactive",
                'priority': "Low",
                'comments': f"Inactivity Reason: {row.get('Reason', '')}. {row.get('Comments', '')}"
            })
        db.commit()

    # STEP 5: Process Active Clients (Final Truth)
    care_start_path = os.path.join(base_dir, "activte client - Sheet1 (1).csv")
    if os.path.exists(care_start_path):
        print("Processing Care Started Clients (Final Overwrite)...")
        df = pd.read_csv(care_start_path)
        for _, row in df.iterrows():
            phone = normalize_phone(row.get('Phone', ''))
            if not phone: phone = normalize_phone(row.get('E - Contact Phone', ''))
            
            status_hh = str(row.get('Status with US (HH)', '')).lower()
            is_active = 'discharged' not in status_hh and 'not active' not in status_hh
            
            staff = identify_staff(row.values)
            upsert_lead(db, {
                'first_name': str(row.get('First Name', '')).strip(),
                'last_name': str(row.get('Last Name', '')).strip(),
                'phone': phone,
                'staff_name': staff,
                'created_by': staff,
                'source': "External Referral",
                'active_client': is_active,
                'authorization_received': is_active,
                'care_status': "Care Start" if is_active else "Not Start",
                'last_contact_status': "Care Start" if is_active else "Inactive",
                'priority': "High" if is_active else "Low",
                'comments': f"Care Status: {status_hh}. {row.get('Comment ', '')}"
            })
        db.commit()

    print("\n--- IMPORT SUMMARY ---")
    print(f"Total Unique Leads: {db.query(Lead).count()}")
    print(f"Total Active Clients: {db.query(Lead).filter(Lead.active_client == True).count()}")
    print(f"Total Inactive Status: {db.query(Lead).filter(Lead.last_contact_status == 'Inactive').count()}")
    print(f"Total Care Started: {db.query(Lead).filter(Lead.care_status == 'Care Start').count()}")
    db.close()

if __name__ == "__main__":
    import_data()
