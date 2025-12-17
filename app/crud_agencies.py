from sqlalchemy.orm import Session
from typing import List, Optional
from . import models
from .utils.activity_logger import log_activity

def create_agency(db: Session, name: str, username: str, user_id: Optional[int] = None) -> models.Agency:
    """Create a new agency"""
    agency = models.Agency(name=name, created_by=username)
    db.add(agency)
    db.commit()
    db.refresh(agency)
    
    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action_type="AGENCY_CREATED",
        entity_type="Agency",
        entity_id=agency.id,
        entity_name=agency.name,
        description=f"Agency '{agency.name}' created",
        new_value={"name": agency.name},
        keywords="agency,create"
    )
    
    return agency

def get_agency(db: Session, agency_id: int) -> Optional[models.Agency]:
    return db.query(models.Agency).filter(models.Agency.id == agency_id).first()

def get_agency_by_name(db: Session, name: str) -> Optional[models.Agency]:
    return db.query(models.Agency).filter(models.Agency.name == name).first()

def get_all_agencies(db: Session) -> List[models.Agency]:
    return db.query(models.Agency).order_by(models.Agency.name).all()

def update_agency(db: Session, agency_id: int, name: str, username: str, user_id: Optional[int] = None) -> Optional[models.Agency]:
    """Update an agency name"""
    agency = get_agency(db, agency_id)
    if not agency:
        return None
    
    old_name = agency.name
    if old_name != name:
        agency.name = name
        agency.updated_by = username
        db.commit()
        db.refresh(agency)
        
        # Log activity
        log_activity(
            db=db,
            user_id=user_id,
            username=username,
            action_type="AGENCY_UPDATED",
            entity_type="Agency",
            entity_id=agency.id,
            entity_name=agency.name,
            description=f"Agency updated from '{old_name}' to '{name}'",
            old_value={"name": old_name},
            new_value={"name": name},
            keywords="agency,update"
        )
        
    return agency

def delete_agency(db: Session, agency_id: int, username: str, user_id: Optional[int] = None) -> bool:
    """Delete an agency"""
    agency = get_agency(db, agency_id)
    if not agency:
        return False
    
    name = agency.name
    db.delete(agency)
    db.commit()
    
    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action_type="AGENCY_DELETED",
        entity_type="Agency",
        entity_id=agency_id,
        entity_name=name,
        description=f"Agency '{name}' deleted",
        old_value={"name": name},
        keywords="agency,delete"
    )
    
    return True
