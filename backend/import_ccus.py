
import sqlite3
import csv
import os

def normalize_ccu_name(name):
    if not name:
        return ""
    # Remove quotes, strip whitespace, and uppercase for consistent comparison
    return name.replace('"', '').strip().upper()

def import_ccus():
    db_path = "backend/leads.db"
    csv_files = [
        "referal sent - Sheet1.csv",
        "inactive - Sheet1.csv",
        "activte client - Sheet1 (1).csv"
    ]
    
    # Store unique CCUs: name -> {phone, address}
    ccu_data = {}

    # 1. Parse 'referal sent - Sheet1.csv' (Primary Source)
    path = "referal sent - Sheet1.csv"
    if os.path.exists(path):
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('CCU Details')
                phone = row.get('CCU Number')
                address = row.get('CCU Address')
                
                if name:
                    norm_name = normalize_ccu_name(name)
                    if norm_name not in ccu_data or not ccu_data[norm_name]['address']:
                        ccu_data[norm_name] = {
                            'display_name': name.strip(),
                            'phone': phone.strip() if phone else None,
                            'address': address.strip() if address else None
                        }

    # 2. Parse 'inactive - Sheet1.csv'
    path = "inactive - Sheet1.csv"
    if os.path.exists(path):
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('CCU')
                address = row.get('Address')
                if name:
                    norm_name = normalize_ccu_name(name)
                    if norm_name not in ccu_data:
                        ccu_data[norm_name] = {
                            'display_name': name.strip(),
                            'phone': None,
                            'address': address.strip() if address else None
                        }
                    elif address and not ccu_data[norm_name]['address']:
                        ccu_data[norm_name]['address'] = address.strip()

    # 3. Parse 'activte client - Sheet1 (1).csv'
    path = "activte client - Sheet1 (1).csv"
    if os.path.exists(path):
        with open(path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name_and_no = row.get('CCU name and  no')
                if name_and_no:
                    # Often "Name (Phone)" or similar
                    name = name_and_no.strip()
                    norm_name = normalize_ccu_name(name)
                    if norm_name not in ccu_data:
                        ccu_data[norm_name] = {
                            'display_name': name,
                            'phone': None,
                            'address': None
                        }

    # Database update
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing CCUs for mapping
    cursor.execute("SELECT id, name FROM ccus")
    existing_ccus = {normalize_ccu_name(row[1]): row[0] for row in cursor.fetchall()}

    added_count = 0
    updated_count = 0

    for norm_name, data in ccu_data.items():
        if norm_name in existing_ccus:
            # Update if address or phone missing
            ccu_id = existing_ccus[norm_name]
            cursor.execute("SELECT address, phone FROM ccus WHERE id = ?", (ccu_id,))
            curr_addr, curr_phone = cursor.fetchone()
            
            updates = []
            params = []
            if not curr_addr and data['address']:
                updates.append("address = ?")
                params.append(data['address'])
            if not curr_phone and data['phone']:
                updates.append("phone = ?")
                params.append(data['phone'])
            
            if updates:
                params.append(ccu_id)
                query = f"UPDATE ccus SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                updated_count += 1
        else:
            # Insert new
            cursor.execute(
                "INSERT INTO ccus (name, address, phone, created_at, created_by, updated_at, updated_by) VALUES (?, ?, ?, datetime('now'), ?, datetime('now'), ?)",
                (data['display_name'], data['address'], data['phone'], 'System Import', 'System Import')
            )
            added_count += 1

    conn.commit()
    conn.close()

    print(f"Migration complete: {added_count} new CCUs added, {updated_count} existing CCUs updated.")

if __name__ == "__main__":
    import_ccus()
