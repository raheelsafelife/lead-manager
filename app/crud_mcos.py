"""
CRUD operations for MCO (Managed Care Organization) management
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from . import models
from .crud_activity_logs import create_activity_log


def get_all_mcos(db: Session) -> List[models.MCO]:
    """Get all MCOs"""
    return db.query(models.MCO).order_by(models.MCO.name).all()


def get_mco_by_id(db: Session, mco_id: int) -> Optional[models.MCO]:
    """Get an MCO by ID"""
    return db.query(models.MCO).filter(models.MCO.id == mco_id).first()


def get_mco_by_name(db: Session, name: str) -> Optional[models.MCO]:
    """Get an MCO by name"""
    return db.query(models.MCO).filter(models.MCO.name == name).first()


def create_mco(
    db: Session,
    name: str,
    username: str,
    user_id: int = None
) -> models.MCO:
    """Create a new MCO"""
    new_mco = models.MCO(
        name=name,
        created_by=username,
        created_at=datetime.utcnow()
    )
    db.add(new_mco)
    db.commit()
    db.refresh(new_mco)
    
    # Log the activity
    create_activity_log(
        db=db,
        user_id=user_id,
        username=username,
        action_type="CREATE",
        entity_type="MCO",
        entity_id=new_mco.id,
        entity_name=name,
        description=f"Created MCO: {name}",
        keywords=f"mco,create,{name}"
    )
    
    return new_mco


def update_mco(
    db: Session,
    mco_id: int,
    name: str,
    username: str,
    user_id: int = None
) -> Optional[models.MCO]:
    """Update an MCO"""
    mco = get_mco_by_id(db, mco_id)
    if not mco:
        return None
    
    old_name = mco.name
    mco.name = name
    mco.updated_by = username
    mco.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(mco)
    
    # Log the activity
    create_activity_log(
        db=db,
        user_id=user_id,
        username=username,
        action_type="UPDATE",
        entity_type="MCO",
        entity_id=mco.id,
        entity_name=name,
        description=f"Updated MCO: {old_name} → {name}",
        old_value={"name": old_name},
        new_value={"name": name},
        keywords=f"mco,update,{name}"
    )
    
    return mco


def delete_mco(
    db: Session,
    mco_id: int,
    username: str,
    user_id: int = None
) -> bool:
    """Delete an MCO"""
    mco = get_mco_by_id(db, mco_id)
    if not mco:
        return False
    
    mco_name = mco.name
    
    # Check if MCO is being used by any leads
    lead_count = db.query(models.Lead).filter(models.Lead.mco_id == mco_id).count()
    if lead_count > 0:
        # Don't delete, but could raise an exception or return False with a message
        return False
    
    db.delete(mco)
    db.commit()
    
    # Log the activity
    create_activity_log(
        db=db,
        user_id=user_id,
        username=username,
        action_type="DELETE",
        entity_type="MCO",
        entity_id=mco_id,
        entity_name=mco_name,
        description=f"Deleted MCO: {mco_name}",
        keywords=f"mco,delete,{mco_name}"
    )
    
    return True
