from app.db import SessionLocal
from app.services_stats import (
    get_basic_counts,
    leads_by_staff,
    leads_by_source,
    leads_by_status,
    monthly_leads,
)

db = SessionLocal()

print("\n=== BASIC COUNTS ===")
print(get_basic_counts(db))

print("\n=== LEADS BY STAFF ===")
print(leads_by_staff(db))

print("\n=== LEADS BY SOURCE ===")
print(leads_by_source(db))

print("\n=== LEADS BY STATUS ===")
print(leads_by_status(db))

print("\n=== MONTHLY LEADS ===")
print(monthly_leads(db))

db.close()
