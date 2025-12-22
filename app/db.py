from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database file (SQLite)
DATABASE_URL = "sqlite:///./leads.db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()
