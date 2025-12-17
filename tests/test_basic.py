import uuid
from app.db import SessionLocal
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.crud_users import create_user, authenticate_user, get_user_by_username
from app.crud_leads import create_lead, list_leads, get_lead, update_lead, delete_lead
from app.services_stats import (
    get_basic_counts,
    leads_by_staff,
    leads_by_source,
    leads_by_status,
    monthly_leads,
)


def test_user_create_and_auth():
    db = SessionLocal()

    # create user with unique username
    unique_username = f"test_user_{uuid.uuid4().hex[:8]}"
    user_in = UserCreate(username=unique_username, password="secret123", role="admin")
    user = create_user(db, user_in)

    assert user.id is not None
    assert user.username == unique_username

    # authenticate with correct password
    auth_ok = authenticate_user(db, unique_username, "secret123")
    assert auth_ok is not None

    # authenticate with wrong password
    auth_fail = authenticate_user(db, unique_username, "wrongpass")
    assert auth_fail is None

    db.close()


def test_lead_crud_and_stats():
    db = SessionLocal()

    # create lead
    lead_in = LeadCreate(
        staff_name="Tester Staff",
        first_name="Lead",
        last_name="One",
        source="HHN",
        active_hh=False,
        phone="1112223333",
        city="TestCity",
        zip_code="00000",
        comments="unit test lead",
    )
    lead = create_lead(db, lead_in)

    assert lead.id is not None
    assert lead.first_name == "Lead"

    # get lead
    same_lead = get_lead(db, lead.id)
    assert same_lead is not None
    assert same_lead.id == lead.id

    # update lead
    updated = update_lead(
        db,
        lead_id=lead.id,
        lead_in=LeadUpdate(last_contact_status="Follow Up"),
    )
    assert updated is not None
    assert updated.last_contact_status == "Follow Up"

    # list leads
    leads = list_leads(db)
    assert len(leads) >= 1

    # stats
    counts = get_basic_counts(db)
    assert "total_leads" in counts
    assert counts["total_leads"] >= 1

    staff_stats = leads_by_staff(db)
    assert isinstance(staff_stats, list)

    source_stats = leads_by_source(db)
    assert isinstance(source_stats, list)

    status_stats = leads_by_status(db)
    assert isinstance(status_stats, list)

    monthly = monthly_leads(db)
    assert isinstance(monthly, list)

    # delete lead
    deleted_ok = delete_lead(db, lead.id)
    assert deleted_ok is True

    deleted_again = delete_lead(db, lead.id)
    assert deleted_again is False

    db.close()
