"""
Automatic Email Scheduler for Lead Reminders
Different schedules based on lead type:
- Interim Referrals: Every 6 hours for 2 days (48 hours)
- Regular Referrals: Every 7 days until authorization received
- Non-Referral Leads: Every 48 hours until inactive
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.crud import crud_leads, crud_users, crud_email_reminders
from app.crud.crud_email_reminders import create_care_start_reminder, get_care_start_reminders_by_lead
from app.utils.email_service import send_simple_lead_email, send_referral_reminder_email
import time
import threading


def should_send_reminder(lead, last_reminder_time):
    """Check if a reminder should be sent for this lead based on type"""
    # Don't send if lead is inactive
    if lead.last_contact_status == "Inactive":
        return False

    # If no reminder sent yet, send immediately (first email)
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
            
        # Updated: Every 6 hours for ALL referrals until Care Start
        # This replaces previous logic of 48h for Interim and 7 days for Regular
        return hours_since_last >= 6
    else:
        # Non-referral lead: Every 48 hours until inactive
        return hours_since_last >= 48


def should_send_care_start_reminder(lead, last_reminder_time, auth_received_time):
    """Check if a care start reminder should be sent for authorized referrals"""
    # Only send for referrals that have authorization received but haven't started care
    if not lead.active_client or not lead.authorization_received or lead.care_status == "Care Start":
        return False

    # Don't send if lead is inactive
    if lead.last_contact_status == "Inactive":
        return False

    # If no reminder sent yet, send immediately (first email)
    if not last_reminder_time:
        return True

    # Calculate hours since last reminder and since authorization was received
    hours_since_last = (datetime.utcnow() - last_reminder_time).total_seconds() / 3600
    hours_since_auth = (datetime.utcnow() - auth_received_time).total_seconds() / 3600

    # Different schedules based on referral type
    # Updated: Every 6 hours for ALL authorized referrals until Care Start
    return hours_since_last >= 6


def send_lead_reminders():
    """Check all active leads and send reminders if needed"""
    db = SessionLocal()
    try:
        # Get all leads that are not inactive
        all_leads = crud_leads.list_leads(db, limit=10000)
        active_leads = [
            lead for lead in all_leads 
            if lead.last_contact_status != "Inactive"
        ]
        
        for lead in active_leads:
            # Get the last reminder sent for this lead
            reminders = crud_email_reminders.get_reminders_by_lead(db, lead.id)
            last_reminder_time = reminders[0].sent_at if reminders else None
            
            if should_send_reminder(lead, last_reminder_time):
                # Get the lead creator's email
                if lead.created_by:
                    user = crud_users.get_user_by_username(db, lead.created_by)
                    if user and user.email:
                        
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
                                'ccu_coordinator': ccu_coordinator
                            }
                            
                            # Send referral email
                            success = send_referral_reminder_email(referral_info, user.email)
                            subject = f"Referral Reminder [{referral_info['referral_type']}]: {lead.first_name} {lead.last_name}"
                            
                        else:  # Regular non-referral lead
                            # Prepare simple lead data
                            lead_info = {
                                'name': f"{lead.first_name} {lead.last_name}",
                                'phone': lead.phone,
                                'creator': lead.created_by,
                                'dob': str(lead.dob) if lead.dob else 'N/A',
                                'source': lead.source,
                                'status': lead.last_contact_status,
                                'created_date': lead.created_at.strftime('%m/%d/%Y')
                            }
                            
                            # Send simple email
                            success = send_simple_lead_email(lead_info, user.email)
                            subject = f"Lead Reminder: {lead.first_name} {lead.last_name}"
                        
                        # Record the reminder
                        status = "sent" if success else "failed"
                        crud_email_reminders.create_reminder(
                            db=db,
                            lead_id=lead.id,
                            recipient_email=user.email,
                            subject=subject,
                            sent_by="system",
                            status=status,
                            error_message=None if success else "Email service error"
                        )
                        
                        if success:
                            if lead.active_client:
                                reminder_type = f"[{referral_info['referral_type']}]"
                            else:
                                reminder_type = "[Lead]"
                            print(f"[SUCCESS] Sent {reminder_type} reminder for lead {lead.id}: {lead.first_name} {lead.last_name}")
                        else:
                            print(f"[ERROR] Failed to send reminder for lead {lead.id}")
                        
                        # Small delay to avoid overwhelming email server
                        time.sleep(1)

        # Now check for care start reminders for authorized referrals
        for lead in active_leads:
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
                # Get the lead creator's email
                if lead.created_by:
                    user = crud_users.get_user_by_username(db, lead.created_by)
                    if user and user.email:

                        # Prepare comprehensive care start reminder data
                        from app.utils.email_service import send_referral_reminder_email

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
                            'days_since_auth': int((datetime.utcnow() - auth_received_time).total_seconds() / 86400)
                        }

                        # Send care start reminder email
                        success = send_referral_reminder_email(care_start_info, user.email)
                        subject = f"⚠️ Care Start Reminder [{care_start_info['referral_type']}]: {lead.first_name} {lead.last_name} - {care_start_info['days_since_auth']} days since authorization"

                        # Record the care start reminder
                        status = "sent" if success else "failed"
                        create_care_start_reminder(
                            db=db,
                            lead_id=lead.id,
                            recipient_email=user.email,
                            subject=subject,
                            sent_by="system",
                            status=status,
                            error_message=None if success else "Email service error"
                        )

                        if success:
                            print(f"[SUCCESS] Sent Care Start reminder for authorized referral {lead.id}: {lead.first_name} {lead.last_name} ({care_start_info['days_since_auth']} days since auth)")
                        else:
                            print(f"[ERROR] Failed to send Care Start reminder for lead {lead.id}")

                        # Small delay to avoid overwhelming email server
                        time.sleep(1)

    except Exception as e:
        print(f"Error in send_lead_reminders: {e}")
    finally:
        db.close()


def run_scheduler():
    """Run the scheduler in background - checks every hour"""
    while True:
        try:
            print(f"[{datetime.now()}] Running lead reminder check...")
            send_lead_reminders()
            print(f"[{datetime.now()}] Reminder check complete. Next check in 1 hour.")
        except Exception as e:
            print(f"Error in scheduler: {e}")
        
        # Wait 1 hour before next check
        time.sleep(3600)


def start_scheduler():
    """Start the background scheduler thread"""
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("[SUCCESS] Email reminder scheduler started")
