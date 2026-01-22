"""
Activity Logger Utility Functions
Professional helpers for logging activities with beautiful formatting
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
# from app.crud import crud_activity_logs # Moved to local import
import json
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


def log_activity(
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
    keywords: Optional[str] = None
):
    """
    Main logging function - call this to log any activity
    
    Example:
        log_activity(
            db=db,
            user_id=1,
            username="john_smith",
            action_type="LEAD_CREATED",
            entity_type="Lead",
            entity_id=123,
            entity_name="Jane Doe",
            description="Lead 'Jane Doe' created",
            new_value={"source": "Event", "status": "Intro Call"},
            keywords="lead,create,event"
        )
    """
    from app.crud import crud_activity_logs
    return crud_activity_logs.create_activity_log(
        db=db,
        user_id=user_id,
        username=username,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
        old_value=old_value,
        new_value=new_value,
        keywords=keywords
    )


def utc_to_local(utc_dt: datetime, tz_name: Optional[str] = None) -> datetime:
    """
    Convert naive UTC datetime to local system time or specified timezone
    """
    if utc_dt is None:
        return None
    
    # Add UTC timezone info if missing
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    if tz_name:
        try:
            return utc_dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass
            
    # Convert to Central Time as requested by user
    return utc_dt.astimezone(ZoneInfo("America/Chicago"))


def format_time_ago(timestamp: datetime, tz_name: Optional[str] = None) -> str:
    """
    Convert timestamp to human-readable relative time
    
    Examples:
        - "2 minutes ago"
        - "1 hour ago"
        - "Today at 2:15 PM"
        - "Yesterday at 10:30 AM"
        - "12/08/2025 at 3:45 PM"
    """
    if timestamp is None:
        return ""
        
    # Ensure timestamp is UTC-aware for comparison
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        
    now_utc = datetime.now(timezone.utc)
    diff = now_utc - timestamp
    
    # Convert to local time for display
    local_timestamp = utc_to_local(timestamp, tz_name)
    
    # Get local "now" for date comparison
    if tz_name:
        try:
            local_now = datetime.now(ZoneInfo(tz_name))
        except Exception:
            local_now = datetime.now().astimezone()
    else:
        local_now = datetime.now().astimezone()
    
    # Less than 1 minute
    if diff.total_seconds() < 60:
        return "Just now"
    
    # Less than 1 hour
    if diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    # Less than 24 hours (today or yesterday)
    if diff.total_seconds() < 86400 * 2:
        if local_timestamp.date() == local_now.date():
            return f"Today at {local_timestamp.strftime('%I:%M %p')}"
        elif (local_now.date() - local_timestamp.date()).days == 1:
            return f"Yesterday at {local_timestamp.strftime('%I:%M %p')}"
    
    # Less than 7 days
    if diff.total_seconds() < 604800:
        days = (local_now.date() - local_timestamp.date()).days
        if days == 1:
            return f"Yesterday at {local_timestamp.strftime('%I:%M %p')}"
        return f"{days} days ago"
    
    # Older than 7 days
    return local_timestamp.strftime("%m/%d/%Y at %I:%M %p")


def get_time_color(timestamp: datetime) -> str:
    """
    Get color code based on how recent the activity is
    Returns: 'success' (green), 'info' (blue), or 'secondary' (gray)
    """
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.total_seconds() < 3600:  # Last hour
        return "success"  # Green
    elif diff.total_seconds() < 86400:  # Last 24 hours
        return "info"  # Blue
    else:
        return "secondary"  # Gray


def get_action_icon(action_type: str) -> str:
    """
    Get emoji icon for action type
    """
    icons = {
        "LEAD_CREATED": "",
        "LEAD_UPDATED": "",
        "LEAD_DELETED": "",
        "STATUS_CHANGED": "",
        "REFERRAL_MARKED": "",
        "REFERRAL_UNMARKED": "",
        "COMMENT_ADDED": "",
        "USER_LOGIN": "",
        "USER_LOGOUT": "",
        "PASSWORD_CHANGED": "",
        "USER_CREATED": "",
        "USER_APPROVED": "",
        "USER_REJECTED": "",
        "EVENT_CREATED": "",
        "EVENT_UPDATED": "",
        "EVENT_DELETED": "",
    }
    return icons.get(action_type, "")


def get_action_label(action_type: str) -> str:
    """
    Get human-readable label for action type
    """
    labels = {
        "LEAD_CREATED": "Lead Created",
        "LEAD_UPDATED": "Lead Updated",
        "LEAD_DELETED": "Lead Deleted",
        "STATUS_CHANGED": "Status Changed",
        "REFERRAL_MARKED": "Referral Marked",
        "REFERRAL_UNMARKED": "Referral Unmarked",
        "COMMENT_ADDED": "Comment Added",
        "USER_LOGIN": "User Login",
        "USER_LOGOUT": "User Logout",
        "PASSWORD_CHANGED": "Password Changed",
        "USER_CREATED": "User Created",
        "USER_APPROVED": "User Approved",
        "USER_REJECTED": "User Rejected",
        "EVENT_CREATED": "Event Created",
        "EVENT_UPDATED": "Event Updated",
        "EVENT_DELETED": "Event Deleted",
    }
    return labels.get(action_type, action_type.replace("_", " ").title())


def get_entity_badge_color(entity_type: str) -> str:
    """
    Get badge color for entity type
    """
    colors = {
        "Lead": "blue",
        "User": "green",
        "Event": "purple",
        "Referral": "orange",
    }
    return colors.get(entity_type, "gray")


def format_changes(old_value: Optional[str], new_value: Optional[str]) -> list:
    """
    Format old/new values into a list of changes
    Returns list of tuples: [(field, old, new), ...]
    """
    if not old_value or not new_value:
        return []
    
    try:
        old_dict = json.loads(old_value) if isinstance(old_value, str) else old_value
        new_dict = json.loads(new_value) if isinstance(new_value, str) else new_value
        
        changes = []
        for key in new_dict:
            if key in old_dict and old_dict[key] != new_dict[key]:
                # Format field name
                field_name = key.replace("_", " ").title()
                old_val = str(old_dict[key]) if old_dict[key] is not None else "None"
                new_val = str(new_dict[key]) if new_dict[key] is not None else "None"
                changes.append((field_name, old_val, new_val))
        
        return changes
    except:
        return []


def get_activity_summary_text(activity) -> str:
    """
    Generate a concise summary text for an activity (for dashboard widget)
    """
    icon = get_action_icon(activity.action_type)
    time_ago = format_time_ago(activity.timestamp)
    
    if activity.entity_name:
        return f"{icon} {activity.entity_name} - {get_action_label(activity.action_type)} ({time_ago})"
    else:
        return f"{icon} {get_action_label(activity.action_type)} by {activity.username} ({time_ago})"
