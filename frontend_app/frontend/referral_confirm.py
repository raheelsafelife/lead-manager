"""
# Authorizations Received page: Handle authorized referrals and care status
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
from frontend.common import prepare_lead_data_for_email, get_call_status_tag, render_time, render_confirmation_modal, open_modal, close_modal, show_add_comment_dialog, render_comment_stack, clear_leads_cache, get_pagination_params, render_pagination


def display_referral_confirm(lead, db, highlight=False):
    """Helper function to display a single referral in the confirm page"""
    from app.crud.crud_leads import update_lead
    from frontend.common import get_tag_color_dot, render_tag_color_picker

    # Show care status indicator in the expander title
    # Layout: Expander
    from frontend.common import get_tag_color_dot
    tag_dot = get_tag_color_dot(lead.tag_color)
    expander_title = f"{tag_dot} ID: {lead.id} | {lead.first_name} {lead.last_name} - {lead.staff_name}"
    
    with st.expander(expander_title, expanded=highlight):
        # Hidden marker to anchor our CSS styles firmly to THIS specific row
        st.markdown(f'<div id="auth-marker-{lead.id}" style="display:none"></div>', unsafe_allow_html=True)
        
        # Custom CSS for Referral Card header specifically for this page
        st.markdown(f"""
            <style>
            /* THE CARD: Target the expander container */
            div[data-testid="stExpander"]:has(#auth-marker-{lead.id}) {{
                background: #EAF7FF !important;
                border: 2px solid #35A7C7 !important;
                border-radius: 10px !important;
                margin: 8px 0 !important;
            }}
            
            /* Header text styling matching blueprint */
            div[data-testid="stExpander"]:has(#auth-marker-{lead.id}) summary p {{
                font-size: 18px !important;
                font-weight: 600 !important;
                color: #0b2a35 !important;
            }}
            
            /* Make the body transparent to blend with the card background */
            div[data-testid="stExpander"]:has(#auth-marker-{lead.id}) div[data-testid="stExpanderDetails"] {{
                background: transparent !important;
            }}
            </style>
        """, unsafe_allow_html=True)

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
            st.info("**AUTHORIZATION CONFIRMED - This referral has received authorization and is ready for care coordination**")
            st.markdown("---")
            st.markdown("## **AUTHORIZATION RECEIVED**")
            st.markdown("---")

            if auth_received_time:
                st.markdown(f"""
                <div style="padding: 1rem; border-radius: 0.5rem; background-color: #d1fae5; border: 1px solid #10b981; color: #065f46; font-weight: bold; margin-bottom: 1rem;">
                    ✅ Authorization Received: {render_time(auth_received_time)}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.success("**Authorization Received**")
            st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ID:** {lead.id}")
            st.write(f"**Name:** {lead.first_name} {lead.last_name}")
            st.write(f"**Staff:** {lead.staff_name}")
            st.write(f"**Employee ID:** {lead.custom_user_id or 'N/A'}")
            st.write(f"**Phone:** {lead.phone or 'N/A'}")
            st.write(f"**Email:** {lead.email or 'N/A'}")
            dob_str = lead.dob.strftime('%m/%d/%Y') if lead.dob else 'N/A'
            st.write(f"**DOB:** {dob_str}")
            st.write(f"**Age:** {lead.age if lead.age is not None else 'N/A'}")
            st.write(f"**SSN:** {lead.ssn or 'N/A'}")
            st.write(f"**Medicaid #:** {lead.medicaid_no or 'N/A'}")
            st.write(f"**Source:** {lead.source}")
            # Source sub-type
            if lead.source == "Event" and lead.event_name:
                st.write(f"**Event:** {lead.event_name}")
            elif lead.source == "Word of Mouth" and lead.word_of_mouth_type:
                st.write(f"**Word of Mouth Type:** {lead.word_of_mouth_type}")
            elif lead.source == "Other" and lead.other_source_type:
                st.write(f"**Other Source:** {lead.other_source_type}")
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
                        st.warning("Payor details temporarily unavailable due to system cache.")

            if lead.ccu:
                with st.container():
                    st.info(f"**CCU Information:**")
                    try:
                        st.write(f"**Name:** {lead.ccu.name}")
                        c_street = getattr(lead.ccu, 'street', None)
                        if c_street: st.write(f"**Street:** {c_street}")
                        if lead.ccu.phone: st.write(f"**Phone:** {lead.ccu.phone}")
                        if lead.ccu.email: st.write(f"**Email:** {lead.ccu.email}")
                    except AttributeError:
                        st.warning("CCU details temporarily unavailable due to system cache.")

        with col2:
            st.write(f"**Status:** {lead.last_contact_status}")
            st.success(f"**Referral Type:** {lead.referral_type or 'Regular'}")
            st.write(f"**City:** {lead.city or 'N/A'}")
            render_comment_stack(lead)
            st.divider()
            render_tag_color_picker(lead.id, lead.tag_color, db, page_type="confirmations")

        st.divider()
        if lead.care_status:
            soc_str = lead.soc_date.strftime('%m/%d/%Y') if (hasattr(lead, 'soc_date') and lead.soc_date) else 'Not Set'
            if lead.care_status == "Care Start":
                st.success(f"**Care Status: {lead.care_status} | SOC: {soc_str}**")
            else:
                st.warning(f"**Care Status: {lead.care_status}**")
        else:
            st.warning("**Care status not set yet**")

        # QUICK ACTIONS ROW
        st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)
        
        # Proportions: Mark Authorization is wider (ratio 1:1:2:1:1)
        sub_col1, sub_col2, sub_col3, sub_col4, sub_col5 = st.columns([1, 1, 2, 1, 1])
        
        with sub_col1:
            if st.button("Edit", key=f"edit_btn_confirm_{lead.id}", use_container_width=True):
                lead_dict = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
                open_modal('save_edit_modal', lead.id, title=f"{lead.first_name} {lead.last_name}", lead_data=lead_dict)
        
        with sub_col2:
            if st.button("Delete", key=f"del_btn_confirm_{lead.id}", use_container_width=True):
                render_confirmation_modal(modal_type='soft_delete', target_id=lead.id, title='Delete Referral?', message=f"Delete <b>{lead.first_name} {lead.last_name}</b>?", icon='🗑️', type='warning', confirm_label='DELETE')
        
        with sub_col3:
            if st.button("Unmark Authorization", key=f"unmark_auth_btn_confirm_{lead.id}", use_container_width=True, type="primary"):
                render_confirmation_modal(modal_type='undo_auth', target_id=lead.id, title='Undo Authorization?', message=f"Undo Authorization for <b>{lead.first_name} {lead.last_name}</b>?", icon='↩️', type='info', confirm_label='UNDO')
        
        with sub_col4:
            if st.button("💬 Comment", key=f"add_comment_btn_{lead.id}", use_container_width=True):
                from frontend.common import clear_modal_state
                clear_modal_state()
                show_add_comment_dialog(lead.id, f"{lead.first_name} {lead.last_name}")

        with sub_col5:
            if st.button("History", key=f"history_btn_{lead.id}", use_container_width=True):
                from frontend.common import clear_modal_state
                clear_modal_state()
                key = f"show_history_conf_{lead.id}"
                st.session_state[key] = not st.session_state.get(key, False)
                st.rerun()

        st.divider()
        st.write("**Manage Status:**")
        current_group = "Active"
        if lead.care_status in ["Hold", "Terminated"]:
            current_group = lead.care_status
        g_col1, g_col2, g_col3 = st.columns([1, 1, 1])
        with g_col1:
            if st.button("Active", key=f"active_grp_{lead.id}", type="primary" if current_group == "Active" else "secondary", use_container_width=True):
                if current_group != "Active":
                    update_lead(db, lead.id, LeadUpdate(care_status=None), st.session_state.username, st.session_state.get('db_user_id'))
                    st.rerun()
        with g_col2:
            if st.button("Hold", key=f"hold_grp_{lead.id}", type="primary" if current_group == "Hold" else "secondary", use_container_width=True):
                update_lead(db, lead.id, LeadUpdate(care_status="Hold", soc_date=None), st.session_state.username, st.session_state.get('db_user_id'))
                st.rerun()
        with g_col3:
            if st.button("Terminated", key=f"term_grp_{lead.id}", type="primary" if current_group == "Terminated" else "secondary", use_container_width=True):
                update_lead(db, lead.id, LeadUpdate(care_status="Terminated", soc_date=None), st.session_state.username, st.session_state.get('db_user_id'))
                st.rerun()
        
        if current_group == "Active":
            st.write("**Care Sub-Status:**")
            s_col1, s_col2, s_col3 = st.columns([1, 1, 1])
            with s_col1:
                if st.button("Care Start", key=f"care_start_{lead.id}", type="primary" if lead.care_status == "Care Start" else "secondary", use_container_width=True):
                    from datetime import date
                    update_lead(db, lead.id, LeadUpdate(care_status="Care Start", soc_date=date.today()), st.session_state.username, st.session_state.get('db_user_id'))
                    st.rerun()
            with s_col2:
                if st.button("Care Not Start", key=f"not_start_{lead.id}", type="primary" if lead.care_status == "Not Start" else "secondary", use_container_width=True):
                    update_lead(db, lead.id, LeadUpdate(care_status="Not Start", soc_date=None), st.session_state.username, st.session_state.get('db_user_id'))
                    st.rerun()

        st.divider()
        st.markdown("### 📎 Attachments")
        try:
            from app.crud import crud_attachments
            with st.expander("➕ Upload New Attachment", expanded=False):
                # GHOST UPLOAD FIX: Use a versioned key to force a reset after successful upload
                up_key_ver = st.session_state.get(f"up_ver_auth_{lead.id}", 0)
                uploaded_file = st.file_uploader("Choose file", type=['pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'csv', 'txt'], key=f"upload_{lead.id}_{up_key_ver}")
                if uploaded_file and st.button("Upload", key=f"btn_upload_{lead.id}_{up_key_ver}", type="primary"):
                    from frontend.common import clear_modal_state
                    # GHOST POPUP KILLER: Proactively clear any stale modal state before rerunning
                    clear_modal_state()
                    
                    upload_dir = Path(__file__).parent.parent.parent / "backend" / "uploads"
                    upload_dir.mkdir(exist_ok=True)
                    file_path = upload_dir / f"{lead.id}_{uploaded_file.name}"
                    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                    crud_attachments.create_attachment(db, lead_id=lead.id, filename=uploaded_file.name, file_path=str(file_path), file_size=uploaded_file.size, uploaded_by=st.session_state.username)
                    
                    # UPLOADER RESET: Increment version to force a new widget
                    st.session_state[f"up_ver_auth_{lead.id}"] = up_key_ver + 1
                    st.rerun()
            
            attachments = crud_attachments.get_attachments_by_lead(db, lead.id)
            if attachments:
                for att in attachments:
                    a_col1, a_col2, a_col3, a_col4 = st.columns([4, 1, 1, 1])
                    with a_col1: st.write(f"📄 **{att.filename}** - {att.uploaded_by}")
                    with a_col2:
                        if st.button("👁️", key=f"view_{att.id}", use_container_width=True, help="Preview Document"):
                            open_modal('file_preview', att.id, title=att.filename, lead_data={'file_path': att.file_path, 'filename': att.filename})
                    with a_col3: 
                         if os.path.exists(att.file_path):
                             with open(att.file_path, "rb") as f:
                                 st.download_button("⬇️", f, file_name=att.filename, key=f"dl_{att.id}", use_container_width=True)
                    with a_col4:
                         if st.session_state.user_role == "admin" and st.button("🗑️", key=f"del_{att.id}", use_container_width=True):
                             crud_attachments.delete_attachment(db, att.id)
                             st.rerun()
        except Exception as e: st.error(f"Attachment error: {e}")

        if st.session_state.get(f"show_history_conf_{lead.id}", False):
            history_logs = crud_activity_logs.get_lead_history(db, lead.id)
            if history_logs:
                for log in history_logs[:5]:
                    st.write(f"**{get_action_label(log.action_type)}** - {render_time(log.timestamp, style='ago')}")
                    st.divider()

def referral_confirm():
    """Authorizations Received page - Shows all clients with authorization received"""
    from app.crud.crud_leads import search_leads, count_search_leads
    # Display persistent status messages if they exist
    if 'success_msg' in st.session_state:
        msg = st.session_state.pop('success_msg')
        st.toast(msg, icon="✅")
        st.success(f"**{msg}**")
    if 'error_msg' in st.session_state:
        msg = st.session_state.pop('error_msg')
        st.toast(msg, icon="❌")
        st.error(f"**{msg}**")

    st.markdown('<div class="main-header">Authorizations Received</div>', unsafe_allow_html=True)

    db = SessionLocal()
    
    # Use native SQL filtering for both count and the main list
    auth_filter = True

    # Check if we should focus on a specific referral
    specific_lead_id = st.session_state.get('referral_confirm_lead_id')
    if specific_lead_id:
        # Find the specific lead using SQL instead of memory
        from app.crud.crud_leads import get_lead
        specific_lead = get_lead(db, specific_lead_id)
        if specific_lead and not specific_lead.authorization_received:
            specific_lead = None

        if specific_lead:
            # Display the specific referral (always shown regardless of page)
            display_referral_confirm(specific_lead, db, highlight=True)
        else:
            # Clear the invalid lead ID if referral not found
            if 'referral_confirm_lead_id' in st.session_state:
                st.session_state.pop('referral_confirm_lead_id', None)

    # Total count for the header
    total_authorized = count_search_leads(
        db,
        exclude_clients=False,
        auth_received_filter=True,
        only_clients=True,
        care_status_filter=st.session_state.confirm_status_filter,
        care_sub_status_filter=st.session_state.confirm_care_filter if st.session_state.confirm_status_filter == "Active" else "All"
    )
    st.write(f"**Total Authorized ({st.session_state.confirm_status_filter}): {total_authorized}**")
    
    st.divider()

    # Search and filter
    col1, col2, col3, col_id, col4 = st.columns([1.5, 1.5, 1.5, 1.5, 1])
    with col1:
        search_name = st.text_input("Search by name")
    with col2:
        filter_staff = st.text_input("Filter by staff")
    with col3:
        filter_source = st.text_input("Filter by source")
    with col_id:
        search_id = st.text_input("Search by ID", key="search_id_input_conf")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Search", key="search_confirm_btn_main", use_container_width=True):
            st.session_state.conf_page = 0
            st.rerun()

    # Sorting
    sort_col1, sort_col2 = st.columns([1.4, 4])
    with sort_col1:
        sort_options = ["Newest Added", "Recently Updated"]
        selected_sort = st.selectbox(
            "Sort By", 
            sort_options, 
            index=sort_options.index(st.session_state.confirmations_sort_by) if st.session_state.confirmations_sort_by in sort_options else 0,
            key="confirmations_sort_by_select"
        )
        if selected_sort != st.session_state.confirmations_sort_by:
            st.session_state.confirmations_sort_by = selected_sort
            st.rerun()

    # Payor Filter
    st.write("**Filter by Payor:**")
    agencies = crud_agencies.get_all_agencies(db)
    
    # Payor filter is now initialized in init_session_state() in common.py
    
    if agencies:
        agency_names = ["All"] + [a.name for a in agencies]
        selected_payor = st.selectbox("Select Payor", agency_names, index=agency_names.index(st.session_state.confirm_payor_filter) if st.session_state.confirm_payor_filter in agency_names else 0, key="confirm_payor_filter_select")
        
        if selected_payor != st.session_state.confirm_payor_filter:
            st.session_state.confirm_payor_filter = selected_payor
            st.rerun()

    # CCU Filter
    st.write("**Filter by CCU:**")
    ccus = crud_ccus.get_all_ccus(db)
    
    # CCU filter is now initialized in init_session_state() in common.py
    
    if ccus:
        ccu_names = ["All"] + [c.name for c in ccus]
        selected_ccu = st.selectbox("Select CCU", ccu_names, index=ccu_names.index(st.session_state.confirm_ccu_filter) if st.session_state.confirm_ccu_filter in ccu_names else 0, key="confirm_ccu_filter_select")
        
        if selected_ccu != st.session_state.confirm_ccu_filter:
            st.session_state.confirm_ccu_filter = selected_ccu
            st.rerun()

    st.write("**Filter by Status:**")
    
    # Tag Color Filter Dropdown
    ct_colors = ["All", "Blue", "Purple"]
    ct_icons = {"All": "All", "Blue": "🔵 Blue", "Purple": "🟣 Purple"}
    
    selected_ct = st.selectbox(
        "Filter by Color Tag",
        options=ct_colors,
        format_func=lambda x: ct_icons.get(x, x),
        index=ct_colors.index(st.session_state.confirm_tag_color_filter) if st.session_state.confirm_tag_color_filter in ct_colors else 0,
        key="referral_confirm_tag_color_filter_select"
    )
    
    if selected_ct != st.session_state.confirm_tag_color_filter:
        st.session_state.confirm_tag_color_filter = selected_ct
        st.session_state.conf_page = 0
        st.rerun()

    st.divider()
    
    col_active, col_hold, col_term, col_spacer = st.columns([1, 1, 1, 3])
    
    with col_active:
        if st.button("Active", key="filter_active_confirm", type="primary" if st.session_state.confirm_status_filter == "Active" else "secondary", use_container_width=True):
            st.session_state.confirm_status_filter = "Active"
            st.session_state.conf_page = 0
            st.rerun()
    
    with col_hold:
        if st.button("Hold", key="filter_hold_confirm", type="primary" if st.session_state.confirm_status_filter == "Hold" else "secondary", use_container_width=True):
            st.session_state.confirm_status_filter = "Hold"
            st.session_state.conf_page = 0
            st.rerun()
    
    with col_term:
        if st.button("Terminated", key="filter_terminated_confirm", type="primary" if st.session_state.confirm_status_filter == "Terminated" else "secondary", use_container_width=True):
            st.session_state.confirm_status_filter = "Terminated"
            st.session_state.conf_page = 0
            st.rerun()
            
    # Sub-filter for Active
    if st.session_state.confirm_status_filter == "Active":
        st.write("Filter by Care Status:")
        col_all, col_start, col_not_start, col_spacer_sub = st.columns([1, 1, 1, 3])
        
        with col_all:
            if st.button("All", key="filter_active_all", type="primary" if st.session_state.confirm_care_filter == "All" else "secondary", use_container_width=True):
                st.session_state.confirm_care_filter = "All"
                st.session_state.conf_page = 0
                st.rerun()
                
        with col_start:
            if st.button("Care Start", key="filter_active_start", type="primary" if st.session_state.confirm_care_filter == "Care Start" else "secondary", use_container_width=True):
                st.session_state.confirm_care_filter = "Care Start"
                st.session_state.conf_page = 0
                st.rerun()
                
        with col_not_start:
            if st.button("Not Start", key="filter_active_not_start", type="primary" if st.session_state.confirm_care_filter == "Not Start" else "secondary", use_container_width=True):
                st.session_state.confirm_care_filter = "Not Start"
                st.session_state.conf_page = 0
                st.rerun()
    
    st.divider()
    
    # --- DATA FETCHING & FILTERING (PERFORMANCE OPTIMIZED) ---
    skip, limit, page_index, rows_per_page = get_pagination_params("conf", default_limit=20)
    
    # SQL-level search and count
    lead_id_filter = None
    if search_id and search_id.strip().isdigit():
        lead_id_filter = int(search_id.strip())

    auth_val = True # All leads on this page should have authorization received
    owner_id = None # Not filtering by owner on this page
    only_my_referrals = False # Not filtering by owner on this page

    leads = search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=None, # Care status filtered below/via custom logic
        priority_filter=None, # Removed call logic from this page
        active_inactive_filter=None,
        owner_id=None,
        only_my_leads=False,
        include_deleted=False,
        exclude_clients=False, # We want active clients
        auth_received_filter=auth_val, # SQL FILTERING
        only_clients=True,        # NEW: Filter at SQL level
        skip=skip,
        limit=limit,
        lead_id_filter=lead_id_filter,
        lead_type_filter=st.session_state.confirm_lead_type_filter,
        care_status_filter=st.session_state.confirm_status_filter,
        care_sub_status_filter=st.session_state.confirm_care_filter if st.session_state.confirm_status_filter == "Active" else "All",
        tag_color_filter=st.session_state.confirm_tag_color_filter,
        sort_by=st.session_state.confirmations_sort_by
    )
    
    # Post-filter (Now handled at SQL level via search_leads)
    pass
        
    if st.session_state.confirm_payor_filter != "All":
        leads = [l for l in leads if l.agency and l.agency.name == st.session_state.confirm_payor_filter]
    
    if st.session_state.confirm_ccu_filter != "All":
        leads = [l for l in leads if l.ccu and l.ccu.name == st.session_state.confirm_ccu_filter]

    total_leads = count_search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        exclude_clients=False,
        only_clients=True, # NEW: Filter at SQL level
        auth_received_filter=True,
        care_status_filter=st.session_state.confirm_status_filter,
        care_sub_status_filter=st.session_state.confirm_care_filter if st.session_state.confirm_status_filter == "Active" else "All",
        lead_id_filter=lead_id_filter,
        tag_color_filter=st.session_state.confirm_tag_color_filter,
        lead_type_filter=st.session_state.confirm_lead_type_filter
    )
    
    # UI Metadata
    num_pages = max(1, (total_leads // rows_per_page) + (1 if total_leads % rows_per_page > 0 else 0))
    current_page_display = page_index + 1 if total_leads > 0 else 0

    # Show filtered count
    st.write(f"**Showing {len(leads)} clients of {total_leads} total**")
    
    if not leads:
        st.info("**No clients match the selected filter.**")
        st.caption("Go to Referrals and click 'Authorization Received' on a referral to mark it as authorized.")
        db.close()
        return
    
    # Display each authorized referral
    for lead in leads:
        # Avoid duplicating focused lead if it happens to be on this page
        if 'specific_lead_id' in locals() and lead.id == specific_lead_id:
            continue
        display_referral_confirm(lead, db)
    
    # --- PAGINATION UI CONTROLS ---
    render_pagination(total_leads, "conf")
    
    db.close()
