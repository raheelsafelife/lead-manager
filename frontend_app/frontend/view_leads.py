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
import os
from app.db import SessionLocal
from app import services_stats
from app.crud import crud_users, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_agency_suboptions
# Local import to fix circular dependency
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email, get_call_status_tag, render_time, render_confirmation_modal, open_modal, close_modal, get_leads_cached, clear_leads_cache, show_add_comment_dialog, render_comment_stack, render_pagination, get_pagination_params, export_leads_to_excel


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
    owner_id = st.session_state.get('db_user_id')

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
    act_col1, act_col2, act_col3, act_spacer = st.columns([1, 1, 1, 2])
    
    with act_col1:
        if st.button("Active", key="active_filter", use_container_width=True,
                    type="primary" if st.session_state.active_inactive_filter == "Active" else "secondary"):
            st.session_state.active_inactive_filter = "Active"
            st.session_state.leads_page = 0
            st.rerun()
    
    with act_col2:
        if st.button("Inactive", key="inactive_filter", use_container_width=True,
                    type="primary" if st.session_state.active_inactive_filter == "Inactive" else "secondary"):
            st.session_state.active_inactive_filter = "Inactive"
            st.session_state.leads_page = 0
            st.rerun()
    
    with act_col3:
        if st.button("All", key="all_active_filter", use_container_width=True,
                    type="primary" if st.session_state.active_inactive_filter == "All" else "secondary"):
            st.session_state.active_inactive_filter = "All"
            st.session_state.leads_page = 0
            st.rerun()
    
    st.divider()
    
    # Contact Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Contact Status</h4>", unsafe_allow_html=True)
    c_col1, c_col2, c_col3, c_col4, c_spacer = st.columns([1.2, 1.2, 1.4, 1, 1])
    
    with c_col1:
        if st.button("Intro Call", key="filter_intro", use_container_width=True, 
                    type="primary" if st.session_state.status_filter == "Intro Call" else "secondary"):
            st.session_state.status_filter = "Intro Call"
            st.session_state.leads_page = 0
            st.rerun()
    
    with c_col2:
        if st.button("Follow Up", key="filter_followup", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "Follow Up" else "secondary"):
            st.session_state.status_filter = "Follow Up"
            st.session_state.leads_page = 0
            st.rerun()
    
    with c_col3:
        if st.button("No Response", key="filter_nores", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "No Response" else "secondary"):
            st.session_state.status_filter = "No Response"
            st.session_state.leads_page = 0
            st.rerun()
    
    with c_col4:
        if st.button("All Status", key="filter_all_status", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "All" else "secondary"):
            st.session_state.status_filter = "All"
            st.session_state.leads_page = 0
            st.rerun()
    
    # Call Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Call Status</h4>", unsafe_allow_html=True)
    cs_col1, cs_col2, cs_col3, cs_col4, cs_spacer = st.columns([1.1, 1, 1, 1, 1.3])
    with cs_col1:
        if st.button("Not Called", key="cs_notcalled", use_container_width=True,
                    type="primary" if st.session_state.call_status_filter == "Not Called" else "secondary"):
            st.session_state.call_status_filter = "Not Called"
            st.session_state.leads_page = 0
            st.rerun()
    with cs_col2:
        if st.button("Pending", key="cs_pending", use_container_width=True,
                    type="primary" if st.session_state.call_status_filter == "Pending" else "secondary"):
            st.session_state.call_status_filter = "Pending"
            st.session_state.leads_page = 0
            st.rerun()
    with cs_col3:
        if st.button("Called", key="cs_called", use_container_width=True,
                    type="primary" if st.session_state.call_status_filter == "Called" else "secondary"):
            st.session_state.call_status_filter = "Called"
            st.session_state.leads_page = 0
            st.rerun()
    with cs_col4:
        if st.button("All", key="cs_all", use_container_width=True,
                    type="primary" if st.session_state.call_status_filter == "All" else "secondary"):
            st.session_state.call_status_filter = "All"
            st.session_state.leads_page = 0
            st.rerun()

    # Tag Color Filter Dropdown
    ct_colors = ["All", "Blue", "Purple"]
    ct_icons = {"All": "All", "Blue": "🔵 Blue", "Purple": "🟣 Purple"}
    
    selected_ct = st.selectbox(
        "Filter by Color Tag",
        options=ct_colors,
        format_func=lambda x: ct_icons.get(x, x),
        index=ct_colors.index(st.session_state.tag_color_filter) if st.session_state.tag_color_filter in ct_colors else 0,
        key="view_leads_tag_color_filter_select"
    )
    
    if selected_ct != st.session_state.tag_color_filter:
        st.session_state.tag_color_filter = selected_ct
        st.session_state.leads_page = 0
        st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3, col_id, col4 = st.columns([1.5, 1.5, 1.5, 1.5, 1])
    with col1:
        search_name = st.text_input("Search by name", key="search_name_input")
    with col2:
        filter_staff = st.text_input("Filter by staff", key="search_staff_input")
    with col3:
        filter_source = st.text_input("Filter by source", key="search_source_input")
    with col_id:
        search_id = st.text_input("Search by ID", key="search_id_input")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Search", key="search_leads_btn", use_container_width=True):
            st.session_state.leads_page = 0
            st.rerun()

    # Excel Download Button
    download_all_col1, download_all_col2 = st.columns([4, 1])
    with download_all_col2:
        if st.button("📥 Download Excel", key="download_leads_excel_btn", use_container_width=True):
            # Fetch all matching leads (limit 2000 to cover all if user wants "all")
            all_filtered_leads = search_leads(
                db,
                search_query=search_name if search_name else None,
                staff_filter=filter_staff if filter_staff else None,
                source_filter=filter_source if filter_source else None,
                status_filter=st.session_state.status_filter,
                priority_filter=st.session_state.call_status_filter,
                active_inactive_filter=st.session_state.active_inactive_filter,
                owner_id=owner_id,
                only_my_leads=st.session_state.show_only_my_leads,
                include_deleted=st.session_state.show_deleted_leads,
                lead_type_filter="Lead",
                auth_received_filter=False,
                skip=0,
                limit=2000, 
                lead_id_filter=int(search_id) if search_id.strip().isdigit() else None,
                tag_color_filter=st.session_state.tag_color_filter,
                sort_by=st.session_state.leads_sort_by
            )
            if all_filtered_leads:
                excel_data = export_leads_to_excel(all_filtered_leads)
                st.download_button(
                    label="Click here to download",
                    data=excel_data,
                    file_name=f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="trigger_download_leads"
                )
            else:
                st.warning("No leads found to download.")

    # Sorting
    sort_col1, sort_col2 = st.columns([1, 4])
    with sort_col1:
        sort_options = ["Newest Added", "Recently Updated"]
        selected_sort = st.selectbox(
            "Sort By", 
            sort_options, 
            index=sort_options.index(st.session_state.leads_sort_by) if st.session_state.leads_sort_by in sort_options else 0,
            key="leads_sort_by_select"
        )
        if selected_sort != st.session_state.leads_sort_by:
            st.session_state.leads_sort_by = selected_sort
            st.rerun()


    # --- DATA FETCHING & FILTERING (PERFORMANCE OPTIMIZED) ---
    skip, limit, page_index, rows_per_page = get_pagination_params("leads", default_limit=10)
    
    only_my_leads = False
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_leads:
        only_my_leads = True
    
    # SQL-level search and count
    lead_id_filter = None
    if search_id and search_id.strip().isdigit():
        lead_id_filter = int(search_id.strip())

    leads = search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.status_filter,
        priority_filter=st.session_state.call_status_filter,
        active_inactive_filter=st.session_state.active_inactive_filter,
        owner_id=owner_id,
        only_my_leads=st.session_state.show_only_my_leads,
        include_deleted=st.session_state.show_deleted_leads,
        lead_type_filter="Lead",
        auth_received_filter=False,
        skip=skip,
        limit=limit,
        lead_id_filter=int(search_id) if search_id.strip().isdigit() else None,
        tag_color_filter=st.session_state.tag_color_filter,
        sort_by=st.session_state.leads_sort_by
    )
    
    # Total count for pagination
    total_leads = count_search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.status_filter,
        priority_filter=st.session_state.call_status_filter,
        active_inactive_filter=st.session_state.active_inactive_filter,
        owner_id=st.session_state.db_user_id,
        only_my_leads=st.session_state.show_only_my_leads,
        include_deleted=st.session_state.show_deleted_leads,
        lead_type_filter="Lead",
        auth_received_filter=False,
        lead_id_filter=int(search_id) if search_id.strip().isdigit() else None,
        tag_color_filter=st.session_state.tag_color_filter
    )
    
    # UI Metadata
    num_pages = max(1, (total_leads // rows_per_page) + (1 if total_leads % rows_per_page > 0 else 0))
    current_page_display = page_index + 1 if total_leads > 0 else 0
    
    # Show count with filter info
    filter_info = f"Active Status: {st.session_state.active_inactive_filter} | Status: {st.session_state.status_filter} | Call Status: {st.session_state.call_status_filter} | Tag: {st.session_state.tag_color_filter}"
    if only_my_leads:
        filter_info += f" | Showing: My Leads Only"
    
    st.write(f"**Showing {len(leads)} leads of {total_leads} total ({filter_info})**")
    
    # Display leads
    if leads:
        for lead in leads:
            from frontend.common import get_tag_color_dot, render_tag_color_picker
            tag_dot = get_tag_color_dot(lead.tag_color)

            # Define status options with emojis
            display_options = ["Not Called", "Pending", "Called"]
            value_map = {"Not Called": "Not Called", "Pending": "Pending", "Called": "Called"}
            reverse_map = {v: k for k, v in value_map.items()}
            
            cur_cs = lead.priority if lead.priority in value_map.values() else "Not Called"
            cur_display = reverse_map.get(cur_cs, "Not Called")

            # Layout: Expander on the left (wide), Dropdown on the right (narrow)
            exp_col, cs_col = st.columns([4.5, 1.5])
            
            with exp_col:
                tag_dot = get_tag_color_dot(lead.tag_color)
                # Remove cs_emoji from here as it's now in the dropdown
                header_label = f"{tag_dot} ID: {lead.id} | {lead.first_name} {lead.last_name}"
                if lead.staff_name:
                    header_label += f" - {lead.staff_name}"


                with st.expander(header_label):
                    # Tag Color Picker
                    render_tag_color_picker(lead.id, lead.tag_color, db, page_type="leads")
                    st.divider()

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**ID:** {lead.id}")
                        st.write(f"**Name:** {lead.first_name} {lead.last_name}")
                        st.write(f"**Staff:** {lead.staff_name}")
                        st.write(f"**Employee ID:** {lead.custom_user_id or 'N/A'}")
                        st.write(f"**Source:** {lead.source}")
                        # Source sub-type
                        if lead.source == "Event" and lead.event_name:
                            st.write(f"**Event:** {lead.event_name}")
                        elif lead.source == "Word of Mouth" and lead.word_of_mouth_type:
                            st.write(f"**Word of Mouth Type:** {lead.word_of_mouth_type}")
                        elif lead.source == "Other" and lead.other_source_type:
                            st.write(f"**Other Source:** {lead.other_source_type}")
                        st.write(f"**Phone:** {lead.phone or 'N/A'}")
                        st.write(f"**Email:** {lead.email or 'N/A'}")
                        dob_str = lead.dob.strftime('%m/%d/%Y') if lead.dob else 'N/A'
                        st.write(f"**DOB:** {dob_str}")
                        st.write(f"**Age:** {lead.age if lead.age is not None else 'N/A'}")
                        st.write(f"**SSN:** {lead.ssn or 'N/A'}")
                        st.write(f"**Medicaid #:** {lead.medicaid_no or 'N/A'}")
                    
                    with col2:
                        st.write(f"**Status:** {lead.last_contact_status}")
                        st.write(f"**Referral:** {'Yes' if lead.active_client else 'No'}")
                        # Address
                        city_str = lead.city or ''
                        state_str = lead.state or ''
                        if city_str and state_str and state_str.lower() in city_str.lower():
                            addr_parts = [p for p in [lead.street, lead.city, lead.zip_code] if p]
                        else:
                            addr_parts = [p for p in [lead.street, lead.city, lead.state, lead.zip_code] if p]
                        st.write(f"**Address:** {', '.join(addr_parts) if addr_parts else 'N/A'}")
                        
                        # Emergency Contact
                        st.write(f"**Emergency Contact:** {lead.e_contact_name or 'N/A'}")
                        st.write(f"**Relation:** {lead.e_contact_relation or 'N/A'}")
                        st.write(f"**EC Phone:** {lead.e_contact_phone or 'N/A'}")
                        
                        st.markdown(f"**Created:** {render_time(lead.created_at)}", unsafe_allow_html=True)
                        st.markdown(f"**Updated:** {render_time(lead.updated_at)}", unsafe_allow_html=True)
                        st.write(f"**Comments:** {lead.comments or 'None'}")
                        
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
                        
                        al_col1, al_col2 = st.columns(2)
                        with al_col1:
                            if st.button("↻ Restore Lead", key=f"restore_{lead.id}", type="primary", use_container_width=True):
                                from app.crud.crud_leads import restore_lead
                                if restore_lead(db, lead.id, st.session_state.username, st.session_state.get('db_user_id')):
                                    st.toast("Lead restored!", icon="✅")
                                    st.rerun()
                        
                        with al_col2:
                            if st.session_state.user_role == "admin":
                                if st.button("🗑️ Permanent Delete", key=f"perm_del_{lead.id}", use_container_width=True):
                                    open_modal('perm_delete', lead.id)
                    else:
                        # NORMAL MODE - Show Edit, Delete, Mark Referral buttons
                        act_col1, act_col2, act_col3, act_col4 = st.columns([0.7, 0.7, 1.3, 3.3])
                        with act_col1:
                            if can_modify:
                                if st.button("Edit", key=f"edit_lead_btn_main_{lead.id}", use_container_width=True):
                                    lead_dict = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
                                    open_modal('save_edit_modal', lead.id, title=f"{lead.first_name} {lead.last_name}", lead_data=lead_dict)
                        
                        with act_col2:
                            if can_modify:
                                if st.button("Delete", key=f"delete_lead_btn_main_{lead.id}", use_container_width=True):
                                    render_confirmation_modal(modal_type='soft_delete', target_id=lead.id, title='Delete Lead?', message=f"Are you sure you want to delete <b>{lead.first_name} {lead.last_name}</b>?", icon='🗑️', type='warning', confirm_label='DELETE')
                        
                        with act_col3:
                            if can_modify:
                                if not lead.active_client:
                                    if st.button("Mark Referral", key=f"mark_ref_btn_main_{lead.id}", type="secondary", use_container_width=True):
                                        render_confirmation_modal(modal_type='mark_ref_confirm', target_id=lead.id, title='Mark as Referral?', message=f"Mark <strong>{lead.first_name} {lead.last_name}</strong> as referral?", icon='🚩', type='info', confirm_label='YES')
                        
                        with act_col4:
                            btn_c1, btn_c2 = st.columns(2)
                            with btn_c1:
                                if st.button("History", key=f"history_btn_main_{lead.id}", use_container_width=True):
                                    from frontend.common import clear_modal_state
                                    clear_modal_state()
                                    key = f"show_history_{lead.id}"
                                    st.session_state[key] = not st.session_state.get(key, False)
                                    st.rerun()
                            with btn_c2:
                                if st.button("💬 Comment", key=f"add_comment_btn_{lead.id}", use_container_width=True):
                                    from frontend.common import clear_modal_state
                                    clear_modal_state()
                                    show_add_comment_dialog(lead.id, f"{lead.first_name} {lead.last_name}")
                    
                    # History View
                    if st.session_state.get(f"show_history_{lead.id}", False):
                        st.info(f"Activity History for {lead.first_name} {lead.last_name}")
                        history_logs = crud_activity_logs.get_lead_history(db, lead.id)
                        if history_logs:
                            for log in history_logs[:10]:
                                st.markdown(f"**{render_time(log.timestamp, style='ago')}** &bull; **{get_action_label(log.action_type)}** by **{log.username}**", unsafe_allow_html=True)
                                st.markdown(f"<div style='font-size: 0.85rem; color: #6B7280;'>Time: {render_time(log.timestamp)}</div>", unsafe_allow_html=True)
                                if log.description and log.description != get_action_label(log.action_type):
                                    st.caption(log.description)
                                
                                # Show changes if available
                                if log.old_value and log.new_value:
                                    changes = format_changes(log.old_value, log.new_value)
                                    if changes:
                                        for field, old, new in changes:
                                            st.markdown(f"<div style='font-size: 0.85rem; color: #6B7280; margin-left: 20px;'>&bull; <b>{field}:</b> {old} &rarr; {new}</div>", unsafe_allow_html=True)
                                st.divider()
                        else:
                            st.caption("No history recorded yet.")

                    # ATTACHMENTS
                    st.divider()
                    st.markdown("### 📎 Attachments")
                    try:
                        from app.crud import crud_attachments
                        with st.expander("➕ Upload New Attachment", expanded=False):
                            # GHOST UPLOAD FIX: Use a versioned key to force a reset after successful upload
                            up_key_ver = st.session_state.get(f"up_ver_leads_{lead.id}", 0)
                            uploaded_file = st.file_uploader("Choose file", type=['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'csv', 'txt'], key=f"attachment_upload_{lead.id}_{up_key_ver}")
                            if uploaded_file is not None and st.button("Upload", key=f"upload_btn_{lead.id}_{up_key_ver}", type="primary"):
                                from frontend.common import clear_modal_state
                                # GHOST POPUP KILLER: Proactively clear any stale modal state before rerunning
                                clear_modal_state()
                                
                                upload_dir = Path(__file__).parent.parent.parent / "backend" / "uploads"
                                upload_dir.mkdir(exist_ok=True)
                                file_path = upload_dir / f"{lead.id}_{uploaded_file.name}"
                                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                                crud_attachments.create_attachment(db, lead_id=lead.id, filename=uploaded_file.name, file_path=str(file_path), file_size=uploaded_file.size, uploaded_by=st.session_state.username)
                                
                                # UPLOADER RESET: Increment version to force a new widget
                                st.session_state[f"up_ver_leads_{lead.id}"] = up_key_ver + 1
                                st.rerun()
                        
                        attachments = crud_attachments.get_attachments_by_lead(db, lead.id)
                        if attachments:
                            for att in attachments:
                                atcol1, atcol2, atcol3, atcol4 = st.columns([4, 1, 1, 1])
                                with atcol1:
                                    time_str = render_time(att.uploaded_at)
                                    st.markdown(f"📄 **{att.filename}** - Uploaded by **{att.uploaded_by}** on {time_str}", unsafe_allow_html=True)
                                with atcol2:
                                    if st.button("👁️", key=f"view_lead_att_{att.id}", use_container_width=True, help="Preview Document"):
                                        open_modal('file_preview', att.id, title=att.filename, lead_data={'file_path': att.file_path, 'filename': att.filename})
                                with atcol3:
                                    if os.path.exists(att.file_path):
                                        with open(att.file_path, "rb") as f:
                                            st.download_button("⬇️", f, file_name=att.filename, key=f"download_{att.id}", use_container_width=True)
                                with atcol4:
                                    if st.session_state.user_role == "admin" and st.button("🗑️", key=f"delete_att_{att.id}", use_container_width=True):
                                        crud_attachments.delete_attachment(db, att.id)
                                        st.rerun()
                    except Exception as e: st.error(f"Attachment error: {str(e)}")

            with cs_col:
                bg_color = {"Not Called": "#FF3B30", "Pending": "#FFCC00", "Called": "#34C759"}.get(cur_cs, "#f0f2f6")
                text_color = "white" if cur_cs != "Pending" else "#1c1c1c"
                
                # Use the new status pill class from common.py
                from frontend.common import get_status_pill_class
                pill_cls = get_status_pill_class(cur_cs)

                # Marker for robust CSS targeting holding the status pill coloring class
                st.markdown(f'<div id="fused-marker-lead-{lead.id}" class="status-marker {pill_cls}" style="display:none"></div>', unsafe_allow_html=True)

                # Dynamic CSS for Pill Style + Referral Card
                st.markdown(f"""
                    <style>
                    /* THE CARD: Target the row containing our marker */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) {{
                        background: #EAF7FF !important;
                        border: 2px solid #35A7C7 !important;
                        border-radius: 10px !important;
                        margin: 8px 0 !important;
                        gap: 0 !important;
                        display: flex !important;
                        align-items: center !important;
                        min-height: 60px !important;
                        padding: 4px 12px 4px 0 !important;
                    }}
                    
                    /* THE LEFT SIDE (Expander) */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) div[data-testid="stExpander"] {{
                        background: transparent !important;
                        border: none !important;
                        flex-grow: 1 !important;
                    }}
                    
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) div[data-testid="stExpander"] summary {{
                        background: transparent !important;
                    }}

                    /* Remove default column padding/borders on the parent columns only */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) > div[data-testid*="olumn"] {{
                        padding: 0 !important;
                        background: transparent !important;
                        border: none !important;
                    }}
                    
                    /* Apply vertical flex layout only to the right column */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) > div[data-testid*="olumn"]:nth-child(2) {{
                        display: flex !important;
                        flex-direction: column !important;
                        justify-content: center !important;
                        height: 100% !important;
                    }}

                    /* Eliminate internal Streamlit gaps that push text out of bounds (Right column only) */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) > div[data-testid*="olumn"]:nth-child(2) > div[data-testid="stVerticalBlock"] {{
                        gap: 0 !important;
                        padding: 0 !important;
                        display: flex !important;
                        flex-direction: column !important;
                        align-items: flex-end !important;
                        justify-content: center !important;
                    }}
                    
                    /* Remove margins from Streamlit element containers in right column */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) > div[data-testid*="olumn"]:nth-child(2) > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {{
                        margin-bottom: 0 !important;
                        min-height: 0 !important;
                    }}
                    
                    /* Header text styling matching blueprint */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-lead-{lead.id}) div[data-testid="stExpander"] summary p {{
                        font-size: 18px !important;
                        font-weight: 600 !important;
                        color: #0b2a35 !important;
                    }}
                    </style>
                """, unsafe_allow_html=True)
                
                cs_key = f"inline_cs_lead_{lead.id}"
                selected_display = st.selectbox(
                    "Status",
                    display_options,
                    index=display_options.index(cur_display),
                    key=cs_key,
                    label_visibility="collapsed"
                )

                # Display updater info below the dropdown
                from frontend.common import get_updater_info
                st.markdown(get_updater_info(lead), unsafe_allow_html=True)
                
                selected_val = value_map.get(selected_display)
                if selected_val != cur_cs:
                    from app.crud.crud_leads import update_lead
                    from datetime import datetime as _dt
                    update_lead(db, lead.id, LeadUpdate(
                        priority=selected_val,
                        call_status_updated_by=st.session_state.username,
                        call_status_updated_at=_dt.utcnow()
                    ), st.session_state.username, st.session_state.get('db_user_id'))
                    clear_leads_cache()
                    st.rerun()

    else:
        st.info("No leads found")
    
    # --- PAGINATION UI CONTROLS ---
    render_pagination(total_leads, "leads")
    
    db.close()


def mark_referral_page():
    """Hidden page for marking a lead as referral with Payor and CCU selection"""
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
    
    col_t1, col_t2 = st.columns([1, 1])
    with col_t1:
        ref_type = st.radio("**Referral Type:**", ["Regular", "Interim"], horizontal=True)
    with col_t2:
        initial_status = st.selectbox("**Initial Status:**", ["Initial Referral Sent", "Assessment Scheduled", "Not Approved", "Services Refused",  "Inactive"])
    
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
            update_dict = {
                "active_client": True,
                "referral_type": ref_type,
                "agency_id": final_agency_id,
                "ccu_id": selected_ccu_id,
                "send_reminders": send_notif,
                "last_contact_status": initial_status
            }
            
            # Care Status Synchronization
            if initial_status == "Care Start":
                update_dict["care_status"] = "Care Start"
                update_dict["authorization_received"] = True
                update_dict["soc_date"] = date.today()
            elif initial_status == "Not Start":
                update_dict["care_status"] = "Not Start"
                update_dict["authorization_received"] = True
            elif initial_status == "Not Approved":
                update_dict["care_status"] = None
                update_dict["authorization_received"] = False
                
            update_data = LeadUpdate(**update_dict)
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
