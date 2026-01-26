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
from app.crud import crud_users, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_agency_suboptions
# Local import to fix circular dependency
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email, get_priority_tag, render_time, render_confirmation_modal, open_modal, close_modal, get_leads_cached, clear_leads_cache, show_add_comment_dialog, render_comment_stack, render_pagination


def view_leads():
    """View and manage leads"""
    # Now import fresh
    from app.crud.crud_leads import search_leads, count_search_leads, list_leads, get_lead, update_lead, delete_lead, restore_lead, list_deleted_leads
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
    
    # Filters are now initialized in init_session_state() in common.py
    
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
            st.session_state.leads_page = 0
            st.rerun()
    
    with act_col2:
        if st.button("Inactive", key="inactive_filter", width="stretch",
                    type="primary" if st.session_state.active_inactive_filter == "Inactive" else "secondary"):
            st.session_state.active_inactive_filter = "Inactive"
            st.session_state.leads_page = 0
            st.rerun()
    
    with act_col3:
        if st.button("All", key="all_active_filter", width="stretch",
                    type="primary" if st.session_state.active_inactive_filter == "All" else "secondary"):
            st.session_state.active_inactive_filter = "All"
            st.session_state.leads_page = 0
            st.rerun()
    
    st.divider()
    
    # Contact Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Contact Status</h4>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Intro Call", width="stretch", 
                    type="primary" if st.session_state.status_filter == "Intro Call" else "secondary"):
            st.session_state.status_filter = "Intro Call"
            st.session_state.leads_page = 0
            st.rerun()
    
    with col2:
        if st.button("Follow Up", width="stretch",
                    type="primary" if st.session_state.status_filter == "Follow Up" else "secondary"):
            st.session_state.status_filter = "Follow Up"
            st.session_state.leads_page = 0
            st.rerun()
    
    with col3:
        if st.button("No Response", width="stretch",
                    type="primary" if st.session_state.status_filter == "No Response" else "secondary"):
            st.session_state.status_filter = "No Response"
            st.session_state.leads_page = 0
            st.rerun()
    
    with col4:
        if st.button("All", width="stretch",
                    type="primary" if st.session_state.status_filter == "All" else "secondary"):
            st.session_state.status_filter = "All"
            st.session_state.leads_page = 0
            st.rerun()
    
    # Priority Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Priority</h4>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3, p_col4 = st.columns([1, 1, 1, 1])
    
    with p_col1:
        if st.button("High", key="p_high", width="stretch",
                    type="primary" if st.session_state.priority_filter == "High" else "secondary"):
            st.session_state.priority_filter = "High"
            st.session_state.leads_page = 0
            st.rerun()
    with p_col2:
        if st.button("Medium", key="p_medium", width="stretch",
                    type="primary" if st.session_state.priority_filter == "Medium" else "secondary"):
            st.session_state.priority_filter = "Medium"
            st.session_state.leads_page = 0
            st.rerun()
    with p_col3:
        if st.button("Low", key="p_low", width="stretch",
                    type="primary" if st.session_state.priority_filter == "Low" else "secondary"):
            st.session_state.priority_filter = "Low"
            st.session_state.leads_page = 0
            st.rerun()
    with p_col4:
        if st.button("All Priorities", key="p_all", width="stretch",
                    type="primary" if st.session_state.priority_filter == "All" else "secondary"):
            st.session_state.priority_filter = "All"
            st.session_state.leads_page = 0
            st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        search_name = st.text_input("Search by name", key="search_name_input")
    with col2:
        filter_staff = st.text_input("Filter by staff", key="search_staff_input")
    with col3:
        filter_source = st.text_input("Filter by source", key="search_source_input")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Search", key="search_leads_btn", use_container_width=True):
            st.session_state.leads_page = 0
            st.rerun()

    # --- DATA FETCHING & FILTERING (PERFORMANCE OPTIMIZED) ---
    
    # Track current page in session state
    if 'leads_page' not in st.session_state:
        st.session_state.leads_page = 0
    
    page_size = 50
    skip = st.session_state.leads_page * page_size
    
    # Owner filter logic
    owner_id = st.session_state.get('db_user_id')
    only_my_leads = False
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_leads:
        only_my_leads = True
    
    # SQL-level search and count
    leads = search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.status_filter,
        priority_filter=st.session_state.priority_filter,
        active_inactive_filter=st.session_state.active_inactive_filter,
        owner_id=owner_id,
        only_my_leads=only_my_leads,
        include_deleted=st.session_state.show_deleted_leads,
        auth_received_filter=False,
        skip=st.session_state.get('leads_skip', 0),
        limit=st.session_state.get('leads_limit', 10)
    )
    
    total_leads = count_search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.status_filter,
        priority_filter=st.session_state.priority_filter,
        active_inactive_filter=st.session_state.active_inactive_filter,
        owner_id=owner_id,
        only_my_leads=only_my_leads,
        include_deleted=st.session_state.show_deleted_leads,
        exclude_clients=not st.session_state.show_deleted_leads,
        auth_received_filter=False
    )
    
    # UI Metadata
    num_pages = (total_leads // page_size) + (1 if total_leads % page_size > 0 else 0)
    current_page_display = st.session_state.leads_page + 1 if total_leads > 0 else 0
    
    # Show count with filter info
    filter_info = f"Active Status: {st.session_state.active_inactive_filter} | Status: {st.session_state.status_filter} | Priority: {st.session_state.priority_filter}"
    if only_my_leads:
        filter_info += f" | Showing: My Leads Only"
    
    st.write(f"**Showing {len(leads)} leads of {total_leads} total ({filter_info})**")
    
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
                    
                    # Display chronological comment stack
                    render_comment_stack(lead)
                
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
                                if restore_lead(db, lead.id, st.session_state.username, st.session_state.get('db_user_id')):
                                    msg = f"Success! {lead.first_name} {lead.last_name} has been restored to active leads."
                                    st.toast(msg, icon="✅")
                                    st.session_state['success_msg'] = msg
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
                    col1, col2, col3, col4 = st.columns([0.7, 0.7, 1.3, 3.3])
                    with col1:
                        if can_modify:
                            if st.button("Edit", key=f"edit_lead_btn_main_{lead.id}", use_container_width=True):
                                # Prepare serializable lead data for modal
                                lead_dict = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
                                st.session_state.modal_open = True
                                st.session_state.modal_action = 'save_edit_modal'
                                st.session_state.modal_lead_id = lead.id
                                st.session_state.modal_lead_name = f"{lead.first_name} {lead.last_name}"
                                st.session_state.modal_data = {'title': f"{lead.first_name} {lead.last_name}", 'lead_data': lead_dict}
                                st.session_state['active_modal'] = {'modal_type': 'save_edit_modal', 'target_id': lead.id, 'title': f"{lead.first_name} {lead.last_name}", 'lead_data': lead_dict}
                                st.rerun()
                    
                    with col2:
                        # Delete button
                        if can_modify:
                            if st.button("Delete", key=f"delete_lead_btn_main_{lead.id}", use_container_width=True):
                                render_confirmation_modal(modal_type='soft_delete', target_id=lead.id, title='Delete Lead?', message=f"Are you sure you want to delete <b>{lead.first_name} {lead.last_name}</b>?<br><br>💡 It will be moved to the Recycle Bin.", icon='🗑️', type='warning', confirm_label='DELETE')
                    
                    with col3:
                        # Toggle Referral button
                        if can_modify:
                            if not lead.active_client:
                                # Not a referral yet -> Navigate to Mark Referral page
                                if st.button("Mark Referral", key=f"mark_ref_btn_v5_{lead.id}", type="secondary", use_container_width=True):
                                    render_confirmation_modal(modal_type='mark_ref_confirm', target_id=lead.id, title='Mark as Referral?', message=f"This will move <strong>{lead.first_name} {lead.last_name}</strong> to 'Referrals Sent' and change its status.<br><br>You'll be redirected to complete referral details.", icon='🚩', type='info', confirm_label='YES, MARK REFERRAL')
                            else:
                                # Already a referral -> Show Unmark button
                                if st.button("Unmark Referral", key=f"unmark_ref_btn_main_{lead.id}", type="primary", use_container_width=True):
                                    render_confirmation_modal(modal_type='unmark_ref', target_id=lead.id, title='Unmark Referral?', message=f"Are you sure you want to unmark <strong>{lead.first_name} {lead.last_name}</strong> as an active referral?", indicator='This will hide it from the Referrals list but keep the record in the main Lead List.', icon='🚫', type='warning', confirm_label='UNMARK')
                    
                    with col4:
                        # History and Add Comment buttons in 2 columns
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            if st.button("History", key=f"history_btn_main_{lead.id}", use_container_width=True):
                                # CRITICAL: Clear modal state BEFORE toggling history
                                st.session_state.modal_open = False
                                st.session_state.modal_action = None
                                st.session_state.modal_lead_id = None
                                st.session_state.modal_lead_name = None
                                st.session_state.modal_data = {}
                                st.session_state.pop('active_modal', None)
                                
                                # Toggle history view
                                key = f"show_history_{lead.id}"
                                st.session_state[key] = not st.session_state.get(key, False)
                                st.rerun()
                        
                        with btn_col2:
                            if st.button("💬 Comment", key=f"add_comment_btn_{lead.id}", use_container_width=True, help="Add a new update/note"):
                                show_add_comment_dialog(db, lead.id, f"{lead.first_name} {lead.last_name}")
                
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

                # End of expander

                # Handle Mark Referral Modal Action
                if 'active_modal' in st.session_state and st.session_state['active_modal']['modal_type'] == 'mark_ref_confirm':
                    m = st.session_state['active_modal']
                    # This logic runs because we called render_confirmation_modal at top level
                    # But we need to define what happens if THIS specific modal is active
                    pass # Handled by the generic action == True block below for unified handling

                
                # Edit form (shown when Edit button is clicked)
                if st.session_state.get(f'editing_{lead.id}', False):
                    st.divider()
                    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Edit Lead</h4>", unsafe_allow_html=True)
                    
                # This block is now handled by the 'save_edit_modal' in the top-level modal logic
                # The content of the form is passed via lead_data to the modal.
                # The actual rendering of the form will happen within the modal function.
    else:
        st.info("No leads found")
    
    # --- PAGINATION UI CONTROLS ---
    st.session_state.leads_skip, st.session_state.leads_limit = render_pagination(total_leads, "leads")
    
    db.close()


def mark_referral_page():
    """Hidden page for marking a lead as referral with Payor and CCU selection"""
    import sys
    # Robustly clear CRUD modules from memory to pick up new signatures
    # We must clear the full package path names that Streamlit uses
    for mod_name in list(sys.modules.keys()):
        if 'app.crud.crud_ccus' in mod_name or 'app.crud.crud_leads' in mod_name:
            del sys.modules[mod_name]
    
    # Import fresh and update GLOBAL references so the rest of the function uses them
    global crud_ccus, crud_leads
    from app.crud import crud_ccus as fresh_ccus, crud_leads as fresh_leads
    crud_ccus = fresh_ccus
    crud_leads = fresh_leads
    
    from app.crud.crud_leads import get_lead, update_lead
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
    lead = get_lead(db, lead_id)
    
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
                            crud_agencies.create_agency(db, new_agency_name, st.session_state.username, st.session_state.db_user_id)
                            st.toast(f"Payor '{new_agency_name}' added!", icon="✅")
                            st.success(f"**Success! Added '{new_agency_name}'**")
                            st.rerun()
                    except Exception as e:
                        st.error(f"**Error creating payor: {e}**")

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
            new_ccu_street = st.text_input("Street")
            new_ccu_city = st.text_input("City")
            new_ccu_state = st.text_input("State", value="IL", max_chars=2)
            new_ccu_zip = st.text_input("Zip Code")
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
                            db, new_ccu_name, st.session_state.username, st.session_state.db_user_id,
                            street=new_ccu_street or None,
                            city=new_ccu_city or None,
                            state=new_ccu_state or None,
                            zip_code=new_ccu_zip or None,
                            phone=new_ccu_phone or None,
                            fax=new_ccu_fax or None,
                            email=new_ccu_email or None,
                            care_coordinator_name=new_ccu_coord or None
                        )
                        st.toast(f"CCU '{new_ccu_name}' added!", icon="✅")
                        st.success(f"**Success! Added '{new_ccu_name}'**")
                        st.rerun()
                except Exception as e:
                    st.error(f"**Error creating CCU: {e}**")

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
                    try:
                        with st.form(f"edit_ccu_ref_form_{selected_ccu.id}"):
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                u_name = st.text_input("Name", value=selected_ccu.name)
                                # Safely get attributes with getattr to handle Streamlit caching issues
                                val_street = getattr(selected_ccu, 'street', '') or ""
                                val_city = getattr(selected_ccu, 'city', '') or ""
                                val_state = getattr(selected_ccu, 'state', 'IL') or "IL"
                                val_zip = getattr(selected_ccu, 'zip_code', '') or ""
                                
                                u_street = st.text_input("Street", value=val_street)
                                u_city = st.text_input("City", value=val_city)
                                u_state = st.text_input("State", value=val_state, max_chars=2)
                                u_zip = st.text_input("Zip Code", value=val_zip)
                                u_phone = st.text_input("Phone", value=selected_ccu.phone or "")
                                u_fax = st.text_input("Fax", value=selected_ccu.fax or "")
                            with col_e2:
                                u_email = st.text_input("Email", value=selected_ccu.email or "")
                                u_coord = st.text_input("Coordinator", value=getattr(selected_ccu, 'care_coordinator_name', '') or "")
                            
                            if st.form_submit_button("Update CCU Details", use_container_width=True):
                                try:
                                    crud_ccus.update_ccu(
                                        db, selected_ccu.id, u_name, st.session_state.username, st.session_state.get('db_user_id'),
                                        street=u_street or None,
                                        city=u_city or None,
                                        state=u_state or None,
                                        zip_code=u_zip or None,
                                        phone=u_phone or None,
                                        fax=u_fax or None,
                                        email=u_email or None,
                                        care_coordinator_name=u_coord or None
                                    )
                                except TypeError as te:
                                    if "unexpected keyword argument 'street'" in str(te):
                                        # Fallback for extreme caching cases
                                        crud_ccus.update_ccu(
                                            db, selected_ccu.id, u_name, st.session_state.username, st.session_state.get('db_user_id')
                                        )
                                        st.warning("CCU updated with name only due to system cache. Full details will be available after server restart.")
                                    else:
                                        raise te
                                st.success("**CCU Updated!**")
                                st.rerun()
                    except AttributeError as e:
                        st.error(f"**Cache Error:** The application is using an older version of the CCU model. Please restart the application (run refresh.sh) to clear the system cache.")
                        st.info(f"Technical details: {e}")
                    except Exception as e:
                        st.error(f"**Error:** {e}")

    # Notification Preference
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Notifications & Tracking</h4>", unsafe_allow_html=True)
    send_notif = st.checkbox("Send Auto Email Reminders for this Lead", value=getattr(lead, 'send_reminders', True), 
                            help="If enabled, you will receive an immediate notification and recurring follow-up emails.")

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
                ccu_id=selected_ccu_id,
                send_reminders=send_notif
            )
            update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
            
            msg = f"Success! {lead.first_name} {lead.last_name} marked as a {ref_type} referral."
            st.toast(msg, icon="✅")
            st.session_state['success_msg'] = msg
            
            # Send email reminder (centralized logic)
            from frontend.common import send_initial_lead_reminders
            send_initial_lead_reminders(db, lead.id, st.session_state.username)
            
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
