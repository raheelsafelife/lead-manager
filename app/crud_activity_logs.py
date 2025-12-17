"""
CRUD operations for Activity Logs
Handles creating, reading, and filtering activity log entries
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from app.models import ActivityLog
from datetime import datetime, timedelta, date
from typing import List, Optional
import json


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles date and datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def create_activity_log(
    db: Session,
    user_id: Optional[int],
    username: str,
    action_type: str,
    entity_type: str,
    entity_id: Optional[int],
    entity_name: Optional[str],
    description: str,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    keywords: Optional[str] = None,
    ip_address: Optional[str] = None
) -> ActivityLog:
    """
    Create a new activity log entry
    """
    activity = ActivityLog(
        user_id=user_id,
        username=username,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
        old_value=json.dumps(old_value, cls=DateTimeEncoder) if old_value else None,
        new_value=json.dumps(new_value, cls=DateTimeEncoder) if new_value else None,
        keywords=keywords,
        ip_address=ip_address
    )
    
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


# Alias for backward compatibility
log_activity = create_activity_log


def get_activity_logs(
    db: Session,
    limit: int = 100,
    offset: int = 0,
    username: Optional[str] = None,
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search_keywords: Optional[str] = None
) -> List[ActivityLog]:
    """
    Get activity logs with optional filtering
    """
    query = db.query(ActivityLog)
    
    # Apply filters
    if username:
        query = query.filter(ActivityLog.username == username)
    
    if action_type:
        query = query.filter(ActivityLog.action_type == action_type)
    
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    
    if start_date:
        query = query.filter(ActivityLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(ActivityLog.timestamp <= end_date)
    
    if search_keywords:
        query = query.filter(
            (ActivityLog.description.contains(search_keywords)) |
            (ActivityLog.keywords.contains(search_keywords)) |
            (ActivityLog.entity_name.contains(search_keywords))
        )
    
    # Order by most recent first
    query = query.order_by(desc(ActivityLog.timestamp))
    
    # Apply pagination
    return query.offset(offset).limit(limit).all()


def get_lead_history(db: Session, lead_id: int) -> List[ActivityLog]:
    """
    Get all activity logs for a specific lead
    """
    return db.query(ActivityLog).filter(
        and_(
            ActivityLog.entity_type == "Lead",
            ActivityLog.entity_id == lead_id
        )
    ).order_by(desc(ActivityLog.timestamp)).all()


def get_recent_activities(db: Session, limit: int = 10) -> List[ActivityLog]:
    """
    Get the most recent activities for dashboard widget
    """
    return db.query(ActivityLog).order_by(
        desc(ActivityLog.timestamp)
    ).limit(limit).all()


def get_activity_count(
    db: Session,
    username: Optional[str] = None,
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> int:
    """
    Get count of activities matching filters
    """
    query = db.query(ActivityLog)
    
    if username:
        query = query.filter(ActivityLog.username == username)
    
    if action_type:
        query = query.filter(ActivityLog.action_type == action_type)
    
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    
    if start_date:
        query = query.filter(ActivityLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(ActivityLog.timestamp <= end_date)
    
    return query.count()


def get_user_activity_summary(db: Session, username: str, days: int = 7) -> dict:
    """
    Get activity summary for a user over the last N days
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total = get_activity_count(db, username=username, start_date=start_date)
    
    # Count by action type
    action_counts = {}
    for action_type in ["LEAD_CREATED", "LEAD_UPDATED", "LEAD_DELETED", "REFERRAL_MARKED", "REFERRAL_UNMARKED"]:
        count = get_activity_count(
            db,
            username=username,
            action_type=action_type,
            start_date=start_date
        )
        if count > 0:
            action_counts[action_type] = count
    
    return {
        "total_activities": total,
        "action_breakdown": action_counts,
        "period_days": days
    }
