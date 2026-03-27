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
import os
from app.db import SessionLocal
from app import services_stats
from app.crud import crud_users, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_agency_suboptions
# Local import to fix circular dependency
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email, get_call_status_tag, render_time, render_confirmation_modal, open_modal, close_modal, get_leads_cached, clear_leads_cache, show_add_comment_dialog, render_comment_stack, render_pagination, get_pagination_params, render_tag_color_picker, export_leads_to_excel


def view_referrals():
    """View and manage referrals only"""
    from app.crud.crud_leads import search_leads, count_search_leads, update_lead
    # Display persistent status messages if they exist
    if 'success_msg' in st.session_state:
        msg = st.session_state.pop('success_msg')
        st.toast(msg, icon="✅")
        st.success(f"**{msg}**")
    if 'refs_page' not in st.session_state:
        st.session_state.refs_page = 0
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
    ref_act_col1, ref_act_col2, ref_act_col3, ref_act_spacer = st.columns([1, 1, 1, 2])
    
    with ref_act_col1:
        if st.button("Active", key="ref_active_filter", use_container_width=True,
                    type="primary" if st.session_state.referral_active_inactive_filter == "Active" else "secondary"):
            st.session_state.referral_active_inactive_filter = "Active"
            st.session_state.referral_status_filter = "All"
            st.session_state.refs_page = 0
            st.rerun()
    
    with ref_act_col2:
        if st.button("Inactive", key="ref_inactive_filter", use_container_width=True,
                    type="primary" if st.session_state.referral_active_inactive_filter == "Inactive" else "secondary"):
            st.session_state.referral_active_inactive_filter = "Inactive"
            st.session_state.referral_status_filter = "All"
            st.session_state.refs_page = 0
            st.rerun()
    
    with ref_act_col3:
        if st.button("All", key="ref_all_active_filter", use_container_width=True,
                    type="primary" if st.session_state.referral_active_inactive_filter == "All" else "secondary"):
            st.session_state.referral_active_inactive_filter = "All"
            st.session_state.referral_status_filter = "All"
            st.session_state.refs_page = 0
            st.rerun()
    
    st.divider()
    
    # Referral Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Referral Status</h4>", unsafe_allow_html=True)
    
    if st.session_state.referral_active_inactive_filter == "Active":
        f_col1, f_col2, f_col_done, f_col_all = st.columns(4)
        with f_col1:
            if st.button("All Active", key="rs_active_all", use_container_width=True,
                        type="primary" if st.session_state.referral_status_filter == "All" else "secondary"):
                st.session_state.referral_status_filter = "All"
                st.session_state.refs_page = 0
                st.rerun()
        with f_col2:
            if st.button("Initial Referral Sent", key="rs_sent", use_container_width=True, 
                        type="primary" if st.session_state.referral_status_filter == "Initial Referral Sent" else "secondary"):
                st.session_state.referral_status_filter = "Initial Referral Sent"
                st.session_state.refs_page = 0
                st.rerun()
        with f_col_done:
            if st.button("Assessment Scheduled", key="rs_assess", use_container_width=True,
                        type="primary" if st.session_state.referral_status_filter == "Assessment Scheduled" else "secondary"):
                st.session_state.referral_status_filter = "Assessment Scheduled"
                st.session_state.refs_page = 0
                st.rerun()
        with f_col_all:
            if st.button("Assessment Done", key="rs_done", use_container_width=True,
                        type="primary" if st.session_state.referral_status_filter == "Assessment Done" else "secondary"):
                st.session_state.referral_status_filter = "Assessment Done"
                st.session_state.refs_page = 0
                st.rerun()
                
    elif st.session_state.referral_active_inactive_filter == "Inactive":
        f_col1, f_col2, f_col3, _4 = st.columns(4)
        with f_col1:
            if st.button("All Inactive", key="rs_inactive_all", use_container_width=True,
                        type="primary" if st.session_state.referral_status_filter == "All" else "secondary"):
                st.session_state.referral_status_filter = "All"
                st.session_state.refs_page = 0
                st.rerun()
        with f_col2:
            if st.button("Not Approved", key="rs_notapp", use_container_width=True,
                        type="primary" if st.session_state.referral_status_filter == "Not Approved" else "secondary"):
                st.session_state.referral_status_filter = "Not Approved"
                st.session_state.refs_page = 0
                st.rerun()
                
        with f_col3:
            if st.button("Services Refused", key="rs_refused", use_container_width=True,
                        type="primary" if st.session_state.referral_status_filter == "Services Refused" else "secondary"):
                st.session_state.referral_status_filter = "Services Refused"
                st.session_state.refs_page = 0
                st.rerun()
    else:
        f_col1, _f = st.columns([1, 4])
        with f_col1:
            if st.button("All Statuses", key="rs_all", use_container_width=True,
                        type="primary" if st.session_state.referral_status_filter == "All" else "secondary"):
                st.session_state.referral_status_filter = "All"
                st.session_state.refs_page = 0
                st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3, col_id, col4 = st.columns([1.5, 1.5, 1.5, 1.5, 1])
    with col1:
        search_name = st.text_input("Search by name", key="ref_search_name_input")
    with col2:
        filter_staff = st.text_input("Filter by staff", key="ref_search_staff_input")
    with col3:
        filter_source = st.text_input("Filter by source", key="ref_search_source_input")
    with col_id:
        search_id = st.text_input("Search by ID", key="search_id_input_ref")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Search", key="search_referrals_btn", use_container_width=True):
            st.session_state.refs_page = 0
            st.rerun()

    # Sorting
    sort_col1, sort_col2 = st.columns([1, 4])
    with sort_col1:
        sort_options = ["Newest Added", "Recently Updated"]
        selected_sort = st.selectbox(
            "Sort By", 
            sort_options, 
            index=sort_options.index(st.session_state.referrals_sort_by) if st.session_state.referrals_sort_by in sort_options else 0,
            key="referrals_sort_by_select"
        )
        if selected_sort != st.session_state.referrals_sort_by:
            st.session_state.referrals_sort_by = selected_sort
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
    
    # Call Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Filter by Call Status</h4>", unsafe_allow_html=True)
    cs_col1, cs_col2, cs_col3, cs_col4, cs_spacer = st.columns([1.1, 1, 1, 1, 1.3])

    with cs_col1:
        if st.button("Not Called", key="rcs_notcalled", use_container_width=True,
                    type="primary" if st.session_state.referral_call_status_filter == "Not Called" else "secondary"):
            st.session_state.referral_call_status_filter = "Not Called"
            st.rerun()
    with cs_col2:
        if st.button("Pending", key="rcs_pending", use_container_width=True,
                    type="primary" if st.session_state.referral_call_status_filter == "Pending" else "secondary"):
            st.session_state.referral_call_status_filter = "Pending"
            st.rerun()
    with cs_col3:
        if st.button("Called", key="rcs_called", use_container_width=True,
                    type="primary" if st.session_state.referral_call_status_filter == "Called" else "secondary"):
            st.session_state.referral_call_status_filter = "Called"
            st.rerun()
    with cs_col4:
        if st.button("All", key="rcs_all", use_container_width=True,
                    type="primary" if st.session_state.referral_call_status_filter == "All" else "secondary"):
            st.session_state.referral_call_status_filter = "All"
            st.rerun()

    # Tag Color Filter Dropdown
    ct_colors = ["All", "Blue", "Purple"]
    ct_icons = {"All": "All", "Blue": "🔵 Blue", "Purple": "🟣 Purple"}
    
    selected_ct = st.selectbox(
        "Filter by Color Tag",
        options=ct_colors,
        format_func=lambda x: ct_icons.get(x, x),
        index=ct_colors.index(st.session_state.referral_tag_color_filter) if st.session_state.referral_tag_color_filter in ct_colors else 0,
        key="referrals_sent_tag_color_filter_select"
    )
    
    if selected_ct != st.session_state.referral_tag_color_filter:
        st.session_state.referral_tag_color_filter = selected_ct
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
            st.session_state.refs_page = 0
            st.rerun()
    
    st.divider()
    
    # --- DATA FETCHING & FILTERING (PERFORMANCE OPTIMIZED) ---
    skip, limit, page_index, rows_per_page = get_pagination_params("refs", default_limit=10)
    
    # Owner filter logic
    owner_id = st.session_state.get('db_user_id')
    only_my_referrals = False
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_referrals:
        only_my_referrals = True
    
    # SQL-level search and count
    lead_id_filter = None
    if search_id and search_id.strip().isdigit():
        lead_id_filter = int(search_id.strip())

    # Strict Separation: ONLY show leads WITHOUT authorization on this page
    auth_val = False

    leads = search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.referral_status_filter,
        priority_filter=st.session_state.referral_call_status_filter,
        active_inactive_filter=st.session_state.referral_active_inactive_filter,
        owner_id=owner_id,
        only_my_leads=only_my_referrals,
        include_deleted=st.session_state.show_deleted_referrals,
        exclude_clients=False,
        only_clients=True,
        auth_received_filter=auth_val,
        skip=skip,
        limit=limit,
        lead_id_filter=lead_id_filter,
        referral_category_filter=st.session_state.referral_type_filter,
        tag_color_filter=st.session_state.referral_tag_color_filter,
        sort_by=st.session_state.referrals_sort_by
    )
    
    # Post-process for referrals sent (Now handled at SQL level)
    # leads = [l for l in leads if l.active_client == True]
    
    total_leads = count_search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=st.session_state.referral_status_filter,
        priority_filter=st.session_state.referral_call_status_filter,
        active_inactive_filter=st.session_state.referral_active_inactive_filter,
        owner_id=owner_id,
        only_my_leads=only_my_referrals,
        include_deleted=st.session_state.show_deleted_referrals,
        exclude_clients=False,
        only_clients=True,
        auth_received_filter=auth_val,
        lead_id_filter=lead_id_filter,
        referral_category_filter=st.session_state.referral_type_filter,
        tag_color_filter=st.session_state.referral_tag_color_filter
    )
    
    # UI Metadata
    num_pages = max(1, (total_leads // rows_per_page) + (1 if total_leads % rows_per_page > 0 else 0))
    current_page_display = st.session_state.refs_page + 1 if total_leads > 0 else 0
    
    # Excel Download Button
    download_all_col1, download_all_col2 = st.columns([4, 1])
    with download_all_col2:
        if st.button(" Download Excel", key="download_referrals_excel_btn", use_container_width=True):
            # Fetch all matching referrals (Match display logic exactly)
            all_filtered_leads = search_leads(
                db,
                search_query=search_name if search_name else None,
                staff_filter=filter_staff if filter_staff else None,
                source_filter=filter_source if filter_source else None,
                status_filter=st.session_state.referral_status_filter,
                priority_filter=st.session_state.referral_call_status_filter,
                active_inactive_filter=st.session_state.referral_active_inactive_filter,
                owner_id=owner_id,
                only_my_leads=only_my_referrals,
                include_deleted=st.session_state.show_deleted_referrals,
                exclude_clients=False,
                only_clients=True,
                auth_received_filter=False, # Match display logic
                referral_category_filter=st.session_state.referral_type_filter,
                skip=0,
                limit=2000, 
                lead_id_filter=int(search_id) if search_id.strip().isdigit() else None,
                tag_color_filter=st.session_state.referral_tag_color_filter,
                sort_by=st.session_state.referrals_sort_by
            )
            if all_filtered_leads:
                excel_data = export_leads_to_excel(all_filtered_leads)
                st.download_button(
                    label="Click here to download",
                    data=excel_data,
                    file_name=f"referrals_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="trigger_download_referrals"
                )
            else:
                st.warning("No referrals found to download.")

    # Show count with filter info
    filter_info = f"Active Status: {st.session_state.referral_active_inactive_filter} | Status: {st.session_state.referral_status_filter} | Call Status: {st.session_state.referral_call_status_filter} | Tag: {st.session_state.referral_tag_color_filter}"
    if only_my_referrals:
        filter_info += f" | Showing: My Referrals Only"
    
    if st.session_state.show_deleted_referrals:
        st.write(f"**Showing {len(leads)} deleted referrals of {total_leads} total**")
    st.write(f"**Showing {len(leads)} referrals of {total_leads} total** ({filter_info})")
    
    if leads:
        for lead in leads:
            from frontend.common import get_tag_color_dot
            from app.crud.crud_leads import update_lead as _ul

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
                header_text = f"{tag_dot} ID: {lead.id} | {lead.first_name} {lead.last_name}"
                if lead.staff_name:
                    header_text += f" - {lead.staff_name}"
                
                with st.expander(header_text):
                    # Tag Color Picker
                    render_tag_color_picker(lead.id, lead.tag_color, db, page_type="referrals")
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

                    with col2:
                        st.write(f"**Status:** {lead.last_contact_status}")
                        st.success(f"**Referral: Yes ({lead.referral_type or 'Regular'})**")
                        if lead.agency:
                            with st.container():
                                st.info(f"**Payor Information:**")
                                try:
                                    st.write(f"**Name:** {lead.agency.name}")
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
                                    c_street = getattr(lead.ccu, 'street', None)
                                    c_city = getattr(lead.ccu, 'city', None)
                                    c_state = getattr(lead.ccu, 'state', None)
                                    c_zip = getattr(lead.ccu, 'zip_code', None)
                                    c_coord = getattr(lead.ccu, 'care_coordinator_name', None)
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

                    # QUICK ACTIONS ROW
                    st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
                    
                    # Proportions: Mark Authorization is wider (ratio 1:1:2:1:1)
                    sub_col1, sub_col2, sub_col3, sub_col4, sub_col5 = st.columns([1, 1, 2, 1, 1])
                    
                    with sub_col1:
                        if st.button("Edit", key=f"edit_btn_ref_{lead.id}", use_container_width=True):
                            lead_dict = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
                            open_modal('save_edit_modal', lead.id, title=f"{lead.first_name} {lead.last_name}", lead_data=lead_dict)
                    
                    with sub_col2:
                        if st.button("Delete", key=f"del_btn_ref_{lead.id}", use_container_width=True):
                            render_confirmation_modal(modal_type='soft_delete', target_id=lead.id, title='Delete Referral?', message=f"Delete <b>{lead.first_name} {lead.last_name}</b>?", icon='🗑️', type='warning', confirm_label='DELETE')
                    
                    with sub_col3:
                        if st.button("Mark Authorization", key=f"mark_auth_btn_ref_{lead.id}", use_container_width=True, type="secondary"):
                            render_confirmation_modal(modal_type='auth_received', target_id=lead.id, title='Authorization Received?', message=f"Mark <b>{lead.first_name} {lead.last_name}</b> as Authorized?", icon='✅', type='success', confirm_label='YES')
                    
                    with sub_col4:
                        if st.button("💬 Comment", key=f"comment_btn_ref_{lead.id}", use_container_width=True):
                            from frontend.common import clear_modal_state
                            clear_modal_state()
                            show_add_comment_dialog(lead.id, f"{lead.first_name} {lead.last_name}")

                    with sub_col5:
                        if st.button("History", key=f"history_btn_ref_{lead.id}", use_container_width=True):
                            from frontend.common import clear_modal_state
                            clear_modal_state()
                            key = f"show_history_ref_{lead.id}"
                            st.session_state[key] = not st.session_state.get(key, False)
                            st.rerun()

                    # ATTACHMENTS SECTION
                    st.divider()
                    st.markdown("### 📎 Attachments")
                    try:
                        from app.crud import crud_attachments
                        with st.expander("➕ Upload New Attachment", expanded=False):
                            # GHOST UPLOAD FIX: Use a versioned key to force a reset after successful upload
                            up_key_ver = st.session_state.get(f"up_ver_{lead.id}", 0)
                            uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'csv', 'txt'], key=f"upload_ref_{lead.id}_{up_key_ver}")
                            if uploaded_file is not None:
                                if st.button("Upload", key=f"btn_upload_ref_{lead.id}_{up_key_ver}", type="primary"):
                                    from frontend.common import clear_modal_state
                                    # GHOST POPUP KILLER: Proactively clear any stale modal state before rerunning
                                    clear_modal_state()
                                    
                                    upload_dir = Path(__file__).parent.parent.parent / "backend" / "uploads"
                                    upload_dir.mkdir(exist_ok=True)
                                    file_path = upload_dir / f"{lead.id}_{uploaded_file.name}"
                                    with open(file_path, "wb") as f:
                                        f.write(uploaded_file.getbuffer())
                                    crud_attachments.create_attachment(db, lead_id=lead.id, filename=uploaded_file.name, file_path=str(file_path), file_size=uploaded_file.size, uploaded_by=st.session_state.username)
                                    
                                    # UPLOADER RESET: Increment version to force a new widget
                                    st.session_state[f"up_ver_{lead.id}"] = up_key_ver + 1
                                    st.success(f"✅ Uploaded: {uploaded_file.name}")
                                    st.rerun()
                        
                        attachments = crud_attachments.get_attachments_by_lead(db, lead.id)
                        if attachments:
                            for att in attachments:
                                att_col1, att_col2, att_col3, att_col4 = st.columns([4, 1, 1, 1])
                                with att_col1:
                                    time_str = render_time(att.uploaded_at)
                                    st.markdown(f"📄 **{att.filename}** - Uploaded by **{att.uploaded_by}** on {time_str}", unsafe_allow_html=True)
                                with att_col2:
                                    if st.button("👁️", key=f"view_ref_{att.id}", use_container_width=True, help="Preview Document"):
                                        open_modal('file_preview', att.id, title=att.filename, lead_data={'file_path': att.file_path, 'filename': att.filename})
                                with att_col3:
                                    if os.path.exists(att.file_path):
                                        with open(att.file_path, "rb") as f:
                                            st.download_button("⬇️", f, file_name=att.filename, key=f"dl_ref_{att.id}", use_container_width=True)
                                with att_col4:
                                    if st.session_state.user_role == "admin" and st.button("🗑️", key=f"del_ref_{att.id}", use_container_width=True):
                                        crud_attachments.delete_attachment(db, att.id)
                                        st.rerun()
                    except Exception as e:
                        st.error(f"Attachment error: {str(e)}")

                    # History View
                    if st.session_state.get(f"show_history_ref_{lead.id}", False):
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
                                         for field, old_val, new_val in changes:
                                             st.markdown(f"<div style='font-size: 0.85rem; color: #6B7280; margin-left: 20px;'>&bull; <b>{field}:</b> {old_val} &rarr; {new_val}</div>", unsafe_allow_html=True)
                                 st.divider()
                        else:
                            st.caption("No history recorded yet.")

            with cs_col:
                bg_color = {"Not Called": "#FF3B30", "Pending": "#FFCC00", "Called": "#34C759"}.get(cur_cs, "#f0f2f6")
                text_color = "white" if cur_cs != "Pending" else "#1c1c1c"
                
                # Use the new status pill class from common.py
                from frontend.common import get_status_pill_class
                pill_cls = get_status_pill_class(cur_cs)

                # Marker for robust CSS targeting holding the status pill coloring class
                st.markdown(f'<div id="fused-marker-ref-{lead.id}" class="status-marker {pill_cls}" style="display:none"></div>', unsafe_allow_html=True)
                
                # Dynamic CSS for Pill Style + Referral Card
                st.markdown(f"""
                    <style>
                    /* THE CARD: Target the row containing our marker */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) {{
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
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) div[data-testid="stExpander"] {{
                        background: transparent !important;
                        border: none !important;
                        flex-grow: 1 !important;
                    }}
                    
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) div[data-testid="stExpander"] summary {{
                        background: transparent !important;
                    }}

                    /* Remove default column padding/borders on the parent columns only */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) > div[data-testid*="olumn"] {{
                        padding: 0 !important;
                        background: transparent !important;
                        border: none !important;
                    }}
                    
                    /* Apply vertical flex layout only to the right column */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) > div[data-testid*="olumn"]:nth-child(2) {{
                        display: flex !important;
                        flex-direction: column !important;
                        justify-content: center !important;
                        height: 100% !important;
                    }}

                    /* Eliminate internal Streamlit gaps that push text out of bounds (Right column only) */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) > div[data-testid*="olumn"]:nth-child(2) > div[data-testid="stVerticalBlock"] {{
                        gap: 0 !important;
                        padding: 0 !important;
                        display: flex !important;
                        flex-direction: column !important;
                        align-items: flex-end !important;
                        justify-content: center !important;
                    }}
                    
                    /* Remove margins from Streamlit element containers in right column */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) > div[data-testid*="olumn"]:nth-child(2) > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] {{
                        margin-bottom: 0 !important;
                        min-height: 0 !important;
                    }}
                    
                    /* Header text styling matching blueprint */
                    div[data-testid="stHorizontalBlock"]:has(#fused-marker-ref-{lead.id}) div[data-testid="stExpander"] summary p {{
                        font-size: 18px !important;
                        font-weight: 600 !important;
                        color: #0b2a35 !important;
                    }}
                    </style>
                """, unsafe_allow_html=True)
                
                cs_key = f"inline_cs_ref_{lead.id}"
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
                    _ul(db, lead.id, LeadUpdate(
                        priority=selected_val,
                        call_status_updated_by=st.session_state.username,
                        call_status_updated_at=datetime.utcnow()
                    ), st.session_state.username, st.session_state.get('db_user_id'))
                    clear_leads_cache()
                    st.rerun()
    else:
        st.info("No referrals found")
    
    # --- PAGINATION UI CONTROLS ---
    render_pagination(total_leads, "refs")
    
    db.close()
