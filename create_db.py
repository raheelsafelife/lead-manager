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
    try:
        from app.models import User
        from app.crud.crud_users import hash_password
        
        # Check for the specific admin user the user is trying to use
        admin_user = db.query(User).filter(User.username == "Safelife").first()
        
        target_password = "123456" # The password the user is sure about
        
        if not admin_user:
            print("Admin 'Safelife' not found. Creating default admin...")
            admin_in = UserCreate(
                username="Safelife",
                user_id="ADMIN001",
                password=target_password,
                email="admin@safelife.local",
                role="admin"
            )
            user = create_user(db, admin_in)
            user.is_approved = True
            db.commit()
            print(f"✓ Created admin: Safelife / {target_password}")
        else:
            print(f"Admin 'Safelife' exists. Ensuring password is set to '{target_password}' for login fix...")
            admin_user.hashed_password = hash_password(target_password)
            admin_user.role = "admin"
            admin_user.is_approved = True
            db.commit()
            print(f"✓ Updated admin 'Safelife' with password: {target_password}")
            
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()
