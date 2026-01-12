"""
Migration: Add session_tokens table for secure session management

This table stores authentication tokens that allow users to stay logged in
across browser refreshes without sharing session data between users.
"""
import sqlite3
import os
from pathlib import Path

# Database path - match the logic in app/db.py
BASE_DIR = Path(__file__).parent.parent
if os.path.exists("/app/data"):
    DB_PATH = "/app/data/leads.db"
else:
    DB_PATH = str(BASE_DIR / 'leads.db')

def migrate():
    """Add session_tokens table"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Create session_tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Create index on token for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_token ON session_tokens(token)
        """)
        
        # Create index on user_id for cleanup queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_user_id ON session_tokens(user_id)
        """)
        
        # Create index on expires_at for expired token cleanup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_expires ON session_tokens(expires_at)
        """)
        
        conn.commit()
        print("[OK] Migration successful: session_tokens table created")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
