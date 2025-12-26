"""
Referral Confirm page: Handle authorized referrals
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
from app.db import SessionLocal
from app import services_stats
from app.crud import crud_users, crud_leads, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email


def display_referral_confirm(lead, db, highlight=False):
    """Helper function to display a single referral in the confirm page"""

    # Show care status indicator in the expander title
    care_indicator = ""
    if lead.care_status == "Care Start":
        care_indicator = ""
    elif lead.care_status == "Not Start":
        care_indicator = ""
    else:
        care_indicator = ""

    # Highlight if this is the focused referral
    expander_title = f"{care_indicator} {lead.first_name} {lead.last_name} - {lead.staff_name}"
    if highlight:
        expander_title = f"{expander_title}"

    with st.expander(expander_title, expanded=highlight):

        # Show authorization received info if applicable
        if lead.authorization_received:
            # Find when authorization was received from activity logs
            auth_received_time = None
            try:
                history_logs = crud_activity_logs.get_lead_history(db, lead.id)
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

            # Show prominent authorization confirmation
            st.info("**AUTHORIZATION CONFIRMED** - This referral has received authorization and is ready for care coordination")
            st.markdown("---")
            st.markdown("## **AUTHORIZATION RECEIVED**")
            st.markdown("---")

            if auth_received_time:
                st.success(f"**Authorization Received:** {utc_to_local(auth_received_time).strftime('%m/%d/%Y at %I:%M %p')}")
            else:
                st.success("**Authorization Received**")

            # Authorization toggle button
            st.write("**Authorization Status:**")
            auth_col1, auth_col2 = st.columns(2)

            with auth_col1:
                if st.button("Mark Authorized", key=f"mark_auth_confirm_{lead.id}",
                           type="primary" if not lead.authorization_received else "secondary",
                           width="stretch",
                           disabled=lead.authorization_received):
                    update_data = LeadUpdate(authorization_received=True)
                    updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                    if updated_lead:
                        st.success(" Authorization marked as received")
                        st.rerun()
                    else:
                        st.error(" Failed to mark authorization")

            with auth_col2:
                if st.button("Unmark Authorized", key=f"unmark_auth_confirm_{lead.id}",
                           type="secondary" if lead.authorization_received else "primary",
                           width="stretch",
                           disabled=not lead.authorization_received):
                    update_data = LeadUpdate(authorization_received=False)
                    updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                    if updated_lead:
                        st.warning(" Authorization unmarked")
                        st.rerun()
                    else:
                        st.error(" Failed to unmark authorization")

            st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** {lead.id}")
            st.write(f"**Staff:** {lead.staff_name}")
            st.write(f"**Phone:** {lead.phone}")
            st.write(f"**Source:** {lead.source}")
            if lead.agency:
                st.info(f"**Payor:** {lead.agency.name}")
            if lead.ccu:
                st.info(f"**CCU:** {lead.ccu.name}")

        with col2:
            st.write(f"**Status:** {lead.last_contact_status}")
            st.success(f"**Referral Type:** {lead.referral_type or 'Regular'}")
            st.write(f"**City:** {lead.city or 'N/A'}")
            st.write(f"**Medicaid #:** {lead.medicaid_no or 'N/A'}")

        st.divider()

        # Show current SOC status if already set
        if lead.care_status:
            soc_str = lead.soc_date.strftime('%m/%d/%Y') if lead.soc_date else 'Not Set'
            if lead.care_status == "Care Start":
                st.success(f" **Care Status:** {lead.care_status} | **SOC:** {soc_str}")
            else:
                st.warning(f" **Care Status:** {lead.care_status}")
        else:
            st.warning(" Care status not set yet")

        st.divider()

        # Action Buttons: Care Start, Not Start, History
        st.write("**Select Care Status:**")
        col_start, col_not_start, col_history = st.columns(3)

        with col_start:
            if st.button("Care Start", key=f"care_start_{lead.id}", type="primary", width="stretch", disabled=(lead.care_status == "Care Start")):
                # Auto-fetch today's date as SOC
                today = date.today()
                update_data = LeadUpdate(
                    care_status="Care Start",
                    soc_date=today
                )
                crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                st.success(f" Care Started! SOC: {today.strftime('%m/%d/%Y')}")
                st.rerun()

        with col_not_start:
            if st.button("Not Start", key=f"not_start_{lead.id}", type="secondary", width="stretch", disabled=(lead.care_status == "Not Start")):
                update_data = LeadUpdate(
                    care_status="Not Start",
                    soc_date=None
                )
                crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                st.warning(" Care Not Started")
                st.rerun()

        with col_history:
            if st.button("History", key=f"history_confirm_{lead.id}", width="stretch"):
                st.session_state[f'show_confirm_history_{lead.id}'] = not st.session_state.get(f'show_confirm_history_{lead.id}', False)
                st.rerun()

        # History View - Show last 5 updates only
        if st.session_state.get(f'show_confirm_history_{lead.id}', False):
            st.divider()
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Last 5 Updates</h4>", unsafe_allow_html=True)
            history_logs = crud_activity_logs.get_lead_history(db, lead.id)

            if history_logs:
                # Limit to last 5 entries
                for log in history_logs[:5]:
                    label = get_action_label(log.action_type)
                    time_ago = format_time_ago(log.timestamp)

                    with st.container():
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.write(f"**{label}**")
                            if log.description:
                                st.caption(log.description[:100] + "..." if len(log.description) > 100 else log.description)
                        with col2:
                            st.caption(time_ago)
                        st.divider()
            else:
                st.caption("No activity history available.")


def referral_confirm():
    """Referral Confirm page - Shows all clients with authorization received"""
    st.markdown('<div class="main-header">Referral Confirm</div>', unsafe_allow_html=True)

    db = SessionLocal()

    # Get all leads with authorization received
    all_leads = crud_leads.list_leads(db, limit=1000)

    # Filter: Only referrals (active_client = True) with authorization_received = True
    authorized_referrals = [l for l in all_leads if l.active_client == True and l.authorization_received == True]

    # Check if we should focus on a specific referral
    specific_lead_id = st.session_state.get('referral_confirm_lead_id')
    if specific_lead_id:
        # Find the specific lead
        specific_lead = None
        for lead in authorized_referrals:
            if lead.id == specific_lead_id:
                specific_lead = lead
                break

        if specific_lead:
            # Show the specific referral first with a highlight
            st.success(f"**Focused Referral: {specific_lead.first_name} {specific_lead.last_name}**")
            st.divider()

            # Display the specific referral
            display_referral_confirm(specific_lead, db, highlight=True)

            # Clear the specific lead ID after displaying
            del st.session_state['referral_confirm_lead_id']

            st.divider()
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>All Other Authorized Referrals</h4>", unsafe_allow_html=True)

            # Remove the specific lead from the list to avoid duplication
            authorized_referrals = [l for l in authorized_referrals if l.id != specific_lead_id]
        else:
            # Clear the invalid lead ID if referral not found
            if 'referral_confirm_lead_id' in st.session_state:
                del st.session_state['referral_confirm_lead_id']

    # Show count
    st.write(f"**Total Clients with Authorization: {len(authorized_referrals)}**")
    
    st.divider()
    
    # Filter buttons for Care Status
    st.write("**Filter by Care Status:**")
    
    # Initialize filter in session state
    if 'confirm_care_filter' not in st.session_state:
        st.session_state.confirm_care_filter = "All"
    
    col_all, col_start, col_not_start = st.columns(3)
    
    with col_all:
        if st.button("All", key="filter_all", type="primary" if st.session_state.confirm_care_filter == "All" else "secondary", width="stretch"):
            st.session_state.confirm_care_filter = "All"
            st.rerun()
    
    with col_start:
        if st.button("Care Start", key="filter_care_start", type="primary" if st.session_state.confirm_care_filter == "Care Start" else "secondary", width="stretch"):
            st.session_state.confirm_care_filter = "Care Start"
            st.rerun()
    
    with col_not_start:
        if st.button("Not Start", key="filter_not_start", type="primary" if st.session_state.confirm_care_filter == "Not Start" else "secondary", width="stretch"):
            st.session_state.confirm_care_filter = "Not Start"
            st.rerun()
    
    st.divider()
    
    # Apply filter
    if st.session_state.confirm_care_filter == "Care Start":
        authorized_referrals = [l for l in authorized_referrals if l.care_status == "Care Start"]
    elif st.session_state.confirm_care_filter == "Not Start":
        authorized_referrals = [l for l in authorized_referrals if l.care_status == "Not Start"]
    
    # Show filtered count
    st.caption(f"Showing: {len(authorized_referrals)} clients ({st.session_state.confirm_care_filter})")
    
    if not authorized_referrals:
        st.info("No clients match the selected filter.")
        st.caption("Go to Referrals and click 'Authorization Received' on a referral to mark it as authorized.")
        db.close()
        return
    
    # Display each authorized referral
    for lead in authorized_referrals:
        display_referral_confirm(lead, db)
    
    db.close()
