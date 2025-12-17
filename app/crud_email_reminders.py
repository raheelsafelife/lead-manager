"""
CRUD operations for Email Reminders
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from . import models
from .utils.activity_logger import log_activity


def create_reminder(
    db: Session,
    lead_id: int,
    recipient_email: str,
    subject: str,
    sent_by: str,
    status: str = "sent",
    error_message: str = None
) -> models.EmailReminder:
    """Create a new email reminder record"""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead with ID {lead_id} not found")
    
    reminder = models.EmailReminder(
        lead_id=lead_id,
        recipient_email=recipient_email,
        subject=subject,
        sent_by=sent_by,
        status=status,
        error_message=error_message,
        lead_name=f"{lead.first_name} {lead.last_name}",
        lead_status=lead.last_contact_status,
        lead_source=lead.source
    )
    
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    
    return reminder


def get_reminders_by_lead(db: Session, lead_id: int) -> List[models.EmailReminder]:
    """Get all email reminders for a specific lead"""
    return db.query(models.EmailReminder)\
        .filter(models.EmailReminder.lead_id == lead_id)\
        .order_by(models.EmailReminder.sent_at.desc())\
        .all()


def get_recent_reminders(db: Session, limit: int = 50) -> List[models.EmailReminder]:
    """Get most recent email reminders across all leads"""
    return db.query(models.EmailReminder)\
        .order_by(models.EmailReminder.sent_at.desc())\
        .limit(limit)\
        .all()


def count_reminders_for_lead(db: Session, lead_id: int) -> int:
    """Count how many reminders have been sent for a lead"""
    return db.query(models.EmailReminder)\
        .filter(models.EmailReminder.lead_id == lead_id)\
        .count()


def create_care_start_reminder(
    db: Session,
    lead_id: int,
    recipient_email: str,
    subject: str,
    sent_by: str,
    status: str = "sent",
    error_message: str = None
) -> models.EmailReminder:
    """Create a new care start reminder record"""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise ValueError(f"Lead with ID {lead_id} not found")

    reminder = models.EmailReminder(
        lead_id=lead_id,
        recipient_email=recipient_email,
        subject=subject,
        sent_by=sent_by,
        status=status,
        error_message=error_message,
        lead_name=f"{lead.first_name} {lead.last_name}",
        lead_status=lead.last_contact_status,
        lead_source=lead.source
    )

    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    return reminder


def get_care_start_reminders_by_lead(db: Session, lead_id: int) -> List[models.EmailReminder]:
    """Get all care start email reminders for a specific lead (identified by subject containing 'Care Start')"""
    return db.query(models.EmailReminder)\
        .filter(
            models.EmailReminder.lead_id == lead_id,
            models.EmailReminder.subject.like("%Care Start%")
        )\
        .order_by(models.EmailReminder.sent_at.desc())\
        .all()
