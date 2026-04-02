from app.db import engine, Base
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            # Add referral_sent_date column
            conn.execute(text("ALTER TABLE leads ADD COLUMN referral_sent_date DATE"))
            print("Added referral_sent_date column to leads table")
            conn.commit()
        except Exception as e:
            print(f"Error adding column (might already exist): {e}")

if __name__ == "__main__":
    migrate()
