"""
CRUD operations for CCUs (Community Care Units)
"""

from sqlalchemy.orm import Session
from app.models import CCU
from datetime import datetime
from app.crud import crud_activity_logs


def get_all_ccus(db: Session):
    """Get all CCUs"""
    return db.query(CCU).order_by(CCU.name).all()


def get_ccu_by_id(db: Session, ccu_id: int):
    """Get a CCU by ID"""
    return db.query(CCU).filter(CCU.id == ccu_id).first()


def get_ccu_by_name(db: Session, name: str):
    """Get a CCU by name"""
    return db.query(CCU).filter(CCU.name == name).first()


def create_ccu(db: Session, name: str, created_by: str, created_by_id: int, 
               address: str = None, street: str = None, city: str = None, 
               state: str = None, zip_code: str = None,
               phone: str = None, fax: str = None, email: str = None, 
               care_coordinator_name: str = None):
    """Create a new CCU"""
    # Auto-format address if components provided but full address is missing
    if not address and (street or city or state or zip_code):
        parts = [p for p in [street, city, state, zip_code] if p]
        address = ", ".join(parts)
        
    ccu = CCU(
        name=name,
        address=address,
        street=street,
        city=city,
        state=state,
        zip_code=zip_code,
        phone=phone,
        fax=fax,
        email=email,
        care_coordinator_name=care_coordinator_name,
        created_at=datetime.utcnow(),
        created_by=created_by
    )
    db.add(ccu)
    db.commit()
    db.refresh(ccu)
    
    # Log activity
    crud_activity_logs.log_activity(
        db=db,
        user_id=created_by_id,
        username=created_by,
        action_type="CCU_CREATED",
        entity_type="CCU",
        entity_id=ccu.id,
        entity_name=name,
        description=f"Created CCU: {name}"
    )
    
    return ccu


def delete_ccu(db: Session, ccu_id: int, deleted_by: str, deleted_by_id: int):
    """Delete a CCU"""
    ccu = get_ccu_by_id(db, ccu_id)
    if ccu:
        ccu_name = ccu.name
        db.delete(ccu)
        db.commit()
        
        # Log activity
        crud_activity_logs.log_activity(
            db=db,
            user_id=deleted_by_id,
            username=deleted_by,
            action_type="CCU_DELETED",
            entity_type="CCU",
            entity_id=ccu_id,
            entity_name=ccu_name,
            description=f"Deleted CCU: {ccu_name}"
        )
        
        return True
    return False


def update_ccu(db: Session, ccu_id: int, name: str, updated_by: str, updated_by_id: int,
               address: str = None, street: str = None, city: str = None,
               state: str = None, zip_code: str = None,
               phone: str = None, fax: str = None, email: str = None,
               care_coordinator_name: str = None):
    """Update a CCU"""
    # Auto-format address if components provided but full address is missing
    if not address and (street or city or state or zip_code):
        parts = [p for p in [street, city, state, zip_code] if p]
        address = ", ".join(parts)
        
    ccu = get_ccu_by_id(db, ccu_id)
    if ccu:
        old_name = ccu.name
        ccu.name = name
        ccu.address = address
        ccu.street = street
        ccu.city = city
        ccu.state = state
        ccu.zip_code = zip_code
        ccu.phone = phone
        ccu.fax = fax
        ccu.email = email
        ccu.care_coordinator_name = care_coordinator_name
        ccu.updated_at = datetime.utcnow()
        ccu.updated_by = updated_by
        db.commit()
        db.refresh(ccu)
        
        # Log activity
        crud_activity_logs.log_activity(
            db=db,
            user_id=updated_by_id,
            username=updated_by,
            action_type="CCU_UPDATED",
            entity_type="CCU",
            entity_id=ccu_id,
            entity_name=name,
            description=f"Updated CCU: {old_name} -> {name}"
        )
        
        return ccu
    return None
