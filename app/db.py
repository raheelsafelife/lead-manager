import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Railway Volume is mounted at /app/data
SQLITE_VOLUME_PATH = "/app/data/leads.db"

# Check for Railway environment or the existence of the volume mount
if os.environ.get("RAILWAY_ENVIRONMENT") or os.path.exists("/app/data"):
    DATABASE_URL = f"sqlite:///{SQLITE_VOLUME_PATH}"
else:
    # Use absolute path locally to avoid ambiguity
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'leads.db')}")

# Adjust URL for SQLAlchemy if it's Postgres (staying compatible)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

# Enable stability pragmas for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        # WAL mode is not recommended on Network Filesystems (like Railway Volumes)
        # We will use DELETE mode (default) but keep a high busy_timeout
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

# Database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()
