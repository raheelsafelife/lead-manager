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

    # Create tables
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized successfully at: {DATABASE_URL}")

    # SEEDING: Ensure at least one admin exists
    db = SessionLocal()
    print(f"--- Starting Seeding Checklist ---")
    try:
        from app.models import User
        from app.crud.crud_users import hash_password, verify_password
        
        target_username = "Safelife"
        target_password = "123456"
        
        # 1. Search for existing admin
        admin_user = db.query(User).filter(User.username == target_username).first()
        
        if not admin_user:
            print(f"1. Admin '{target_username}' not found. Creating fresh...")
            admin_in = UserCreate(
                username=target_username,
                user_id="ADMIN001",
                password=target_password,
                email="admin@safelife.local",
                role="admin"
            )
            user = create_user(db, admin_in)
            user.is_approved = True
            db.commit()
            print(f"   ✓ Created admin: {target_username} with password {target_password}")
        else:
            print(f"1. Admin '{target_username}' found. Checking password validity...")
            
            # 2. Check if current password works
            if not verify_password(target_password, admin_user.hashed_password):
                print(f"2. Password mismatch. Force-resetting password to '{target_password}'...")
                admin_user.hashed_password = hash_password(target_password)
            else:
                print(f"2. Password is already correct.")
            
            # 3. Ensure role and approval
            admin_user.role = "admin"
            admin_user.is_approved = True
            db.commit()
            print(f"3. ✓ Account {target_username} is verified and READY.")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print(f"--- Seeding Checklist Complete ---")
