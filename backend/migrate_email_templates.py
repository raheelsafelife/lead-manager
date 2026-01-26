import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import SessionLocal, engine, Base
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

# Define the new model locally for migration
class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True) # e.g. 'referral_reminder'
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False) # Supports placeholders like {first_name}
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def migrate():
    print("Running Email Templates Migration...")
    
    # Create table
    # This might error if Base is already connected to other tables, 
    # but checkfirst=True is safe.
    try:
        EmailTemplate.__table__.create(engine, checkfirst=True)
        print("Table 'email_templates' verified/created.")
    except Exception as e:
        print(f"Error creating table: {e}")

    db = SessionLocal()
    
    # Default templates
    defaults = [
        {
            "slug": "referral_reminder",
            "subject": "Referral Reminder [{referral_type}]: {name}",
            "body": """
Hello,

This is an automated reminder for the following referral:

Name: {name}
Phone: {phone}
DOB: {dob}
Status: {status}
Referral Type: {referral_type}

CCU Info:
Name: {ccu_name}
Phone: {ccu_phone}
Fax: {ccu_fax}
Address: {ccu_address}

Payor Info:
Name: {payor_name}
Suboption: {payor_suboption}

Please follow up with this referral as soon as possible.

Best Regards,
SafeLife Lead Management System
            """
        },
        {
            "slug": "lead_reminder",
            "subject": "Lead Reminder: {name}",
            "body": """
Hello,

This is an automated reminder for the following lead:

Name: {name}
Phone: {phone}
Source: {source}
Status: {status}
Created On: {created_date}

Please follow up with this lead to ensure they are moving through the pipeline.

Best Regards,
SafeLife Lead Management System
            """
        },
        {
            "slug": "care_start_reminder",
            "subject": "Care Start Reminder [{referral_type}]: {name} - {days_since_auth} days since auth",
            "body": """
Hello,

Authorization was received {days_since_auth} days ago (on {auth_received_date}) for the following referral, but CARE HAS NOT STARTED yet:

Name: {name}
Phone: {phone}
Referral Type: {referral_type}

CCU Info:
Name: {ccu_name}
Coordinator: {ccu_coordinator}

Payor Info:
Name: {payor_name}

Please finalize care coordination and mark the Start of Care (SOC) date in the system.

Best Regards,
SafeLife Lead Management System
            """
        }
    ]
    
    for d in defaults:
        try:
            existing = db.query(EmailTemplate).filter(EmailTemplate.slug == d['slug']).first()
            if not existing:
                template = EmailTemplate(**d)
                db.add(template)
                print(f"Created default template: {d['slug']}")
            else:
                print(f"Template already exists: {d['slug']}")
        except Exception as e:
            print(f"Error processing {d['slug']}: {e}")
            
    db.commit()
    db.close()
    print("Migration Complete.")

if __name__ == "__main__":
    migrate()
