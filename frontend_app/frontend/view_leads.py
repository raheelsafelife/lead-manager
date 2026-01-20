"""
View Leads page: View and manage leads, mark referral
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
from frontend.common import prepare_lead_data_for_email, get_priority_tag, render_time, render_confirmation_modal, open_modal, close_modal


def view_leads():
    """View and manage leads"""
    # Display persistent status messages if they exist
    if 'success_msg' in st.session_state:
        msg = st.session_state.pop('success_msg')
        st.toast(msg, icon="✅")
        st.success(f"**{msg}**")
    if 'error_msg' in st.session_state:
        msg = st.session_state.pop('error_msg')
        st.toast(msg, icon="❌")
        st.error(f"**{msg}**")

    st.markdown('<div class="main-header">Manage Leads</div>', unsafe_allow_html=True)
    
    db = SessionLocal()

    # --- TOP-LEVEL NAVIGATION HANDLING ---
    
    # Initialize status filter in session state
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = "All"
    
    # Initialize priority filter
    if 'priority_filter' not in st.session_state:
        st.session_state.priority_filter = "All"
    
    # Initialize my leads filter
    if 'show_only_my_leads' not in st.session_state:
        st.session_state.show_only_my_leads = True  # Default to showing only user's leads
    
    # Initialize active/inactive filter
    if 'active_inactive_filter' not in st.session_state:
        st.session_state.active_inactive_filter = "Active"  # Default to showing only active leads
    
    # Initialize recycle bin filter
    if 'show_deleted_leads' not in st.session_state:
        st.session_state.show_deleted_leads = False
    
    # Recycle Bin Toggle (Admin and Users can see their own deleted leads)
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Recycle Bin</h4>", unsafe_allow_html=True)
    show_deleted = st.checkbox(
        "Show Deleted Leads",
        value=st.session_state.show_deleted_leads,
        help="View leads that have been deleted (can be restored)"
    )
    if show_deleted != st.session_state.show_deleted_leads:
        st.session_state.show_deleted_leads = show_deleted
        st.rerun()
    
    st.divider()
    
    # Toggle buttons for regular users to switch between My Leads and All Leads
    if st.session_state.user_role != "admin":
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>View Mode</h4>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "My Leads",
                width="stretch",
                type="primary" if st.session_state.show_only_my_leads else "secondary"
            ):
                st.session_state.show_only_my_leads = True
                st.rerun()
        
        with col2:
            if st.button(
                "All Leads",
                width="stretch",
                type="primary" if not st.session_state.show_only_my_leads else "secondary"
            ):
                st.session_state.show_only_my_leads = False
                st.rerun()
        
        st.divider()
    
    # Active/Inactive Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Active Status</h4>", unsafe_allow_html=True)
    act_col1, act_col2, act_col3 = st.columns(3)
    
    with act_col1:
        if st.button("Active", key="active_filter", width="stretch",
                    type="primary" if st.session_state.active_inactive_filter == "Active" else "secondary"):
            st.session_state.active_inactive_filter = "Active"
            st.rerun()
    
    with act_col2:
        if st.button("Inactive", key="inactive_filter", width="stretch",
                    type="primary" if st.session_state.active_inactive_filter == "Inactive" else "secondary"):
            st.session_state.active_inactive_filter = "Inactive"
            st.rerun()
    
    with act_col3:
        if st.button("All", key="all_active_filter", width="stretch",
                    type="primary" if st.session_state.active_inactive_filter == "All" else "secondary"):
            st.session_state.active_inactive_filter = "All"
            st.rerun()
    
    st.divider()
    
    # Contact Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Contact Status</h4>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Intro Call", width="stretch", 
                    type="primary" if st.session_state.status_filter == "Intro Call" else "secondary"):
            st.session_state.status_filter = "Intro Call"
            st.rerun()
    
    with col2:
        if st.button("Follow Up", width="stretch",
                    type="primary" if st.session_state.status_filter == "Follow Up" else "secondary"):
            st.session_state.status_filter = "Follow Up"
            st.rerun()
    
    with col3:
        if st.button("No Response", width="stretch",
                    type="primary" if st.session_state.status_filter == "No Response" else "secondary"):
            st.session_state.status_filter = "No Response"
            st.rerun()
    
    with col4:
        if st.button("All", width="stretch",
                    type="primary" if st.session_state.status_filter == "All" else "secondary"):
            st.session_state.status_filter = "All"
            st.rerun()
    
    # Priority Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Priority</h4>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3, p_col4 = st.columns([1, 1, 1, 1])
    
    with p_col1:
        if st.button("High", key="p_high", width="stretch",
                    type="primary" if st.session_state.priority_filter == "High" else "secondary"):
            st.session_state.priority_filter = "High"
            st.rerun()
    with p_col2:
        if st.button("Medium", key="p_medium", width="stretch",
                    type="primary" if st.session_state.priority_filter == "Medium" else "secondary"):
            st.session_state.priority_filter = "Medium"
            st.rerun()
    with p_col3:
        if st.button("Low", key="p_low", width="stretch",
                    type="primary" if st.session_state.priority_filter == "Low" else "secondary"):
            st.session_state.priority_filter = "Low"
            st.rerun()
    with p_col4:
        if st.button("All Priorities", key="p_all", width="stretch",
                    type="primary" if st.session_state.priority_filter == "All" else "secondary"):
            st.session_state.priority_filter = "All"
            st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        search_name = st.text_input("Search by name")
    with col2:
        filter_staff = st.text_input("Filter by staff")
    with col3:
        filter_source = st.text_input("Filter by source")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Search", key="search_leads_btn", use_container_width=True):
            st.rerun()
    
    # Get leads based on recycle bin filter
    if st.session_state.show_deleted_leads:
        # Show only deleted leads
        leads = crud_leads.list_deleted_leads(db, limit=1000)
        st.info("**Recycle Bin Mode - Showing deleted leads only. Uncheck to see active leads.**")
    else:
        # Show normal leads (not deleted)
        leads = crud_leads.list_leads(db, limit=1000, include_deleted=False)
        # CRITICAL: Exclude active referrals (leads only appear here if not yet a referral)
        leads = [l for l in leads if not l.active_client]
    
    # Apply 'Show Only My Leads' filter for regular users
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_leads:
        leads = [l for l in leads if l.staff_name == st.session_state.username]
    
    # Apply contact status filter
    if st.session_state.status_filter != "All":
        leads = [l for l in leads if l.last_contact_status == st.session_state.status_filter]
    
    # Apply priority filter
    if st.session_state.priority_filter != "All":
        leads = [l for l in leads if l.priority == st.session_state.priority_filter]
    
    # Apply active/inactive filter
    if st.session_state.active_inactive_filter == "Active":
        leads = [l for l in leads if l.last_contact_status != "Inactive"]
    elif st.session_state.active_inactive_filter == "Inactive":
        leads = [l for l in leads if l.last_contact_status == "Inactive"]
    # If "All", no filtering needed
    
    # Apply other filters
    if search_name:
        leads = [l for l in leads if search_name.lower() in f"{l.first_name} {l.last_name}".lower()]
    if filter_staff:
        leads = [l for l in leads if filter_staff.lower() in l.staff_name.lower()]
    if filter_source:
        leads = [l for l in leads if filter_source.lower() in l.source.lower()]
    
    # Show count with filter info
    filter_info = f"Active Status: {st.session_state.active_inactive_filter} | Status: {st.session_state.status_filter} | Priority: {st.session_state.priority_filter}"
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_leads:
        filter_info += f" | Showing: My Leads Only"
    st.write(f"**Showing {len(leads)} leads ({filter_info})**")
    
    # Display leads
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
                    st.write(f"**Referral:** {'Yes' if lead.active_client else 'No'}")
                    st.markdown(f"**Created:** {render_time(lead.created_at)}", unsafe_allow_html=True)
                    st.markdown(f"**Updated:** {render_time(lead.updated_at)}", unsafe_allow_html=True)
                    if lead.comments:
                        st.write(f"**Comments:** {lead.comments}")
                
                # Creator/Updater Info
                st.divider()
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    if lead.created_by:
                        st.markdown(f"**Created by: {lead.created_by} on** {render_time(lead.created_at)}", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Created on** {render_time(lead.created_at)}", unsafe_allow_html=True)
                
                with info_col2:
                    if lead.updated_by:
                        st.markdown(f"**Last updated by: {lead.updated_by} on** {render_time(lead.updated_at)}", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Last updated on** {render_time(lead.updated_at)}", unsafe_allow_html=True)
                
                # Permission check for edit/delete
                can_modify = (st.session_state.user_role == "admin" or 
                             lead.staff_name == st.session_state.username)
                
                if not can_modify:
                    st.warning("**You can only edit/delete your own leads**")
                
                # Action buttons row
                if st.session_state.show_deleted_leads:
                    # RECYCLE BIN MODE - Show Restore and Permanent Delete
                    st.markdown("<div style='background-color: #fef3c7; padding: 10px; border-radius: 5px; margin: 10px 0;'>", unsafe_allow_html=True)
                    st.markdown("<p style='margin: 0; color: #92400e; font-weight: 600;'>Deleted Lead</p>", unsafe_allow_html=True)
                    if lead.deleted_at:
                        st.markdown(f"<p style='margin: 0; color: #78350f; font-size: 0.85rem;'>Deleted by: {lead.deleted_by} on {render_time(lead.deleted_at)}</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("↻ Restore Lead", key=f"restore_{lead.id}", type="primary", use_container_width=True):
                            # Restore confirmation
                            st.session_state[f'confirm_restore_{lead.id}'] = True
                            st.rerun()
                    
                    with col2:
                        if st.session_state.user_role == "admin":
                            if st.button("🗑️ Permanent Delete", key=f"perm_del_{lead.id}", use_container_width=True):
                                st.session_state[f'confirm_perm_delete_{lead.id}'] = True
                                st.rerun()
                    
                    # Restore confirmation dialog
                    if st.session_state.get(f'confirm_restore_{lead.id}', False):
                        st.warning("⚠️ **Restore Lead?**")
                        st.write(f"Restore **{lead.first_name} {lead.last_name}** back to active leads?")
                        conf_col1, conf_col2 = st.columns(2)
                        with conf_col1:
                            if st.button("✅ Yes, Restore", key=f"yes_restore_{lead.id}", type="primary"):
                                if crud_leads.restore_lead(db, lead.id, st.session_state.username, st.session_state.get('db_user_id')):
                                    st.session_state['success_msg'] = f"Success! {lead.first_name} {lead.last_name} has been restored to active leads."
                                    st.session_state.pop(f'confirm_restore_{lead.id}', None)
                                    st.rerun()
                                else:
                                    st.error("**Restore Failed - Could not restore lead.**")
                        with conf_col2:
                            if st.button("❌ Cancel", key=f"no_restore_{lead.id}"):
                                st.session_state.pop(f'confirm_restore_{lead.id}', None)
                                st.rerun()
                    
                    # Permanent delete confirmation dialog
                    if st.session_state.get(f'confirm_perm_delete_{lead.id}', False):
                        st.session_state['active_modal'] = {
                            'modal_type': 'perm_delete',
                            'target_id': lead.id,
                            'title': 'Permanent Delete?',
                            'message': f"Are you absolutely sure you want to <strong>PERMANENTLY DELETE</strong> <strong>{lead.first_name} {lead.last_name}</strong>?<br><br><span style='color: #DC2626; font-weight: bold;'>🔥 This action cannot be undone.</span>",
                            'icon': '⚠️',
                            'type': 'error',
                            'confirm_label': 'DELETE FOREVER'
                        }
                        st.session_state.pop(f'confirm_perm_delete_{lead.id}', None)
                        st.rerun()
                else:
                    # NORMAL MODE - Show Edit, Delete, Mark Referral buttons
                    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 1.5])
                    with col1:
                        if can_modify and st.button("Edit", key=f"edit_lead_btn_main_{lead.id}"):
                            # Prepare serializable lead data for modal
                            lead_dict = {
                                "id": lead.id,
                                "first_name": lead.first_name,
                                "last_name": lead.last_name,
                                "phone": lead.phone,
                                "staff_name": lead.staff_name,
                                "source": lead.source,
                                "city": lead.city,
                                "last_contact_status": lead.last_contact_status,
                                "priority": lead.priority,
                                "dob": lead.dob,
                                "medicaid_no": lead.medicaid_no,
                                "e_contact_name": lead.e_contact_name,
                                "e_contact_phone": lead.e_contact_phone,
                                "active_client": lead.active_client,
                                "comments": lead.comments
                            }
                            # Action-scoped state (Stability Refactor)
                            st.session_state.modal_open = True
                            st.session_state.modal_action = 'save_edit_modal'
                            st.session_state.modal_lead_id = lead.id
                            st.session_state.modal_lead_name = f"{lead.first_name} {lead.last_name}"
                            st.session_state.modal_data = {
                                'title': f"{lead.first_name} {lead.last_name}",
                                'lead_data': lead_dict
                            }
                            
                            # Legacy active_modal mapping
                            st.session_state['active_modal'] = {
                                'modal_type': 'save_edit_modal',
                                'target_id': lead.id,
                                'title': f"{lead.first_name} {lead.last_name}",
                                'lead_data': lead_dict
                            }
                            st.rerun()
                    
                    with col2:
                        # Delete button
                        if can_modify:
                            if st.button("Delete", key=f"delete_lead_btn_main_{lead.id}"):
                                render_confirmation_modal(
                                    modal_type='soft_delete',
                                    target_id=lead.id,
                                    title='Delete Lead?',
                                    message=f"Are you sure you want to delete <b>{lead.first_name} {lead.last_name}</b>?<br><br>💡 It will be moved to the Recycle Bin.",
                                    icon='🗑️',
                                    type='warning',
                                    confirm_label='DELETE'
                                )
                    
                    with col3:
                        # Toggle Referral button
                        if can_modify:
                            if not lead.active_client:
                                # Not a referral yet -> Navigate to Mark Referral page
                                if st.button("Mark Referral", key=f"mark_ref_btn_main_{lead.id}", use_container_width=True):
                                    render_confirmation_modal(
                                        modal_type='mark_ref_confirm',
                                        target_id=lead.id,
                                        title='Mark as Referral?',
                                        message=f"This will move <strong>{lead.first_name} {lead.last_name}</strong> to 'Referrals Sent' and change its status.<br><br>You'll be redirected to complete referral details.",
                                        icon='🚩',
                                        type='info',
                                        confirm_label='YES, MARK REFERRAL'
                                    )
                            else:
                                # Already a referral -> Show Unmark button
                                if st.button("Unmark Referral", key=f"unmark_ref_btn_main_{lead.id}", type="primary", use_container_width=True):
                                    render_confirmation_modal(
                                        modal_type='unmark_ref',
                                        target_id=lead.id,
                                        title='Unmark Referral?',
                                        message=f"Are you sure you want to unmark <strong>{lead.first_name} {lead.last_name}</strong> as an active referral?",
                                        indicator='This will hide it from the Referrals list but keep the record in the main Lead List.',
                                        icon='🚫',
                                        type='warning',
                                        confirm_label='UNMARK'
                                    )
                    
                    with col4:
                        # History button
                        if st.button("History", key=f"history_btn_main_{lead.id}"):
                            # Toggle history view
                            key = f"show_history_main_{lead.id}"
                            st.session_state[key] = not st.session_state.get(key, False)
                            st.rerun()
                
                # End of expander

                # Handle Mark Referral Modal Action
                if 'active_modal' in st.session_state and st.session_state['active_modal']['modal_type'] == 'mark_ref_confirm':
                    m = st.session_state['active_modal']
                    # This logic runs because we called render_confirmation_modal at top level
                    # But we need to define what happens if THIS specific modal is active
                    pass # Handled by the generic action == True block below for unified handling
                
                # History View
                if st.session_state.get(f"show_history_{lead.id}", False):
                    st.info(f"Activity History for {lead.first_name} {lead.last_name}")
                    history_logs = crud_activity_logs.get_lead_history(db, lead.id)
                    
                    if history_logs:
                        for log in history_logs:
                            label = get_action_label(log.action_type)
                            time_ago = format_time_ago(log.timestamp, st.session_state.get('user_timezone'))
                            with st.container():
                                timeframe = render_time(log.timestamp, style='ago')
                                st.markdown(f"**{label}** - {timeframe}", unsafe_allow_html=True)
                                st.markdown(f"By **{log.username}** on {render_time(log.timestamp)}", unsafe_allow_html=True)
                                
                                if log.description:
                                    st.write(log.description)
                                
                                if log.old_value and log.new_value:
                                    changes = format_changes(log.old_value, log.new_value)
                                    if changes:
                                        for field, old_val, new_val in changes:
                                            st.caption(f"- {field}: {old_val} -> {new_val}")
                                st.divider()
                    else:
                        st.caption("No history recorded yet.")

                
                # Edit form (shown when Edit button is clicked)
                if st.session_state.get(f'editing_{lead.id}', False):
                    st.divider()
                    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Edit Lead</h4>", unsafe_allow_html=True)
                    
                # This block is now handled by the 'save_edit_modal' in the top-level modal logic
                # The content of the form is passed via lead_data to the modal.
                # The actual rendering of the form will happen within the modal function.
    else:
        st.info("No leads found")
    
    db.close()


def mark_referral_page():
    """Hidden page for marking a lead as referral with Payor and CCU selection"""
    st.markdown('<div class="main-header">Mark Referral</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Get the lead ID from session state
    lead_id = st.session_state.get('mark_referral_lead_id')
    
    if not lead_id:
        st.warning("**No lead selected. Please go to View Leads and click 'Mark Referral' on a lead.**")
        if st.button("Go to View Leads"):
            st.session_state['current_page'] = None
            st.rerun()
        db.close()
        return
    
    # Get the lead
    lead = crud_leads.get_lead(db, lead_id)
    
    if not lead:
        st.error("**Lead not found**")
        if st.button("Go to View Leads"):
            st.session_state['current_page'] = None
            st.session_state['mark_referral_lead_id'] = None
            st.rerun()
        db.close()
        return
    
    # Back button
    if st.button("Back to Referrals"):
        st.session_state['current_page'] = None
        st.session_state['mark_referral_lead_id'] = None
        st.rerun()
    
    st.divider()
    
    # Show lead details
    st.markdown(f"<h4 style='font-weight: bold; color: #111827;'>{lead.first_name} {lead.last_name}</h4>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**ID:** {lead.id}")
        st.write(f"**Staff:** {lead.staff_name}")
        st.write(f"**Phone:** {lead.phone}")
        st.write(f"**Source:** {lead.source}")
    with col2:
        st.write(f"**Status:** {lead.last_contact_status}")
        st.write(f"**City:** {lead.city or 'N/A'}")
        st.write(f"**Medicaid #:** {lead.medicaid_no or 'N/A'}")
    
    st.divider()

    # REDUNDANCY CHECK: Prevent re-marking if already an active referral
    if lead.active_client:
        st.warning(f"**This lead is already marked as a referral ({lead.referral_type}).**")
        st.info("You cannot mark this lead as a referral again. Please return to the View Leads page.")
        
        if st.button("Back to View Leads", type="primary"):
            st.session_state['current_page'] = None
            st.session_state['mark_referral_lead_id'] = None
            st.rerun()
        
        db.close()
        return
    
    # Referral Type Selection
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Select Referral Type and Payor</h4>", unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        ref_type = st.radio("**Referral Type:**", ["Regular", "Interim"], horizontal=True)
    
    st.divider()
    
    # Payor Selection with Admin Add capability
    st.write("**Payor:**")
    
    # Add Payor (Admin Only)
    if st.session_state.user_role == "admin":
        with st.expander("Add New Payor", expanded=False):
            with st.form("add_agency_referral_form"):
                new_agency_name = st.text_input("New Payor Name")
                col_ab1, col_ab2 = st.columns([1, 1])
                with col_ab1:
                    submit_agency = st.form_submit_button("Add Payor", width="stretch", type="primary")
                
                if submit_agency and new_agency_name:
                    try:
                        existing = crud_agencies.get_agency_by_name(db, new_agency_name)
                        if existing:
                            st.error(f"**'{new_agency_name}' already exists**")
                        else:
                            crud_agencies.create_agency(db, new_agency_name, st.session_state.username, st.session_state.user_id)
                            st.success(f"**Added '{new_agency_name}'**")
                            st.rerun()
                    except Exception as e:
                        st.error(f"**Error: {e}**")

    agencies = crud_agencies.get_all_agencies(db)
    agency_options = {a.name: a.id for a in agencies}
    
    if not agencies:
        st.warning("**No payors available.**")
        selected_agency_name = "None"
    else:
        agency_list = ["None"] + list(agency_options.keys())
        selected_agency_name = st.selectbox("Select Payor", agency_list, label_visibility="collapsed")
    
    final_agency_id = agency_options.get(selected_agency_name) if selected_agency_name != "None" else None
    
    st.divider()
    
    # CCU Selection with General Add/Edit capability
    st.write("**CCU Details:**")
    
    # Add CCU (All Users)
    with st.expander("Add New CCU", expanded=False):
        with st.form("add_ccu_referral_form"):
            new_ccu_name = st.text_input("CCU Name *")
            new_ccu_address = st.text_input("Address")
            new_ccu_phone = st.text_input("Phone")
            new_ccu_fax = st.text_input("Fax")
            new_ccu_email = st.text_input("Email")
            new_ccu_coord = st.text_input("Care Coordinator")
            
            col_cb1, col_cb2 = st.columns([1, 1])
            with col_cb1:
                submit_ccu = st.form_submit_button("Add CCU", width="stretch", type="primary")
            
            if submit_ccu and new_ccu_name:
                try:
                    existing = crud_ccus.get_ccu_by_name(db, new_ccu_name)
                    if existing:
                        st.error(f"**'{new_ccu_name}' already exists**")
                    else:
                        crud_ccus.create_ccu(
                            db, new_ccu_name, st.session_state.username, st.session_state.user_id,
                            address=new_ccu_address or None,
                            phone=new_ccu_phone or None,
                            fax=new_ccu_fax or None,
                            email=new_ccu_email or None,
                            care_coordinator_name=new_ccu_coord or None
                        )
                        st.success(f"**Added '{new_ccu_name}'**")
                        st.rerun()
                except Exception as e:
                    st.error(f"**Error: {e}**")

    from app.crud import crud_ccus
    ccus = crud_ccus.get_all_ccus(db)
    ccu_options = {c.name: c.id for c in ccus}
    
    selected_ccu_id = None
    if not ccus:
        st.info("No CCUs available.")
    else:
        ccu_list = ["None"] + list(ccu_options.keys())
        selected_ccu_name = st.selectbox("Select CCU", ccu_list, label_visibility="collapsed")
        
        if selected_ccu_name != "None":
            selected_ccu_id = ccu_options.get(selected_ccu_name)
            
            # Show CCU Details with Edit capability
            selected_ccu = crud_ccus.get_ccu_by_id(db, selected_ccu_id)
            if selected_ccu:
                with st.expander(" Edit CCU Details (Update)", expanded=True):
                    with st.form(f"edit_ccu_ref_form_{selected_ccu.id}"):
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            u_name = st.text_input("Name", value=selected_ccu.name)
                            u_phone = st.text_input("Phone", value=selected_ccu.phone or "")
                            u_fax = st.text_input("Fax", value=selected_ccu.fax or "")
                        with col_e2:
                            u_email = st.text_input("Email", value=selected_ccu.email or "")
                            u_coord = st.text_input("Coordinator", value=selected_ccu.care_coordinator_name or "")
                            u_addr = st.text_input("Address", value=selected_ccu.address or "")
                        
                        if st.form_submit_button("Update CCU Details", width="stretch"):
                            try:
                                crud_ccus.update_ccu(
                                    db, selected_ccu.id, u_name, st.session_state.username, st.session_state.get('user_id'),
                                    address=u_addr or None,
                                    phone=u_phone or None,
                                    fax=u_fax or None,
                                    email=u_email or None,
                                    care_coordinator_name=u_coord or None
                                )
                                st.success("**CCU Updated!**")
                                st.rerun()
                            except Exception as e:
                                st.error(f"**Error: {e}**")

    st.divider()
    
    # Action Buttons
    col_confirm, col_cancel = st.columns(2)
    
    with col_confirm:
        if st.button("Confirm", type="primary", width="stretch"):
            update_data = LeadUpdate(
                active_client=True,
                referral_type=ref_type,
                agency_id=final_agency_id,
                # agency_suboption_id=final_agency_suboption_id, # Removed
                ccu_id=selected_ccu_id
            )
            crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
            
            # Send email reminder
            try:
                current_user = crud_users.get_user_by_username(db, st.session_state.username)
                if current_user and current_user.email:
                    payor_str = selected_agency_name if selected_agency_name != "None" else None
                    
                    ccu_details = {}
                    if selected_ccu_id:
                        ccu = crud_ccus.get_ccu_by_id(db, selected_ccu_id)
                        if ccu:
                            ccu_details = {
                                'ccu_name': ccu.name,
                                'ccu_address': ccu.address,
                                'ccu_email': ccu.email,
                                'ccu_fax': ccu.fax,
                                'ccu_phone': ccu.phone,
                                'ccu_coordinator': ccu.care_coordinator_name
                            }
                    
                    send_referral_reminder(
                        current_user.email,
                        st.session_state.username,
                        f"{lead.first_name} {lead.last_name}",
                        lead.id,
                        payor_name=payor_str,
                        payor_suboption=None, # Removed
                        phone=lead.phone,
                        source=lead.source,
                        **ccu_details
                    )
            except Exception as e:
                st.error(f"**Failed to send email: {e}**")
                pass # Still pass to allow status update, but user sees error.
            
            st.success(f"**Marked as {ref_type} Referral!**")
            st.session_state['current_page'] = None
            st.session_state['mark_referral_lead_id'] = None
            st.rerun()
    
    with col_cancel:
        if st.button("Cancel", width="stretch"):
            st.session_state['current_page'] = None
            st.session_state['mark_referral_lead_id'] = None
            st.rerun()
    
    db.close()
