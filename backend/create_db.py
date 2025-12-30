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
    print(f"[DB] Creating tables...", flush=True)
    Base.metadata.create_all(bind=engine)
    
    # SEEDING: Ensure at least one admin exists
    db = SessionLocal()
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
            print(f"SUCCESSFULLY CREATED: {target_username} / {target_password}", flush=True)
        else:
            print(f"Account '{target_username}' found. Force-resetting for access recovery...", flush=True)
            # FORCE RE-SYNC EVERYTHING to ensure the user can get in
            admin_user.hashed_password = hash_password(target_password)
            admin_user.role = "admin"
            admin_user.is_approved = True
            # Also ensure optional fields aren't blocking anything
            if not admin_user.email:
                admin_user.email = "admin@safelife.local"
            
            db.commit()
            print(f"SUCCESSFULLY RECOVERY: {target_username} is now ACTIVE with password {target_password}", flush=True)

    except Exception as e:
        print(f"CRITICAL ERROR DURING SEEDING: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print(f"--- SECURE ADMIN SEEDING COMPLETE ---", flush=True)
