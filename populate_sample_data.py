from app.db import SessionLocal
from app.crud import crud_leads, schemas
from datetime import date, datetime

db = SessionLocal()

# Create sample leads
sample_leads = [
    schemas.LeadCreate(
        staff_name="Alice Johnson",
        first_name="John",
        last_name="Smith",
        source="Web",
        phone="555-1234",
        city="New York",
        active_hh=True,
        last_contact_status="Initial Call"
    ),
    schemas.LeadCreate(
        staff_name="Alice Johnson",
        first_name="Mary",
        last_name="Davis",
        source="Referral",
        phone="555-5678",
        city="Los Angeles",
        active_hh=False,
        last_contact_status="Follow Up"
    ),
    schemas.LeadCreate(
        staff_name="Bob Williams",
        first_name="Robert",
        last_name="Brown",
        source="Web",
        phone="555-9012",
        city="Chicago",
        active_hh=True,
        last_contact_status="Initial Call"
    ),
    schemas.LeadCreate(
        staff_name="Bob Williams",
        first_name="Sarah",
        last_name="Wilson",
        source="Event",
        phone="555-3456",
        city="Houston",
        active_hh=False,
        last_contact_status="No Response"
    ),
    schemas.LeadCreate(
        staff_name="Carol Martinez",
        first_name="James",
        last_name="Taylor",
        source="Web",
        phone="555-7890",
        city="Phoenix",
        active_hh=True,
        last_contact_status="Initial Call"
    ),
    schemas.LeadCreate(
        staff_name="Alice Johnson",
        first_name="Linda",
        last_name="Anderson",
        source="Referral",
        phone="555-2345",
        city="Philadelphia",
        active_hh=True,
        last_contact_status="Follow Up"
    ),
]

print("Creating sample leads...")
for lead_data in sample_leads:
    lead = crud_leads.create_lead(db, lead_data)
    print(f"Created: {lead.first_name} {lead.last_name} (ID: {lead.id})")

db.close()
print(f"\nSuccessfully created {len(sample_leads)} sample leads!")
print("Now run: python test_stats.py")
