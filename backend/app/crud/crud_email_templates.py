from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import app.models as models

def get_templates(db: Session) -> List[models.EmailTemplate]:
    """Get all email templates"""
    return db.query(models.EmailTemplate).all()

def get_template_by_slug(db: Session, slug: str) -> Optional[models.EmailTemplate]:
    """Get a template by its slug (e.g. 'referral_reminder')"""
    return db.query(models.EmailTemplate).filter(models.EmailTemplate.slug == slug).first()

def update_template(db: Session, slug: str, subject: str, body: str) -> Optional[models.EmailTemplate]:
    """Update template content"""
    template = get_template_by_slug(db, slug)
    if template:
        template.subject = subject
        template.body = body
        db.commit()
        db.refresh(template)
        return template
    return None
