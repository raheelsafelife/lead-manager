from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json

from .. import models
from ..schemas import LeadCreate, LeadUpdate
from ..utils.activity_logger import log_activity


# ------- CREATE -------
def create_lead(db: Session, lead_in: LeadCreate, username: str = "system", user_id: Optional[int] = None) -> models.Lead:
    """Create a new lead with activity logging"""
    lead = models.Lead(**lead_in.dict())
    
    # Ensure owner_id is set from function argument if not in schema
    if user_id and lead.owner_id is None:
        lead.owner_id = user_id
        
    lead.created_by = lead_in.staff_name
    lead.updated_by = lead_in.staff_name
    
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    # Log the activity - use the passed in username/user_id or defaults
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action_type="LEAD_CREATED",
        entity_type="Lead",
        entity_id=lead.id,
        entity_name=f"{lead.first_name} {lead.last_name}",
        description=f"Lead '{lead.first_name} {lead.last_name}' created",
        new_value=lead_in.dict(),
        keywords=f"lead,create,{lead.source.lower()}"
    )
    
    return lead


# ------- READ -------
def get_lead(db: Session, lead_id: int, include_deleted: bool = False) -> Optional[models.Lead]:
    """Get a lead by ID, optionally including deleted leads"""
    query = db.query(models.Lead).filter(models.Lead.id == lead_id)
    if not include_deleted:
        query = query.filter(models.Lead.deleted_at == None)
    return query.first()


def check_duplicate_lead(db: Session, first_name: str, last_name: str, phone: str) -> Optional[models.Lead]:
    """Check if a lead with the same name and phone already exists (excluding deleted)"""
    return db.query(models.Lead).filter(
        models.Lead.first_name == first_name,
        models.Lead.last_name == last_name,
        models.Lead.phone == phone,
        models.Lead.deleted_at == None
    ).first()


def list_leads(db: Session, skip: int = 0, limit: int = 50, include_deleted: bool = False) -> List[models.Lead]:
    """List leads, optionally including deleted ones. Eagerly loads relationships for caching."""
    query = db.query(models.Lead).options(
        joinedload(models.Lead.agency),
        joinedload(models.Lead.ccu),
        joinedload(models.Lead.mco),
        joinedload(models.Lead.agency_suboption)
    )
    if not include_deleted:
        query = query.filter(models.Lead.deleted_at == None)
    return (
        query
        .order_by(models.Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ------- UPDATE -------
def update_lead(
    db: Session, 
    lead_id: int, 
    lead_in: LeadUpdate, 
    username: str, 
    user_id: Optional[int] = None
) -> Optional[models.Lead]:
    """Update a lead with activity logging and change tracking"""
    lead = get_lead(db, lead_id)
    if not lead:
        return None
    
    # Capture old values for change tracking
    old_values = {}
    new_values = {}
    changes_made = False
    
    for field, value in lead_in.dict(exclude_unset=True).items():
        old_value = getattr(lead, field)
        if old_value != value:
            old_values[field] = old_value
            new_values[field] = value
            changes_made = True
            setattr(lead, field, value)
    
    if changes_made:
        lead.updated_by = username
        db.commit()
        db.refresh(lead)
        
        # Determine action type based on what changed
        action_type = "LEAD_UPDATED"
        keywords = ["lead", "update"]
        
        # Special handling for referral changes
        if "active_client" in new_values:
            if new_values["active_client"]:
                action_type = "REFERRAL_MARKED"
                keywords.append("referral")
            else:
                action_type = "REFERRAL_UNMARKED"
                keywords.append("referral")
        
        # Special handling for status changes
        elif "last_contact_status" in new_values:
            action_type = "STATUS_CHANGED"
            keywords.append("status")
            
        # Special handling for agency changes
        elif "agency_id" in new_values:
            action_type = "AGENCY_ASSIGNED"
            keywords.append("agency")
        
        # Log the activity
        log_activity(
            db=db,
            user_id=user_id,
            username=username,
            action_type=action_type,
            entity_type="Lead",
            entity_id=lead.id,
            entity_name=f"{lead.first_name} {lead.last_name}",
            description=f"Lead '{lead.first_name} {lead.last_name}' updated",
            old_value=old_values,
            new_value=new_values,
            keywords=",".join(keywords)
        )
    
    return lead


# ------- DELETE -------
def delete_lead(db: Session, lead_id: int, username: str, user_id: Optional[int] = None, permanent: bool = False) -> bool:
    """Soft delete a lead (move to recycle bin) or permanently delete"""
    lead = get_lead(db, lead_id, include_deleted=True)
    if not lead:
        return False
    
    # Capture lead info before deletion
    lead_name = f"{lead.first_name} {lead.last_name}"
    lead_data = {
        "name": lead_name,
        "source": lead.source,
        "staff_name": lead.staff_name
    }
    
    if permanent:
        # Permanent deletion
        db.delete(lead)
        action_type = "LEAD_PERMANENTLY_DELETED"
        description = f"Lead '{lead_name}' permanently deleted"
    else:
        # Soft delete - move to recycle bin
        from datetime import datetime
        lead.deleted_at = datetime.utcnow()
        lead.deleted_by = username
        action_type = "LEAD_DELETED"
        description = f"Lead '{lead_name}' moved to recycle bin"
    
    db.commit()
    
    # Log the activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action_type=action_type,
        entity_type="Lead",
        entity_id=lead_id,
        entity_name=lead_name,
        description=description,
        old_value=lead_data,
        keywords="lead,delete"
    )
    
    return True


def restore_lead(db: Session, lead_id: int, username: str, user_id: Optional[int] = None) -> bool:
    """Restore a deleted lead from recycle bin"""
    lead = get_lead(db, lead_id, include_deleted=True)
    if not lead or not lead.deleted_at:
        return False
    
    lead_name = f"{lead.first_name} {lead.last_name}"
    lead.deleted_at = None
    lead.deleted_by = None
    db.commit()
    
    # Log the activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action_type="LEAD_RESTORED",
        entity_type="Lead",
        entity_id=lead_id,
        entity_name=lead_name,
        description=f"Lead '{lead_name}' restored from recycle bin",
        keywords="lead,restore,recycle"
    )
    
    return True


def list_deleted_leads(db: Session, skip: int = 0, limit: int = 50) -> List[models.Lead]:
    """List only deleted leads (recycle bin). Eagerly loads relationships for caching."""
    return (
        db.query(models.Lead)
        .options(
            joinedload(models.Lead.agency),
            joinedload(models.Lead.ccu),
            joinedload(models.Lead.mco),
            joinedload(models.Lead.agency_suboption)
        )
        .filter(models.Lead.deleted_at != None)
        .order_by(models.Lead.deleted_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
