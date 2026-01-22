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
                
        # 3. Comprehensive CCU List
        list_ccus = [
            'DuPage County CS Programs', 'Grundy County Health Department', 'Senior Services Ass. Elgin',
            'Senior Services Ass. Aurora', 'Catholic Charities Of the Diocese of Joliet (Kankakee)',
            'Senior Services Ass. Kendall', 'Senior Services of Will County', 'Lake County Senior Social Services (Lake)',
            'Catholic Charities NWSS', 'Catholic Charities SSSS', 'CCSI Case Coordination, LLC (Area 5)',
            'Catholic Charities SWSS', 'Premier Home Health Care (North)', 'Premier Home Health Care (South)',
            'Catholic Charities OAS/NENW', 'CCSI Case Coordination, LLC (Area 6)', 'CCSI Case Coordination, LLC (Area 10)',
            'CCSI Case Coordination, LLC (Area 8)', 'CCSI Case Coordination, LLC (Area 11)', 'CCSI Case Coordination, LLC (Area 12)',
            'Solutions for Care', 'Aging Care Connections', 'Oak Park Township', 'Pathlights',
            'Kenneth Young Center (Schaumburg)', 'North Shore Senior Center', 'Stickney Township Office on Aging',
            'General CCU'
        ]
        ccu_count = 0
        for name in list_ccus:
            if not db.query(CCU).filter(CCU.name == name).first():
                db.add(CCU(name=name, created_by="System"))
                ccu_count += 1
        
        if ccu_count > 0:
            print(f"  ✓ Seeded {ccu_count} new CCUs.")
            
        db.commit()
        print("--- BASE DATA SEEDING COMPLETE ---")
    except Exception as e:
        print(f"Error seeding base data: {e}")
    finally:
        db.close()
