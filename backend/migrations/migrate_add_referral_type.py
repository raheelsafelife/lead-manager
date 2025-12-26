from app.db import engine, Base
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            # Add referral_type column
            conn.execute(text("ALTER TABLE leads ADD COLUMN referral_type VARCHAR(50)"))
            print("Added referral_type column to leads table")
            conn.commit()
        except Exception as e:
            print(f"Error adding column (might already exist): {e}")

if __name__ == "__main__":
    migrate()
