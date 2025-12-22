"""
Migration script to add activity logging tables and fields.
Run this script to update your database schema for activity tracking.
"""

from app.db import engine, Base
from app.models import ActivityLog, Lead, Event
from sqlalchemy import text

def migrate():
    print("🔄 Starting activity logging migration...")
    
    # Create activity_logs table
    print("📝 Creating activity_logs table...")
    Base.metadata.create_all(bind=engine, tables=[ActivityLog.__table__])
    print("✅ activity_logs table created!")
    
    # Add new columns to leads table
    print("📝 Adding tracking fields to leads table...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE leads ADD COLUMN created_by VARCHAR(100)"))
            conn.execute(text("ALTER TABLE leads ADD COLUMN updated_by VARCHAR(100)"))
            conn.commit()
            print("✅ Leads table updated!")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  Leads tracking fields already exist")
            else:
                print(f"⚠️  Error updating leads table: {e}")
    
    # Add new columns to events table
    print("📝 Adding tracking fields to events table...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN updated_at DATETIME"))
            conn.execute(text("ALTER TABLE events ADD COLUMN updated_by VARCHAR(100)"))
            conn.commit()
            print("✅ Events table updated!")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  Events tracking fields already exist")
            else:
                print(f"⚠️  Error updating events table: {e}")
    
    print("\n🎉 Migration completed successfully!")
    print("📊 Activity logging system is now ready to use!")

if __name__ == "__main__":
    migrate()
