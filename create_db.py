from app.db import Base, engine
import app.models  # ensures models are loaded

# This creates the database file and tables
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database 'leads.db' created successfully.")
