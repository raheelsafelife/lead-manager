import logging
import sys
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure logging to stderr to avoid stdout issues
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Priority 1: Check for Persistent Volume mount (Docker/AWS)
if os.path.exists("/app/data"):
    DATABASE_URL = "sqlite:////app/data/leads.db"
    logger.info(f"[DB] Starting in Persistent Mode -> Using: /app/data/leads.db")
else:
    # Priority 2: Use DATABASE_URL from environment if provided
    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        DATABASE_URL = env_db_url
        logger.info(f"[DB] Starting in Custom Mode -> Using Env URL")
    else:
        # Priority 3: Default to local leads.db
        local_db_path = os.path.join(BASE_DIR, "leads.db")
        DATABASE_URL = f"sqlite:///{local_db_path}"
        logger.info(f"[DB] Starting in Local Mode -> Using: {local_db_path}")

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

# Automatic Schema Upgrades
from sqlalchemy import inspect, text

def auto_upgrade_db(eng):
    try:
        inspector = inspect(eng)
        if "leads" in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns("leads")]
            
            with eng.begin() as conn:
                if "tag_color" not in columns:
                    try:
                        conn.execute(text("ALTER TABLE leads ADD COLUMN tag_color VARCHAR(30)"))
                        logger.info("Auto-added 'tag_color' column to leads table")
                    except Exception as e:
                        logger.error(f"Failed to add tag_color: {e}")
                
                if "call_status_updated_by" not in columns:
                    try:
                        conn.execute(text("ALTER TABLE leads ADD COLUMN call_status_updated_by VARCHAR(50)"))
                        logger.info("Auto-added 'call_status_updated_by' column to leads table")
                    except Exception as e:
                        pass
                
                if "call_status_updated_at" not in columns:
                    try:
                        conn.execute(text("ALTER TABLE leads ADD COLUMN call_status_updated_at DATETIME"))
                        logger.info("Auto-added 'call_status_updated_at' column to leads table")
                    except Exception as e:
                        pass

                if "caregiver_type" not in columns:
                    try:
                        conn.execute(text("ALTER TABLE leads ADD COLUMN caregiver_type VARCHAR(50)"))
                        logger.info("Auto-added 'caregiver_type' column to leads table")
                    except Exception as e:
                        logger.error(f"Failed to add caregiver_type: {e}")
                        
        if "users" in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns("users")]
            with eng.begin() as conn:
                if "profile_pic" not in columns:
                    try:
                        conn.execute(text("ALTER TABLE users ADD COLUMN profile_pic TEXT"))
                        logger.info("Auto-added 'profile_pic' column to users table")
                    except Exception as e:
                        logger.error(f"Failed to add profile_pic: {e}")
    except Exception as e:
        logger.error(f"DB Auto-upgrade failed: {e}")


# Run upgrades automatically
def init_db(eng):
    # Ensure all tables defined in models are created
    from app.models import Base
    Base.metadata.create_all(bind=eng)
    auto_upgrade_db(eng)

init_db(engine)
