"""
Migration: Add address, phone, email, care_coordinator_name to CCUs table
"""
from sqlalchemy import create_engine, text

# Database setup
DATABASE_URL = "sqlite:///./leads.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def migrate():
    print("Starting migration: Add CCU detail fields...")
    
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(text("PRAGMA table_info(ccus)"))
        columns = [row[1] for row in result.fetchall()]
        
        columns_to_add = {
            'address': 'VARCHAR(255)',
            'phone': 'VARCHAR(50)',
            'email': 'VARCHAR(255)',
            'care_coordinator_name': 'VARCHAR(150)'
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE ccus ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"✓ Added {col_name} column to ccus table")
            else:
                print(f"⚠ '{col_name}' column already exists in ccus table")
        
        print("\n✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
