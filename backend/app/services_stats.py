from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Dict

from . import models


# ------------------------------
# BASIC COUNTS
# ------------------------------
def get_basic_counts(db: Session) -> Dict[str, int]:
    total_leads = db.query(models.Lead).count()
    total_users = db.query(models.User).count()

    return {
        "total_leads": total_leads,
        "total_users": total_users,
    }


# ------------------------------
# LEADS BY STAFF
# ------------------------------
def leads_by_staff(db: Session) -> List[dict]:
    rows = (
        db.query(models.Lead.staff_name, func.count(models.Lead.id))
        .group_by(models.Lead.staff_name)
        .all()
    )

    return [{"staff_name": r[0], "count": r[1]} for r in rows]


# ------------------------------
# LEADS BY SOURCE
# ------------------------------
def leads_by_source(db: Session) -> List[dict]:
    rows = (
        db.query(models.Lead.source, func.count(models.Lead.id))
        .group_by(models.Lead.source)
        .all()
    )

    return [{"source": r[0], "count": r[1]} for r in rows]


# ------------------------------
# LEADS BY STATUS
# ------------------------------
def leads_by_status(db: Session) -> List[dict]:
    rows = (
        db.query(models.Lead.last_contact_status, func.count(models.Lead.id))
        .group_by(models.Lead.last_contact_status)
        .all()
    )

    return [{"status": r[0], "count": r[1]} for r in rows]


# ------------------------------
# MONTHLY LEADS
# ------------------------------
def monthly_leads(db: Session):
    """
    Return count of leads created per month.
    Simple approach: year-month as string.
    """
    leads = db.query(models.Lead).all()
    if not leads:
        return []

    from collections import defaultdict

    month_counts = defaultdict(int)
    for lead in leads:
        month_str = lead.created_at.strftime("%Y-%m")
        month_counts[month_str] += 1

    # Convert to list of dicts
    result = []
    for month_str in sorted(month_counts.keys()):
        result.append({"month": month_str, "count": month_counts[month_str]})

    return result


def leads_by_event(db: Session):
    """
    Return count of leads grouped by event name (for source='Event').
    """
    from sqlalchemy import func

    results = (
        db.query(models.Lead.event_name, func.count(models.Lead.id).label("count"))
        .filter(models.Lead.source == "Event")
        .filter(models.Lead.event_name.isnot(None))
        .group_by(models.Lead.event_name)
        .all()
    )

    if not results:
        return []

    return [{"event_name": r[0], "count": r[1]} for r in results]


def word_of_mouth_breakdown(db: Session):
    """
    Return count of leads grouped by word_of_mouth_type (for source='Word of Mouth').
    """
    from sqlalchemy import func

    results = (
        db.query(models.Lead.word_of_mouth_type, func.count(models.Lead.id).label("count"))
        .filter(models.Lead.source == "Word of Mouth")
        .filter(models.Lead.word_of_mouth_type.isnot(None))
        .group_by(models.Lead.word_of_mouth_type)
        .all()
    )

    if not results:
        return []

    return [{"type": r[0], "count": r[1]} for r in results]


# ------------------------------
# USER-SPECIFIC STATS
# ------------------------------
def get_user_stats(db: Session, username: str):
    """Get stats for a specific user's leads"""
    total_leads = db.query(models.Lead).filter(
        models.Lead.staff_name == username
    ).count()
    
    active_clients = db.query(models.Lead).filter(
        models.Lead.staff_name == username,
        models.Lead.active_client == True
    ).count()
    
    return {
        "total_leads": total_leads,
        "active_clients": active_clients
    }


def leads_by_month_for_user(db: Session, username: str):
    """Monthly leads for a specific user"""
    leads = db.query(models.Lead).filter(
        models.Lead.staff_name == username
    ).all()
    
    if not leads:
        return []

    from collections import defaultdict

    month_counts = defaultdict(int)
    for lead in leads:
        month_str = lead.created_at.strftime("%Y-%m")
        month_counts[month_str] += 1

    result = []
    for month_str in sorted(month_counts.keys()):
        result.append({"month": month_str, "count": month_counts[month_str]})

    return result


def leads_by_source_for_user(db: Session, username: str):
    """Leads by source for a specific user"""
    from sqlalchemy import func

    results = (
        db.query(models.Lead.source, func.count(models.Lead.id).label("count"))
        .filter(models.Lead.staff_name == username)
        .group_by(models.Lead.source)
        .all()
    )

    if not results:
        return []

    return [{"source": r[0], "count": r[1]} for r in results]


# ------------------------------
# REFERRAL-SPECIFIC STATS FOR USERS
# ------------------------------

def referrals_by_month_for_user(db: Session, username: str):
    """Monthly referrals for a specific user"""
    referrals = db.query(models.Lead).filter(
        models.Lead.staff_name == username,
        models.Lead.active_client == True
    ).all()

    if not referrals:
        return []

    from collections import defaultdict

    month_counts = defaultdict(int)
    for referral in referrals:
        month_str = referral.created_at.strftime("%Y-%m")
        month_counts[month_str] += 1

    result = []
    for month_str in sorted(month_counts.keys()):
        result.append({"month": month_str, "count": month_counts[month_str]})

    return result


def referrals_by_status_for_user(db: Session, username: str):
    """Referrals by contact status for a specific user"""
    from sqlalchemy import func

    results = (
        db.query(models.Lead.last_contact_status, func.count(models.Lead.id).label("count"))
        .filter(models.Lead.staff_name == username)
        .filter(models.Lead.active_client == True)
        .group_by(models.Lead.last_contact_status)
        .all()
    )

    if not results:
        return []

    return [{"status": r[0], "count": r[1]} for r in results]


def referrals_by_authorization_for_user(db: Session, username: str):
    """Referrals by authorization status for a specific user"""
    from sqlalchemy import func

    results = (
        db.query(models.Lead.authorization_received, func.count(models.Lead.id).label("count"))
        .filter(models.Lead.staff_name == username)
        .filter(models.Lead.active_client == True)
        .group_by(models.Lead.authorization_received)
        .all()
    )

    if not results:
        return []

    return [{"authorized": "Yes" if r[0] else "No", "count": r[1]} for r in results]


def referrals_by_care_status_for_user(db: Session, username: str):
    """Referrals by care status for a specific user"""
    from sqlalchemy import func

    results = (
        db.query(models.Lead.care_status, func.count(models.Lead.id).label("count"))
        .filter(models.Lead.staff_name == username)
        .filter(models.Lead.active_client == True)
        .filter(models.Lead.care_status.isnot(None))
        .group_by(models.Lead.care_status)
        .all()
    )

    if not results:
        return []

    return [{"care_status": r[0], "count": r[1]} for r in results]


def referral_status_breakdown(db: Session):
    """All referrals by contact status (for cumulative view)"""
    from sqlalchemy import func

    results = (
        db.query(models.Lead.last_contact_status, func.count(models.Lead.id).label("count"))
        .filter(models.Lead.active_client == True)
        .group_by(models.Lead.last_contact_status)
        .all()
    )

    if not results:
        return []

    return [{"status": r[0], "count": r[1]} for r in results]


# ------------------------------
# ADMIN PERFORMANCE METRICS
# ------------------------------

def get_staff_performance(db: Session) -> List[dict]:
    """
    Computes performance metrics for each staff member.
    Metrics: Total Leads, Total Referrals, Conversion Rate (%)
    """
    staff_list = db.query(models.Lead.staff_name).distinct().all()
    performance = []

    for (name,) in staff_list:
        if not name: continue
        
        total = db.query(models.Lead).filter(models.Lead.staff_name == name).count()
        referrals = db.query(models.Lead).filter(
            models.Lead.staff_name == name, 
            models.Lead.active_client == True
        ).count()
        
        rate = round((referrals / total * 100), 2) if total > 0 else 0
        
        performance.append({
            "staff_name": name,
            "total_leads": total,
            "total_referrals": referrals,
            "conversion_rate": rate
        })
        
    return sorted(performance, key=lambda x: x['total_leads'], reverse=True)


def get_system_wide_distribution(db: Session) -> Dict[str, List[dict]]:
    """
    Returns distribution data for all leads in the system.
    Used for global admin pie charts.
    """
    status_rows = db.query(models.Lead.last_contact_status, func.count(models.Lead.id)).group_by(models.Lead.last_contact_status).all()
    source_rows = db.query(models.Lead.source, func.count(models.Lead.id)).group_by(models.Lead.source).all()
    priority_rows = db.query(models.Lead.priority, func.count(models.Lead.id)).group_by(models.Lead.priority).all()
    
    return {
        "status": [{"label": r[0], "value": r[1]} for r in status_rows],
        "source": [{"label": r[0], "value": r[1]} for r in source_rows],
        "priority": [{"label": r[0], "value": r[1]} for r in priority_rows]
    }


def get_referrals_by_ccu(db: Session) -> List[dict]:
    """
    Returns count of all referrals (Sent + Confirm) grouped by CCU.
    """
    results = (
        db.query(models.CCU.name, func.count(models.Lead.id))
        .join(models.Lead, models.Lead.ccu_id == models.CCU.id)
        .filter(models.Lead.active_client == True)
        .group_by(models.CCU.name)
        .all()
    )
    
    return [{"ccu_name": r[0], "count": r[1]} for r in results]


def get_referral_segments_by_ccu(db: Session) -> Dict[str, List[dict]]:
    """
    Returns separate counts for 'Sent' and 'Confirmed' referrals by CCU.
    Sent = Active client + 'Referral Sent' status
    Confirmed = Active client + 'Care Start' care status
    """
    # 1. Sent Referrals
    sent_rows = (
        db.query(models.CCU.name, func.count(models.Lead.id))
        .join(models.Lead, models.Lead.ccu_id == models.CCU.id)
        .filter(models.Lead.active_client == True)
        .filter(models.Lead.last_contact_status == "Referral Sent")
        .group_by(models.CCU.name)
        .all()
    )
    
    # 2. Confirmed Referrals
    conf_rows = (
        db.query(models.CCU.name, func.count(models.Lead.id))
        .join(models.Lead, models.Lead.ccu_id == models.CCU.id)
        .filter(models.Lead.active_client == True)
        .filter(models.Lead.care_status == "Care Start")
        .group_by(models.CCU.name)
        .all()
    )
    
    return {
        "sent": [{"ccu_name": r[0], "count": r[1]} for r in sent_rows],
        "confirmed": [{"ccu_name": r[0], "count": r[1]} for r in conf_rows]
    }
