"""
Migration: Add MCOs table and mco_id column to leads
"""
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey, Index, text
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite:///./leads.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

def migrate():
    print("Starting migration: Add MCOs table and mco_id to leads...")
    
    with engine.connect() as conn:
        # Check if mcos table already exists
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='mcos'"))
        if result.fetchone():
            print("⚠ 'mcos' table already exists, skipping table creation")
        else:
            # Create mcos table
            conn.execute(text("""
                CREATE TABLE mcos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(150) NOT NULL UNIQUE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by VARCHAR(100)
                )
            """))
            conn.commit()
            print("✓ 'mcos' table created")
            
            # Create indexes
            conn.execute(text("CREATE INDEX ix_mcos_name ON mcos (name)"))
            conn.commit()
            print("✓ Indexes created")
            
            # Insert default MCOs
            default_mcos = [
                "Aetna – Medicaid",
                "Aetna – MMAI",
                "BCBSIL",
                "Meridian",
                "Molina"
            ]
            
            for mco_name in default_mcos:
                conn.execute(text("""
                    INSERT INTO mcos (name, created_by, created_at)
                    VALUES (:name, 'system', :created_at)
                """), {"name": mco_name, "created_at": datetime.utcnow()})
            conn.commit()
            print(f"✓ Inserted {len(default_mcos)} default MCOs")
        
        # Check if mco_id column exists in leads table
        result = conn.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'mco_id' in columns:
            print("⚠ 'mco_id' column already exists in leads table")
        else:
            # Add mco_id column to leads table
            conn.execute(text("ALTER TABLE leads ADD COLUMN mco_id INTEGER"))
            conn.commit()
            print("✓ Added mco_id column to leads table")
        
        print("\n✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
