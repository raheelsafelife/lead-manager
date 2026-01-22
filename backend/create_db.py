from app.db import Base, engine, DATABASE_URL, SessionLocal
from app.crud.crud_users import create_user
from app.schemas import UserCreate
import app.models  # ensures models are loaded
import os

# This creates the database file and tables
if __name__ == "__main__":
    # If using a file path, ensure the directory exists
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"Created directory: {db_dir}")

    # Create tables if they don't exist
    print(f"[DB] Creating tables using {DATABASE_URL}...", flush=True)
    import app.models # Load all models to register with Base
    Base.metadata.create_all(bind=engine)
    print("  ✓ Tables synchronized.")
    
    # SEEDING: Ensure at least one admin exists
    db = SessionLocal()
    # Security guard for admin reset
    ALLOW_ADMIN_RESET = os.getenv('ALLOW_ADMIN_RESET', 'false').lower() == 'true'
    print(f"--- SECURE ADMIN SEEDING START ---", flush=True)
    try:
        from app.models import User
        from app.crud.crud_users import hash_password
        
        target_username = "Safelife"
        target_password = "123456"
        
        print(f"Checking for existing admin: {target_username}...", flush=True)
        admin_user = db.query(User).filter(User.username == target_username).first()
        
        if not admin_user:
            print(f"Creating NEW admin account '{target_username}'...", flush=True)
            admin_in = UserCreate(
                username=target_username,
                user_id="ADMIN001",
                password=target_password,
                email="admin@safelife.local",
                role="admin"
            )
            # Create user then force override fields
            user = create_user(db, admin_in)
            user.is_approved = True
            db.commit()
            print(f"SUCCESSFULLY CREATED: {target_username} / [HIDDEN]", flush=True)
        else:
            if ALLOW_ADMIN_RESET:
                print(f"Account '{target_username}' found. ALLOW_ADMIN_RESET is true. Resetting for access recovery...", flush=True)
                # FORCE RE-SYNC EVERYTHING to ensure the user can get in
                admin_user.hashed_password = hash_password(target_password)
                admin_user.role = "admin"
                admin_user.is_approved = True
                # Also ensure optional fields aren't blocking anything
                if not admin_user.email:
                    admin_user.email = "admin@safelife.local"
                
                db.commit()
                print(f"SUCCESSFULLY RECOVERY: {target_username} is now ACTIVE with password [HIDDEN]", flush=True)
            else:
                print(f"Account '{target_username}' found. Skipping reset (ALLOW_ADMIN_RESET=false).", flush=True)

    except Exception as e:
        print(f"CRITICAL ERROR DURING SEEDING: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print(f"--- SECURE ADMIN SEEDING COMPLETE ---", flush=True)

    # SEEDING: Agencies, MCOs, etc.
    db = SessionLocal()
    try:
        from app.models import Agency, MCO, CCU
        
        # 1. Agencies
        agencies = ["IDOA", "MCO", "DORS"]
        for name in agencies:
            if not db.query(Agency).filter(Agency.name == name).first():
                db.add(Agency(name=name, created_by="System"))
        
        # 2. MCOs
        mcos = ["BCBS", "Aetna", "Meridian", "Humana", "CountyCare", "Molina"]
        for name in mcos:
            if not db.query(MCO).filter(MCO.name == name).first():
                db.add(MCO(name=name, created_by="System"))
                
        # 3. Comprehensive CCU List with Details
        list_ccus = [
            {'name': 'DuPage County CS Programs', 'address': '421 N. County Farm Rd., Wheaton, IL 60187', 'phone': '(630)407-6500', 'email': 'csprograms@dupagecounty.gov'},
            {'name': 'Grundy County Health Department', 'address': '1320 Union St., Morris, IL 60450', 'phone': '(815)941-3400'},
            {'name': 'Senior Services Ass. Elgin', 'address': '101 S. Grove Ave., Elgin, IL 60120', 'phone': '(847)741-0404', 'email': 'ssaiccu@seniorservicesassoc.org'},
            {'name': 'Senior Services Ass. Aurora', 'address': '2111 Plum St. Suite 250, Aurora, IL 60506', 'phone': '(630)897-4035', 'email': 'ssaiccu@seniorservicesassoc.org'},
            {'name': 'Catholic Charities Of the Diocese of Joliet (Kankakee)', 'address': '249 S. Schuyler Ave. #300, Kankakee, IL 60901', 'phone': '(815)932-1921'},
            {'name': 'Senior Services Ass. Kendall', 'address': '908 Game Farm Rd., Yorkville, IL 60560', 'phone': '(630)553-5777', 'email': 'ssaiccu@seniorservicesassoc.org'},
            {'name': 'Senior Services of Will County', 'address': '251 N Center St., Joliet, IL 60435', 'phone': '(815)740-4225', 'email': 'ccuwillco@willcountyseniors.org'},
            {'name': 'Lake County Senior Social Services (Lake)', 'address': '116 N Lincoln Ave. Round Lake, IL 60073', 'phone': '(847)546-5733', 'email': 'cclakeccu@catholiccharities.net'},
            {'name': 'Catholic Charities NWSS', 'address': '1801 W. Central Rd., Arlington Heights, IL 60005', 'phone': '(847)253-5500', 'email': 'infoccnw@catholiccharities.net'},
            {'name': 'Catholic Charities SSSS', 'address': '15300 S. Lexington Ave., Harvey, IL 60426', 'phone': '(708)596-2222', 'email': 'ccssssccu@catholiccharities.net'},
            {'name': 'CCSI Case Coordination, LLC (Area 5)', 'address': '329 W 18th St. Suite 801, Chicago, IL 60616', 'phone': '(312)726-1364', 'email': 'chicagoccu@ccsiccu.com'},
            {'name': 'Catholic Charities SWSS', 'address': '2601 W. Marquette Ave, Chicago, IL 60629', 'phone': '(773)349-8092', 'email': 'intakesubarea7@catholiccharities'},
            {'name': 'Premier Home Health Care (North)', 'address': '6321 N. Avondale Suite 101A, Chicago, IL 60631', 'phone': '(312)766-3361', 'email': 'premierccunorth@phhc.com'},
            {'name': 'Premier Home Health Care (South)', 'address': '1081 S. Western Ave Suite LL 100, Chicago, IL 60643', 'phone': '(312)256-2900', 'email': 'PremierILCCU@phss.com'},
            {'name': 'Catholic Charities OAS/NENW', 'address': '3125 N. Knox, Chicago, IL 60641', 'phone': '(773)583-9224', 'email': 'ccnenwccu@catholiccharities.net'},
            {'name': 'CCSI Case Coordination, LLC (Area 6)', 'address': '310 S. Racine 8N, Chicago, IL 60607', 'phone': '(773)341-1790', 'email': 'chicagoccu@ccsiccu.com'},
            {'name': 'CCSI Case Coordination, LLC (Area 10)', 'address': '310 S. Racine 8N, Chicago, IL 60607', 'phone': '(773)341-1790', 'email': 'ccsiarea10@ccsiccu.com'},
            {'name': 'CCSI Case Coordination, LLC (Area 8)', 'address': '1000 E. 111th St. Suite 800, Chicago, IL 60628', 'phone': '(312)686-1515', 'email': 'ccsisoutheast@ccsiccu.com'},
            {'name': 'CCSI Case Coordination, LLC (Area 11)', 'address': '1000 E. 111th St. Suite 800, Chicago, IL 60628', 'phone': '(312)686-1515', 'email': 'ccsisoutheast@ccsiccu.com'},
            {'name': 'CCSI Case Coordination, LLC (Area 12)', 'address': '1000 E. 111th St. Suite 800, Chicago, IL 60628', 'phone': '(312)686-1515', 'email': 'ccsisoutheast@ccsiccu.com'},
            {'name': 'Solutions for Care', 'address': '7222 W. Cermak Rd. Suite 200, Riverside, IL 60546', 'phone': '(708)447-2448', 'email': 'Info@solutionsforcare.org'},
            {'name': 'Aging Care Connections', 'address': '111 W Harris Ave, La Grange, IL 60525', 'phone': '(708)354-1323', 'email': 'Info@agingcareconnection.org'},
            {'name': 'Oak Park Township', 'address': '130 S. Oak Park Ave, 2nd Floor, Oak Park, IL 60302', 'phone': '(708)383-8060', 'email': 'ccureferrals@oakparktownship.org'},
            {'name': 'Pathlights', 'address': '7808 West College Drive Suite 5E, Palos Heights, IL 60463', 'phone': '(708)361-0219', 'email': 'ldoa.tx@pathlights.org'},
            {'name': 'Kenneth Young Center (Schaumburg)', 'address': '1001 Rohlwing Rd., Elk Grove Village, IL 60007', 'phone': '(847)524-8800'},
            {'name': 'North Shore Senior Center', 'address': '161 Northfield Rd, IL 60061', 'phone': '(847)784-6040', 'email': 'mco@nssc.org'},
            {'name': 'Stickney Township Office on Aging', 'address': '7745 S. Leamington Ave., Burbank, IL 60459', 'phone': '(708)636-8850', 'email': 'klivigni@townshipofstickney.org'},
            {'name': 'General CCU'}
        ]
        
        ccu_added = 0
        ccu_updated = 0
        for data in list_ccus:
            name = data['name']
            existing = db.query(CCU).filter(CCU.name == name).first()
            if not existing:
                new_ccu = CCU(
                    name=name,
                    address=data.get('address'),
                    phone=data.get('phone'),
                    email=data.get('email'),
                    created_by="System"
                )
                db.add(new_ccu)
                ccu_added += 1
            else:
                # Update existing if details missing
                changed = False
                if data.get('address') and not existing.address: existing.address = data['address']; changed = True
                if data.get('phone') and not existing.phone: existing.phone = data['phone']; changed = True
                if data.get('email') and not existing.email: existing.email = data['email']; changed = True
                if changed: ccu_updated += 1
        
        if ccu_added > 0 or ccu_updated > 0:
            print(f"  ✓ CCUs: {ccu_added} added, {ccu_updated} updated with details.")
            
        db.commit()
        print("--- BASE DATA SEEDING COMPLETE ---")
    except Exception as e:
        print(f"Error seeding base data: {e}")
    finally:
        db.close()
