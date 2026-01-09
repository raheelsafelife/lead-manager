"""
Referrals Sent page: View and manage referrals
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

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
from frontend.common import prepare_lead_data_for_email, get_priority_tag


def view_referrals():
    """View and manage referrals only"""
    st.markdown('<div class="main-header">Referrals</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Initialize status filter in session state
    if 'referral_status_filter' not in st.session_state:
        st.session_state.referral_status_filter = "All"
    
    # Initialize my referrals filter
    if 'show_only_my_referrals' not in st.session_state:
        st.session_state.show_only_my_referrals = True  # Default to showing only user's referrals
    
    # Initialize active/inactive filter for referrals
    if 'referral_active_inactive_filter' not in st.session_state:
        st.session_state.referral_active_inactive_filter = "Active"  # Default to showing only active referrals
    
    # Toggle buttons for regular users to switch between My Referrals and All Referrals
    if st.session_state.user_role != "admin":
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>View Mode</h4>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "My Referrals",
                width="stretch",
                type="primary" if st.session_state.show_only_my_referrals else "secondary"
            ):
                st.session_state.show_only_my_referrals = True
                st.rerun()
        
        with col2:
            if st.button(
                "All Referrals",
                width="stretch",
                type="primary" if not st.session_state.show_only_my_referrals else "secondary"
            ):
                st.session_state.show_only_my_referrals = False
                st.rerun()
        
        st.divider()
    
    # Active/Inactive Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Active Status</h4>", unsafe_allow_html=True)
    ref_act_col1, ref_act_col2, ref_act_col3 = st.columns(3)
    
    with ref_act_col1:
        if st.button("Active", key="ref_active_filter", width="stretch",
                    type="primary" if st.session_state.referral_active_inactive_filter == "Active" else "secondary"):
            st.session_state.referral_active_inactive_filter = "Active"
            st.rerun()
    
    with ref_act_col2:
        if st.button("Inactive", key="ref_inactive_filter", width="stretch",
                    type="primary" if st.session_state.referral_active_inactive_filter == "Inactive" else "secondary"):
            st.session_state.referral_active_inactive_filter = "Inactive"
            st.rerun()
    
    with ref_act_col3:
        if st.button("All", key="ref_all_active_filter", width="stretch",
                    type="primary" if st.session_state.referral_active_inactive_filter == "All" else "secondary"):
            st.session_state.referral_active_inactive_filter = "All"
            st.rerun()
    
    st.divider()
    
    # Contact Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Contact Status</h4>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Intro Call", width="stretch", 
                    type="primary" if st.session_state.referral_status_filter == "Intro Call" else "secondary"):
            st.session_state.referral_status_filter = "Intro Call"
            st.rerun()
    
    with col2:
        if st.button("Follow Up", width="stretch",
                    type="primary" if st.session_state.referral_status_filter == "Follow Up" else "secondary"):
            st.session_state.referral_status_filter = "Follow Up"
            st.rerun()
    
    with col3:
        if st.button("No Response", width="stretch",
                    type="primary" if st.session_state.referral_status_filter == "No Response" else "secondary"):
            st.session_state.referral_status_filter = "No Response"
            st.rerun()
    
    with col4:
        if st.button("All", width="stretch",
                    type="primary" if st.session_state.referral_status_filter == "All" else "secondary"):
            st.session_state.referral_status_filter = "All"
            st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3 = st.columns(3)
    with col1:
        search_name = st.text_input("Search by name")
    with col2:
        filter_staff = st.text_input("Filter by staff")
    with col3:
        filter_source = st.text_input("Filter by source")
        
    # Referral Type Filter Buttons
    st.write("**Filter by Referral Type:**")
    col_t1, col_t2, col_t3 = st.columns([1, 1, 3])
    
    # Initialize referral type filter
    if 'referral_type_filter' not in st.session_state:
        st.session_state.referral_type_filter = "All"
        
    with col_t1:
        if st.button("Regular", type="primary" if st.session_state.referral_type_filter == "Regular" else "secondary", key="filter_reg"):
            st.session_state.referral_type_filter = "Regular"
            st.rerun()
            
    with col_t2:
        if st.button("Interim", type="primary" if st.session_state.referral_type_filter == "Interim" else "secondary", key="filter_int"):
            st.session_state.referral_type_filter = "Interim"
            st.rerun()
            
    with col_t3:
        if st.button("All Types", type="primary" if st.session_state.referral_type_filter == "All" else "secondary", key="filter_all_types"):
            st.session_state.referral_type_filter = "All"
            st.rerun()
    
    # Priority Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Priority</h4>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3, p_col4 = st.columns([1, 1, 1, 1])
    
    # Initialize priority filter
    if 'referral_priority_filter' not in st.session_state:
        st.session_state.referral_priority_filter = "All"
    
    with p_col1:
        if st.button("High", key="rp_high", width="stretch",
                    type="primary" if st.session_state.referral_priority_filter == "High" else "secondary"):
            st.session_state.referral_priority_filter = "High"
            st.rerun()
    with p_col2:
        if st.button("Medium", key="rp_medium", width="stretch",
                    type="primary" if st.session_state.referral_priority_filter == "Medium" else "secondary"):
            st.session_state.referral_priority_filter = "Medium"
            st.rerun()
    with p_col3:
        if st.button("Low", key="rp_low", width="stretch",
                    type="primary" if st.session_state.referral_priority_filter == "Low" else "secondary"):
            st.session_state.referral_priority_filter = "Low"
            st.rerun()
    with p_col4:
        if st.button("All Priorities", key="rp_all", width="stretch",
                    type="primary" if st.session_state.referral_priority_filter == "All" else "secondary"):
            st.session_state.referral_priority_filter = "All"
            st.rerun()
    
    # Payor Filter
    st.write("**Filter by Payor:**")
    agencies = crud_agencies.get_all_agencies(db)
    
    if 'payor_filter' not in st.session_state:
        st.session_state.payor_filter = "All"
    
    if agencies:
        agency_names = ["All"] + [a.name for a in agencies]
        selected_payor = st.selectbox("Select Payor", agency_names, index=agency_names.index(st.session_state.payor_filter) if st.session_state.payor_filter in agency_names else 0, key="payor_filter_select")
        
        if selected_payor != st.session_state.payor_filter:
            st.session_state.payor_filter = selected_payor
            st.rerun()
    else:
        st.info("No payors available. Add payors in User Management -> Payor.")
    
    # CCU Filter
    st.write("**Filter by CCU:**")
    from app.crud import crud_ccus
    
    ccus = crud_ccus.get_all_ccus(db)
    
    if 'ccu_filter' not in st.session_state:
        st.session_state.ccu_filter = "All"
    
    if ccus:
        ccu_names = ["All"] + [c.name for c in ccus]
        selected_ccu = st.selectbox("Select CCU", ccu_names, index=ccu_names.index(st.session_state.ccu_filter) if st.session_state.ccu_filter in ccu_names else 0, key="ccu_filter_select")
        
        if selected_ccu != st.session_state.ccu_filter:
            st.session_state.ccu_filter = selected_ccu
            st.rerun()
    else:
        st.info("No CCUs available. Add CCUs in User Management -> CCU.")
    
    st.divider()
    
    # Get all leads
    leads = crud_leads.list_leads(db, limit=1000)
    
    # FILTER: Only show referrals (active_client = True)
    leads = [l for l in leads if l.active_client == True]
    
    # Apply 'Show Only My Referrals' filter for regular users
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_referrals:
        leads = [l for l in leads if l.staff_name == st.session_state.username]
    
    # Apply contact status filter
    if st.session_state.referral_status_filter != "All":
        leads = [l for l in leads if l.last_contact_status == st.session_state.referral_status_filter]
    
    # Apply other filters
    if search_name:
        leads = [l for l in leads if search_name.lower() in f"{l.first_name} {l.last_name}".lower()]
    if filter_staff:
        leads = [l for l in leads if filter_staff.lower() in l.staff_name.lower()]
    if filter_source:
        leads = [l for l in leads if filter_source.lower() in l.source.lower()]
        
    # Apply Payor filter
    if st.session_state.payor_filter != "All":
        leads = [l for l in leads if l.agency and l.agency.name == st.session_state.payor_filter]
    
    # Apply CCU filter
    if st.session_state.ccu_filter != "All":
        leads = [l for l in leads if l.ccu and l.ccu.name == st.session_state.ccu_filter]
    
    # Apply Referral Type filter
    if st.session_state.referral_type_filter != "All":
        leads = [l for l in leads if l.referral_type == st.session_state.referral_type_filter]
    
    # Apply Priority filter
    if st.session_state.referral_priority_filter != "All":
        leads = [l for l in leads if l.priority == st.session_state.referral_priority_filter]
    
    # Apply active/inactive filter
    if st.session_state.referral_active_inactive_filter == "Active":
        leads = [l for l in leads if l.last_contact_status != "Inactive"]
    elif st.session_state.referral_active_inactive_filter == "Inactive":
        leads = [l for l in leads if l.last_contact_status == "Inactive"]
    # If "All", no filtering needed
    
    # Show count with filter info
    filter_info = f"Active Status: {st.session_state.referral_active_inactive_filter} | Status: {st.session_state.referral_status_filter} | Priority: {st.session_state.referral_priority_filter}"
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_referrals:
        filter_info += f" | Showing: My Referrals Only"
    st.write(f"**Showing {len(leads)} referrals** ({filter_info})")
    
    # Display referrals
    if leads:
        for lead in leads:
            p_tag = get_priority_tag(lead.priority)
            with st.expander(f"{lead.first_name} {lead.last_name} - {lead.staff_name}"):
                # Add priority tag at the top of expander
                st.markdown(p_tag, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {lead.id}")
                    st.write(f"**Name:** {lead.first_name} {lead.last_name}")
                    st.write(f"**Staff:** {lead.staff_name}")
                    st.write(f"**Source:** {lead.source}")
                    st.write(f"**Phone:** {lead.phone}")
                    if lead.age:
                        st.write(f"**Age:** {lead.age}")
                    st.markdown(f"**Priority:** {p_tag}", unsafe_allow_html=True)
                    st.write(f"**City:** {lead.city or 'N/A'}")
                
                with col2:
                    st.write(f"**Status:** {lead.last_contact_status}")
                    st.success(f"**Referral:** Yes ({lead.referral_type or 'Regular'})")
                    if lead.agency:
                        st.info(f"**Payor:** {lead.agency.name}")
                    if lead.ccu:
                        st.info(f"**CCU:** {lead.ccu.name}")
                    # Authorization Status
                    if lead.authorization_received:
                        soc_str = lead.soc_date.strftime('%m/%d/%Y') if lead.soc_date else 'Not Set'
                        st.success(f"**Auth:** Received | **Care:** {lead.care_status or 'N/A'} | **SOC:** {soc_str}")
                    else:
                        st.warning("**Auth:** Pending")
                    st.write(f"**Created:** {utc_to_local(lead.created_at).strftime('%Y-%m-%d')}")
                    st.write(f"**Updated:** {utc_to_local(lead.updated_at).strftime('%Y-%m-%d')}")
                    if lead.comments:
                        st.write(f"**Comments:** {lead.comments}")
                
                # Creator/Updater Info
                st.divider()
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    if lead.created_by:
                        st.markdown(f"**Created by: {lead.created_by} on {utc_to_local(lead.created_at).strftime('%m/%d/%Y at %I:%M %p')}**")
                    else:
                        st.markdown(f"**Created on {utc_to_local(lead.created_at).strftime('%m/%d/%Y')}**")
                
                with info_col2:
                    if lead.updated_by:
                        st.markdown(f"**Last updated by: {lead.updated_by} on {utc_to_local(lead.updated_at).strftime('%m/%d/%Y at %I:%M %p')}**")
                    else:
                        st.markdown(f"**Last updated on {utc_to_local(lead.updated_at).strftime('%m/%d/%Y')}**")
                
                # Permission check for edit/delete
                can_modify = (st.session_state.user_role == "admin" or 
                             lead.staff_name == st.session_state.username)
                
                if not can_modify:
                    st.warning(" You can only edit/delete your own referrals")
                
                # Action buttons
                col1, col2, col3, col4 = st.columns([1.0, 1.0, 2.0, 2.0])
                with col1:
                    if can_modify and st.button(" Edit", key=f"edit_ref_{lead.id}"):
                        st.session_state[f'editing_{lead.id}'] = True
                        st.rerun()
                with col2:
                    if can_modify and st.button(" Delete", key=f"delete_ref_{lead.id}"):
                        crud_leads.delete_lead(db, lead.id, st.session_state.username, st.session_state.get('user_id'))
                        st.success(" Referral deleted")
                        st.rerun()
                with col3:
                    # Show automatic email status
                    if lead.last_contact_status != "Inactive":
                        schedule = "6h x 2 days" if lead.referral_type == "Interim" else "24h x 7 days"
                        st.caption(f"Auto-emails: {schedule}")
                    else:
                        st.caption("Inactive - No emails")
                
                # Show email history for this referral
                reminders = crud_email_reminders.get_reminders_by_lead(db, lead.id)
                if reminders:
                    st.caption(f" Email History ({len(reminders)} sent):")
                    for reminder in reminders[:3]:  # Show last 3
                        status_icon = "" if reminder.status == "sent" else ""
                        st.caption(f"{status_icon} {utc_to_local(reminder.sent_at).strftime('%m/%d/%Y %I:%M %p')} -> {reminder.recipient_email}")
                
                with col3:
                    # Unmark Referral button (always shows unmark since we're in referrals view)
                    if can_modify:
                        if st.button("Unmark Referral", key=f"unmark_ref_{lead.id}", type="primary"):
                            # Toggle the referral status to False
                            update_data = LeadUpdate(
                                staff_name=lead.staff_name,
                                first_name=lead.first_name,
                                last_name=lead.last_name,
                                source=lead.source,
                                phone=lead.phone,
                                city=lead.city,
                                zip_code=lead.zip_code,
                                active_client=False,  # Unmark as referral
                                last_contact_status=lead.last_contact_status,
                                dob=lead.dob,
                                medicaid_no=lead.medicaid_no,
                                e_contact_name=lead.e_contact_name,
                                e_contact_phone=lead.e_contact_phone,
                                comments=lead.comments
                            )
                            crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                            st.success(f" Lead unmarked as Referral!")
                            st.rerun()
                
                with col4:
                    # History button and Authorization Received button side by side
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("History", key=f"history_ref_{lead.id}"):
                            # Toggle history view
                            key = f"show_history_ref_{lead.id}"
                            st.session_state[key] = not st.session_state.get(key, False)
                            st.rerun()
                    
                    with btn_col2:
                        # Authorization Received button - toggleable
                        if lead.authorization_received:
                            # Show unmark button if already authorized
                            if st.button("Unmark Auth", key=f"unmark_auth_ref_{lead.id}",
                                       help="Remove authorization received status"):
                                update_data = LeadUpdate(authorization_received=False)
                                updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                                if updated_lead:
                                    st.warning(f" Authorization unmarked for {lead.first_name} {lead.last_name}")
                                    st.rerun()
                                else:
                                    st.error(" Failed to unmark authorization")
                        else:
                            # Show mark as received button if not authorized
                            if st.button("Authorization Received", key=f"auth_ref_{lead.id}",
                                       help="Mark this referral as having received authorization"):
                                # Mark authorization as received
                                update_data = LeadUpdate(authorization_received=True)
                                updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                                if updated_lead:
                                    st.success(f" Authorization marked as received for {lead.first_name} {lead.last_name}")

                                    # Send authorization confirmation email
                                    try:
                                        # Get user email
                                        user = crud_users.get_user_by_username(db, st.session_state.username)
                                        if user and user.email:
                                            # Prepare referral data for email
                                            agency_name = "N/A"
                                            if lead.agency_id:
                                                agency = crud_agencies.get_agency(db, lead.agency_id)
                                                if agency:
                                                    agency_name = agency.name

                                            auth_data = {
                                                'name': f"{lead.first_name} {lead.last_name}",
                                                'phone': lead.phone,
                                                'creator': lead.created_by,
                                                'created_date': lead.created_at.strftime('%m/%d/%Y'),
                                                'referral_type': lead.referral_type or 'Regular',
                                                'payor_name': agency_name,
                                                'auth_date': datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')
                                            }

                                            # Send authorization confirmation email
                                            from app.utils.email_service import send_authorization_confirmation_email
                                            success = send_authorization_confirmation_email(auth_data, user.email)

                                            if success:
                                                st.info(" Authorization confirmation email sent")
                                            else:
                                                st.warning(" Authorization marked but email failed to send")
                                    except Exception as e:
                                        st.warning(" Authorization marked but email failed to send")

                                    # Store lead id and navigate to Referral Confirm page
                                    st.session_state['referral_confirm_lead_id'] = lead.id
                                    st.session_state['current_page'] = 'Referral Confirm'
                                    st.rerun()
                                else:
                                    st.error(" Failed to mark authorization as received")
                
                # History View
                if st.session_state.get(f"show_history_ref_{lead.id}", False):
                    st.info(f"Activity History for {lead.first_name} {lead.last_name}")
                    history_logs = crud_activity_logs.get_lead_history(db, lead.id)
                    
                    if history_logs:
                        for log in history_logs:
                            label = get_action_label(log.action_type)
                            time_ago = format_time_ago(log.timestamp)
                            
                            with st.container():
                                st.markdown(f"**{label}** - {time_ago}")
                                st.caption(f"By **{log.username}** on {utc_to_local(log.timestamp).strftime('%m/%d/%Y at %I:%M %p')}")
                                
                                if log.description:
                                    st.write(log.description)
                                
                                if log.old_value and log.new_value:
                                    changes = format_changes(log.old_value, log.new_value)
                                    if changes:
                                        for field, old_val, new_val in changes:
                                            st.caption(f"• {field}: {old_val} -> {new_val}")
                                st.divider()
                    else:
                        st.caption("No history recorded yet.")

                
                # Edit form (shown when Edit button is clicked)
                if st.session_state.get(f'editing_{lead.id}', False):
                    st.divider()
                    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Edit Referral</h4>", unsafe_allow_html=True)
                    
                    with st.form(f"edit_ref_form_{lead.id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_staff_name = st.text_input("**Staff Name** *", value=lead.staff_name)
                            edit_first_name = st.text_input("**First Name** *", value=lead.first_name)
                            edit_last_name = st.text_input("**Last Name** *", value=lead.last_name)
                            
                            edit_age = st.number_input("**Age**", min_value=0, max_value=120, value=int(lead.age or 0))
                            
                            source_options = ["Home Health Notify", "Web", "Direct Through CCU", "Event", "Word of Mouth", "Transfer", "Other"]
                            edit_source = st.selectbox("**Source** *", 
                                                      source_options,
                                                      index=source_options.index(lead.source) if lead.source in source_options else source_options.index("Other"))
                            edit_phone = st.text_input("**Phone** *", value=lead.phone)
                            edit_priority = st.selectbox("**Priority**", ["High", "Medium", "Low"], 
                                                        index=["High", "Medium", "Low"].index(lead.priority) if lead.priority in ["High", "Medium", "Low"] else 1)
                            st.markdown(get_priority_tag(edit_priority), unsafe_allow_html=True)
                            edit_city = st.text_input("**City**", value=lead.city or "")
                            edit_zip_code = st.text_input("**Zip Code**", value=lead.zip_code or "")
                            
                            # Payor Selection (only if active client)
                            edit_agency_id = None
                            edit_ccu_id = None
                            if lead.active_client:
                                from app.crud import crud_ccus
                                agencies = crud_agencies.get_all_agencies(db)
                                agency_options = {a.name: a.id for a in agencies}
                                current_agency_name = lead.agency.name if lead.agency else "None"
                                edit_agency_name = st.selectbox("**Payor**", ["None"] + list(agency_options.keys()), 
                                                              index=(["None"] + list(agency_options.keys())).index(current_agency_name) if current_agency_name in agency_options else 0)
                                
                                # Get payor ID
                                edit_agency_id = agency_options.get(edit_agency_name) if edit_agency_name != "None" else None
                                
                                # Payor Suboption Selection (if agency selected)
                                edit_agency_suboption_id = None
                                if edit_agency_id:
                                    from app.crud import crud_agency_suboptions
                                    suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=edit_agency_id)
                                    
                                    if suboptions:
                                        suboption_options = {s.name: s.id for s in suboptions}
                                        current_suboption_name = lead.agency_suboption.name if lead.agency_suboption else "None"
                                        edit_suboption_name = st.selectbox("**Suboption**", ["None"] + list(suboption_options.keys()),
                                                                          index=(["None"] + list(suboption_options.keys())).index(current_suboption_name) if current_suboption_name in suboption_options else 0)
                                        edit_agency_suboption_id = suboption_options.get(edit_suboption_name) if edit_suboption_name != "None" else None
                                
                                # CCU Selection
                                ccus = crud_ccus.get_all_ccus(db)
                                ccu_options = {c.name: c.id for c in ccus}
                                current_ccu_name = lead.ccu.name if lead.ccu else "None"
                                
                                if ccus:
                                    edit_ccu_name = st.selectbox("**CCU**", ["None"] + list(ccu_options.keys()),
                                                               index=(["None"] + list(ccu_options.keys())).index(current_ccu_name) if current_ccu_name in ccu_options else 0)
                                    edit_ccu_id = ccu_options.get(edit_ccu_name) if edit_ccu_name != "None" else None
                        
                        
                        with col2:
                            edit_status = st.selectbox("Contact Status", 
                                                      ["Intro Call", "Follow Up", "No Response", "Inactive"],
                                                      index=["Intro Call", "Follow Up", "No Response", "Inactive"].index(lead.last_contact_status) if lead.last_contact_status in ["Intro Call", "Follow Up", "No Response", "Inactive"] else 0)
                            edit_dob = st.date_input("Date of Birth", value=lead.dob)
                            edit_medicaid_no = st.text_input("Medicaid Number", value=lead.medicaid_no or "")
                            edit_e_contact_name = st.text_input("Emergency Contact Name", value=lead.e_contact_name or "")
                            edit_e_contact_phone = st.text_input("Emergency Contact Phone", value=lead.e_contact_phone or "")
                            edit_comments = st.text_area("Comments", value=lead.comments or "")
                        
                        st.divider()
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            save = st.form_submit_button("Save Changes", width="stretch", type="primary")
                        with col2:
                            cancel = st.form_submit_button(" Cancel", width="stretch")
                        
                        if save:
                            update_data = LeadUpdate(
                                staff_name=edit_staff_name,
                                first_name=edit_first_name,
                                last_name=edit_last_name,
                                source=edit_source,
                                phone=edit_phone,
                                age=edit_age if edit_age > 0 else None,
                                city=edit_city or None,
                                zip_code=edit_zip_code or None,
                                active_client=True,  # Keep as referral
                                last_contact_status=edit_status,
                                priority=edit_priority,
                                dob=edit_dob if edit_dob else None,
                                medicaid_no=edit_medicaid_no or None,
                                e_contact_name=edit_e_contact_name or None,
                                e_contact_relation=None,
                                e_contact_phone=edit_e_contact_phone or None,
                                comments=edit_comments or None,
                                agency_id=edit_agency_id,
                                agency_suboption_id=edit_agency_suboption_id,
                                ccu_id=edit_ccu_id
                            )
                            
                            crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                            st.session_state[f'editing_{lead.id}'] = False
                            st.success(" Referral updated successfully!")
                            st.rerun()
                        
                        if cancel:
                            st.session_state[f'editing_{lead.id}'] = False
                            st.rerun()
    else:
        st.info("No referrals found")
    
    db.close()
