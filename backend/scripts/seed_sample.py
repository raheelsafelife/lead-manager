import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db import SessionLocal
from app.crud import crud_leads, crud_users
from app.schemas import LeadCreate
from app.models import Agency, CCU, MCO, User

def seed_sample_data():
    db = SessionLocal()
    try:
        # Get or create admin user
        admin = db.query(User).filter(User.username == "Safelife").first()
        if not admin:
            print("Admin user 'Safelife' not found. Please run create_db.py first.")
            return

        # Get existing CCU/Agency
        ccu = db.query(CCU).first()
        agency = db.query(Agency).first()
        
        sample_leads = [
            {
                "staff_name": "Safelife",
                "first_name": "John",
                "last_name": "Doe",
                "source": "HHN",
                "phone": "555-0101",
                "active_client": False,
                "priority": "High",
                "last_contact_status": "Initial Call"
            },
            {
                "staff_name": "Safelife",
                "first_name": "Jane",
                "last_name": "Smith",
                "source": "Event",
                "event_name": "Community Health Fair",
                "phone": "555-0102",
                "active_client": True,
                "ccu_id": ccu.id if ccu else None,
                "authorization_received": True,
                "care_status": "Care Start",
                "priority": "Medium",
                "last_contact_status": "Assessment Scheduled"
            },
            {
                "staff_name": "Safelife",
                "first_name": "Robert",
                "last_name": "Johnson",
                "source": "Word of Mouth",
                "word_of_mouth_type": "Client",
                "phone": "555-0103",
                "active_client": True,
                "ccu_id": ccu.id if ccu else None,
                "authorization_received": False,
                "priority": "Low",
                "last_contact_status": "Initial Referral Sent"
            }
        ]

        print(f"Seeding {len(sample_leads)} sample leads...")
        for lead_data in sample_leads:
            lead_in = LeadCreate(**lead_data)
            crud_leads.create_lead(db, lead_in, username=admin.username, user_id=admin.id)
        
        print("Successfully seeded sample data!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_sample_data()
