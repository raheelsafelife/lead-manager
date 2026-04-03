"""
Generic Dimension Report Service
================================
Queries the top N entities by referral count for a given dimension 
(CCU, Source, Status, Staff, MCO, etc.), then fetches all referral 
detail for each entity. Delegates Excel/Word generation to report_engine.

Supported Dimensions:
- 'ccu'    -> Lead.ccu_id
- 'source' -> Lead.source
- 'status' -> Lead.last_contact_status
- 'staff'  -> Lead.staff_name
- 'mco'    -> Lead.mco_id
- 'payor'  -> Lead.agency_id
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models import Lead, CCU, Agency, MCO, LeadComment
from app.services import report_engine


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _format_date(dt) -> str:
    if dt is None:
        return ""
    if hasattr(dt, "strftime"):
        return dt.strftime("%m/%d/%Y")
    return str(dt)


def _latest_comment(lead: Lead) -> str:
    if not lead.lead_comments:
        return ""
    sorted_c = sorted(lead.lead_comments, key=lambda c: c.created_at, reverse=True)
    return sorted_c[0].content if sorted_c else ""


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, 20))


def _get_dimension_column(dimension: str):
    mapping = {
        "ccu": Lead.ccu_id,
        "source": Lead.source,
        "status": Lead.last_contact_status,
        "staff": Lead.staff_name,
        "mco": Lead.mco_id,
        "payor": Lead.agency_id,
    }
    return mapping.get(dimension.lower(), Lead.ccu_id)


def _get_entity_display_name(db: Session, dimension: str, value: Any) -> str:
    if value is None:
        return "Unknown / N/A"
    
    if dimension.lower() == "ccu":
        obj = db.query(CCU).filter(CCU.id == value).first()
        return obj.name if obj else f"CCU ID: {value}"
    elif dimension.lower() == "payor":
        obj = db.query(Agency).filter(Agency.id == value).first()
        return obj.name if obj else f"Payor ID: {value}"
    elif dimension.lower() == "mco":
        obj = db.query(MCO).filter(MCO.id == value).first()
        return obj.name if obj else f"MCO ID: {value}"
    
    return str(value)


def _get_entity_summary_data(db: Session, dimension: str, value: Any) -> Dict[str, Any]:
    """Returns a dict of summary info for the sheet header."""
    name = _get_entity_display_name(db, dimension, value)
    
    if value is None:
        return {"Name": name}

    if dimension.lower() == "ccu":
        obj = db.query(CCU).filter(CCU.id == value).first()
        if obj:
            return {
                "CCU Name": obj.name,
                "Phone": obj.phone or "—",
                "Email": obj.email or "—",
                "Coordinator": obj.care_coordinator_name or "—",
                "Address": obj.address or "—",
            }
    elif dimension.lower() == "payor":
        obj = db.query(Agency).filter(Agency.id == value).first()
        if obj:
            return {
                "Payor Name": obj.name,
                "Phone": obj.phone or "—",
                "Email": obj.email or "—",
                "Address": obj.address or "—",
            }
    
    # For source, status, staff, just return the name
    dim_label = dimension.replace("_", " ").title()
    return {dim_label: name}


# ─────────────────────────────────────────────────────────────────────────────
# Core query
# ─────────────────────────────────────────────────────────────────────────────

def get_top_entities_with_leads(db: Session, dimension: str = "ccu", limit: int = 5) -> List[Dict[str, Any]]:
    """
    Return top N entities ranked by referral (active_client) count for a dimension.
    """
    limit = _clamp_limit(limit)
    col = _get_dimension_column(dimension)

    # Group leads by dimension column, count all active records
    top_entries = (
        db.query(col, func.count(Lead.id).label("cnt"))
        .filter(
            Lead.deleted_at == None,
            col != None,
            ~Lead.last_contact_status.in_(["Not Approved", "Services Refused", "Inactive", "Not Interested"]),
            ~Lead.care_status.in_(["Hold", "Terminated", "Deceased"])
        )
        .group_by(col)
        .order_by(func.count(Lead.id).desc())
        .limit(limit)
        .all()
    )

    results = []
    for rank, (val, count) in enumerate(top_entries, start=1):
        leads = (
            db.query(Lead)
            .options(
                joinedload(Lead.agency),
                joinedload(Lead.ccu),
                joinedload(Lead.mco),
                joinedload(Lead.lead_comments),
            )
            .filter(
                col == val,
                Lead.deleted_at == None,
                ~Lead.last_contact_status.in_(["Not Approved", "Services Refused", "Inactive", "Not Interested"]),
                ~Lead.care_status.in_(["Hold", "Terminated", "Deceased"])
            )
            .order_by(Lead.created_at.desc())
            .all()
        )

        results.append(
            {
                "rank": rank,
                "value": val,
                "display_name": _get_entity_display_name(db, dimension, val),
                "referral_count": count,
                "leads": leads,
            }
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Stats (for frontend display)
# ─────────────────────────────────────────────────────────────────────────────

def get_dimension_report_stats(db: Session, dimension: str = "ccu", limit: int = 5) -> Dict[str, Any]:
    limit = _clamp_limit(limit)
    top_data = get_top_entities_with_leads(db, dimension, limit)

    total_referrals = sum(c["referral_count"] for c in top_data)

    leaderboard = []
    for entry in top_data:
        count = entry["referral_count"]
        pct = round((count / total_referrals * 100), 1) if total_referrals > 0 else 0
        
        # Get more details if it's CCU/Payor
        summary = _get_entity_summary_data(db, dimension, entry["value"])
        
        leaderboard.append(
            {
                "rank": entry["rank"],
                "name": entry["display_name"],
                "referral_count": count,
                "percentage": pct,
                "details": summary
            }
        )

    return {
        "dimension": dimension,
        "limit": limit,
        "total_referrals_in_top": total_referrals,
        "leaderboard": leaderboard,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Build report_config (shared between Excel & Word)
# ─────────────────────────────────────────────────────────────────────────────

DETAIL_COLUMNS = [
    "Lead ID",
    "Client Name",
    "Phone",
    "Email",
    "DOB",
    "Age",
    "Call Status",
    "Auth Received",
    "Authorization Status",
    "SOC Date",
    "Care Status",
    "Referral Type",
    "Priority",
    "Source",
    "Staff",
    "Payor / MCO",
    "CCU",
    "Address",
    "Latest Comment",
    "Created At",
    "Created By",
]


def _build_report_config(db: Session, top_data: List[Dict], dimension: str, limit: int, title: str) -> Dict:
    sections = []
    for entry in top_data:
        val = entry["value"]
        count = entry["referral_count"]
        rank = entry["rank"]
        display_name = entry["display_name"]

        heading = f"#{rank} — {display_name} ({count} referral{'s' if count != 1 else ''})"
        sheet_name = f"#{rank} {display_name}"

        summary_row = _get_entity_summary_data(db, dimension, val)

        detail_rows = []
        for lead in entry["leads"]:
            # Payor / MCO combined label
            payor_label = ""
            if lead.agency:
                payor_label = lead.agency.name
            elif lead.mco:
                payor_label = getattr(lead.mco, "name", "")

            # CCU Name
            ccu_name = lead.ccu.name if lead.ccu else ""

            # Address
            addr_parts = []
            if getattr(lead, 'street', None):   addr_parts.append(lead.street)
            if getattr(lead, 'city', None):     addr_parts.append(lead.city)
            if getattr(lead, 'state', None):    addr_parts.append(lead.state)
            if getattr(lead, 'zip_code', None): addr_parts.append(lead.zip_code)
            address_str = ", ".join(addr_parts)

            # Auth/Referral status label
            if lead.authorization_received:
                auth_status = "Authorized"
            elif getattr(lead, "last_contact_status", "") == "Not Approved":
                auth_status = "Rejected"
            else:
                auth_status = "Pending"

            detail_rows.append({
                "Lead ID":            str(lead.id),
                "Client Name":        f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
                "Phone":              lead.phone or "",
                "Email":              lead.email or "",
                "DOB":                _format_date(lead.dob),
                "Age":                str(lead.age or ""),
                "Call Status":        lead.last_contact_status or "",
                "Auth Received":      "Yes" if lead.authorization_received else "No",
                "Authorization Status": auth_status,
                "SOC Date":           _format_date(lead.soc_date),
                "Care Status":        lead.care_status or "",
                "Referral Type":      lead.referral_type or "",
                "Priority":           lead.priority or "",
                "Source":             lead.source or "",
                "Staff":              lead.staff_name or "",
                "Payor / MCO":        payor_label,
                "CCU":                ccu_name,
                "Address":            address_str,
                "Latest Comment":     _latest_comment(lead),
                "Created At":         _format_date(lead.created_at),
                "Created By":         lead.created_by or "",
            })

        sections.append(
            {
                "heading":        heading,
                "sheet_name":     sheet_name,
                "summary_row":    summary_row,
                "detail_columns": DETAIL_COLUMNS,
                "detail_rows":    detail_rows,
            }
        )

    return {
        "title":        title,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sections":     sections,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public export functions
# ─────────────────────────────────────────────────────────────────────────────

def generate_dimension_report_excel(db: Session, dimension: str = "ccu", limit: int = 5) -> bytes:
    limit = _clamp_limit(limit)
    top_data = get_top_entities_with_leads(db, dimension, limit)
    title = f"Top {limit} {dimension.upper()} Referral Report"
    config = _build_report_config(db, top_data, dimension, limit, title)
    return report_engine.generate_excel(config)


def generate_dimension_report_word(db: Session, dimension: str = "ccu", limit: int = 5) -> bytes:
    limit = _clamp_limit(limit)
    top_data = get_top_entities_with_leads(db, dimension, limit)
    title = f"Top {limit} {dimension.upper()} Referral Report"
    config = _build_report_config(db, top_data, dimension, limit, title)
    return report_engine.generate_word(config)
