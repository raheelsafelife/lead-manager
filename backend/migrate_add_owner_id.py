from sqlalchemy import create_engine, text
import os

# Connect to database
DATABASE_URL = "sqlite:///backend/leads.db"
engine = create_engine(DATABASE_URL)

def run_migration():
    print("Starting migration: Adding owner_id to leads table...")
    
    with engine.connect() as conn:
        # 1. Add column if not exists (handled by model change, but needed for raw SQL if not using Alembic)
        # Check if column exists
        try:
            conn.execute(text("SELECT owner_id FROM leads LIMIT 1"))
            print("Column 'owner_id' already exists.")
        except:
            print("Adding 'owner_id' column...")
            try:
                conn.execute(text("ALTER TABLE leads ADD COLUMN owner_id INTEGER"))
                print("Column added successfully.")
            except Exception as e:
                print(f"Error adding column: {e}")
                return

        # 2. Populate owner_id based on staff_name
        print("\nMapping usernames to User IDs...")
        
        # Get all users
        users = conn.execute(text("SELECT id, username FROM users")).fetchall()
        
        updates = 0
        for user_id, username in users:
            # Update leads where staff_name matches username
            result = conn.execute(
                text("UPDATE leads SET owner_id = :uid WHERE staff_name = :uname"),
                {"uid": user_id, "uname": username}
            )
            updates += result.rowcount
            if result.rowcount > 0:
                print(f"Linked {result.rowcount} leads to User '{username}' (ID: {user_id})")
        
        conn.commit()
        print(f"\nMigration complete. Total leads updated: {updates}")

if __name__ == "__main__":
    run_migration()
