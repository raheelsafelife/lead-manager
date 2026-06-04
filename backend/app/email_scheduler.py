import os
from dotenv import load_dotenv

# Load environment variables (Check root then current)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path)
load_dotenv()

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.crud import crud_leads, crud_users, crud_email_reminders, crud_notifications
from app.crud.crud_email_reminders import create_care_start_reminder, get_care_start_reminders_by_lead
import time
import threading

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


_last_digest_attempt_date = None


def _digest_enabled():
    return os.getenv("DAILY_DIGEST_ENABLED", "true").lower() in ("1", "true", "yes", "on")


def _digest_send_hour():
    try:
        return int(os.getenv("DAILY_DIGEST_SEND_HOUR", "18"))
    except ValueError:
        return 18


def send_daily_digest_if_due():
    """Send daily digest emails once per day after the configured local hour."""
    global _last_digest_attempt_date

    if not _digest_enabled():
        return

    now_local = datetime.now(ZoneInfo("America/Chicago"))
    digest_date = now_local.date()
    if now_local.hour < _digest_send_hour():
        return
    if _last_digest_attempt_date == digest_date:
        return

    _last_digest_attempt_date = digest_date
    db = SessionLocal()
    try:
        from app.services.daily_digest_service import send_daily_digests

        print(f"[{datetime.now()}] Starting daily digest scan for {digest_date}...")
        result = send_daily_digests(db, digest_date=digest_date)
        print(f"[SUCCESS] Daily digest complete: {result}")
    except Exception as e:
        print(f"[ERROR] Daily digest scan failed: {e}")
    finally:
        db.close()


def should_send_reminder(lead, last_reminder_time):
    """Check if a reminder should be sent for this lead based on type"""
    # Respect user preference
    if hasattr(lead, 'send_reminders') and not lead.send_reminders:
        return False

    # Don't send if lead is inactive
    if lead.last_contact_status == "Inactive":
        return False

    # If no reminder sent yet, notify immediately (first reminder)
    if not last_reminder_time:
        return True

    # Calculate hours since last reminder and since lead creation
    hours_since_last = (datetime.utcnow() - last_reminder_time).total_seconds() / 3600
    hours_since_created = (datetime.utcnow() - lead.created_at).total_seconds() / 3600

    # Different schedules based on referral type
    # Different schedules based on referral type
    if lead.active_client:  # Is a referral
        # Stop if Care Start 
        if lead.care_status == "Care Start":
            return False
            
        # Interim: 48h, Regular: 1 week (168h)
        referral_type = lead.referral_type if lead.referral_type else 'Regular'
        interval_hours = 48 if referral_type == 'Interim' else 168
        return hours_since_last >= interval_hours
    else:
        # Non-referral lead: Every 7 days (1 week)
        return hours_since_last >= 168


def should_send_care_start_reminder(lead, last_reminder_time, auth_received_time):
    """Check if a care start reminder should be sent for authorized referrals"""
    # Respect user preference
    if hasattr(lead, 'send_reminders') and not lead.send_reminders:
        return False

    # Only send for referrals that have authorization received but haven't started care
    if not lead.active_client or not lead.authorization_received or lead.care_status == "Care Start":
        return False

    # Don't send if lead is inactive
    if lead.last_contact_status == "Inactive":
        return False

    # If no reminder sent yet, notify immediately (first reminder)
    if not last_reminder_time:
        return True

    # Calculate hours since last reminder and since authorization was received
    hours_since_last = (datetime.utcnow() - last_reminder_time).total_seconds() / 3600
    hours_since_auth = (datetime.utcnow() - auth_received_time).total_seconds() / 3600

    # Different schedules based on referral type
    # Updated: Every 24 hours for authorized referrals until Care Start
    return hours_since_last >= 24


def send_lead_reminders():
    """Check all active leads and create in-app reminder notifications if needed."""
    db = SessionLocal()
    print(f"[{datetime.now()}] Starting lead reminder scan...")
    try:
        # Get all leads that are not inactive
        all_leads = crud_leads.list_leads(db, limit=10000)
        active_leads = [
            lead for lead in all_leads 
            if lead.last_contact_status != "Inactive"
        ]
        
        print(f"[INFO] Found {len(active_leads)} active/follow-up leads to check.")
        
        for lead in active_leads:
            try:
                # Get the last reminder sent for this lead
                reminders = crud_email_reminders.get_reminders_by_lead(db, lead.id)
                last_reminder_time = reminders[0].sent_at if reminders else None
                
                if should_send_reminder(lead, last_reminder_time):
                    # Get the lead creator for in-app notifications.
                    if lead.created_by:
                        user = crud_users.get_user_by_username(db, lead.created_by)
                        if user:
                            print(f"[DEBUG] Reminder condition met for Lead ID {lead.id} ({lead.first_name}). Creating notification for {user.username}...")
                            
                            # Check if this is a referral or regular lead
                            if lead.active_client:  # Is a referral
                                # Get agency (payor) information
                                agency_name = "N/A"
                                agency_suboption = ""
                                if lead.agency_id:
                                    from app.crud.crud_agencies import get_agency
                                    agency = get_agency(db, lead.agency_id)
                                    if agency:
                                        agency_name = agency.name
                                
                                if lead.agency_suboption_id:
                                    from app.crud.crud_agency_suboptions import get_suboption_by_id
                                    suboption = get_suboption_by_id(db, lead.agency_suboption_id)
                                    if suboption:
                                        agency_suboption = suboption.name
                                
                                # Get CCU information
                                ccu_name = "N/A"
                                ccu_phone = "N/A"
                                ccu_fax = "N/A"
                                ccu_email = "N/A"
                                ccu_address = "N/A"
                                ccu_coordinator = "N/A"
                                if lead.ccu_id:
                                    from app.crud.crud_ccus import get_ccu_by_id
                                    ccu = get_ccu_by_id(db, lead.ccu_id)
                                    if ccu:
                                        ccu_name = ccu.name
                                        ccu_phone = ccu.phone if ccu.phone else "N/A"
                                        ccu_fax = ccu.fax if ccu.fax else "N/A"
                                        ccu_email = ccu.email if ccu.email else "N/A"
                                        ccu_address = ccu.address if ccu.address else "N/A"
                                        ccu_coordinator = ccu.care_coordinator_name if ccu.care_coordinator_name else "N/A"
                                
                                # Prepare referral-specific data
                                referral_info = {
                                    'name': f"{lead.first_name} {lead.last_name}",
                                    'phone': lead.phone,
                                    'dob': str(lead.dob) if lead.dob else 'N/A',
                                    'creator': lead.created_by,
                                    'created_date': lead.created_at.strftime('%m/%d/%Y'),
                                    'status': lead.last_contact_status,
                                    'referral_type': lead.referral_type if lead.referral_type else 'Regular',
                                    'payor_name': agency_name,
                                    'payor_suboption': agency_suboption,
                                    'ccu_name': ccu_name,
                                    'ccu_phone': ccu_phone,
                                    'ccu_fax': ccu_fax,
                                    'ccu_email': ccu_email,
                                    'ccu_address': ccu_address,
                                    'ccu_coordinator': ccu_coordinator,
                                    'care_status': lead.care_status if lead.care_status else 'N/A',
                                    'priority': lead.priority if lead.priority else 'Medium'
                                }
                                
                                subject = f"Referral Reminder [{referral_info['referral_type']}]: {lead.first_name} {lead.last_name}"
                                
                            else:  # Regular non-referral lead
                                subject = f"Lead Reminder: {lead.first_name} {lead.last_name}"
                            
                            # Record the reminder for scheduler timing/history only.
                            crud_email_reminders.create_reminder(
                                db=db,
                                lead_id=lead.id,
                                recipient_email=user.email or "",
                                subject=subject,
                                sent_by="system",
                                status="notification_only",
                                error_message=None
                            )
                            
                            # CREATE IN-APP NOTIFICATION
                            try:
                                notification_title = f"ID: {lead.id} | {lead.first_name} {lead.last_name}"
                                if lead.active_client:
                                    description = f"Referral Sent: Please follow-up with this referral. ({referral_info['referral_type']})"
                                    entity_type = "referral"
                                else:
                                    description = "Lead: Please follow-up with this lead."
                                    entity_type = "lead"
                                
                                crud_notifications.create_notification(
                                    db=db,
                                    user_id=user.id,
                                    title=notification_title,
                                    description=description,
                                    entity_id=lead.id,
                                    entity_type=entity_type
                                )
                            except Exception as notif_e:
                                print(f"[ERROR] Failed to create in-app notification: {notif_e}")
                            
                            if lead.active_client:
                                reminder_type = f"[{referral_info['referral_type']}]"
                            else:
                                reminder_type = "[Lead]"
                            print(f"[SUCCESS] Created {reminder_type} notification reminder for lead {lead.id}: {lead.first_name} {lead.last_name}")
                        else:
                            print(f"[WARN] No user found for lead creator: {lead.created_by} (Lead ID: {lead.id})")
                else:
                    # Optional tracking of why skipped
                    pass
            except Exception as inner_e:
                print(f"[ERROR] Error processing Lead ID {lead.id}: {inner_e}")

        # Now check for care start reminders for authorized referrals
        print(f"[INFO] Checking authorized referrals for Care Start reminders...")
        for lead in active_leads:
            try:
                # Only check referrals with authorization received but no care started
                if not lead.active_client or not lead.authorization_received or lead.care_status == "Care Start":
                    continue

                # Find when authorization was received
                auth_received_time = None
                try:
                    from app.crud.crud_activity_logs import get_lead_history
                    import json
                    history_logs = get_lead_history(db, lead.id)
                    for log in history_logs:
                        if log.old_value and log.new_value:
                            try:
                                old_val = json.loads(log.old_value) if isinstance(log.old_value, str) else log.old_value
                                new_val = json.loads(log.new_value) if isinstance(log.new_value, str) else log.new_value

                                # Check if authorization_received changed from False to True
                                if (isinstance(old_val, dict) and isinstance(new_val, dict) and
                                    old_val.get('authorization_received') == False and
                                    new_val.get('authorization_received') == True):
                                    auth_received_time = log.timestamp
                                    break
                            except (json.JSONDecodeError, TypeError):
                                continue
                except Exception:
                    pass

                if not auth_received_time:
                    continue  # Skip if we can't determine when authorization was received

                # Get the last care start reminder sent for this lead
                care_start_reminders = get_care_start_reminders_by_lead(db, lead.id)
                last_care_reminder_time = care_start_reminders[0].sent_at if care_start_reminders else None

                if should_send_care_start_reminder(lead, last_care_reminder_time, auth_received_time):
                    # Get the lead creator for in-app notifications.
                    if lead.created_by:
                        user = crud_users.get_user_by_username(db, lead.created_by)
                        if user:
                            print(f"[DEBUG] Care Start condition met for authorized Lead ID {lead.id}. Creating notification...")
                            
                            # Get agency (payor) information
                            agency_name = "N/A"
                            agency_suboption = ""
                            if lead.agency_id:
                                from app.crud.crud_agencies import get_agency
                                agency = get_agency(db, lead.agency_id)
                                if agency:
                                    agency_name = agency.name

                            if lead.agency_suboption_id:
                                from app.crud.crud_agency_suboptions import get_suboption_by_id
                                suboption = get_suboption_by_id(db, lead.agency_suboption_id)
                                if suboption:
                                    agency_suboption = suboption.name

                            # Get CCU information
                            ccu_name = "N/A"
                            ccu_phone = "N/A"
                            ccu_fax = "N/A"
                            ccu_email = "N/A"
                            ccu_address = "N/A"
                            ccu_coordinator = "N/A"
                            if lead.ccu_id:
                                from app.crud.crud_ccus import get_ccu_by_id
                                ccu = get_ccu_by_id(db, lead.ccu_id)
                                if ccu:
                                    ccu_name = ccu.name
                                    ccu_phone = ccu.phone if ccu.phone else "N/A"
                                    ccu_fax = ccu.fax if ccu.fax else "N/A"
                                    ccu_email = ccu.email if ccu.email else "N/A"
                                    ccu_address = ccu.address if ccu.address else "N/A"
                                    ccu_coordinator = ccu.care_coordinator_name if ccu.care_coordinator_name else "N/A"

                            # Prepare comprehensive care start reminder data
                            care_start_info = {
                                'name': f"{lead.first_name} {lead.last_name}",
                                'phone': lead.phone,
                                'dob': str(lead.dob) if lead.dob else 'N/A',
                                'creator': lead.created_by,
                                'created_date': lead.created_at.strftime('%m/%d/%Y'),
                                'status': lead.last_contact_status,
                                'referral_type': lead.referral_type if lead.referral_type else 'Regular',
                                'payor_name': agency_name,
                                'payor_suboption': agency_suboption,
                                'ccu_name': ccu_name,
                                'ccu_phone': ccu_phone,
                                'ccu_fax': ccu_fax,
                                'ccu_email': ccu_email,
                                'ccu_address': ccu_address,
                                'ccu_coordinator': ccu_coordinator,
                                'auth_received_date': auth_received_time.strftime('%m/%d/%Y'),
                                'days_since_auth': int((datetime.utcnow() - auth_received_time).total_seconds() / 86400),
                                'care_status': lead.care_status if lead.care_status else 'N/A',
                                'priority': lead.priority if lead.priority else 'Medium'
                            }

                            subject = f"Care Start Reminder [{care_start_info['referral_type']}]: {lead.first_name} {lead.last_name} - {care_start_info['days_since_auth']} days since authorization"

                            # Record the care start reminder for scheduler timing/history only.
                            create_care_start_reminder(
                                db=db,
                                lead_id=lead.id,
                                recipient_email=user.email or "",
                                subject=subject,
                                sent_by="system",
                                status="notification_only",
                                error_message=None
                            )

                            # CREATE IN-APP NOTIFICATION (CARE START)
                            try:
                                notification_title = f"ID: {lead.id} | {lead.first_name} {lead.last_name}"
                                description = f"Referral Sent: Please follow-up with this referral. ({care_start_info['days_since_auth']} days since Authorization)"
                                
                                crud_notifications.create_notification(
                                    db=db,
                                    user_id=user.id,
                                    title=notification_title,
                                    description=description,
                                    entity_id=lead.id,
                                    entity_type="referral"
                                )
                            except Exception as notif_e:
                                print(f"[ERROR] Failed to create care start notification: {notif_e}")

                            print(f"[SUCCESS] Created Care Start notification for authorized referral {lead.id}: {lead.first_name} {lead.last_name} ({care_start_info['days_since_auth']} days since auth)")
                        else:
                            print(f"[WARN] No user found for lead creator: {lead.created_by} (Lead ID: {lead.id})")
            except Exception as inner_e:
                 print(f"[ERROR] Error processing Care Start reminder for Lead ID {lead.id}: {inner_e}")

    except Exception as e:
        print(f"[CRITICAL] Error in send_lead_reminders: {e}")
    finally:
        db.close()
        print(f"[{datetime.now()}] Lead reminder scan complete.")


def run_scheduler():
    """Run the scheduler in background."""
    print(f"[{datetime.now()}] Scheduler continuous loop started.")
    while True:
        try:
            send_lead_reminders()
            send_daily_digest_if_due()
            print(f"[{datetime.now()}] Waiting 10 minutes for next check...")
        except Exception as e:
            print(f"[CRITICAL] Error in scheduler loop: {e}")
        
        # Wait 10 minutes before next check
        time.sleep(600)


def start_scheduler():
    """Start the background scheduler thread"""
    try:
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        print("[SUCCESS] Notification reminder background thread spawned.")
    except Exception as e:
        print(f"[ERROR] Failed to spawn scheduler thread: {e}")
