"""
Daily digest email service.

Builds a role-aware summary from activity_logs and sends one polished email per
user per day. SMTP delivery stays centralized in app.utils.email_service.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from html import escape
import json
import os
import time as sleep_time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

# Ensure app.db initializes the shared SQLAlchemy Base before model imports.
import app.db  # noqa: F401
from app.models import ActivityLog, DailyDigestEmail, Lead, User
from app.utils.email_service import send_email

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


DIGEST_TIMEZONE = os.getenv("DAILY_DIGEST_TIMEZONE", "America/Chicago")
DIGEST_SEND_DELAY_SECONDS = 3
DIGEST_ACTIONS = {
    "CREATE_LEAD",
    "UPDATE_LEAD",
    "DELETE_LEAD",
    "RESTORE_LEAD",
    "PERMANENT_DELETE",
    "ADD_COMMENT",
    "UPLOAD_ATTACHMENT",
    "DELETE_ATTACHMENT",
    "CARE_START_MARKED",
    "AUTHORIZATION_MARKED",
    "LEAD_CREATED",
    "LEAD_UPDATED",
    "LEAD_ASSIGNED",
    "LEAD_DELETED",
    "LEAD_PERMANENTLY_DELETED",
    "LEAD_RESTORED",
    "STATUS_CHANGED",
    "COMMENT_ADDED",
    "REFERRAL_MARKED",
    "REFERRAL_UNMARKED",
    "AGENCY_ASSIGNED",
}

SENSITIVE_FIELDS = {
    "ssn",
    "medicaid_no",
    "hashed_password",
    "password",
    "sender_password",
}

FIELD_LABELS = {
    "active_client": "Referral",
    "agency_id": "Payor",
    "agency_suboption_id": "Payor Option",
    "authorization_received": "Authorization",
    "care_status": "Care Status",
    "ccu_id": "CCU",
    "comments": "Lead Notes",
    "custom_user_id": "Employee ID",
    "dob": "DOB",
    "e_contact_name": "Emergency Contact",
    "e_contact_phone": "Emergency Phone",
    "e_contact_relation": "Emergency Relation",
    "first_name": "First Name",
    "last_contact_status": "Contact Status",
    "last_name": "Last Name",
    "mco_id": "MCO",
    "owner_id": "Owner",
    "phone": "Phone",
    "priority": "Priority",
    "referral_sent_date": "Referral Sent Date",
    "referral_type": "Referral Type",
    "soc_date": "SOC Date",
    "staff_name": "Assigned Staff",
}

SECTION_LABELS = {
    "leads": "Leads",
    "referrals": "Referrals",
    "authorizations": "Authorizations",
    "comments": "Comments",
}


def _local_day_window(digest_date: date) -> Tuple[datetime, datetime]:
    tz = ZoneInfo(DIGEST_TIMEZONE)
    local_start = datetime.combine(digest_date, time.min, tzinfo=tz)
    local_end = datetime.combine(digest_date, time.max, tzinfo=tz)
    start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _timestamp_query_value(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _digest_send_delay_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("DAILY_DIGEST_SEND_DELAY_SECONDS", DIGEST_SEND_DELAY_SECONDS)))
    except ValueError:
        return float(DIGEST_SEND_DELAY_SECONDS)


def _parse_json(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _format_bool(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return "Not set"
    if isinstance(value, bool):
        return _format_bool(value)
    return str(value)


def _field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


def _safe_changes(old_value: Optional[str], new_value: Optional[str]) -> List[Dict[str, str]]:
    old_data = _parse_json(old_value)
    new_data = _parse_json(new_value)
    if not new_data and old_data:
        new_data = {}

    changes = []
    fields = sorted(set(old_data.keys()) | set(new_data.keys()))
    for field in fields:
        if field in SENSITIVE_FIELDS:
            continue
        old = old_data.get(field)
        new = new_data.get(field)
        if old == new and field in old_data and field in new_data:
            continue
        changes.append({
            "field": _field_label(field),
            "old": _format_value(old),
            "new": _format_value(new),
        })
    return changes[:12]


def _log_has_field(log: ActivityLog, *fields: str) -> bool:
    old_data = _parse_json(log.old_value)
    new_data = _parse_json(log.new_value)
    keys = set(old_data.keys()) | set(new_data.keys())
    return any(field in keys for field in fields)


def _section_for_log(log: ActivityLog) -> str:
    if log.action_type in {"AUTHORIZATION_MARKED", "CARE_START_MARKED"}:
        return "authorizations"
    if _log_has_field(log, "authorization_received", "care_status", "soc_date"):
        return "authorizations"
    if (
        log.action_type in {"REFERRAL_MARKED", "REFERRAL_UNMARKED", "AGENCY_ASSIGNED"}
        or _log_has_field(log, "active_client", "referral_type", "agency_id", "agency_suboption_id", "ccu_id", "referral_sent_date")
    ):
        return "referrals"
    return "leads"


def _action_label(log: ActivityLog) -> str:
    if _log_has_field(log, "authorization_received"):
        new_data = _parse_json(log.new_value)
        if new_data.get("authorization_received") is True:
            return "Authorization Received"
        if new_data.get("authorization_received") is False:
            return "Authorization Removed"
    labels = {
        "CREATE_LEAD": "Lead Created",
        "UPDATE_LEAD": "Lead Updated",
        "DELETE_LEAD": "Lead Deleted",
        "RESTORE_LEAD": "Lead Restored",
        "PERMANENT_DELETE": "Lead Permanently Deleted",
        "ADD_COMMENT": "Comment Added",
        "UPLOAD_ATTACHMENT": "Attachment Uploaded",
        "DELETE_ATTACHMENT": "Attachment Deleted",
        "CARE_START_MARKED": "Care Start Marked",
        "AUTHORIZATION_MARKED": "Authorization Marked",
        "LEAD_CREATED": "Lead Created",
        "LEAD_UPDATED": "Lead Updated",
        "LEAD_ASSIGNED": "Lead Assigned",
        "LEAD_DELETED": "Lead Deleted",
        "LEAD_PERMANENTLY_DELETED": "Lead Permanently Deleted",
        "LEAD_RESTORED": "Lead Restored",
        "STATUS_CHANGED": "Status Changed",
        "COMMENT_ADDED": "Comment Added",
        "REFERRAL_MARKED": "Referral Marked",
        "REFERRAL_UNMARKED": "Referral Removed",
        "AGENCY_ASSIGNED": "Payor Assigned",
    }
    return labels.get(log.action_type, log.action_type.replace("_", " ").title())


def _action_color(section: str, action_label: str) -> str:
    if "Deleted" in action_label or "Removed" in action_label:
        return "#DC2626"
    if section == "authorizations":
        return "#16A34A"
    if section == "referrals":
        return "#0B5C7A"
    if "Comment" in action_label:
        return "#14C8C4"
    return "#2563EB"


def _local_time(timestamp: datetime) -> str:
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(ZoneInfo(DIGEST_TIMEZONE)).strftime("%I:%M %p")


def _lead_context(db: Session, log: ActivityLog) -> Dict[str, str]:
    lead = None
    if log.entity_id:
        lead = db.query(Lead).filter(Lead.id == log.entity_id).first()

    old_data = _parse_json(log.old_value)
    new_data = _parse_json(log.new_value)

    name = log.entity_name or old_data.get("name")
    if lead:
        name = f"{lead.first_name} {lead.last_name}"

    return {
        "name": name or "Unknown lead",
        "lead_id": str(log.entity_id or "N/A"),
        "phone": _format_value(getattr(lead, "phone", None) or new_data.get("phone") or old_data.get("phone")),
        "source": _format_value(getattr(lead, "source", None) or new_data.get("source") or old_data.get("source")),
        "status": _format_value(getattr(lead, "last_contact_status", None) or new_data.get("last_contact_status") or old_data.get("last_contact_status")),
    }


def _build_digest_items(db: Session, logs: Iterable[ActivityLog]) -> Dict[str, List[Dict[str, Any]]]:
    sections = {"leads": [], "referrals": [], "authorizations": [], "comments": []}
    for log in logs:
        section = _section_for_log(log)
        label = _action_label(log)
        item = {
            "action": label,
            "color": _action_color(section, label),
            "time": _local_time(log.timestamp),
            "by": log.username,
            "description": log.description,
            "changes": _safe_changes(log.old_value, log.new_value),
            "context": _lead_context(db, log),
        }
        if log.action_type in {"COMMENT_ADDED", "ADD_COMMENT"}:
            sections["comments"].append(item)
        else:
            sections[section].append(item)
    return sections


def _activity_query(db: Session, user: User, start_utc: datetime, end_utc: datetime) -> List[ActivityLog]:
    query = db.query(ActivityLog).filter(
        ActivityLog.timestamp >= _timestamp_query_value(start_utc),
        ActivityLog.timestamp <= _timestamp_query_value(end_utc),
        ActivityLog.action_type.in_(DIGEST_ACTIONS),
    )

    if user.role != "super_admin":
        query = query.filter(
            (ActivityLog.user_id == user.id) | (ActivityLog.username == user.username)
        )

    return query.order_by(desc(ActivityLog.timestamp)).all()


def _digest_record(db: Session, user_id: int, digest_date: date) -> Optional[DailyDigestEmail]:
    return db.query(DailyDigestEmail).filter(
        DailyDigestEmail.user_id == user_id,
        DailyDigestEmail.digest_date == digest_date,
    ).first()


def _summary_counts(sections: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
    counts = {
        "total": sum(len(items) for items in sections.values()),
        "leads": len(sections["leads"]),
        "referrals": len(sections["referrals"]),
        "authorizations": len(sections["authorizations"]),
        "comments": len(sections.get("comments", [])),
        "deletes": 0,
    }
    for items in sections.values():
        for item in items:
            if "Deleted" in item["action"] or "Removed" in item["action"]:
                counts["deletes"] += 1
    return counts


def _render_change_rows(changes: List[Dict[str, str]]) -> str:
    if not changes:
        return '<div style="color:#64748B;font-size:13px;">No field-level details were recorded for this action.</div>'

    rows = []
    for change in changes:
        rows.append(f"""
            <tr>
                <td style="padding:8px 10px;border-top:1px solid #E2E8F0;color:#0F2742;font-weight:700;">{escape(change['field'])}</td>
                <td style="padding:8px 10px;border-top:1px solid #E2E8F0;color:#64748B;">{escape(change['old'])}</td>
                <td style="padding:8px 10px;border-top:1px solid #E2E8F0;color:#0F766E;font-weight:700;">{escape(change['new'])}</td>
            </tr>
        """)
    return f"""
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;">
            <thead>
                <tr>
                    <th align="left" style="padding:8px 10px;color:#475569;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">Field</th>
                    <th align="left" style="padding:8px 10px;color:#475569;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">Before</th>
                    <th align="left" style="padding:8px 10px;color:#475569;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">After</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """


def _render_item(item: Dict[str, Any]) -> str:
    context = item["context"]
    return f"""
        <div style="background:#FFFFFF;border:1px solid #DCEAF0;border-radius:18px;padding:18px;margin:14px 0;box-shadow:0 8px 24px rgba(11,92,122,.08);">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="display:inline-block;background:{item['color']};color:#FFFFFF;border-radius:999px;padding:6px 12px;font-size:12px;font-weight:800;letter-spacing:.02em;">{escape(item['action'])}</span>
                <span style="color:#64748B;font-size:13px;">{escape(item['time'])} by {escape(item['by'])}</span>
            </div>
            <div style="font-size:18px;font-weight:900;color:#0F2742;margin-bottom:6px;">{escape(context['name'])}</div>
            <div style="color:#475569;font-size:13px;line-height:1.65;margin-bottom:12px;">
                <strong>ID:</strong> {escape(context['lead_id'])} &nbsp; | &nbsp;
                <strong>Phone:</strong> {escape(context['phone'])} &nbsp; | &nbsp;
                <strong>Source:</strong> {escape(context['source'])} &nbsp; | &nbsp;
                <strong>Status:</strong> {escape(context['status'])}
            </div>
            <div style="color:#334155;font-size:14px;line-height:1.6;margin-bottom:14px;">{escape(item['description'])}</div>
            {_render_change_rows(item['changes'])}
        </div>
    """


def _render_section(title: str, items: List[Dict[str, Any]]) -> str:
    if not items:
        return f"""
            <div style="margin-top:26px;">
                <h2 style="color:#0F2742;margin:0 0 10px;font-size:22px;">{escape(title)}</h2>
                <div style="background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:16px;padding:16px;color:#64748B;">No {escape(title.lower())} activity recorded.</div>
            </div>
        """
    return f"""
        <div style="margin-top:26px;">
            <h2 style="color:#0F2742;margin:0 0 10px;font-size:22px;">{escape(title)}</h2>
            {''.join(_render_item(item) for item in items)}
        </div>
    """


def build_digest_email(user: User, digest_date: date, sections: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str]:
    counts = _summary_counts(sections)
    display_date = digest_date.strftime("%B %d, %Y")
    scope_label = "All workspace activity" if user.role == "super_admin" else "Your activity"
    subject = f"SafeLife Daily Digest - {display_date}"

    metric_cards = [
        ("Total Actions", counts["total"], "#0B5C7A"),
        ("Lead Updates", counts["leads"], "#2563EB"),
        ("Referral Updates", counts["referrals"], "#14C8C4"),
        ("Authorizations", counts["authorizations"], "#24D17E"),
    ]
    cards_html = "".join(
        f"""
        <td width="25%" style="padding:6px;">
            <div style="background:#FFFFFF;border:1px solid #DCEAF0;border-radius:18px;padding:16px;text-align:center;">
                <div style="color:{color};font-size:28px;font-weight:900;line-height:1;">{value}</div>
                <div style="color:#64748B;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;margin-top:8px;">{escape(label)}</div>
            </div>
        </td>
        """
        for label, value, color in metric_cards
    )

    html_body = f"""
    <!doctype html>
    <html>
      <body style="margin:0;background:#EAF5F7;padding:28px;font-family:Inter,Arial,sans-serif;color:#0F2742;">
        <div style="max-width:920px;margin:0 auto;background:#F8FCFD;border-radius:28px;overflow:hidden;border:1px solid #D6E9EF;box-shadow:0 24px 70px rgba(3,18,38,.14);">
            <div style="background:linear-gradient(135deg,#0B5C7A,#07354F 58%,#14C8C4);padding:34px 38px;color:#FFFFFF;">
                <div style="font-size:28px;font-weight:900;letter-spacing:-.04em;">Safe<span style="color:#14C8C4;">Life</span></div>
                <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#B7F5F3;margin-top:4px;">Home Health | Home Care | Hospice</div>
                <h1 style="font-size:34px;line-height:1.1;margin:26px 0 8px;">Daily Digest</h1>
                <div style="font-size:15px;color:#DDFBFA;">{escape(display_date)} - {escape(scope_label)}</div>
            </div>

            <div style="padding:28px 34px 38px;">
                <p style="font-size:16px;line-height:1.65;color:#334155;margin:0 0 18px;">
                    Here is the complete operational summary for the day. It is grouped by leads, referrals, and authorizations so a reader can understand what changed and who handled it.
                </p>

                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;margin:8px 0 18px;">
                    <tr>{cards_html}</tr>
                </table>

                {_render_section(SECTION_LABELS['leads'], sections['leads'])}
                {_render_section(SECTION_LABELS['referrals'], sections['referrals'])}
                {_render_section(SECTION_LABELS['authorizations'], sections['authorizations'])}
                {_render_section(SECTION_LABELS['comments'], sections['comments'])}

                <div style="margin-top:30px;background:#E6F7F7;border:1px solid #BFEDEC;border-radius:18px;padding:16px;color:#0B5C7A;font-size:13px;line-height:1.6;">
                    Secure operations note: sensitive fields such as SSN and passwords are intentionally excluded from digest emails.
                </div>
            </div>
        </div>
      </body>
    </html>
    """

    plain_body = [
        f"SafeLife Daily Digest - {display_date}",
        f"Scope: {scope_label}",
        f"Total actions: {counts['total']}",
        "",
    ]
    for key in ["leads", "referrals", "authorizations", "comments"]:
        plain_body.append(SECTION_LABELS[key])
        if not sections[key]:
            plain_body.append("No activity recorded.")
            plain_body.append("")
            continue
        for item in sections[key]:
            context = item["context"]
            plain_body.append(f"- {item['action']} | {context['name']} | {item['time']} by {item['by']}")
            plain_body.append(f"  ID: {context['lead_id']} | Phone: {context['phone']} | Status: {context['status']}")
            for change in item["changes"]:
                plain_body.append(f"  {change['field']}: {change['old']} -> {change['new']}")
        plain_body.append("")

    return subject, "\n".join(plain_body), html_body


def send_digest_for_user(db: Session, user: User, digest_date: Optional[date] = None) -> str:
    if not user.email or not user.is_approved:
        return "skipped"

    digest_date = digest_date or datetime.now(ZoneInfo(DIGEST_TIMEZONE)).date()
    existing = _digest_record(db, user.id, digest_date)
    if existing and existing.status == "sent":
        return "already_sent"

    start_utc, end_utc = _local_day_window(digest_date)
    logs = _activity_query(db, user, start_utc, end_utc)
    sections = _build_digest_items(db, logs)
    subject, plain_body, html_body = build_digest_email(user, digest_date, sections)
    activity_count = sum(len(items) for items in sections.values())

    sent = send_email(
        to_email=user.email,
        subject=subject,
        body=plain_body,
        html_body=html_body,
        include_admin_bcc=False,
    )

    now = datetime.utcnow()
    if existing:
        existing.recipient_email = user.email
        existing.activity_count = activity_count
        existing.status = "sent" if sent else "failed"
        existing.sent_at = now
        existing.error_message = None if sent else "SMTP send failed"
    else:
        db.add(DailyDigestEmail(
            user_id=user.id,
            recipient_email=user.email,
            digest_date=digest_date,
            activity_count=activity_count,
            status="sent" if sent else "failed",
            sent_at=now,
            error_message=None if sent else "SMTP send failed",
        ))
    db.commit()
    return "sent" if sent else "failed"


def send_daily_digests(db: Session, digest_date: Optional[date] = None) -> Dict[str, int]:
    users = db.query(User).filter(User.is_approved == 1).order_by(User.id.asc()).all()
    delay_seconds = _digest_send_delay_seconds()
    result = {
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "already_sent": 0,
        "no_activity": 0,
    }

    for user in users:
        try:
            status = send_digest_for_user(db, user, digest_date=digest_date)
            result[status] = result.get(status, 0) + 1
            if status in ("sent", "failed") and delay_seconds > 0:
                print(f"[INFO] Waiting {delay_seconds:g}s before next digest email...")
                sleep_time.sleep(delay_seconds)
        except Exception as exc:
            print(f"[ERROR] Daily digest failed for user {getattr(user, 'username', 'unknown')}: {exc}")
            result["failed"] += 1

    return result
