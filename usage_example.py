
from app.db import SessionLocal
from app.schemas import UserCreate, LeadCreate
from app.crud_users import create_user, authenticate_user
from app.crud_leads import create_lead, list_leads
from app.services_stats import get_basic_counts, leads_by_staff


def main():
    db = SessionLocal()

    # --- create a user (if not exists) ---
    print("Creating example user...")
    try:
        user = create_user(
            db,
            UserCreate(username="demo", password="demo123", role="admin"),
        )
        print("User created:", user.username)
    except Exception as e:
        print("User may already exist (this is OK)")
        # Rollback the session to clear the failed transaction
        db.rollback()

    # --- authenticate user ---
    user_auth = authenticate_user(db, "demo", "demo123")
    print("Authenticated:", bool(user_auth))

    # --- create a lead ---
    print("Creating example lead...")
    lead = create_lead(
        db,
        LeadCreate(
            staff_name="Demo Staff",
            first_name="Demo",
            last_name="Lead",
            source="HHN",
            active_hh=False,
            phone="0001112222",
            city="DemoCity",
            zip_code="12345",
            comments="Created from usage_example.py",
        ),
    )
    print("Lead created with ID:", lead.id)

    # --- list leads ---
    leads = list_leads(db)
    print(f"Total leads returned: {len(leads)}")

    # --- stats ---
    counts = get_basic_counts(db)
    print("Basic counts:", counts)

    staff_stats = leads_by_staff(db)
    print("Leads by staff:", staff_stats)

    db.close()


if __name__ == "__main__":
    main()
