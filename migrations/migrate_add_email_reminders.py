"""
Migration: Add email_reminders table
"""
import sqlite3
from datetime import datetime

DB_PATH = "leads.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create email_reminders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            recipient_email VARCHAR(255) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sent_by VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'sent',
            error_message TEXT,
            lead_name VARCHAR(300) NOT NULL,
            lead_status VARCHAR(50) NOT NULL,
            lead_source VARCHAR(150) NOT NULL,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    """)
    
    # Create indexes for better performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_reminders_lead_id 
        ON email_reminders(lead_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_reminders_sent_at 
        ON email_reminders(sent_at)
    """)
    
    conn.commit()
    conn.close()
    print(" Migration complete: email_reminders table created")

if __name__ == "__main__":
    migrate()
