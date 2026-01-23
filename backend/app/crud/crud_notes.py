from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

# Ensure we can import app.models
import app.models as models
import importlib

# Logger
logger = logging.getLogger(__name__)

def add_new_comment(db: Session, lead_id: int, username: str, content: str):
    """Create a new comment for a lead"""
    
    # Use top-level model directly
    # Streamlit cache handling is done centralized


    comment = models.LeadComment(
        lead_id=lead_id,
        username=username,
        content=content,
        created_at=datetime.utcnow()
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Log activity
    from app.utils.activity_logger import log_activity
    log_activity(
        db=db,
        user_id=None,
        username=username,
        action_type="COMMENT_ADDED",
        entity_type="Lead",
        entity_id=lead_id,
        entity_name="Comment Added",
        description=f"User '{username}' added a comment: {content[:50]}...",
        new_value={"content": content},
        keywords="lead,comment,add"
    )
    
    return comment

def get_comments(db: Session, lead_id: int):
    """Get all comments for a lead, newest first"""
    # Use top-level model directly

    return (
        db.query(models.LeadComment)
        .filter(models.LeadComment.lead_id == lead_id)
        .order_by(models.LeadComment.created_at.desc())
        .all()
    )

def delete_comment(db: Session, comment_id: int) -> bool:
    """Delete a comment"""
    comment = db.query(models.LeadComment).filter(models.LeadComment.id == comment_id).first()
    if comment:
        db.delete(comment)
        db.commit()
        return True
    return False
