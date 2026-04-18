# Force Reload
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
import re

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
    
    # Auto-populate Employee ID based on staff_name
    if lead_in.staff_name:
        from app.crud.crud_users import get_user_by_username
        user_prof = get_user_by_username(db, lead_in.staff_name)
        if user_prof and user_prof.user_id:
            lead.custom_user_id = user_prof.user_id
    
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

    # Send notification to assigned staff
    if lead.staff_name:
        from app.crud.crud_users import get_user_by_username
        from app.crud.crud_notifications import create_notification
        
        assignee = get_user_by_username(db, lead.staff_name)
        if assignee:
            create_notification(
                db=db,
                user_id=assignee.id,
                title="New Lead Assigned",
                description=f"You have been assigned a new lead: {lead.first_name} {lead.last_name}",
                entity_id=lead.id,
                entity_type="Lead"
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


def _normalize_phone(phone: str) -> str:
    """Strip all non-digit characters from a phone number for comparison"""
    return re.sub(r'\D', '', phone or '')


def check_duplicate_lead(db: Session, first_name: str, last_name: str, phone: str) -> Optional[models.Lead]:
    """
    Check if a non-deleted lead with the same name and phone already exists.
    - Names are compared case-insensitively.
    - Phone is normalized (digits only) before comparison.
    Returns the first matching lead, or None.
    """
    norm_phone = _normalize_phone(phone)
    candidates = db.query(models.Lead).filter(
        models.Lead.first_name.ilike(first_name),
        models.Lead.last_name.ilike(last_name),
        models.Lead.deleted_at == None
    ).all()
    for lead in candidates:
        if _normalize_phone(lead.phone) == norm_phone:
            return lead
    return None


def check_deleted_duplicate_lead(db: Session, first_name: str, last_name: str, phone: str) -> Optional[models.Lead]:
    """
    Check if a SOFT-DELETED lead with the same name and phone exists in the recycle bin.
    Used to offer restoration instead of creating a brand-new record.
    - Names are compared case-insensitively.
    - Phone is normalized (digits only) before comparison.
    Returns the first matching deleted lead, or None.
    """
    norm_phone = _normalize_phone(phone)
    candidates = db.query(models.Lead).filter(
        models.Lead.first_name.ilike(first_name),
        models.Lead.last_name.ilike(last_name),
        models.Lead.deleted_at != None
    ).all()
    for lead in candidates:
        if _normalize_phone(lead.phone) == norm_phone:
            return lead
    return None


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
        
        # Independent check for staff assignment changes
        if "staff_name" in new_values:
            from app.crud.crud_users import get_user_by_username
            from app.crud.crud_notifications import create_notification
            
            new_staff = new_values["staff_name"]
            user_prof = get_user_by_username(db, new_staff)
            
            # Auto-populate Employee ID if found
            if user_prof:
                if user_prof.user_id:
                    lead.custom_user_id = user_prof.user_id
                    new_values["custom_user_id"] = user_prof.user_id
                
                # Notification logic
                create_notification(
                    db=db,
                    user_id=user_prof.id,
                    title="Lead Assigned to You",
                    description=f"Lead '{lead.first_name} {lead.last_name}' has been assigned to you by {username}",
                    entity_id=lead.id,
                    entity_type="Lead"
                )
            action_type = "LEAD_ASSIGNED"
            keywords.append("assignment")

        # Independent check for referral changes
        if "active_client" in new_values:
            if new_values["active_client"]:
                action_type = "REFERRAL_MARKED"
                keywords.append("referral")
            else:
                action_type = "REFERRAL_UNMARKED"
                keywords.append("referral")
        
        # Independent check for status changes
        if "last_contact_status" in new_values:
            action_type = "STATUS_CHANGED"
            keywords.append("status")
            
            
            
        # Independent check for agency changes
        if "agency_id" in new_values:
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
    only_clients: bool = False,
    auth_received_filter: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    city_filter: Optional[str] = None,
    zip_filter: Optional[str] = None,
    lead_id_filter: Optional[int] = None,
    lead_id_search: Optional[str] = None,  # Partial ID text search (ILIKE)
    lead_type_filter: Optional[str] = None, # "Lead", "Initial Referral Sent", "Referral Confirmed"
    referral_category_filter: Optional[str] = None,
    care_status_filter: Optional[str] = None,
    care_sub_status_filter: Optional[str] = None,
    tag_color_filter: Optional[str] = None,
    caregiver_type_filter: Optional[str] = None,
    ccu_filter: Optional[str] = None,
    agency_filter: Optional[str] = None,
    sort_by: str = "Newest Added"
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
        
    # 1.5 Lead Type Shorthands
    if lead_type_filter == "Referral Sent":
        only_clients = True
        auth_received_filter = False
    elif lead_type_filter == "Referral Confirmed": # Authorizations Received
        only_clients = True
        auth_received_filter = True
    elif lead_type_filter == "Lead":
        only_clients = False
        exclude_clients = True
        
    # 2. Client State
    if only_clients:
        query = query.filter(models.Lead.active_client == True)
    elif exclude_clients and not include_deleted:
        query = query.filter(models.Lead.active_client == False)
    
    # 2.5 Authorization Received Filter
    if auth_received_filter is not None:
        query = query.filter(models.Lead.authorization_received == auth_received_filter)
    
    # 3. Ownership / My Leads
    if only_my_leads:
        if owner_id:
            query = query.filter(models.Lead.owner_id == owner_id)
        # fallback to staff name if needed is handled via schema usually
        
    # 3.5 Lead ID Filter — exact match for URL-navigation (e.g. from suggestion clicks)
    if lead_id_filter:
        query = query.filter(models.Lead.id == lead_id_filter)

    # 3.6 Partial ID Search — ILIKE on CAST(id, text) for search boxes
    # Only applied when no exact id filter is present so they don't conflict
    elif lead_id_search and lead_id_search.strip():
        from sqlalchemy import cast, String as SAString
        query = query.filter(
            cast(models.Lead.id, SAString).ilike(f"%{lead_id_search.strip()}%")
        )

    # 4. Smart Multi-Token Name Search
    # ─────────────────────────────────────────────────────────────────────────
    # Tokenize the raw query so that multi-word input like "Robert Raheel"
    # is split into ["robert", "raheel"] and BOTH tokens must be found
    # somewhere in the record (AND logic).  Single-word input continues to
    # work exactly as before (one token → standard partial ILIKE).
    # Fields searched per token: first_name, last_name, concatenated full
    # name (forward and reversed), phone, email, medicaid_no, custom_user_id.
    # ─────────────────────────────────────────────────────────────────────────
    if search_query:
        from sqlalchemy import or_, and_, func, cast, String as SAString
        # Normalize: trim, lowercase, collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', search_query.strip()).lower()
        tokens = [t for t in normalized.split() if t]  # drop empty strings

        if tokens:
            # Build a lower-cased full-name expression (first last) and its reverse
            full_name_expr = func.lower(
                models.Lead.first_name + ' ' + models.Lead.last_name
            )
            full_name_rev_expr = func.lower(
                models.Lead.last_name + ' ' + models.Lead.first_name
            )

            token_conditions = []
            for token in tokens:
                tok_pat = f"%{token}%"
                # Each token must appear in at least ONE of these fields
                token_conditions.append(or_(
                    models.Lead.first_name.ilike(tok_pat),
                    models.Lead.last_name.ilike(tok_pat),
                    full_name_expr.ilike(tok_pat),
                    full_name_rev_expr.ilike(tok_pat),
                    models.Lead.phone.ilike(tok_pat),
                    models.Lead.email.ilike(tok_pat),
                    models.Lead.medicaid_no.ilike(tok_pat),
                    models.Lead.custom_user_id.ilike(tok_pat),
                ))

            # ALL token conditions must hold (AND across tokens)
            query = query.filter(and_(*token_conditions))
        
    # 5. Staff Filter
    if staff_filter:
        query = query.filter(models.Lead.staff_name.ilike(f"%{staff_filter}%"))
        
    # 6. Source Filter
    if source_filter:
        query = query.filter(models.Lead.source.ilike(f"%{source_filter}%"))
        
    # 7. Status Filter
    if status_filter and status_filter != "All":
        if status_filter in ["Initial Referral Sent", "Referral Sent"]:
            from sqlalchemy import or_
            query = query.filter(models.Lead.last_contact_status.in_(["Initial Referral Sent", "Referral Sent"]))
        else:
            query = query.filter(models.Lead.last_contact_status == status_filter)
        
    # 7.5 Referral Category Filter (Regular/Interim)
    if referral_category_filter and referral_category_filter != "All":
        query = query.filter(models.Lead.referral_type == referral_category_filter)
    if priority_filter and priority_filter != "All":
        if priority_filter == "Not Called":
            from sqlalchemy import or_
            query = query.filter(or_(models.Lead.priority == "Not Called", models.Lead.priority == None))
        else:
            query = query.filter(models.Lead.priority == priority_filter)
        
    # 8.5 Tag Color Filter
    if tag_color_filter and tag_color_filter != "All":
        query = query.filter(models.Lead.tag_color == tag_color_filter)
        
    # 8.6 Caregiver Type Filter
    if caregiver_type_filter and caregiver_type_filter != "All":
        if caregiver_type_filter == "None":
            from sqlalchemy import or_
            query = query.filter(or_(models.Lead.caregiver_type == None, models.Lead.caregiver_type == "", models.Lead.caregiver_type == "None"))
        else:
            query = query.filter(models.Lead.caregiver_type == caregiver_type_filter)
            
    # 8.7 Agency / CCU Filter
    if agency_filter and agency_filter != "All":
        query = query.join(models.Agency, isouter=True).filter(models.Agency.name == agency_filter)
        
    if ccu_filter and ccu_filter != "All":
        query = query.join(models.CCU, isouter=True).filter(models.CCU.name == ccu_filter)
            
    # 9. Active/Inactive Filter
    if only_clients:
        inactive_statuses = ["Not Approved", "Services Refused", "Inactive", "Not Interested"]
        if active_inactive_filter == "Active":
            query = query.filter(~models.Lead.last_contact_status.in_(inactive_statuses))
        elif active_inactive_filter == "Inactive":
            query = query.filter(models.Lead.last_contact_status.in_(inactive_statuses))
    else:
        if active_inactive_filter == "Active":
            query = query.filter(~models.Lead.last_contact_status.in_(["Inactive", "Not Interested"]))
        elif active_inactive_filter == "Inactive":
            query = query.filter(models.Lead.last_contact_status.in_(["Inactive", "Not Interested"]))
        
    # 10. Advanced Filters (City / Zip)
    if city_filter:
        from sqlalchemy import or_
        query = query.filter(or_(
            models.Lead.city.ilike(f"%{city_filter}%"),
            models.CCU.city.ilike(f"%{city_filter}%")
        )).join(models.CCU, isouter=True)
        
    if zip_filter:
        from sqlalchemy import or_
        query = query.filter(or_(
            models.Lead.zip_code.ilike(f"%{zip_filter}%"),
            models.CCU.zip_code.ilike(f"%{zip_filter}%")
        )).join(models.CCU, isouter=True)
        
    if lead_id_filter:
        query = query.filter(models.Lead.id == lead_id_filter)
        
    # 11. Care Status Filter (for Authorizations Received / Confirmations page)
    if care_status_filter:
        from sqlalchemy import or_
        if care_status_filter == "Active":
            # Active means NOT Hold, NOT Terminated, NOT Deceased, and NOT Transfer Received
            query = query.filter(or_(
                models.Lead.care_status == None,
                ~models.Lead.care_status.in_(["Hold", "Terminated", "Deceased", "Transfer Received"])
            ))
            
            # REFINED: If source is Transfer, it ONLY shows in Active if care_status is "Care Start"
            # Cases with source "Transfer" OR care_status "Transfer Received" are hidden from Active
            query = query.filter(or_(
                models.Lead.source != "Transfer",
                models.Lead.care_status == "Care Start"
            ))
            
            # Apply sub-filter if Active
            if care_sub_status_filter and care_sub_status_filter != "All":
                query = query.filter(models.Lead.care_status == care_sub_status_filter)
                
        elif care_status_filter == "Transfer":
            # Dedicated filter for Transfer cases (either by source OR by care_status)
            from sqlalchemy import and_
            query = query.filter(or_(
                models.Lead.care_status.ilike("%Transfer%"),
                and_(models.Lead.source == "Transfer", models.Lead.care_status != "Care Start")
            ))
        elif care_status_filter == "Inactive":
            query = query.filter(models.Lead.care_status.in_(["Hold", "Terminated", "Deceased"]))
            # Apply sub-filter if Inactive
            if care_sub_status_filter and care_sub_status_filter != "All":
                query = query.filter(models.Lead.care_status == care_sub_status_filter)
        elif care_status_filter in ["Hold", "Terminated", "Deceased"]:
            query = query.filter(models.Lead.care_status == care_status_filter)
        elif care_status_filter != "All":
            query = query.filter(models.Lead.care_status == care_status_filter)
        
            
            
    # 10.6 Lead Type Filter
    if lead_type_filter and lead_type_filter != "All":
        if lead_type_filter == "Lead":
            query = query.filter(models.Lead.active_client == False)
        elif lead_type_filter == "Initial Referral Sent":
            query = query.filter(models.Lead.active_client == True, models.Lead.authorization_received == False)
        elif lead_type_filter == "Referral Confirmed":
            query = query.filter(models.Lead.active_client == True, models.Lead.authorization_received == True)
            
    # 10.7 Referral Category Filter
    if referral_category_filter and referral_category_filter != "All":
        if referral_category_filter == "Regular":
            from sqlalchemy import or_
            query = query.filter(or_(models.Lead.referral_type == "Regular", models.Lead.referral_type == None, models.Lead.referral_type == ""))
        elif referral_category_filter == "Interim":
            query = query.filter(models.Lead.referral_type == "Interim")
        
        
    # 11. Order and Pagination
    if sort_by == "Recently Updated":
        query = query.order_by(models.Lead.updated_at.desc())
    else:
        # Default: Newest Added
        query = query.order_by(models.Lead.created_at.desc())
        
    return (
        query
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
    only_clients: bool = False,
    auth_received_filter: Optional[bool] = None,
    city_filter: Optional[str] = None,
    zip_filter: Optional[str] = None,
    lead_id_filter: Optional[int] = None,
    lead_id_search: Optional[str] = None,  # Partial ID text search (ILIKE)
    lead_type_filter: Optional[str] = None,
    referral_category_filter: Optional[str] = None,
    care_status_filter: Optional[str] = None,
    care_sub_status_filter: Optional[str] = None,
    tag_color_filter: Optional[str] = None,
    caregiver_type_filter: Optional[str] = None,
    ccu_filter: Optional[str] = None,
    agency_filter: Optional[str] = None
) -> int:
    """Returns the total count of leads matching the search criteria (for pagination)"""
    from sqlalchemy import func
    query = db.query(func.count(models.Lead.id))
    
    if include_deleted:
        query = query.filter(models.Lead.deleted_at != None)
    else:
        query = query.filter(models.Lead.deleted_at == None)
        
    # 1.5 Lead Type Shorthands
    if lead_type_filter == "Referral Sent":
        only_clients = True
        auth_received_filter = False
    elif lead_type_filter == "Referral Confirmed": # Authorizations Received
        only_clients = True
        auth_received_filter = True
    elif lead_type_filter == "Lead":
        only_clients = False
        exclude_clients = True
        
    if only_clients:
        query = query.filter(models.Lead.active_client == True)
    elif exclude_clients and not include_deleted:
        query = query.filter(models.Lead.active_client == False)
        
    if auth_received_filter is not None:
        query = query.filter(models.Lead.authorization_received == auth_received_filter)
        
    if only_my_leads and owner_id:
        query = query.filter(models.Lead.owner_id == owner_id)
        
    # Exact ID filter (URL navigation)
    if lead_id_filter:
        query = query.filter(models.Lead.id == lead_id_filter)

    # Partial ID search (ILIKE on cast)
    elif lead_id_search and lead_id_search.strip():
        from sqlalchemy import cast, String as SAString
        query = query.filter(
            cast(models.Lead.id, SAString).ilike(f"%{lead_id_search.strip()}%")
        )

    # Smart multi-token name / field search (mirrors search_leads)
    if search_query:
        from sqlalchemy import or_, and_, func, cast, String as SAString
        normalized = re.sub(r'\s+', ' ', search_query.strip()).lower()
        tokens = [t for t in normalized.split() if t]

        if tokens:
            full_name_expr = func.lower(
                models.Lead.first_name + ' ' + models.Lead.last_name
            )
            full_name_rev_expr = func.lower(
                models.Lead.last_name + ' ' + models.Lead.first_name
            )

            token_conditions = []
            for token in tokens:
                tok_pat = f"%{token}%"
                token_conditions.append(or_(
                    models.Lead.first_name.ilike(tok_pat),
                    models.Lead.last_name.ilike(tok_pat),
                    full_name_expr.ilike(tok_pat),
                    full_name_rev_expr.ilike(tok_pat),
                    models.Lead.phone.ilike(tok_pat),
                    models.Lead.email.ilike(tok_pat),
                    models.Lead.medicaid_no.ilike(tok_pat),
                    models.Lead.custom_user_id.ilike(tok_pat),
                ))

            query = query.filter(and_(*token_conditions))
        
    if staff_filter:
        query = query.filter(models.Lead.staff_name.ilike(f"%{staff_filter}%"))
        
    if source_filter:
        query = query.filter(models.Lead.source.ilike(f"%{source_filter}%"))
        
    if status_filter and status_filter != "All":
        if status_filter in ["Initial Referral Sent", "Referral Sent"]:
            from sqlalchemy import or_
            query = query.filter(models.Lead.last_contact_status.in_(["Initial Referral Sent", "Referral Sent"]))
        else:
            query = query.filter(models.Lead.last_contact_status == status_filter)
        
    # 7.5 Referral Category Filter (Regular/Interim)
    if referral_category_filter and referral_category_filter != "All":
        query = query.filter(models.Lead.referral_type == referral_category_filter)
        
    if priority_filter and priority_filter != "All":
        if priority_filter == "Not Called":
            from sqlalchemy import or_
            query = query.filter(or_(models.Lead.priority == "Not Called", models.Lead.priority == None))
        else:
            query = query.filter(models.Lead.priority == priority_filter)
        
    if tag_color_filter and tag_color_filter != "All":
        query = query.filter(models.Lead.tag_color == tag_color_filter)
        
    # 8.6 Caregiver Type Filter
    if caregiver_type_filter and caregiver_type_filter != "All":
        if caregiver_type_filter == "None":
            from sqlalchemy import or_
            query = query.filter(or_(models.Lead.caregiver_type == None, models.Lead.caregiver_type == "", models.Lead.caregiver_type == "None"))
        else:
            query = query.filter(models.Lead.caregiver_type == caregiver_type_filter)
            
    # 8.7 Agency / CCU Filter
    if agency_filter and agency_filter != "All":
        query = query.join(models.Agency, isouter=True).filter(models.Agency.name == agency_filter)
        
    if ccu_filter and ccu_filter != "All":
        query = query.join(models.CCU, isouter=True).filter(models.CCU.name == ccu_filter)
            
    if only_clients:
        inactive_statuses = ["Not Approved", "Services Refused", "Inactive", "Not Interested"]
        if active_inactive_filter == "Active":
            query = query.filter(~models.Lead.last_contact_status.in_(inactive_statuses))
        elif active_inactive_filter == "Inactive":
            query = query.filter(models.Lead.last_contact_status.in_(inactive_statuses))
    else:
        from sqlalchemy import or_
        if active_inactive_filter == "Active":
            query = query.filter(~models.Lead.last_contact_status.in_(["Inactive", "Not Interested"]))
        elif active_inactive_filter == "Inactive":
            query = query.filter(models.Lead.last_contact_status.in_(["Inactive", "Not Interested"]))
        
    if city_filter:
        from sqlalchemy import or_
        query = query.filter(or_(
            models.Lead.city.ilike(f"%{city_filter}%"),
            models.CCU.city.ilike(f"%{city_filter}%")
        )).join(models.CCU, isouter=True)
        
    if zip_filter:
        from sqlalchemy import or_
        query = query.filter(or_(
            models.Lead.zip_code.ilike(f"%{zip_filter}%"),
            models.CCU.zip_code.ilike(f"%{zip_filter}%")
        )).join(models.CCU, isouter=True)
        
            
            
    if lead_type_filter and lead_type_filter != "All":
        if lead_type_filter == "Lead":
            query = query.filter(models.Lead.active_client == False)
        elif lead_type_filter == "Initial Referral Sent":
            query = query.filter(models.Lead.active_client == True, models.Lead.authorization_received == False)
        elif lead_type_filter == "Referral Confirmed":
            query = query.filter(models.Lead.active_client == True, models.Lead.authorization_received == True)

    if referral_category_filter and referral_category_filter != "All":
        if referral_category_filter == "Regular":
            from sqlalchemy import or_
            query = query.filter(or_(models.Lead.referral_type == "Regular", models.Lead.referral_type == None, models.Lead.referral_type == ""))
        elif referral_category_filter == "Interim":
            query = query.filter(models.Lead.referral_type == "Interim")
            
    # 11. Care Status Filter (Mirroring search_leads)
    if care_status_filter:
        from sqlalchemy import or_
        if care_status_filter == "Active":
            query = query.filter(or_(
                models.Lead.care_status == None,
                ~models.Lead.care_status.in_(["Hold", "Terminated", "Deceased"])
            ))
            
            # REFINED: Mirror search_leads logic for count
            query = query.filter(or_(
                models.Lead.source != "Transfer",
                models.Lead.care_status == "Care Start"
            ))
            
            # Apply sub-filter if Active
            if care_sub_status_filter and care_sub_status_filter != "All":
                query = query.filter(models.Lead.care_status == care_sub_status_filter)
                
        elif care_status_filter == "Transfer":
            query = query.filter(
                models.Lead.source == "Transfer",
                models.Lead.care_status != "Care Start"
            )
        elif care_status_filter == "Inactive":
            query = query.filter(models.Lead.care_status.in_(["Hold", "Terminated", "Deceased"]))
            # Apply sub-filter if Inactive
            if care_sub_status_filter and care_sub_status_filter != "All":
                query = query.filter(models.Lead.care_status == care_sub_status_filter)
        elif care_status_filter in ["Hold", "Terminated", "Deceased"]:
            query = query.filter(models.Lead.care_status == care_status_filter)
        elif care_status_filter != "All":
            query = query.filter(models.Lead.care_status == care_status_filter)
        
    return query.scalar()
