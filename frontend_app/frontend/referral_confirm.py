"""
Referral Confirm page: Handle authorized referrals
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
from frontend.common import prepare_lead_data_for_email, render_time, get_leads_cached, clear_leads_cache, show_add_comment_dialog, render_comment_stack, render_pagination


def display_referral_confirm(lead, db, highlight=False):
    """Helper function to display a single referral in the confirm page"""
    
    
    from app.crud.crud_leads import update_lead

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
            st.write(f"**Staff:** {lead.staff_name}")
            st.write(f"**Phone:** {lead.phone}")
            st.write(f"**Source:** {lead.source}")
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

        with col2:
            st.write(f"**Status:** {lead.last_contact_status}")
            st.success(f"**Referral Type:** {lead.referral_type or 'Regular'}")
            st.write(f"**City:** {lead.city or 'N/A'}")
            st.write(f"**Medicaid #:** {lead.medicaid_no or 'N/A'}")
            
            # Display chronological comment stack
            render_comment_stack(lead)

        st.divider()

        # Show current SOC status if already set
        if lead.care_status:
            soc_str = lead.soc_date.strftime('%m/%d/%Y') if lead.soc_date else 'Not Set'
            if lead.care_status == "Care Start":
                st.success(f"**Care Status: {lead.care_status} | SOC: {soc_str}**")
            else:
                st.warning(f"**Care Status: {lead.care_status}**")
        else:
            st.warning("**Care status not set yet**")

        # Sub-Action Buttons: Edit, History, Comment, Undo Auth
        st.write("**Manage Referral:**")
        sub_col1, sub_col2, sub_col3, sub_col4 = st.columns([0.7, 0.7, 1.3, 1.3])
        
        with sub_col1:
            if st.button("Edit", key=f"edit_btn_confirm_{lead.id}", use_container_width=True):
                # Prepare lead data for edit modal
                lead_dict = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
                st.session_state.modal_open = True
                st.session_state.modal_action = 'save_edit_modal'
                st.session_state.modal_lead_id = lead.id
                st.session_state.modal_lead_name = f"{lead.first_name} {lead.last_name}"
                st.session_state.modal_data = {'title': f"{lead.first_name} {lead.last_name}", 'lead_data': lead_dict}
                st.session_state['active_modal'] = {'modal_type': 'save_edit_modal', 'target_id': lead.id, 'title': f"{lead.first_name} {lead.last_name}", 'lead_data': lead_dict}
                st.rerun()

        with sub_col2:
            if st.button("History", key=f"history_btn_confirm_{lead.id}", use_container_width=True):
                st.session_state.modal_open = False
                st.session_state.modal_action = None
                st.session_state.pop('active_modal', None)
                key = f"show_history_conf_{lead.id}"
                st.session_state[key] = not st.session_state.get(key, False)
                st.rerun()

        with sub_col3:
            if st.button("💬 Comment", key=f"add_comment_btn_confirm_{lead.id}", use_container_width=True, help="Add a new update/note"):
                show_add_comment_dialog(db, lead.id, f"{lead.first_name} {lead.last_name}")
                
        with sub_col4:
            if st.button("Undo Auth", key=f"undo_auth_btn_confirm_{lead.id}", 
                         help="Remove authorization and move back to Referrals Sent", type="primary", use_container_width=True):
                st.session_state.modal_open = False
                st.session_state.modal_action = None
                st.session_state.pop('active_modal', None)
                
                update_data = LeadUpdate(authorization_received=False)
                if update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('db_user_id')):
                    clear_leads_cache()
                    st.toast(f"Auth undone for {lead.last_name}", icon="↩️")
                    st.rerun()

        st.divider()

        # Action Buttons: Care Start, Not Start
        st.write("**Select Care Status:**")
        col_start, col_not_start = st.columns(2)

        with col_start:
            if st.button("Care Start", key=f"care_start_btn_confirm_{lead.id}", type="primary", width="stretch", disabled=(lead.care_status == "Care Start")):
                # CRITICAL: Clear modal state
                st.session_state.modal_open = False
                st.session_state.modal_action = None
                st.session_state.pop('active_modal', None)
                
                # Auto-fetch today's date as SOC
                today = date.today()
                update_data = LeadUpdate(
                    care_status="Care Start",
                    soc_date=today
                )
                update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('db_user_id'))
                clear_leads_cache()
                msg = f"Success! Care Started for {lead.first_name} {lead.last_name}. SOC: {today.strftime('%m/%d/%Y')}"
                st.toast(msg, icon="✅")
                st.session_state['success_msg'] = msg
                st.rerun()

        with col_not_start:
            if st.button("Not Start", key=f"not_start_btn_confirm_{lead.id}", type="secondary", width="stretch", disabled=(lead.care_status == "Not Start")):
                # CRITICAL: Clear modal state
                st.session_state.modal_open = False
                st.session_state.modal_action = None
                st.session_state.pop('active_modal', None)
                
                update_data = LeadUpdate(
                    care_status="Not Start",
                    soc_date=None
                )
                update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('db_user_id'))
                clear_leads_cache()
                msg = f"Success! Care marked as 'Not Start' for {lead.first_name} {lead.last_name}."
                st.toast(msg, icon="⏳")
                st.session_state['success_msg'] = msg
                st.rerun()

        # History View - Show last 5 updates only
        if st.session_state.get(f"show_history_conf_{lead.id}", False):
            st.divider()
            st.markdown("<h4 style='font-weight: bold; color: #111827;'>Last 5 Updates</h4>", unsafe_allow_html=True)
            history_logs = crud_activity_logs.get_lead_history(db, lead.id)

            if history_logs:
                # Limit to last 5 entries
                for log in history_logs[:5]:
                    label = get_action_label(log.action_type)
                    time_ago = format_time_ago(log.timestamp, st.session_state.get('user_timezone'))

                    with st.container():
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.write(f"**{label}**")
                            if log.description:
                                st.caption(log.description[:100] + "..." if len(log.description) > 100 else log.description)
                        with col2:
                            timeframe = render_time(log.timestamp, style="ago")
                            st.markdown(timeframe, unsafe_allow_html=True)
                        st.divider()
            else:
                st.caption("No activity history available.")


def referral_confirm():
    """Referral Confirm page - Shows all clients with authorization received"""
    # Force module reload to pick up model changes (AttributeError Fix)
    import sys
    modules_to_reload = [k for k in sys.modules.keys() if 'crud_' in k or 'app.models' in k or 'backend.app.models' in k or 'services_stats' in k]
    for mod in list(modules_to_reload):
        if mod in sys.modules:
            del sys.modules[mod]
            
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

    st.markdown('<div class="main-header">Referral Confirm</div>', unsafe_allow_html=True)

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
        auth_received_filter=True
    )
    st.write(f"**Total Clients with Authorization: {total_authorized}**")
    
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
        if st.button("Search", key="search_confirm_btn_main", use_container_width=True):
            st.session_state.confirm_page = 0
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
    
    st.divider()
    
    # Filter buttons for Care Status
    st.write("**Filter by Care Status:**")
    
    # Care filter is now initialized in init_session_state() in common.py
    
    col_all, col_start, col_not_start = st.columns(3)
    
    with col_all:
        if st.button("All", key="filter_all_confirm", type="primary" if st.session_state.confirm_care_filter == "All" else "secondary", width="stretch"):
            st.session_state.confirm_care_filter = "All"
            st.session_state.confirm_page = 0
            st.rerun()
    
    with col_start:
        if st.button("Care Start", key="filter_care_start_confirm", type="primary" if st.session_state.confirm_care_filter == "Care Start" else "secondary", width="stretch"):
            st.session_state.confirm_care_filter = "Care Start"
            st.session_state.confirm_page = 0
            st.rerun()
    
    with col_not_start:
        if st.button("Not Start", key="filter_not_start_confirm", type="primary" if st.session_state.confirm_care_filter == "Not Start" else "secondary", width="stretch"):
            st.session_state.confirm_care_filter = "Not Start"
            st.session_state.confirm_page = 0
            st.rerun()
    
    st.divider()
    
    # --- DATA FETCHING & FILTERING (PERFORMANCE OPTIMIZED) ---
    
    # Track current page in session state
    if 'confirm_page' not in st.session_state:
        st.session_state.confirm_page = 0
    
    page_size = 20 # Detail heavy, so smaller page size
    skip = st.session_state.confirm_page * page_size
    
    # SQL-level search and count
    leads = search_leads(
        db,
        search_query=search_name if search_name else None,
        staff_filter=filter_staff if filter_staff else None,
        source_filter=filter_source if filter_source else None,
        status_filter=None, # Care status filtered below/via custom logic
        priority_filter=None,
        active_inactive_filter=None,
        owner_id=None,
        only_my_leads=False,
        include_deleted=False,
        exclude_clients=False, # We want active clients
        auth_received_filter=True, # SQL FILTERING
        only_clients=True,        # NEW: Filter at SQL level
        skip=st.session_state.get('conf_skip', 0),
        limit=st.session_state.get('conf_limit', 10)
    )
    
    # Post-filter (Now handled at SQL level)
    # leads = [l for l in leads if l.active_client == True]
    
    if st.session_state.confirm_care_filter == "Care Start":
        leads = [l for l in leads if l.care_status == "Care Start"]
    elif st.session_state.confirm_care_filter == "Not Start":
        leads = [l for l in leads if l.care_status == "Not Start"]
        
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
        auth_received_filter=True
    )
    
    # UI Metadata
    num_pages = (total_leads // page_size) + (1 if total_leads % page_size > 0 else 0)
    current_page_display = st.session_state.confirm_page + 1 if total_leads > 0 else 0

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
    st.session_state.conf_skip, st.session_state.conf_limit = render_pagination(total_leads, "conf")
    
    db.close()
