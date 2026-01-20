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
from app.crud import crud_users, crud_leads, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email, get_priority_tag


def add_lead():
    """Add new lead"""
    st.markdown('<div class="main-header"> Add New Lead</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Source Selection OUTSIDE form for dynamic updates
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
    ], label_visibility="collapsed")
    
    # Conditional fields based on source (OUTSIDE form)
    event_name = None
    word_of_mouth_type = None
    other_source_type = None
    agency_id = None
    agency_suboption_id = None
    ccu_id = None
    soc_date = None
    
    if source == "Transfer":
        st.markdown('SOC Date (Start of Care) <span class="required-star">*</span>', unsafe_allow_html=True)
        soc_date = st.date_input("SOC Date", value=date.today(), key="transfer_soc_date", label_visibility="collapsed")
    
    elif source == "Event":
        # ... existing event logic ...
        # (skipping for brevity in replacement)
        pass # placeholder to keep context if needed, but I'll replace the whole block carefully
    
    elif source == "Direct Through CCU":
        # Get all agencies from database
        from app.crud import crud_ccus
        agencies = crud_agencies.get_all_agencies(db)
        agency_names = [a.name for a in agencies]
        
        # Initialize variables
        agency_id = None
        agency_suboption_id = None
        
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Select Payor</h4>", unsafe_allow_html=True)
        
        if not agency_names:
            st.warning(" No payors available.")
            if st.session_state.user_role == "admin":
                st.info("Add payors using User Management -> Payor")
            selected_agency_name = None
            agency_id = None
        else:
            agency_list = ["None", "Other (Add New)"] + agency_names
            selected_agency_name = st.selectbox("**Select Payor**", agency_list, key="agency_name_select")
            
            # If "Other" is selected, show button to add new agency (ADMIN ONLY)
            if selected_agency_name == "Other (Add New)":
                if st.session_state.user_role == "admin":
                    st.info("Click the button below to add a new payor")
                    if st.button(" Add New Payor", key="add_new_agency_btn", type="primary"):
                        st.session_state['show_agency_form'] = True
                        st.rerun()
                else:
                    st.warning(" Only admins can add new payors. Please contact your administrator.")
                    st.info("You can find existing payors in the dropdown or contact admin.")
                    selected_agency_name = "None"
            elif selected_agency_name != "None":
                # Get the agency ID
                agency_id = None
                for agency in agencies:
                    if agency.name == selected_agency_name:
                        agency_id = agency.id
                        break
            else:
                agency_id = None
        
        # Show payor add form if triggered (ADMIN ONLY)
        if st.session_state.get('show_agency_form', False) and st.session_state.user_role == "admin":
            with st.form("add_new_agency_form"):
                st.write("**Add New Payor:**")
                new_agency_name = st.text_input("**Payor Name**", placeholder="e.g. IDoA, MCO, DCFS...")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_new_agency = st.form_submit_button(" Add Payor", width="stretch", type="primary")
                with col_btn2:
                    cancel_new_agency = st.form_submit_button(" Cancel", width="stretch")
                
                if submit_new_agency and new_agency_name:
                    try:
                        existing = crud_agencies.get_agency_by_name(db, new_agency_name)
                        if existing:
                            st.error(f" '{new_agency_name}' already exists")
                        else:
                            crud_agencies.create_agency(db, new_agency_name, st.session_state.username, st.session_state.get('db_user_id'))
                            st.success(f" '{new_agency_name}' added successfully!")
                            st.session_state['show_agency_form'] = False
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
                
                if cancel_new_agency:
                    st.session_state['show_agency_form'] = False
                    st.rerun()
        
        # Reset agency_id if "Other" is still selected
        if selected_agency_name == "Other (Add New)":
            agency_id = None
        
        # Payor Suboption Selection (if agency selected and agency_id exists)
        if agency_id:
            from app.crud import crud_agency_suboptions
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
        
        # CCU Selection ()
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Select CCU</h4>", unsafe_allow_html=True)
        ccu_id = None
        
        # Get ALL CCUs (not filtered by agency)
        ccus = crud_ccus.get_all_ccus(db)
        ccu_names = [c.name for c in ccus]
        
        if not ccu_names:
            st.info(" No CCUs available.")
            if st.button(" Add CCU", key="add_ccu_btn", type="secondary"):
                st.session_state['show_ccu_form'] = True
                st.rerun()
        else:
            ccu_list = ["None", "Other (Add New)"] + ccu_names
            selected_ccu_name = st.selectbox("**Select CCU**", ccu_list, key="ccu_name_select", label_visibility="collapsed")
            
            # If "Other" is selected, show add button
            if selected_ccu_name == "Other (Add New)":
                st.info("Click below to add a new CCU")
                if st.button(" Add New CCU", key="add_new_ccu_btn", type="secondary"):
                    st.session_state['show_ccu_form'] = True
                    st.rerun()
            elif selected_ccu_name != "None":
                # Get the CCU ID
                for ccu in ccus:
                    if ccu.name == selected_ccu_name:
                        ccu_id = ccu.id
                        break
        
        # Show CCU add form if triggered (ALL USERS CAN ADD)
        if st.session_state.get('show_ccu_form', False):
            with st.form("add_new_ccu_form"):
                st.write("**Add New CCU:**")
                new_ccu_name = st.text_input("**CCU Name** *", placeholder="e.g. CCU North, CCU South...")
                new_ccu_address = st.text_input("**Address**", placeholder="e.g. 123 Main St, Chicago, IL")
                new_ccu_phone = st.text_input("**Phone**", placeholder="e.g. (555) 123-4567")
                new_ccu_fax = st.text_input("**Fax**", placeholder="e.g. (555) 123-4568")
                new_ccu_email = st.text_input("**Email**", placeholder="e.g. contact@ccu.com")
                new_ccu_coordinator = st.text_input("**Care Coordinator Name (Optional)**", placeholder="e.g. John Doe")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_new_ccu = st.form_submit_button(" Add CCU", width="stretch", type="primary")
                with col_btn2:
                    cancel_new_ccu = st.form_submit_button(" Cancel", width="stretch")
                
                if submit_new_ccu and new_ccu_name:
                    try:
                        # Check if CCU exists
                        existing = crud_ccus.get_ccu_by_name(db, new_ccu_name)
                        if existing:
                            st.error(f" CCU '{new_ccu_name}' already exists")
                        else:
                            crud_ccus.create_ccu(
                                db, new_ccu_name, st.session_state.username, st.session_state.get('db_user_id'),
                                address=new_ccu_address or None,
                                phone=new_ccu_phone or None,
                                fax=new_ccu_fax or None,
                                email=new_ccu_email or None,
                                care_coordinator_name=new_ccu_coordinator or None
                            )
                            st.success(f" CCU '{new_ccu_name}' added successfully!")
                            st.session_state['show_ccu_form'] = False
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
                
                if cancel_new_ccu:
                    st.session_state['show_ccu_form'] = False
                    st.rerun()
                
    elif source == "Word of Mouth":
        st.markdown('**Word of Mouth Type** <span class="required-star">*</span>', unsafe_allow_html=True)
        word_of_mouth_type = st.selectbox("Word of Mouth Type", [
            "Caregiver",
            "Community",
            "Client"
        ], key="wom_type_input", label_visibility="collapsed")
    elif source == "Other":
        st.markdown('**Specify Source Type** <span class="required-star">*</span>', unsafe_allow_html=True)
        other_source_type = st.text_input("Specify Source Type", value="", key="other_type_input", label_visibility="collapsed")
    
    st.divider()

    # Priority Selection (Outside form for dynamic updates)
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Priority</h4>", unsafe_allow_html=True)
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        st.markdown('**Set Priority** <span class="required-star">*</span>', unsafe_allow_html=True)
        priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=1, label_visibility="collapsed", key="priority_outside_form")
    with col_p2:
        st.markdown('<div style="margin-top: 5px;"></div>', unsafe_allow_html=True)
        st.markdown(get_priority_tag(priority), unsafe_allow_html=True)
    
    st.divider()
    
    # Main form with other fields
    with st.form("add_lead_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Staff assignment based on role
            if st.session_state.user_role == "admin":
                st.markdown('**Staff Name** <span class="required-star">*</span>', unsafe_allow_html=True)
                staff_name = st.text_input("Staff Name", value="", label_visibility="collapsed")
            else:
                staff_name = st.session_state.username
                st.info(f" Lead will be created by : **{staff_name}**")
            
            # New field: User ID (Compulsory)
            st.markdown('**User ID** <span class="required-star">*</span> (Unique Identifier)', unsafe_allow_html=True)
            custom_user_id = st.text_input("User ID", help="Unique ID for this lead (e.g. Patient ID)", label_visibility="collapsed")
            
            st.markdown('**First Name** <span class="required-star">*</span>', unsafe_allow_html=True)
            first_name = st.text_input("First Name", value="", label_visibility="collapsed")
            
            st.markdown('**Last Name** <span class="required-star">*</span>', unsafe_allow_html=True)
            last_name = st.text_input("Last Name", value="", label_visibility="collapsed")
            
            age = st.number_input("**Age / Year**", min_value=0, max_value=3000, value=0)
            
            email = st.text_input("**Email**")  # New field
            
            st.markdown('**Phone** <span class="required-star">*</span>', unsafe_allow_html=True)
            phone = st.text_input("Phone", value="", label_visibility="collapsed")
            ssn = st.text_input("**SSN**")  # New field
            city = st.text_input("**City**")
            zip_code = st.text_input("**Zip Code**")
        
        with col2:
            st.markdown('**Contact Status** <span class="required-star">*</span>', unsafe_allow_html=True)
            last_contact_status = st.selectbox("Contact Status", 
                                              ["Intro Call", "Follow Up", "No Response", "Inactive"],
                                              label_visibility="collapsed")
            dob = st.date_input("**Date of Birth**", value=None, min_value=date(1900, 1, 1), max_value=date.today())
            medicaid_no = st.text_input("**Medicaid Number**")
            e_contact_name = st.text_input("**Emergency Contact Name**")
            e_contact_phone = st.text_input("**Emergency Contact Phone**")
            
            comments = st.text_area("**Comments**")
        
        st.divider()
        st.markdown('<small>Fields marked with <span style="color:var(--required-star-pink)">*</span> are required</small>', unsafe_allow_html=True)
       
        submit = st.form_submit_button("Save Lead", width="stretch", type="primary")

        
        if submit:
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
                    lead_data = LeadCreate(
                        staff_name=staff_name,
                        first_name=first_name,
                        last_name=last_name,
                        source=source,
                        event_name=event_name,
                        word_of_mouth_type=word_of_mouth_type,
                        other_source_type=other_source_type,
                        phone=phone,
                        email=email or None,
                        ssn=ssn or None,
                        age=age if age > 0 else None,
                        custom_user_id=custom_user_id,
                        city=city or None,
                        zip_code=zip_code or None,
                        active_client=True if source == "Transfer" else False,
                        care_status="Care Start" if source == "Transfer" else None,
                        authorization_received=True if source == "Transfer" else False,
                        soc_date=soc_date if source == "Transfer" else None,
                        priority=priority,
                        last_contact_status=last_contact_status,
                        dob=dob if dob else None,
                        medicaid_no=medicaid_no or None,
                        e_contact_name=e_contact_name or None,
                        e_contact_phone=e_contact_phone or None,
                        comments=comments or None,
                        agency_id=agency_id,
                        agency_suboption_id=agency_suboption_id,
                        ccu_id=ccu_id,
                        owner_id=st.session_state.get('db_user_id')  # Save Owner ID for stable linking
                    )
                    lead = crud_leads.create_lead(db, lead_data, st.session_state.username, st.session_state.get('db_user_id'))
                    st.toast(f"Lead '{first_name} {last_name}' created successfully!", icon="✅")
                    st.success(f"**Success! Lead created successfully! (ID: {lead.id})**")
                    
                    # Auto-send email to lead creator (always for non-inactive leads)
                    if lead.last_contact_status != "Inactive":
                        user = crud_users.get_user_by_username(db, st.session_state.username)
                        if user and user.email:
                            try:
                                # Check if this is a referral or regular lead
                                if lead.active_client:  # Is a referral
                                    from app.utils.email_service import send_referral_reminder_email
                                    
                                    # Get payor (payor) information
                                    agency_name = "N/A"
                                    agency_suboption = ""
                                    if lead.agency_id:
                                        agency = crud_agencies.get_agency(db, lead.agency_id)
                                        if agency:
                                            agency_name = agency.name
                                    
                                    if lead.agency_suboption_id:
                                        from app.crud.crud_agency_suboptions import get_suboption_by_id
                                        suboption = get_suboption_by_id(db, lead.agency_suboption_id)
                                        if suboption:
                                            agency_suboption = suboption.name
                                    
                                    # Get CCU information
                                    ccu_name = "N/A"
                                    ccu_phone = "N/A"
                                    ccu_fax = "N/A"
                                    ccu_email = "N/A"
                                    ccu_address = "N/A"
                                    ccu_coordinator = "N/A"
                                    if lead.ccu_id:
                                        ccu = crud_ccus.get_ccu_by_id(db, lead.ccu_id)
                                        if ccu:
                                            ccu_name = ccu.name
                                            ccu_phone = ccu.phone if ccu.phone else "N/A"
                                            ccu_fax = ccu.fax if ccu.fax else "N/A"
                                            ccu_email = ccu.email if ccu.email else "N/A"
                                            ccu_address = ccu.address if ccu.address else "N/A"
                                            ccu_coordinator = ccu.care_coordinator_name if ccu.care_coordinator_name else "N/A"
                                    
                                    # Prepare referral info
                                    referral_info = {
                                        'name': f"{lead.first_name} {lead.last_name}",
                                        'phone': lead.phone,
                                        'dob': str(lead.dob) if lead.dob else 'N/A',
                                        'creator': st.session_state.username,
                                        'created_date': utc_to_local(lead.created_at, st.session_state.get('user_timezone')).strftime('%m/%d/%Y'),
                                        'status': lead.last_contact_status,
                                        'referral_type': lead.referral_type if lead.referral_type else 'Regular',
                                        'payor_name': agency_name,
                                        'payor_suboption': agency_suboption,
                                        'ccu_name': ccu_name,
                                        'ccu_phone': ccu_phone,
                                        'ccu_fax': ccu_fax,
                                        'ccu_email': ccu_email,
                                        'ccu_address': ccu_address,
                                        'ccu_coordinator': ccu_coordinator
                                    }
                                    
                                    # Send referral email
                                    auto_email_success = send_referral_reminder_email(referral_info, user.email)
                                    email_subject = f"New Referral [{referral_info['referral_type']}]: {lead.first_name} {lead.last_name}"
                                    
                                else:  # Regular lead
                                    from app.utils.email_service import send_simple_lead_email
                                    
                                    # Prepare simple lead info
                                    lead_info = {
                                        'name': f"{lead.first_name} {lead.last_name}",
                                        'phone': lead.phone,
                                        'creator': st.session_state.username,
                                        'dob': str(lead.dob) if lead.dob else 'N/A',
                                        'source': lead.source,
                                        'status': lead.last_contact_status,
                                        'created_date': utc_to_local(lead.created_at, st.session_state.get('user_timezone')).strftime('%m/%d/%Y')
                                    }
                                    
                                    # Send simple email
                                    auto_email_success = send_simple_lead_email(lead_info, user.email)
                                    email_subject = f"New Lead: {lead.first_name} {lead.last_name}"
                                
                                if auto_email_success:
                                    # Record the auto email
                                    crud_email_reminders.create_reminder(
                                        db=db,
                                        lead_id=lead.id,
                                        recipient_email=user.email,
                                        subject=email_subject,
                                        sent_by="system",
                                        status="sent"
                                    )
                                    st.info(f"Auto-reminder email sent to {user.email}")
                                else:
                                    # Record failed attempt
                                    crud_email_reminders.create_reminder(
                                        db=db,
                                        lead_id=lead.id,
                                        recipient_email=user.email,
                                        subject=email_subject,
                                        sent_by="system",
                                        status="failed",
                                        error_message="Email service error"
                                    )
                            except Exception as auto_email_error:
                                pass  # Don't show error for auto-email, it's background
                    
                except Exception as e:
                    st.error(f" Error: {e}")
    
    db.close()
