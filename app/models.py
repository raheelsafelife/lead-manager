from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    Date,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=True, index=True)  # Unique user identifier
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    is_approved = Column(Boolean, nullable=False, default=False)
    password_reset_requested = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    
    # Activity tracking
    created_by = Column(String(100), nullable=True)  # Username who created
    updated_by = Column(String(100), nullable=True)  # Username who last updated

    # who is responsible
    staff_name = Column(String(150), nullable=False)

    # basic identity
    first_name = Column(String(150), nullable=False)
    last_name = Column(String(150), nullable=False)

    # where this lead came from
    source = Column(String(150), nullable=False)  # e.g. "HHN", "Event", "External Referral", "Word of Mouth", "Other"
    event_name = Column(String(150), nullable=True)  # For Event source
    word_of_mouth_type = Column(String(50), nullable=True)  # Caregiver/Community/Client
    other_source_type = Column(String(150), nullable=True)  # For Other source
    active_client = Column(Boolean, nullable=False, default=False)  # Renamed from active_hh
    referral_type = Column(String(50), nullable=True)  # "Regular" or "Interim"
    
    # Agency / Payor
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=True)
    agency = relationship("Agency")
    
    # Agency Suboption (e.g., INH2502076 for IDoA)
    agency_suboption_id = Column(Integer, ForeignKey("agency_suboptions.id"), nullable=True)
    agency_suboption = relationship("AgencySuboption", back_populates="leads")
    
    # CCU
    ccu_id = Column(Integer, ForeignKey("ccus.id"), nullable=True)
    ccu = relationship("CCU")
    
    # MCO
    mco_id = Column(Integer, ForeignKey("mcos.id"), nullable=True)
    mco = relationship("MCO")
    
    # Authorization tracking
    authorization_received = Column(Boolean, nullable=False, default=False)  # Whether authorization was received
    care_status = Column(String(50), nullable=True)  # "Care Start" or "Not Start"
    priority = Column(String(50), nullable=True, default="Medium")  # "High", "Medium", "Low"
    soc_date = Column(Date, nullable=True)  # Start of Care date

    # contact info
    phone = Column(String(50), nullable=False)
    city = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)

    # extra details
    dob = Column(Date, nullable=True)
    medicaid_no = Column(String(100), nullable=True)

    # emergency contact
    e_contact_name = Column(String(150), nullable=True)
    e_contact_relation = Column(String(100), nullable=True)
    e_contact_phone = Column(String(50), nullable=True)

    # follow-up tracking
    last_contact_status = Column(
        String(50), nullable=False, default="Initial Call"
    )  # e.g. Initial Call / Follow Up / No Response / Awaiting Call
    last_contact_date = Column(DateTime, nullable=True)

    # free text notes
    comments = Column(Text, nullable=True)

    # New fields
    ssn = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    custom_user_id = Column(String(50), nullable=True)  # User ID for the lead (Compulsory in UI)
    
    # SafeLife CCP Form fields
    relation_to_client = Column(String(100), nullable=True)  # Relationship of form submitter to client
    age = Column(Integer, nullable=True)  # Client's age (if birthdate unknown)
    medicaid_status = Column(String(10), nullable=True)  # "yes" or "no"
    address = Column(Text, nullable=True)  # Full address from form
    state = Column(String(2), nullable=True)  # 2-letter state code

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(150), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=False)  # Admin username who created it
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by = Column(String(100), nullable=True)  # Admin username who last updated


class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by = Column(String(100), nullable=True)
    
    # Relationships
    suboptions = relationship("AgencySuboption", back_populates="agency")


class AgencySuboption(Base):
    __tablename__ = "agency_suboptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by = Column(String(100), nullable=True)
    
    # Relationships
    agency = relationship("Agency", back_populates="suboptions")
    leads = relationship("Lead", back_populates="agency_suboption")


class CCU(Base):
    __tablename__ = "ccus"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True, unique=True)
    address = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    fax = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    care_coordinator_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by = Column(String(100), nullable=True)


class MCO(Base):
    __tablename__ = "mcos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    updated_by = Column(String(100), nullable=True)


class ActivityLog(Base):
    """
    Comprehensive activity logging for audit trail and history tracking.
    Tracks all user actions across the application.
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Who performed the action
    user_id = Column(Integer, nullable=True)  # FK to users table
    username = Column(String(100), nullable=False, index=True)
    
    # What action was performed
    action_type = Column(String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, etc.
    entity_type = Column(String(50), nullable=False, index=True)  # Lead, User, Event, etc.
    entity_id = Column(Integer, nullable=True)  # ID of the affected entity
    entity_name = Column(String(200), nullable=True)  # Display name (e.g., "John Doe")
    
    # Details
    description = Column(Text, nullable=False)  # Human-readable description
    old_value = Column(Text, nullable=True)  # JSON string of old values
    new_value = Column(Text, nullable=True)  # JSON string of new values
    keywords = Column(String(200), nullable=True, index=True)  # Comma-separated tags for filtering
    
    # Optional metadata
    ip_address = Column(String(50), nullable=True)


class EmailReminder(Base):
    """
    Tracks email reminders sent for leads.
    Reminders continue until lead becomes inactive or is marked as referral.
    """
    __tablename__ = "email_reminders"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    lead = relationship("Lead")
    
    # Email details
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_by = Column(String(100), nullable=False)  # Username who triggered the reminder
    
    # Status tracking
    status = Column(String(50), nullable=False, default="sent")  # sent, failed, pending
    error_message = Column(Text, nullable=True)
    
    # Lead snapshot at time of email (for historical record)
    lead_name = Column(String(300), nullable=False)
    lead_status = Column(String(50), nullable=False)
    lead_source = Column(String(150), nullable=False)
