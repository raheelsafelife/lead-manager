"""
Add Lead page: Add new lead form
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
from app.crud import crud_users, crud_leads, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_events, crud_agency_suboptions
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email, get_priority_tag, clear_leads_cache


def add_lead():
    """Add new lead"""
    st.markdown('<div class="main-header"> Add New Lead</div>', unsafe_allow_html=True)
    
    # Display persistent status messages if they exist
    if 'success_msg' in st.session_state:
        msg = st.session_state.pop('success_msg')
        st.toast(msg, icon="✅")
        st.success(f"**{msg}**")
    if 'error_msg' in st.session_state:
        msg = st.session_state.pop('error_msg')
        st.toast(msg, icon="❌")
        st.error(f"**{msg}**")
    
    db = SessionLocal()
    
    # Main Form Container
    st.markdown('<div style="padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: white;">', unsafe_allow_html=True)
    
    # Initialization for automation
    if 'age_input' not in st.session_state:
        st.session_state.age_input = 0

    def on_dob_change():
        if st.session_state.dob_input:
            today = date.today()
            dob = st.session_state.dob_input
            calc_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            st.session_state.age_input = calc_age

    # Source Selection
    st.markdown("<h4 style='font-weight: bold; color: #111827;'>Lead Source</h4>", unsafe_allow_html=True)
    st.markdown('Source <span class="required-star">*</span>', unsafe_allow_html=True)
    source = st.selectbox("Source", [
        "Home Health Notify",
        "Web",
        "Direct Through CCU",
        "Event",
        "Word of Mouth",
        "Transfer",
        "Other"
    ], label_visibility="collapsed", key="lead_source_select")
    
    # Conditional fields based on source
    event_name = None
    word_of_mouth_type = None
    other_source_type = None
    agency_id = None
    agency_suboption_id = None
    ccu_id = None
    soc_date = None
    
    if source == "Transfer":
        st.markdown('SOC Date (Start of Care) <span class="required-star">*</span>', unsafe_allow_html=True)
        soc_date = st.date_input("SOC Date", value=date.today(), key="transfer_soc_date", label_visibility="collapsed", format="MM/DD/YYYY")
    
    elif source == "Event":
        events = crud_events.get_all_events(db)
        event_names = [e.event_name for e in events]
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Select Event</h4>", unsafe_allow_html=True)
        
        if not event_names:
            st.warning(" No events available.")
            if st.session_state.user_role == "admin":
                st.info("Add events using User Management -> Events")
            selected_event_name = None
        else:
            event_list = ["None", "Other (Add New)"] + event_names
            selected_event_name = st.selectbox("**Select Event**", event_list, key="event_name_select")
            if selected_event_name == "Other (Add New)":
                if st.session_state.user_role == "admin":
                    st.info("Click the button below to add a new event")
                    if st.button(" Add New Event", key="add_new_event_btn", type="primary"):
                        st.session_state['show_event_form'] = True
                        st.rerun()
                else:
                    st.warning(" Only admins can add new events.")
                    selected_event_name = "None"
            elif selected_event_name != "None":
                event_name = selected_event_name

        if st.session_state.get('show_event_form', False) and st.session_state.user_role == "admin":
            with st.container(border=True):
                st.write("**Add New Event:**")
                new_event_val = st.text_input("**Event Name**", placeholder="e.g. Health Fair 2026...", key="new_event_val_input")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button(" Add Event", width="stretch", type="primary", key="submit_new_event_btn"):
                        if new_event_val:
                            try:
                                existing = crud_events.get_event_by_name(db, new_event_val)
                                if existing: st.error(f" '{new_event_val}' already exists")
                                else:
                                    st.session_state['success_msg'] = f"Success! Event '{new_event_val}' added successfully!"
                                    st.session_state['show_event_form'] = False
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error adding Event: {str(e)}")
                with col_btn2:
                    if st.button(" Cancel", width="stretch", key="cancel_new_event_btn"):
                        st.session_state['show_event_form'] = False
                        st.rerun()
        st.divider()
    
    elif source == "Direct Through CCU":
        agencies = crud_agencies.get_all_agencies(db)
        agency_names = [a.name for a in agencies]
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Select Payor</h4>", unsafe_allow_html=True)
        
        if not agency_names:
            st.warning(" No payors available.")
            selected_agency_name = None
        else:
            agency_list = ["None", "Other (Add New)"] + agency_names
            selected_agency_name = st.selectbox("**Select Payor**", agency_list, key="agency_name_select")
            if selected_agency_name == "Other (Add New)":
                if st.session_state.user_role == "admin":
                    st.info("Click the button below to add a new payor")
                    if st.button(" Add New Payor", key="add_new_agency_btn", type="primary"):
                        st.session_state['show_agency_form'] = True
                        st.rerun()
                else:
                    st.warning(" Only admins can add new payors.")
                    selected_agency_name = "None"
            elif selected_agency_name != "None":
                for agency in agencies:
                    if agency.name == selected_agency_name:
                        agency_id = agency.id
                        break

        if st.session_state.get('show_agency_form', False) and st.session_state.user_role == "admin":
            with st.container(border=True):
                st.write("**Add New Payor:**")
                new_agency_name = st.text_input("**Payor Name**", placeholder="e.g. IDoA, MCO, DCFS...", key="new_agency_name_input")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button(" Add Payor", width="stretch", type="primary", key="submit_new_agency_btn"):
                        if new_agency_name:
                            try:
                                existing = crud_agencies.get_agency_by_name(db, new_agency_name)
                                if existing: st.error(f" '{new_agency_name}' already exists")
                                else:
                                    st.session_state['success_msg'] = f"Success! Payor '{new_agency_name}' added successfully!"
                                    st.session_state['show_agency_form'] = False
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error adding Payor: {str(e)}")
                with col_btn2:
                    if st.button(" Cancel", width="stretch", key="cancel_new_agency_btn"):
                        st.session_state['show_agency_form'] = False
                        st.rerun()

        if agency_id:
            suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=agency_id)
            if suboptions:
                st.write("**Select Suboption:**")
                suboption_names = [s.name for s in suboptions]
                suboption_list = ["None"] + suboption_names
                selected_suboption_name = st.selectbox("**Select suboption**", suboption_list, key="agency_suboption_select", label_visibility="collapsed")
                if selected_suboption_name != "None":
                    for suboption in suboptions:
                        if suboption.name == selected_suboption_name:
                            agency_suboption_id = suboption.id
                            break
        st.divider()
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Select CCU</h4>", unsafe_allow_html=True)
        ccus = crud_ccus.get_all_ccus(db)
        ccu_names = [c.name for c in ccus]
        if not ccu_names:
            st.info(" No CCUs available.")
            if st.button(" Add CCU", key="add_ccu_btn"):
                st.session_state['show_ccu_form'] = True
                st.rerun()
        else:
            ccu_list = ["None", "Other (Add New)"] + ccu_names
            selected_ccu_name = st.selectbox("**Select CCU**", ccu_list, key="ccu_name_select", label_visibility="collapsed")
            if selected_ccu_name == "Other (Add New)":
                if st.button(" Add New CCU", key="add_new_ccu_btn_manual"):
                    st.session_state['show_ccu_form'] = True
                    st.rerun()
            elif selected_ccu_name != "None":
                for ccu in ccus:
                    if ccu.name == selected_ccu_name:
                        ccu_id = ccu.id
                        break
        
        if st.session_state.get('show_ccu_form', False):
            with st.container(border=True):
                st.write("**Add New CCU:**")
                nc_name = st.text_input("**CCU Name** *", placeholder="e.g. CCU North...", key="nc_name")
                nc_street = st.text_input("**Street**", key="nc_street")
                nc_city = st.text_input("**City**", key="nc_city")
                nc_state = st.text_input("**State**", value="IL", max_chars=2, key="nc_state")
                nc_zip = st.text_input("**Zip Code**", key="nc_zip")
                nc_phone = st.text_input("**Phone**", key="nc_phone")
                nc_fax = st.text_input("**Fax**", key="nc_fax")
                nc_email = st.text_input("**Email**", key="nc_email")
                nc_coord = st.text_input("**Care Coordinator Name**", key="nc_coord")
                cb1, cb2 = st.columns(2)
                with cb1:
                    if st.button(" Add CCU", type="primary", key="save_new_ccu"):
                        if nc_name:
                            try:
                                crud_ccus.create_ccu(db, nc_name, st.session_state.username, st.session_state.get('db_user_id'),
                                    street=nc_street, city=nc_city, state=nc_state, zip_code=nc_zip, phone=nc_phone,
                                    fax=nc_fax, email=nc_email, care_coordinator_name=nc_coord)
                                st.session_state['success_msg'] = f"Success! CCU '{nc_name}' added!"
                                st.session_state['show_ccu_form'] = False
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                with cb2:
                    if st.button(" Cancel", key="cancel_ccu"):
                        st.session_state['show_ccu_form'] = False
                        st.rerun()

    elif source == "Word of Mouth":
        st.markdown('**Word of Mouth Type** <span class="required-star">*</span>', unsafe_allow_html=True)
        word_of_mouth_type = st.selectbox("Word of Mouth Type", ["Caregiver", "Community", "Client"], key="wom_type_input", label_visibility="collapsed")
    elif source == "Other":
        st.markdown('**Specify Source Type** <span class="required-star">*</span>', unsafe_allow_html=True)
        other_source_type = st.text_input("Specify Source Type", value="", key="other_type_input", label_visibility="collapsed")
    
    st.divider()

    # Priority Selection
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Priority</h4>", unsafe_allow_html=True)
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=1, key="priority_select")
    with col_p2:
        st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
        st.markdown(get_priority_tag(priority), unsafe_allow_html=True)

    st.divider()

    # Fetch approved users for admin selection
    approved_users = crud_users.get_approved_users(db)
    user_options = [u.username for u in approved_users]
    user_map = {u.username: u for u in approved_users}

    # Lead Information Section
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Lead Details</h4>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        current_owner_id = None
        auto_user_id = ""

        if st.session_state.user_role == "admin":
            st.markdown('Staff Name <span class="required-star">*</span>', unsafe_allow_html=True)
            # Staff Name Toggle/Dropdown
            staff_name = st.selectbox("Staff Name", options=["Select User"] + user_options, key="staff_name_select", label_visibility="collapsed")
            
            if staff_name != "Select User":
                sel_user = user_map.get(staff_name)
                if sel_user:
                    # REACTIVE: If staff selection changed, update the calculated auto_user_id
                    auto_user_id = sel_user.user_id or ""
                    current_owner_id = sel_user.id
            else:
                staff_name = ""
        else:
            staff_name = st.session_state.username
            current_owner_id = st.session_state.get('db_user_id')
            # For non-admin, try to fetch their own user_id if not in session
            curr_user_obj = crud_users.get_user_by_username(db, staff_name)
            if curr_user_obj:
                auto_user_id = curr_user_obj.user_id or ""
            
            st.info(f" Lead will be created by : **{staff_name}**")
        
        # REACTIVE: If selection has changed, force update the User ID widget state
        if st.session_state.get('last_staff_selection') != staff_name:
             st.session_state.user_id_input = auto_user_id
             st.session_state.last_staff_selection = staff_name

        st.markdown('User ID <span class="required-star">*</span>', unsafe_allow_html=True)
        custom_user_id = st.text_input("User ID", key="user_id_input", label_visibility="collapsed")
        
        st.markdown('First Name <span class="required-star">*</span>', unsafe_allow_html=True)
        first_name = st.text_input("First Name", key="first_name_input", label_visibility="collapsed")
        
        st.markdown('Last Name <span class="required-star">*</span>', unsafe_allow_html=True)
        last_name = st.text_input("Last Name", key="last_name_input", label_visibility="collapsed")
        
        dob = st.date_input("**Date of Birth**", value=None, min_value=date(1900, 1, 1), max_value=date.today(), key="dob_input", on_change=on_dob_change, format="MM/DD/YYYY")
        age = st.number_input("**Age / Year**", min_value=0, max_value=3000, key="age_input")
        
        email = st.text_input("**Email**", key="email_input")
        
        st.markdown('Phone <span class="required-star">*</span>', unsafe_allow_html=True)
        phone = st.text_input("Phone", key="phone_input", label_visibility="collapsed")
        ssn = st.text_input("**SSN**", key="ssn_input")
        medicaid_no = st.text_input("**Medicaid Number**", key="medicaid_input")
    
    with col2:
        st.markdown('Contact Status <span class="required-star">*</span>', unsafe_allow_html=True)
        last_contact_status = st.selectbox("Contact Status", ["Intro Call", "Follow Up", "No Response", "Inactive"], key="status_select", label_visibility="collapsed")
                                            
        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
        street = st.text_input("**Street**", key="street_input")
        city = st.text_input("**City**", key="city_input")
        state = st.text_input("**State**", value="IL", max_chars=2, key="state_input")
        zip_code = st.text_input("**Zip Code**", key="zip_input")
        
        e_contact_name = st.text_input("**Emergency Contact Name**", key="ec_name_input")
        e_contact_relation = st.text_input("**Relation**", key="ec_rel_input")
        e_contact_phone = st.text_input("**Emergency Contact Phone**", key="ec_phone_input")
        
        comments = st.text_area("**Comments**", height=150, key="comments_input")
    
    st.divider()
    st.markdown('<small>Fields marked with <span style="color:var(--required-star-pink)">*</span> are required</small>', unsafe_allow_html=True)
    
    save_lead = st.button("Save Lead", width="stretch", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if save_lead:
            # Validation
            required_fields = [staff_name, first_name, last_name, source, phone, custom_user_id]
            if source == "Event" and not event_name:
                st.toast("Event Required - Please select an Event", icon="❌")
                st.error("**Event Required - Please select an Event**")
                db.close()
                return
            elif source == "Direct Through CCU" and not agency_id:
                st.toast("Payor Required - Please select a Payor", icon="❌")
                st.error("**Payor Required - Please select a Payor**")
                db.close()
                return
            elif source == "Other" and not other_source_type:
                st.toast("Source Type Required - Please specify Source Type", icon="❌")
                st.error("**Source Type Required - Please specify Source Type**")
                db.close()
                return
            
            if not all(required_fields):
                missing = []
                if not staff_name: missing.append("Staff Name")
                if not first_name: missing.append("First Name")
                if not last_name: missing.append("Last Name")
                if not source: missing.append("Source")
                if not phone: missing.append("Phone")
                if not custom_user_id: missing.append("Employee ID")
                st.toast(f"Missing Required Fields: {', '.join(missing)}", icon="❌")
                st.error(f"**Missing Required Fields - Please fill in: {', '.join(missing)}**")
            elif source == "Transfer" and not soc_date:
                st.toast("SOC Date Required for Transfer", icon="❌")
                st.error("**SOC Date Required - SOC Date is required for Transfer source**")
            else:
                # Check for duplicate lead
                existing_lead = crud_leads.check_duplicate_lead(db, first_name, last_name, phone)
                if existing_lead:
                    st.toast("Duplicate Lead Detected", icon="❌")
                    st.error(f"**Duplicate Lead Detected - {first_name} {last_name} with phone {phone} already exists (ID: {existing_lead.id})**")
                    st.info(f"Created on: {utc_to_local(existing_lead.created_at, st.session_state.get('user_timezone')).strftime('%m/%d/%Y %I:%M %p')}")
                    st.info(f"Created by: {existing_lead.created_by or 'Unknown'}")
                    st.info(f"Status: {existing_lead.last_contact_status}")
                    st.info("Please update the existing lead instead of creating a duplicate.")
                    db.close()
                    return
                
                try:
                    # Prepare data into a dictionary for the modal
                    lead_dict = {
                        "staff_name": staff_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "source": source,
                        "event_name": event_name,
                        "word_of_mouth_type": word_of_mouth_type,
                        "other_source_type": other_source_type,
                        "phone": phone,
                        "email": email or None,
                        "ssn": ssn or None,
                        "age": age if age > 0 else None,
                        "custom_user_id": custom_user_id,
                        "street": street or None,
                        "city": city or None,
                        "state": state or None,
                        "zip_code": zip_code or None,
                        "active_client": True if source == "Transfer" else False,
                        "care_status": "Care Start" if source == "Transfer" else None,
                        "authorization_received": True if source == "Transfer" else False,
                        "soc_date": soc_date if source == "Transfer" else None,
                        "priority": priority,
                        "last_contact_status": last_contact_status,
                        "dob": dob.strftime('%Y-%m-%d') if dob else None, # JSON serializable
                        "medicaid_no": medicaid_no or None,
                        "e_contact_name": e_contact_name or None,
                        "e_contact_relation": e_contact_relation or None,
                        "e_contact_phone": e_contact_phone or None,
                        "comments": comments or None,
                        "agency_id": agency_id,
                        "agency_suboption_id": agency_suboption_id,
                        "ccu_id": ccu_id,
                        "owner_id": current_owner_id or st.session_state.get('db_user_id'),
                        "send_reminders": True # Default in modal
                    }
                    
                    # Open confirmation modal
                    from frontend.common import open_modal
                    open_modal(
                        modal_type='create_lead_confirm',
                        target_id=0, # New lead
                        title='Create Lead?',
                        message=f"Are you sure you want to create lead <b>{first_name} {last_name}</b>?",
                        lead_data=lead_dict,
                        icon='👤',
                        type='info',
                        confirm_label='CREATE LEAD'
                    )
                except Exception as e:
                    st.error(f" Error: {e}")
    
    db.close()
