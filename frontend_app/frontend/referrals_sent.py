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
from app.crud import crud_users, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_agency_suboptions
# Local import to fix circular dependency
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email, get_priority_tag, render_time, render_confirmation_modal, open_modal, close_modal, get_leads_cached, clear_leads_cache, show_add_comment_dialog, render_comment_stack, render_pagination


def view_referrals():
    """View and manage referrals only"""
    from app.crud.crud_leads import search_leads, count_search_leads, update_lead
    # Display persistent status messages if they exist
    if 'success_msg' in st.session_state:
        msg = st.session_state.pop('success_msg')
        st.toast(msg, icon="✅")
        st.success(f"**{msg}**")
    if 'error_msg' in st.session_state:
        msg = st.session_state.pop('error_msg')
        st.toast(msg, icon="❌")
        st.error(f"**{msg}**")

    st.markdown('<div class="main-header">Referrals</div>', unsafe_allow_html=True)
    
    db = SessionLocal()

    # --- TOP-LEVEL NAVIGATION HANDLING ---
    
    # Filters are now initialized in init_session_state() in common.py
    
    # Recycle Bin Toggle
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>🗑️ Recycle Bin</h4>", unsafe_allow_html=True)
    show_deleted = st.checkbox(
        "Show Deleted Leads",
        value=st.session_state.show_deleted_referrals,
        help="View referrals that have been deleted (can be restored)",
        key="ref_show_deleted_chk"
    )
    if show_deleted != st.session_state.show_deleted_referrals:
        st.session_state.show_deleted_referrals = show_deleted
        st.rerun()
    
    st.divider()
    
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
            st.session_state.referrals_page = 0
            st.rerun()
    
    with ref_act_col2:
        if st.button("Inactive", key="ref_inactive_filter", width="stretch",
                    type="primary" if st.session_state.referral_active_inactive_filter == "Inactive" else "secondary"):
            st.session_state.referral_active_inactive_filter = "Inactive"
            st.session_state.referrals_page = 0
            st.rerun()
    
    with ref_act_col3:
        if st.button("All", key="ref_all_active_filter", width="stretch",
                    type="primary" if st.session_state.referral_active_inactive_filter == "All" else "secondary"):
            st.session_state.referral_active_inactive_filter = "All"
            st.session_state.referrals_page = 0
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
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        search_name = st.text_input("Search by name")
    with col2:
        filter_staff = st.text_input("Filter by staff")
    with col3:
        filter_source = st.text_input("Filter by source")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Search", key="search_referrals_btn", use_container_width=True):
            st.session_state.referrals_page = 0
            st.rerun()
        
    # Referral Type Filter Buttons
    st.write("**Filter by Referral Type:**")
    col_t1, col_t2, col_t3 = st.columns([1, 1, 3])
    
    # Referral Type filter is now initialized in init_session_state() in common.py
        
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
    
    # Priority filter is now initialized in init_session_state() in common.py
    
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
    
    # Payor filter is now initialized in init_session_state() in common.py
    
    if agencies:
        agency_names = ["All"] + [a.name for a in agencies]
        selected_payor = st.selectbox("Select Payor", agency_names, index=agency_names.index(st.session_state.payor_filter) if st.session_state.payor_filter in agency_names else 0, key="payor_filter_select")
        
        if selected_payor != st.session_state.payor_filter:
            st.session_state.payor_filter = selected_payor
            st.session_state.referrals_page = 0
            st.rerun()
    else:
        st.info("No payors available. Add payors in User Management -> Payor.")
    
    # CCU Filter
    st.write("**Filter by CCU:**")
    
    ccus = crud_ccus.get_all_ccus(db)
    
    # CCU filter is now initialized in init_session_state() in common.py
    
    if ccus:
        ccu_names = ["All"] + [c.name for c in ccus]
        selected_ccu = st.selectbox("Select CCU", ccu_names, index=ccu_names.index(st.session_state.ccu_filter) if st.session_state.ccu_filter in ccu_names else 0, key="ccu_filter_select")
        
        if selected_ccu != st.session_state.ccu_filter:
            st.session_state.ccu_filter = selected_ccu
            st.session_state.referrals_page = 0
            st.rerun()
    else:
        st.info("No CCUs available. Add CCUs in User Management -> CCU.")
    
    st.divider()
    
    # --- DATA FETCHING & FILTERING (PERFORMANCE OPTIMIZED) ---
    
    # Track current page in session state
    if 'referrals_page' not in st.session_state:
        st.session_state.referrals_page = 0
    
    page_size = 50
    skip = st.session_state.referrals_page * page_size
    
    # Owner filter logic
    owner_id = st.session_state.get('db_user_id')
    only_my_referrals = False
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_referrals:
        only_my_referrals = True
    
    # SQL-level search and count
    leads = search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.referral_status_filter,
        priority_filter=st.session_state.referral_priority_filter,
        active_inactive_filter=st.session_state.referral_active_inactive_filter,
        owner_id=owner_id,
        only_my_leads=only_my_referrals,
        include_deleted=st.session_state.show_deleted_referrals,
        exclude_clients=False,
        only_clients=True,
        auth_received_filter=False,
        skip=st.session_state.get('refs_skip', 0),
        limit=st.session_state.get('refs_limit', 10)
    )
    
    # Post-process for referrals sent (Now handled at SQL level)
    # leads = [l for l in leads if l.active_client == True]
    
    total_leads = count_search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.referral_status_filter,
        priority_filter=st.session_state.referral_priority_filter,
        active_inactive_filter=st.session_state.referral_active_inactive_filter,
        owner_id=owner_id,
        only_my_leads=only_my_referrals,
        include_deleted=st.session_state.show_deleted_referrals,
        exclude_clients=False,
        only_clients=True,
        auth_received_filter=False
    )
    
    # UI Metadata
    num_pages = (total_leads // page_size) + (1 if total_leads % page_size > 0 else 0)
    current_page_display = st.session_state.referrals_page + 1 if total_leads > 0 else 0
    
    # Show count with filter info
    filter_info = f"Active Status: {st.session_state.referral_active_inactive_filter} | Status: {st.session_state.referral_status_filter} | Priority: {st.session_state.referral_priority_filter}"
    if only_my_referrals:
        filter_info += f" | Showing: My Referrals Only"
    
    if st.session_state.show_deleted_referrals:
        st.write(f"**Showing {len(leads)} deleted referrals of {total_leads} total**")
    st.write(f"**Showing {len(leads)} referrals of {total_leads} total** ({filter_info})")
    
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
                    st.success(f"**Referral: Yes ({lead.referral_type or 'Regular'})**")
                    if lead.agency:
                        with st.container():
                            st.info(f"**Payor Information:**")
                            try:
                                st.write(f"**Name:** {lead.agency.name}")
                                # Safely get Agency fields to avoid AttributeError due to caching
                                a_addr = getattr(lead.agency, 'address', None)
                                a_phone = getattr(lead.agency, 'phone', None)
                                a_fax = getattr(lead.agency, 'fax', None)
                                a_email = getattr(lead.agency, 'email', None)

                                if a_addr: st.write(f"**Address:** {a_addr}")
                                if a_phone: st.write(f"**Phone:** {a_phone}")
                                if a_fax: st.write(f"**Fax:** {a_fax}")
                                if a_email: st.write(f"**Email:** {a_email}")
                            except AttributeError:
                                st.warning("Payor details temporarily unavailable due to system cache. Please refresh.")

                    if lead.ccu:
                        with st.container():
                            st.info(f"**CCU Information:**")
                            try:
                                st.write(f"**Name:** {lead.ccu.name}")
                                # Safely get new fields to avoid AttributeError due to caching
                                c_street = getattr(lead.ccu, 'street', None)
                                c_city = getattr(lead.ccu, 'city', None)
                                c_state = getattr(lead.ccu, 'state', None)
                                c_zip = getattr(lead.ccu, 'zip_code', None)
                                c_coord = getattr(lead.ccu, 'care_coordinator_name', None)

                                # Display individual address components if available, otherwise fallback to full address
                                if any([c_street, c_city, c_state, c_zip]):
                                    addr_parts = []
                                    if c_street: addr_parts.append(c_street)
                                    if c_city: addr_parts.append(c_city)
                                    if c_state: addr_parts.append(c_state)
                                    if c_zip: addr_parts.append(c_zip)
                                    st.write(f"**Address:** {', '.join(addr_parts)}")
                                elif lead.ccu.address:
                                    st.write(f"**Address:** {lead.ccu.address}")
                                
                                if lead.ccu.phone: st.write(f"**Phone:** {lead.ccu.phone}")
                                if lead.ccu.fax: st.write(f"**Fax:** {lead.ccu.fax}")
                                if lead.ccu.email: st.write(f"**Email:** {lead.ccu.email}")
                                if c_coord: st.write(f"**Coordinator:** {c_coord}")
                            except AttributeError:
                                st.warning("CCU details temporarily unavailable due to system cache. Please refresh.")
                    # Authorization Status
                    if lead.authorization_received:
                        soc_str = lead.soc_date.strftime('%m/%d/%Y') if lead.soc_date else 'Not Set'
                        st.success(f"**Auth: Received | Care: {lead.care_status or 'N/A'} | SOC: {soc_str}**")
                    else:
                        st.warning("**Auth: Pending**")
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
                    st.warning("**You can only edit/delete your own referrals**")
                
                # RECYCLE BIN ACTIONS
                if st.session_state.show_deleted_referrals:
                    st.markdown("<div style='background-color: #fef3c7; padding: 10px; border-radius: 5px; margin: 10px 0;'>", unsafe_allow_html=True)
                    st.markdown("<p style='margin: 0; color: #92400e; font-weight: 600;'>🗑️ Deleted Referral</p>", unsafe_allow_html=True)
                    if lead.deleted_at:
                        st.markdown(f"<p style='margin: 0; color: #78350f; font-size: 0.85rem;'>Deleted by: {lead.deleted_by} on {render_time(lead.deleted_at)}</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("↻ Restore Referral", key=f"restore_ref_{lead.id}", type="primary", use_container_width=True):
                            st.session_state['active_modal'] = {
                                'modal_type': 'restore_ref',
                                'target_id': lead.id,
                                'title': 'Restore Referral?',
                                'message': f"Restore <strong>{lead.first_name} {lead.last_name}</strong> back to active referrals?",
                                'icon': '↻',
                                'type': 'info',
                                'confirm_label': 'RESTORE'
                            }
                            st.rerun()
                    
                    with col2:
                        if st.session_state.user_role == "admin":
                            if st.button("🗑️ Permanent Delete", key=f"perm_del_ref_{lead.id}", use_container_width=True):
                                st.session_state['active_modal'] = {
                                    'modal_type': 'perm_delete_ref',
                                    'target_id': lead.id,
                                    'title': 'Permanent Delete?',
                                    'message': f"Are you sure you want to <strong>PERMANENTLY DELETE</strong> <strong>{lead.first_name} {lead.last_name}</strong>?<br><br><span style='color: #DC2626; font-weight: bold;'>🔥 This cannot be undone.</span>",
                                    'icon': '⚠️',
                                    'type': 'error',
                                    'confirm_label': 'DELETE FOREVER'
                                }
                                st.rerun()
                    
                    # Skip normal actions in recycle bin mode
                    st.divider()
                    continue

                # Action buttons
                col1, col2, col3, col4 = st.columns([0.7, 0.7, 1.3, 3.3])
                with col1:
                    if can_modify:
                        if st.button("Edit", key=f"edit_lead_btn_ref_{lead.id}", use_container_width=True):
                            # Prepar lead data for edit modal
                            lead_dict = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
                            st.session_state.modal_open = True
                            st.session_state.modal_action = 'save_edit_modal'
                            st.session_state.modal_lead_id = lead.id
                            st.session_state.modal_lead_name = f"{lead.first_name} {lead.last_name}"
                            st.session_state.modal_data = {'title': f"{lead.first_name} {lead.last_name}", 'lead_data': lead_dict}
                            st.session_state['active_modal'] = {'modal_type': 'save_edit_modal', 'target_id': lead.id, 'title': f"{lead.first_name} {lead.last_name}", 'lead_data': lead_dict}
                            st.rerun()
                with col2:
                    if can_modify:
                        if st.button("Delete", key=f"delete_lead_btn_ref_{lead.id}", use_container_width=True):
                            render_confirmation_modal(modal_type='soft_delete_ref', target_id=lead.id, title='Delete Referral?', message=f"Are you sure you want to delete <strong>{lead.first_name} {lead.last_name}</strong>?", icon='🗑️', type='warning', confirm_label='DELETE', indicator='This will move it to the Recycle Bin.')
                
                with col3:
                    # Unmark Referral button
                    if can_modify:
                        if st.button("Unmark Referral", key=f"unmark_ref_btn_ref_{lead.id}", type="primary", use_container_width=True):
                            render_confirmation_modal(modal_type='unmark_ref', target_id=lead.id, title='Unmark Referral?', message=f"Are you sure you want to unmark <strong>{lead.first_name} {lead.last_name}</strong> as an active referral?", indicator='This will hide it from the Referrals list but keep the record in the main Lead List.', icon='🚫', type='warning', confirm_label='UNMARK')
                
                with col4:
                    # History, Add Comment, and Auth buttons in 3 columns
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    with btn_col1:
                        if st.button("History", key=f"history_btn_ref_{lead.id}", use_container_width=True):
                            st.session_state.modal_open = False
                            st.session_state.modal_action = None
                            st.session_state.pop('active_modal', None)
                            key = f"show_history_ref_{lead.id}"
                            st.session_state[key] = not st.session_state.get(key, False)
                            st.rerun()
                    
                    with btn_col2:
                         if st.button("💬 Comment", key=f"add_comment_btn_ref_{lead.id}", use_container_width=True, help="Add a new update/note"):
                            show_add_comment_dialog(db, lead.id, f"{lead.first_name} {lead.last_name}")
                            
                    with btn_col3:
                        # Authorization Received button - toggleable
                        if lead.authorization_received:
                            if st.button("Unmark Auth", key=f"unmark_auth_btn_ref_{lead.id}", help="Remove authorization received status", type="primary", use_container_width=True):
                                update_data = LeadUpdate(authorization_received=False)
                                updated_lead = update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('db_user_id'))
                                if updated_lead:
                                    st.toast(f"Auth reversed for {lead.last_name}", icon="↩️")
                                    st.rerun()
                        else:
                            if st.button("Mark Auth", key=f"mark_auth_btn_ref_{lead.id}", help="Mark as authorized and move to Referral Confirm", type="primary", use_container_width=True):
                                render_confirmation_modal(modal_type='auth_received', target_id=lead.id, title='Authorization Received?', message=f"Mark authorization as received for <strong>{lead.first_name} {lead.last_name}</strong>?", icon='✅', type='info', confirm_label='MARK RECEIVED')
                
                # History View
                if st.session_state.get(f"show_history_ref_{lead.id}", False):
                    st.info(f"Activity History for {lead.first_name} {lead.last_name}")
                    history_logs = crud_activity_logs.get_lead_history(db, lead.id)
                    if history_logs:
                        for log in history_logs:
                            label = get_action_label(log.action_type)
                            timeframe = render_time(log.timestamp, style="ago")
                            st.markdown(f"**{label}** - {timeframe}", unsafe_allow_html=True)
                            st.markdown(f"By **{log.username}** on {render_time(log.timestamp)}", unsafe_allow_html=True)
                            if log.description: st.write(log.description)
                            if log.old_value and log.new_value:
                                changes = format_changes(log.old_value, log.new_value)
                                if changes:
                                    for field, old_val, new_val in changes:
                                        st.caption(f"- {field}: {old_val} -> {new_val}")
                            st.divider()
                    else:
                        st.caption("No history recorded yet.")
    else:
        st.info("No referrals found")
    
    # --- PAGINATION UI CONTROLS ---
    st.session_state.refs_skip, st.session_state.refs_limit = render_pagination(total_leads, "refs")
    
    db.close()
