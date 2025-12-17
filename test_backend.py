from app.db import SessionLocal, engine, Base
from app import models, schemas, crud_users, crud_leads
from datetime import date

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def test_backend():
    db = SessionLocal()
    try:
        print("--- Testing User CRUD ---")
        # 1. Create User
        username = "testuser_unique"
        # Cleanup if exists
        existing_user = crud_users.get_user_by_username(db, username)
        if existing_user:
            db.delete(existing_user)
            db.commit()
            print(f"Cleaned up existing user: {username}")

        user_in = schemas.UserCreate(username=username, password="secretpassword")
        user = crud_users.create_user(db, user_in)
        print(f"User created: {user.username} (ID: {user.id})")

        # 2. Authenticate User
        auth_user = crud_users.authenticate_user(db, username, "secretpassword")
        if auth_user:
            print("Authentication successful!")
        else:
            print("Authentication FAILED!")

        print("\n--- Testing Lead CRUD ---")
        # 3. Create Lead
        lead_in = schemas.LeadCreate(
            staff_name="Agent Smith",
            first_name="John",
            last_name="Doe",
            source="Web",
            phone="555-0199",
            email="john@example.com",
            dob=date(1990, 1, 1)
        )
        lead = crud_leads.create_lead(db, lead_in)
        print(f"Lead created: {lead.first_name} {lead.last_name} (ID: {lead.id})")

        # 4. Read Lead
        fetched_lead = crud_leads.get_lead(db, lead.id)
        if fetched_lead:
            print(f"Lead fetched: {fetched_lead.first_name} {fetched_lead.last_name}")

        # 5. Update Lead
        update_data = schemas.LeadUpdate(city="New York", comments="Interested in premium plan")
        updated_lead = crud_leads.update_lead(db, lead.id, update_data)
        print(f"Lead updated: City={updated_lead.city}, Comments={updated_lead.comments}")

        # 6. List Leads
        leads = crud_leads.list_leads(db)
        print(f"Total leads in DB: {len(leads)}")

        # 7. Delete Lead
        success = crud_leads.delete_lead(db, lead.id)
        if success:
            print("Lead deleted successfully.")
        else:
            print("Failed to delete lead.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_backend()
