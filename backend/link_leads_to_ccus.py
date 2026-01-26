
import sqlite3
import csv
import os

def normalize_text(text):
    if not text:
        return ""
    return str(text).replace('"', '').strip().upper()

def normalize_phone(phone):
    if not phone:
        return ""
    # Remove all non-digits
    return "".join(filter(str.isdigit, str(phone)))

def link_leads_to_ccus():
    # Use dynamic path detection (matches app/db.py behavior)
    if os.path.exists("/app/data"):
        db_path = "/app/data/leads.db"
    else:
        db_path = "backend/leads.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Get CCU Mapping: Normalized Name -> ID
    cursor.execute("SELECT id, name FROM ccus")
    ccu_map = {normalize_text(row[1]): row[0] for row in cursor.fetchall()}
    
    print(f"Loaded {len(ccu_map)} CCUs from database.")

    link_count = 0
    not_found_ccu = set()
    not_found_lead = 0

    # Helper to update lead in DB
    def update_lead_ccu(first, last, phone, ccu_id):
        norm_first = first.strip()
        norm_last = last.strip()
        # Try matching by name and phone
        # Note: Database might have different formatting, so we use LIKE or normalized comparison if possible
        # For simplicity in this script, we'll try exact match on name and cleaned phone
        
        # We need to find the lead ID first
        # Phone matching is tricky because of formatting like (773) 474-6556 vs 7734746556
        # Let's search by name first and verify phone
        cursor.execute(
            "SELECT id, phone FROM leads WHERE UPPER(first_name) = ? AND UPPER(last_name) = ?",
            (norm_first.upper(), norm_last.upper())
        )
        matches = cursor.fetchall()
        
        if not matches:
            return False
            
        target_id = None
        clean_target_phone = normalize_phone(phone)
        
        for m_id, m_phone in matches:
            if not phone or normalize_phone(m_phone) == clean_target_phone:
                target_id = m_id
                break
        
        if target_id:
            cursor.execute("UPDATE leads SET ccu_id = ?, updated_at = datetime('now') WHERE id = ?", (ccu_id, target_id))
            return True
        return False

    # 2. Process CSV Files
    files_configs = [
        {
            'path': "referal sent - Sheet1.csv",
            'ccu_col': 'CCU Details',
            'first_col': 'First Name',
            'last_col': 'Last Name',
            'phone_col': 'Phone'
        },
        {
            'path': "inactive - Sheet1.csv",
            'ccu_col': 'CCU',
            'first_col': 'First Name',
            'last_col': 'Last Name',
            'phone_col': 'Phone'
        },
        {
            'path': "activte client - Sheet1 (1).csv",
            'ccu_col': 'CCU name and  no',
            'first_col': 'First Name',
            'last_col': 'Last Name',
            'phone_col': 'Phone'
        }
    ]

    for config in files_configs:
        path = config['path']
        if not os.path.exists(path):
            print(f"Skipping missing file: {path}")
            continue
            
        print(f"Processing {path}...")
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ccu_name = row.get(config['ccu_col'])
                first = row.get(config['first_col'])
                last = row.get(config['last_col'])
                phone = row.get(config['phone_col'])
                
                if not ccu_name or not first or not last:
                    continue
                
                norm_ccu = normalize_text(ccu_name)
                ccu_id = ccu_map.get(norm_ccu)
                
                if not ccu_id:
                    not_found_ccu.add(ccu_name)
                    continue
                
                if update_lead_ccu(first, last, phone, ccu_id):
                    link_count += 1
                else:
                    not_found_lead += 1

    conn.commit()
    conn.close()

    print(f"\nLinking Complete!")
    print(f"Successfully linked: {link_count} leads to CCUs.")
    print(f"Leads not found in DB: {not_found_lead}")
    if not_found_ccu:
        print(f"CCUs mentioned in CSV but not found in DB ({len(not_found_ccu)}):")
        # for c in sorted(list(not_found_ccu))[:10]: print(f" - {c}")

if __name__ == "__main__":
    link_leads_to_ccus()
