"""
Database migration to add messages table
Run this script to create the messages table in the database
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.db import Base, engine, SessionLocal

# Define Message model for migration
from app.models import Message

def migrate():
    """Create messages table"""
    print("Creating messages table...")
    Base.metadata.create_all(bind=engine, tables=[Message.__table__])
    print("✅ Messages table created successfully!")

if __name__ == "__main__":
    migrate()
