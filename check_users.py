import sys
from pathlib import Path
sys.path.append(str(Path.cwd() / "backend"))
from app.db import SessionLocal
from app import models

db = SessionLocal()
users = db.query(models.User).all()

print(f"{'ID':<5} | {'Username':<20} | {'Employee ID':<15}")
print("-" * 45)
for user in users:
    print(f"{user.id:<5} | {user.username:<20} | {user.user_id or 'None':<15}")

# Assign EMP IDs to anyone missing one
for user in users:
    if not user.user_id:
        user.user_id = f"EMP{user.id:02d}"
        print(f"Assigned {user.user_id} to {user.username}")
db.commit()

db.close()
