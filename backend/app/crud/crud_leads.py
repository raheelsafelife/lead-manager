# Force Reload
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json

import app.models as models
from app.schemas import LeadCreate, LeadUpdate
# from app.utils.activity_logger import log_activity # Moved to local import


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
    from app.utils.activity_logger import log_activity
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
def get_lead(db: Session, lead_id: int, include_deleted: bool = False):
    """Get a lead by ID, optionally including deleted leads. Eagerly loads relationships."""
    
    query = db.query(models.Lead).options(
        joinedload(models.Lead.agency),
        joinedload(models.Lead.ccu),
        joinedload(models.Lead.mco),
        joinedload(models.Lead.agency_suboption)
    )
    
    # Defensive eager loading
    try:
        query = query.options(joinedload(models.Lead.lead_comments))
    except Exception:
        pass
    
    query = query.filter(models.Lead.id == lead_id)
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
    
    # Defensive eager loading - gracefully handle if relationship unavailable
    try:
        query = query.options(joinedload(models.Lead.lead_comments))
    except Exception:
        pass  # Continue without eager loading if relationship not available
    
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
        from ..utils.activity_logger import log_activity
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
    from ..utils.activity_logger import log_activity
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
    from ..utils.activity_logger import log_activity
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
    query = (
        db.query(models.Lead)
        .options(
            joinedload(models.Lead.agency),
            joinedload(models.Lead.ccu),
            joinedload(models.Lead.mco),
            joinedload(models.Lead.agency_suboption)
        )
    )
    
    # Defensive eager loading
    try:
        query = query.options(joinedload(models.Lead.lead_comments))
    except Exception:
        pass
    
    return (
        query
        .filter(models.Lead.deleted_at != None)
        .order_by(models.Lead.deleted_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def search_leads(
    db: Session,
    search_query: Optional[str] = None,
    staff_filter: Optional[str] = None,
    source_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    active_inactive_filter: Optional[str] = None,
    owner_id: Optional[int] = None,
    only_my_leads: bool = False,
    include_deleted: bool = False,
    exclude_clients: bool = True,
    auth_received_filter: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50
):
    """
    Search leads with comprehensive SQL-level filtering and pagination.
    Super fast performance.
    """
    import app.models as models
    # Centralized reloading in streamlit_app.py handles updates
    
    query = db.query(models.Lead).options(
        joinedload(models.Lead.agency),
        joinedload(models.Lead.ccu),
        joinedload(models.Lead.mco),
        joinedload(models.Lead.agency_suboption)
    )
    
    # Defensive eager loading
    try:
        query = query.options(joinedload(models.Lead.lead_comments))
    except Exception:
        pass
    
    # 1. Deleted State
    if include_deleted:
        query = query.filter(models.Lead.deleted_at != None)
    else:
        query = query.filter(models.Lead.deleted_at == None)
        
    # 2. Exclude active clients (for main leads view)
    if exclude_clients and not include_deleted:
        query = query.filter(models.Lead.active_client == False)
    
    # 2.5 Authorization Received Filter
    if auth_received_filter is not None:
        query = query.filter(models.Lead.authorization_received == auth_received_filter)
    
    # 3. Ownership / My Leads
    if only_my_leads:
        if owner_id:
            query = query.filter(models.Lead.owner_id == owner_id)
        # fallback to staff name if needed is handled via schema usually
        
    # 4. Search Query (Name)
    if search_query:
        search_query = f"%{search_query}%"
        from sqlalchemy import or_
        query = query.filter(or_(
            models.Lead.first_name.ilike(search_query),
            models.Lead.last_name.ilike(search_query)
        ))
        
    # 5. Staff Filter
    if staff_filter:
        query = query.filter(models.Lead.staff_name.ilike(f"%{staff_filter}%"))
        
    # 6. Source Filter
    if source_filter:
        query = query.filter(models.Lead.source.ilike(f"%{source_filter}%"))
        
    # 7. Status Filter
    if status_filter and status_filter != "All":
        query = query.filter(models.Lead.last_contact_status == status_filter)
        
    # 8. Priority Filter
    if priority_filter and priority_filter != "All":
        query = query.filter(models.Lead.priority == priority_filter)
        
    # 9. Active/Inactive Filter
    if active_inactive_filter == "Active":
        query = query.filter(models.Lead.last_contact_status != "Inactive")
    elif active_inactive_filter == "Inactive":
        query = query.filter(models.Lead.last_contact_status == "Inactive")
        
    # 10. Order and Pagination
    return (
        query
        .order_by(models.Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_search_leads(
    db: Session,
    search_query: Optional[str] = None,
    staff_filter: Optional[str] = None,
    source_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    active_inactive_filter: Optional[str] = None,
    owner_id: Optional[int] = None,
    only_my_leads: bool = False,
    include_deleted: bool = False,
    exclude_clients: bool = True,
    auth_received_filter: Optional[bool] = None
) -> int:
    """Returns the total count of leads matching the search criteria (for pagination)"""
    from sqlalchemy import func
    query = db.query(func.count(models.Lead.id))
    
    if include_deleted:
        query = query.filter(models.Lead.deleted_at != None)
    else:
        query = query.filter(models.Lead.deleted_at == None)
        
    if exclude_clients and not include_deleted:
        query = query.filter(models.Lead.active_client == False)
        
    if auth_received_filter is not None:
        query = query.filter(models.Lead.authorization_received == auth_received_filter)
        
    if only_my_leads and owner_id:
        query = query.filter(models.Lead.owner_id == owner_id)
        
    if search_query:
        search_query = f"%{search_query}%"
        from sqlalchemy import or_
        query = query.filter(or_(
            models.Lead.first_name.ilike(search_query),
            models.Lead.last_name.ilike(search_query)
        ))
        
    if staff_filter:
        query = query.filter(models.Lead.staff_name.ilike(f"%{staff_filter}%"))
        
    if source_filter:
        query = query.filter(models.Lead.source.ilike(f"%{source_filter}%"))
        
    if status_filter and status_filter != "All":
        query = query.filter(models.Lead.last_contact_status == status_filter)
        
    if priority_filter and priority_filter != "All":
        query = query.filter(models.Lead.priority == priority_filter)
        
    if active_inactive_filter == "Active":
        query = query.filter(models.Lead.last_contact_status != "Inactive")
    elif active_inactive_filter == "Inactive":
        query = query.filter(models.Lead.last_contact_status == "Inactive")
        
    return query.scalar()
