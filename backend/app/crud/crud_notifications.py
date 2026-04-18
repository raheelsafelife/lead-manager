"""
CRUD operations for in-app notifications
"""
from sqlalchemy.orm import Session
from app.models import Notification, User
from datetime import datetime
from typing import List, Optional


def create_notification(
    db: Session, 
    user_id: int, 
    title: str, 
    description: str, 
    entity_id: Optional[int] = None, 
    entity_type: Optional[str] = None
):
    """Create a new in-app notification for a user"""
    notification = Notification(
        user_id=user_id,
        title=title,
        description=description,
        entity_id=entity_id,
        entity_type=entity_type,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_user_notifications(db: Session, user_id: int, limit: int = 20) -> List[Notification]:
    """Get recent notifications for a user"""
    return db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()


def get_unread_count(db: Session, user_id: int) -> int:
    """Get count of unread notifications for a user"""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).count()


def mark_as_read(db: Session, notification_id: int):
    """Mark a specific notification as read"""
    db.query(Notification).filter(Notification.id == notification_id).update({"is_read": True})
    db.commit()


def mark_all_as_read(db: Session, user_id: int):
    """Mark all notifications for a user as read"""
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()


def delete_notification(db: Session, notification_id: int):
    """Delete a notification"""
    db.query(Notification).filter(Notification.id == notification_id).delete()
    db.commit()


def get_total_count(db: Session, user_id: int) -> int:
    """Get total count of all notifications for a user"""
    return db.query(Notification).filter(
        Notification.user_id == user_id
    ).count()

