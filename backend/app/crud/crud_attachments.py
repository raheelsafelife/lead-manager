"""
CRUD operations for attachment functionality
"""
from sqlalchemy.orm import Session
from app.models import Attachment
from datetime import datetime


def create_attachment(db: Session, lead_id: int, filename: str, file_path: str, file_size: int, uploaded_by: str):
    """Create a new attachment record"""
    attachment = Attachment(
        lead_id=lead_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.utcnow()
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachments_by_lead(db: Session, lead_id: int):
    """Get all attachments for a specific lead"""
    return db.query(Attachment).filter(Attachment.lead_id == lead_id).order_by(Attachment.uploaded_at.desc()).all()


def get_attachment_by_id(db: Session, attachment_id: int):
    """Get a specific attachment by ID"""
    return db.query(Attachment).filter(Attachment.id == attachment_id).first()


def delete_attachment(db: Session, attachment_id: int):
    """Delete an attachment record"""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if attachment:
        db.delete(attachment)
        db.commit()
        return True
    return False
