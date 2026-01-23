from sqlalchemy.orm import Session
from typing import Optional
import app.models as models
from ..utils.activity_logger import log_activity


def create_event(db: Session, event_name: str, created_by: str, user_id: Optional[int] = None):
    """Create a new event with logging"""
    event = models.Event(
        event_name=event_name,
        created_by=created_by,
        updated_by=created_by
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=created_by,
        action_type="EVENT_CREATED",
        entity_type="Event",
        entity_id=event.id,
        entity_name=event_name,
        description=f"Event '{event_name}' created",
        new_value={"event_name": event_name},
        keywords="event,create"
    )
    
    return event


def get_all_events(db: Session):
    """Get all events"""
    return db.query(models.Event).order_by(models.Event.event_name).all()


def get_event_by_name(db: Session, event_name: str):
    """Get event by name"""
    return db.query(models.Event).filter(models.Event.event_name == event_name).first()


def delete_event(db: Session, event_id: int, username: str, user_id: Optional[int] = None):
    """Delete an event with logging"""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if event:
        event_name = event.event_name
        db.delete(event)
        db.commit()
        
        # Log activity
        log_activity(
            db=db,
            user_id=user_id,
            username=username,
            action_type="EVENT_DELETED",
            entity_type="Event",
            entity_id=event_id,
            entity_name=event_name,
            description=f"Event '{event_name}' deleted",
            old_value={"event_name": event_name},
            keywords="event,delete"
        )
        return True
    return False


def update_event(db: Session, event_id: int, new_event_name: str, username: str, user_id: Optional[int] = None):
    """Update an event name with logging"""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        return None
    
    # Check if new name already exists
    existing = get_event_by_name(db, new_event_name)
    if existing and existing.id != event_id:
        raise ValueError(f"Event name '{new_event_name}' already exists")
    
    old_name = event.event_name
    event.event_name = new_event_name
    event.updated_by = username
    
    db.commit()
    db.refresh(event)
    
    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action_type="EVENT_UPDATED",
        entity_type="Event",
        entity_id=event.id,
        entity_name=new_event_name,
        description=f"Event updated from '{old_name}' to '{new_event_name}'",
        old_value={"event_name": old_name},
        new_value={"event_name": new_event_name},
        keywords="event,update"
    )
    
    return event
