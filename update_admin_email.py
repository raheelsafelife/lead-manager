

from app.db import SessionLocal
from app import crud_users

db = SessionLocal()

try:
    print("Updating admin email...")
    print("=" * 50)
    
    # Find the demo admin user (or any admin)
    admin_user = crud_users.get_user_by_username(db, "demo")
    
    if admin_user:
        old_email = admin_user.email
        admin_user.email = "raheelnazir.safelife@gmail.com"
        db.commit()
        
        print(f"✓ Updated admin email")
        print(f"  User: {admin_user.username}")
        print(f"  Old email: {old_email}")
        print(f"  New email: {admin_user.email}")
    else:
        print("✗ Admin user 'demo' not found")
        print("\nAvailable users:")
        users = db.query(crud_users.models.User).filter(
            crud_users.models.User.role == "admin"
        ).all()
        for u in users:
            print(f"  - {u.username} ({u.email})")
    
    print("=" * 50)
    
except Exception as e:
    print(f"✗ Error: {e}")
    db.rollback()
    
finally:
    db.close()
