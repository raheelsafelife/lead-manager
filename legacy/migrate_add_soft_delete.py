"""
Database Migration: Add soft delete columns to leads table
Run this script to add deleted_at and deleted_by columns
"""
import sys
from pathlib import Path
sys.path.append(str(Path.cwd() / "backend"))

from app.db import SessionLocal, engine
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        print("Adding soft delete columns to leads table...")
        
        # Check if columns already exist
        result = db.execute(text("PRAGMA table_info(leads)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'deleted_at' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN deleted_at DATETIME NULL"))
            print("[OK] Added deleted_at column")
        else:
            print("[OK] deleted_at column already exists")
            
        if 'deleted_by' not in columns:
            db.execute(text("ALTER TABLE leads ADD COLUMN deleted_by VARCHAR(100) NULL"))
            print("[OK] Added deleted_by column")
        else:
            print("[OK] deleted_by column already exists")
        
        db.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
