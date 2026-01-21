import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Priority 1: Check for Persistent Volume mount (Docker/AWS)
if os.path.exists("/app/data"):
    DATABASE_URL = "sqlite:////app/data/leads.db"
    print(f"[DB] Starting in Persistent Mode -> Using: /app/data/leads.db")
else:
    # Priority 2: Use DATABASE_URL from environment if provided
    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        DATABASE_URL = env_db_url
        print(f"[DB] Starting in Custom Mode -> Using Env URL")
    else:
        # Priority 3: Default to local leads.db
        local_db_path = os.path.join(BASE_DIR, "leads.db")
        DATABASE_URL = f"sqlite:///{local_db_path}"
        print(f"[DB] Starting in Local Mode -> Using: {local_db_path}")

# Adjust URL for SQLAlchemy if it's Postgres (staying compatible)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True  # Ensure connections are alive
)

# Enable stability pragmas for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=10000") # Increased timeout for network volumes
        cursor.close()

# Database session with detached-friendly configuration
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Keep object data accessible after commit/close
)

# Base class for models
Base = declarative_base()
