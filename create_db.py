from app.db import Base, engine, DATABASE_URL
import app.models  # ensures models are loaded
import os

# This creates the database file and tables
if __name__ == "__main__":
    # If using a file path, ensure the directory exists
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"Created directory: {db_dir}")

    Base.metadata.create_all(bind=engine)
    print(f"Database initialized successfully at: {DATABASE_URL}")
