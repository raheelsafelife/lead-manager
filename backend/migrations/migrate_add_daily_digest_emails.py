"""
Migration: Add daily_digest_emails table
"""
import sqlite3

DB_PATH = "leads.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_digest_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipient_email VARCHAR(255) NOT NULL,
            digest_date DATE NOT NULL,
            activity_count INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(50) NOT NULL DEFAULT 'sent',
            sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_digest_emails_user_id
        ON daily_digest_emails(user_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_digest_emails_digest_date
        ON daily_digest_emails(digest_date)
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_digest_user_date
        ON daily_digest_emails(user_id, digest_date)
    """)

    conn.commit()
    conn.close()
    print("Migration complete: daily_digest_emails table created")


if __name__ == "__main__":
    migrate()
