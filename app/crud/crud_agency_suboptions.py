"""
CRUD operations for Agency Suboptions
"""

from sqlalchemy.orm import Session
from app.models import AgencySuboption
from datetime import datetime
from app.crud import crud_activity_logs


def get_all_suboptions(db: Session, agency_id: int = None):
    """Get all agency suboptions, optionally filtered by agency"""
    query = db.query(AgencySuboption)
    if agency_id:
        query = query.filter(AgencySuboption.agency_id == agency_id)
    return query.order_by(AgencySuboption.name).all()


def get_suboption_by_id(db: Session, suboption_id: int):
    """Get a suboption by ID"""
    return db.query(AgencySuboption).filter(AgencySuboption.id == suboption_id).first()


def get_suboption_by_name_and_agency(db: Session, name: str, agency_id: int):
    """Get a suboption by name and agency"""
    return db.query(AgencySuboption).filter(
        AgencySuboption.name == name,
        AgencySuboption.agency_id == agency_id
    ).first()


def create_suboption(db: Session, name: str, agency_id: int, created_by: str, created_by_id: int):
    """Create a new agency suboption"""
    suboption = AgencySuboption(
        name=name,
        agency_id=agency_id,
        created_at=datetime.utcnow(),
        created_by=created_by
    )
    db.add(suboption)
    db.commit()
    db.refresh(suboption)
    
    # Log activity
    crud_activity_logs.log_activity(
        db=db,
        user_id=created_by_id,
        username=created_by,
        action_type="AGENCY_SUBOPTION_CREATED",
        entity_type="AgencySuboption",
        entity_id=suboption.id,
        description=f"Created agency suboption: {name}"
    )
    
    return suboption


def delete_suboption(db: Session, suboption_id: int, deleted_by: str, deleted_by_id: int):
    """Delete an agency suboption"""
    suboption = get_suboption_by_id(db, suboption_id)
    if suboption:
        suboption_name = suboption.name
        db.delete(suboption)
        db.commit()
        
        # Log activity
        crud_activity_logs.log_activity(
            db=db,
            user_id=deleted_by_id,
            username=deleted_by,
            action_type="AGENCY_SUBOPTION_DELETED",
            entity_type="AgencySuboption",
            entity_id=suboption_id,
            description=f"Deleted agency suboption: {suboption_name}"
        )
        
        return True
    return False


def update_suboption(db: Session, suboption_id: int, name: str, updated_by: str, updated_by_id: int):
    """Update an agency suboption"""
    suboption = get_suboption_by_id(db, suboption_id)
    if suboption:
        old_name = suboption.name
        suboption.name = name
        suboption.updated_at = datetime.utcnow()
        suboption.updated_by = updated_by
        db.commit()
        db.refresh(suboption)
        
        # Log activity
        crud_activity_logs.log_activity(
            db=db,
            user_id=updated_by_id,
            username=updated_by,
            action_type="AGENCY_SUBOPTION_UPDATED",
            entity_type="AgencySuboption",
            entity_id=suboption_id,
            description=f"Updated agency suboption: {old_name} → {name}"
        )
        
        return suboption
    return None
