from app.db import SessionLocal
from app.models import Lead
from sqlalchemy import func

def check():
    db = SessionLocal()
    
    # Status distribution
    print("\n--- STATUS DISTRIBUTION ---")
    results = db.query(Lead.last_contact_status, func.count(Lead.id)).group_by(Lead.last_contact_status).all()
    for status, count in results:
        print(f"{status}: {count}")
    
    # Active vs Inactive
    print("\n--- ACTIVE STATUS ---")
    active = db.query(Lead).filter(Lead.active_client == True).count()
    inactive = db.query(Lead).filter(Lead.active_client == False).count()
    print(f"Active (Referrals): {active}")
    print(f"Inactive: {inactive}")
    
    # Source distribution
    print("\n--- SOURCE DISTRIBUTION ---")
    results = db.query(Lead.source, func.count(Lead.id)).group_by(Lead.source).all()
    for source, count in results:
        print(f"{source}: {count}")
    
    db.close()

if __name__ == "__main__":
    check()
