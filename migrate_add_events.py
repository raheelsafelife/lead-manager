"""
Migration script to add the events table to the database.
Run this script to update your database schema.
"""

from app.db import engine, Base
from app.models import Event  # Import the new Event model

def migrate():
    print("Creating events table...")
    Base.metadata.create_all(bind=engine, tables=[Event.__table__])
    print("✅ Events table created successfully!")

if __name__ == "__main__":
    migrate()
