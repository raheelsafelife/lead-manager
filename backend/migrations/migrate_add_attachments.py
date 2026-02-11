"""
Database migration to add attachments table
Run this script to create the attachments table in the database
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db import Base, engine
from app.models import Attachment

def migrate():
    """Create attachments table"""
    print("Creating attachments table...")
    Base.metadata.create_all(bind=engine, tables=[Attachment.__table__])
    print("Success! Attachments table created successfully!")

if __name__ == "__main__":
    migrate()
