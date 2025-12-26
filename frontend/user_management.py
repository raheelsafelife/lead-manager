"""
User Management page: Admin panel, password updates, historian
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
from app.db import SessionLocal
from app import services_stats
from app.crud import crud_users, crud_leads, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_mcos, crud_agency_suboptions
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email


def update_password():
    """Password update page for logged-in users"""
    st.markdown('<div class="main-header"> Update Password</div>', unsafe_allow_html=True)
    
    st.write(f"Updating password for: **{st.session_state.username}**")
    
    with st.form("update_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password (min 6 characters)", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        submit = st.form_submit_button(" Update Password")
        
        if submit:
            # Validation
            if not all([current_password, new_password, confirm_password]):
                st.error(" Please fill in all fields")
            elif new_password != confirm_password:
                st.error(" New passwords do not match")
            elif len(new_password) < 6:
                st.error(" Password must be at least 6 characters")
            else:
                db = SessionLocal()
                try:
                    # Verify current password
                    user = crud_users.authenticate_user(db, st.session_state.username, current_password)
                    
                    if not user or user == "pending":
                        st.error(" Current password is incorrect")
                    else:
                        # Update password
                        updated_user = crud_users.update_user_credentials(
                            db=db,
                            user_id=st.session_state.user_id,
                            new_password=new_password,
                            performer_username=st.session_state.username,
                            performer_id=st.session_state.user_id
                        )
                        
                        if updated_user:
                            st.success(" Password updated successfully!")
                        else:
                            st.error(" Failed to update password")
                except Exception as e:
                    st.error(f" Error: {e}")
                finally:
                    db.close()


def admin_panel():
    """Admin panel for user management"""
    st.markdown('<div class="main-header"> User Management</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        " Pending Users", 
        " Password Resets", 
        " Approved Users", 
        " Create User", 
        " Change My Password",
        " Payor",
        " CCU"
    ])
    
    with tab1:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Pending User Approvals</h4>", unsafe_allow_html=True)
        pending_users = crud_users.get_pending_users(db)
        
        if pending_users:
            for user in pending_users:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Username:</span> {user.username}", unsafe_allow_html=True)
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Email:</span> {user.email}", unsafe_allow_html=True)
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Requested:</span> {utc_to_local(user.created_at).strftime('%Y-%m-%d %H:%M')}", unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("Approve", key=f"approve_{user.id}", type="primary", use_container_width=True):
                            crud_users.approve_user(db, user.id, st.session_state.username, st.session_state.user_id)
                            st.success(f"Approved {user.username}")
                            st.rerun()
                    
                    with col3:
                        if st.button("Reject", key=f"reject_{user.id}", type="primary", use_container_width=True):
                            crud_users.reject_user(db, user.id, st.session_state.username, st.session_state.user_id)
                            st.info(f"Rejected {user.username}")
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No pending user approvals")
    
    with tab2:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Password Reset Requests</h4>", unsafe_allow_html=True)
        reset_requests = crud_users.get_password_reset_requests(db)
        
        if reset_requests:
            for user in reset_requests:
                with st.container():
                    st.markdown(f"<span style='font-weight: 900; color: black;'>Username:</span> {user.username}", unsafe_allow_html=True)
                    st.markdown(f"<span style='font-weight: 900; color: black;'>Email:</span> {user.email}", unsafe_allow_html=True)
                    st.markdown(f"<span style='font-weight: 900; color: black;'>Role:</span> {user.role}", unsafe_allow_html=True)
                    
                    with st.form(f"reset_password_form_{user.id}"):
                        new_password = st.text_input("New Password (min 6 characters)", type="password", key=f"new_pwd_{user.id}")
                        confirm_password = st.text_input("Confirm Password", type="password", key=f"confirm_pwd_{user.id}")
                        
                        submit = st.form_submit_button(" Reset Password")
                        
                        if submit:
                            if not new_password or not confirm_password:
                                st.error(" Please fill in both password fields")
                            elif new_password != confirm_password:
                                st.error(" Passwords do not match")
                            elif len(new_password) < 6:
                                st.error(" Password must be at least 6 characters")
                            else:
                                try:
                                    crud_users.admin_reset_password(db, user.id, new_password, st.session_state.username, st.session_state.user_id)
                                    st.success(f" Password reset for {user.username}!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f" Error: {e}")
                    
                    st.divider()
        else:
            st.info("No password reset requests")
    
    with tab3:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Approved Users</h4>", unsafe_allow_html=True)
        approved_users = crud_users.get_approved_users(db)
        
        if approved_users:
            st.write(f"**Total Approved Users:** {len(approved_users)}")
            st.divider()
            
            # Display each user with edit/delete options
            for user in approved_users:
                # Check if we're editing this user
                editing = st.session_state.get(f"editing_user_{user.id}", False)
                
                if not editing:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.markdown(f"<span style='font-weight: 900; color: black;'>ID:</span> {user.id} | <span style='font-weight: 900; color: black;'>User ID:</span> {user.user_id or 'N/A'} | <span style='font-weight: 900; color: black;'>Username:</span> {user.username} | <span style='font-weight: 900; color: black;'>Email:</span> {user.email} | <span style='font-weight: 900; color: black;'>Role:</span> {user.role}", unsafe_allow_html=True)
                            st.caption(f"Created: {utc_to_local(user.created_at).strftime('%Y-%m-%d')}")
                        
                        with col2:
                            if st.button(" Edit", key=f"edit_{user.id}"):
                                st.session_state[f"editing_user_{user.id}"] = True
                                st.rerun()
                        
                        with col3:
                            if st.button(" Delete", key=f"del_{user.id}"):
                                crud_users.delete_user(db, user.id, st.session_state.username, st.session_state.user_id)
                                st.success(f"Deleted {user.username}")
                                st.rerun()
                        
                        st.divider()
                
                # Edit form
                if editing:
                    with st.form(f"edit_user_form_{user.id}"):
                        st.write(f"Editing **{user.username}**")
                        new_username = st.text_input("Username", value=user.username, key=f"edit_username_{user.id}")
                        new_user_id_val = st.text_input("User ID", value=user.user_id or "", key=f"edit_userid_{user.id}")
                        new_email = st.text_input("Email", value=user.email, key=f"edit_email_{user.id}")
                        new_role = st.selectbox("Role", ["user", "admin"], index=0 if user.role == "user" else 1, key=f"edit_role_{user.id}")
                        new_password = st.text_input("New Password (leave blank to keep current)", type="password")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.form_submit_button("Save"):
                                try:
                                    # Update username
                                    if new_username != user.username:
                                        crud_users.admin_update_username(db, user.id, new_username, st.session_state.username, st.session_state.user_id)
                                    
                                    # Update User ID
                                    if new_user_id_val != (user.user_id or ""):
                                        crud_users.admin_update_user_id(db, user.id, new_user_id_val, st.session_state.username, st.session_state.user_id)
                                    
                                    # Update email
                                    if new_email != user.email:
                                        crud_users.admin_update_email(db, user.id, new_email, st.session_state.username, st.session_state.user_id)
                                    
                                    # Update role
                                    if new_role != user.role:
                                        crud_users.update_user_role(db, user.id, new_role, st.session_state.username, st.session_state.user_id)
                                    
                                    # Update password
                                    if new_password:
                                        crud_users.admin_reset_password(db, user.id, new_password, st.session_state.username, st.session_state.user_id)
                                    st.session_state[f"editing_user_{user.id}"] = False
                                    st.success("Updated!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with col_b:
                            if st.form_submit_button(" Cancel"):
                                st.session_state[f"editing_user_{user.id}"] = False
                                st.rerun()
                    st.divider()
        else:
            st.info("No approved users found")
    
    with tab4:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Create New User</h4>", unsafe_allow_html=True)
        st.info(" Users created here are automatically approved and can login immediately.")
        
        with st.form("create_user_form"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                st.markdown('**Username** <span class="required-star">*</span>', unsafe_allow_html=True)
                new_username = st.text_input("Username", label_visibility="collapsed")
            with col_u2:
                st.markdown('**User ID** <span class="required-star">*</span>', unsafe_allow_html=True)
                new_user_id = st.text_input("User ID", placeholder="Employee ID (Compulsory)", label_visibility="collapsed")
                
            st.markdown('**Email** <span class="required-star">*</span>', unsafe_allow_html=True)
            new_email = st.text_input("Email", label_visibility="collapsed")
            
            st.markdown('**Password** (min 6 characters) <span class="required-star">*</span>', unsafe_allow_html=True)
            new_password = st.text_input("Password", type="password", label_visibility="collapsed")
            
            st.markdown('**Confirm Password** <span class="required-star">*</span>', unsafe_allow_html=True)
            confirm_password = st.text_input("Confirm Password", type="password", label_visibility="collapsed")
            
            st.markdown('**Role** <span class="required-star">*</span>', unsafe_allow_html=True)
            new_role = st.selectbox("Role", ["user", "admin"], label_visibility="collapsed")
            
            submit = st.form_submit_button(" Create User")
            
            if submit:
                # Validation
                if not all([new_username, new_email, new_password, confirm_password, new_user_id]):
                    st.error(" Please fill in all fields (User ID is compulsory)")
                elif new_password != confirm_password:
                    st.error(" Passwords do not match")
                elif len(new_password) < 6:
                    st.error(" Password must be at least 6 characters")
                elif '@' not in new_email:
                    st.error(" Please enter a valid email")
                else:
                    try:
                        # Check if username or email already exists
                        existing_user = crud_users.get_user_by_username(db, new_username)
                        if existing_user:
                            st.error(f" Username '{new_username}' already exists")
                        else:
                            existing_email = crud_users.get_user_by_email(db, new_email)
                            if existing_email:
                                st.error(f" Email '{new_email}' already registered")
                            else:
                                # Check for existing User ID
                                existing_uid = crud_users.get_user_by_user_id(db, new_user_id)
                                if existing_uid:
                                    st.error(f" User ID '{new_user_id}' is already assigned to {existing_uid.username}")
                                else:
                                    # Create user with is_approved=True
                                    user_data = UserCreate(
                                        username=new_username,
                                        email=new_email,
                                        password=new_password,
                                        role=new_role,
                                        user_id=new_user_id
                                    )
                                    user = crud_users.create_user(db, user_data, st.session_state.username, st.session_state.user_id)
                                    # Auto-approve the user
                                    crud_users.approve_user(db, user.id, st.session_state.username, st.session_state.user_id)
                                    st.success(f" User '{new_username}' created successfully!")
                                    st.info(f"ID: {new_user_id} | Email: {new_email} | Role: {new_role}")
                                    st.balloons()
                    except Exception as e:
                        st.error(f" Error creating user: {e}")
    
    with tab5:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Change My Password</h4>", unsafe_allow_html=True)
        st.write(f"Updating password for: **{st.session_state.username}**")
        
        with st.form("admin_update_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password (min 6 characters)", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submit = st.form_submit_button(" Update Password")
            
            if submit:
                # Validation
                if not all([current_password, new_password, confirm_password]):
                    st.error(" Please fill in all fields")
                elif new_password != confirm_password:
                    st.error(" New passwords do not match")
                elif len(new_password) < 6:
                    st.error(" Password must be at least 6 characters")
                else:
                    try:
                        # Verify current password
                        user = crud_users.authenticate_user(db, st.session_state.username, current_password)
                        
                        if not user or user == "pending":
                            st.error(" Current password is incorrect")
                        else:
                            # Update password
                            updated_user = crud_users.update_user_credentials(
                                db=db,
                                user_id=st.session_state.user_id,
                                new_password=new_password,
                                performer_username=st.session_state.username,
                                performer_id=st.session_state.user_id
                            )
                            
                            if updated_user:
                                st.success(" Password updated successfully!")
                            else:
                                st.error(" Failed to update password")
                    except Exception as e:
                        st.error(f" Error: {e}")
    
    with tab6:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Manage Payor</h4>", unsafe_allow_html=True)
        st.write("Add, edit, or delete payors that users can select when creating external referrals.")
        
        # Add new agency
        with st.expander(" Add New Payor", expanded=False):
            with st.form("add_agency_admin_form"):
                new_agency_name = st.text_input("Payor Name", placeholder="e.g. IDoA, MCO, DCFS...")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_agency = st.form_submit_button(" Add Payor", use_container_width=True, type="primary")
                with col_btn2:
                    st.form_submit_button(" Cancel", use_container_width=True)
                
                if submit_agency and new_agency_name:
                    try:
                        existing = crud_agencies.get_agency_by_name(db, new_agency_name)
                        if existing:
                            st.error(f" Agency '{new_agency_name}' already exists")
                        else:
                            crud_agencies.create_agency(db, new_agency_name, st.session_state.username, st.session_state.user_id)
                            st.success(f" Agency '{new_agency_name}' added successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
        
        st.divider()
        
        # List all agencies
        agencies = crud_agencies.get_all_agencies(db)
        if agencies:
            st.write(f"**Total Agencies: {len(agencies)}**")
            st.divider()
            
            
            
            for agency in agencies:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"<span style='font-size: 16px;'>**{agency.name}**</span>", unsafe_allow_html=True)
                    st.caption(f"Created: {utc_to_local(agency.created_at).strftime('%Y-%m-%d %H:%M')} by {agency.created_by}")
                with col2:
                    if st.button("Delete", key=f"del_agency_admin_{agency.id}", help=f"Delete {agency.name}", type="primary"):
                        try:
                            crud_agencies.delete_agency(db, agency.id, st.session_state.username, st.session_state.user_id)
                            st.success(f" Deleted '{agency.name}'")
                            st.rerun()
                        except Exception as e:
                            st.error(f" Error: {e}")
                
                # Suboptions removed as per request
                # suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=agency.id)
                # ... check git history if needed
                
                st.divider()
        else:
            st.info("No agencies found. Add your first agency above.")
    
    with tab7:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Manage CCUs</h4>", unsafe_allow_html=True)
        st.write("Add, edit, or delete CCUs that users can select when creating referrals.")
        
        # Add new CCU
        with st.expander(" Add New CCU", expanded=False):
            with st.form("add_ccu_admin_form"):
                new_ccu_name = st.text_input("CCU Name *", placeholder="e.g. CCU North, CCU South...")
                new_ccu_address = st.text_input("Address", placeholder="e.g. 123 Main St, Chicago, IL")
                new_ccu_phone = st.text_input("Phone", placeholder="e.g. (555) 123-4567")
                new_ccu_fax = st.text_input("Fax", placeholder="e.g. (555) 123-4568")
                new_ccu_email = st.text_input("Email", placeholder="e.g. contact@ccu.com")
                new_ccu_coordinator = st.text_input("Care Coordinator Name (Optional)", placeholder="e.g. John Doe")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_ccu = st.form_submit_button(" Add CCU", use_container_width=True, type="primary")
                with col_btn2:
                    st.form_submit_button(" Cancel", use_container_width=True)
                
                if submit_ccu and new_ccu_name:
                    try:
                        existing = crud_ccus.get_ccu_by_name(db, new_ccu_name)
                        if existing:
                            st.error(f" CCU '{new_ccu_name}' already exists")
                        else:
                            crud_ccus.create_ccu(
                                db, new_ccu_name, st.session_state.username, st.session_state.user_id,
                                address=new_ccu_address or None,
                                phone=new_ccu_phone or None,
                                fax=new_ccu_fax or None,
                                email=new_ccu_email or None,
                                care_coordinator_name=new_ccu_coordinator or None
                            )
                            st.success(f" CCU '{new_ccu_name}' added successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
        
        st.divider()
        
        # List all CCUs
        ccus = crud_ccus.get_all_ccus(db)
        if ccus:
            st.write(f"**Total CCUs: {len(ccus)}**")
            st.divider()
            
            for ccu in ccus:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.markdown(f"<span style='font-size: 16px;'> **{ccu.name}**</span>", unsafe_allow_html=True)
                    st.caption(f"Created: {utc_to_local(ccu.created_at).strftime('%Y-%m-%d %H:%M')} by {ccu.created_by}")
                with col2:
                    if st.button("Details", key=f"details_ccu_admin_{ccu.id}", help="View CCU Details", type="primary"):
                        st.session_state[f"viewing_ccu_{ccu.id}"] = not st.session_state.get(f"viewing_ccu_{ccu.id}", False)
                        st.rerun()
                with col3:
                    if st.button("Edit", key=f"edit_ccu_admin_{ccu.id}", help="Edit CCU", type="primary"):
                        st.session_state[f"editing_ccu_{ccu.id}"] = not st.session_state.get(f"editing_ccu_{ccu.id}", False)
                        st.rerun()
                with col4:
                    if st.button("Delete", key=f"del_ccu_admin_{ccu.id}", help=f"Delete CCU: {ccu.name}", type="primary"):
                        try:
                            crud_ccus.delete_ccu(db, ccu.id, st.session_state.username, st.session_state.user_id)
                            st.success(f" Deleted CCU '{ccu.name}'")
                            st.rerun()
                        except Exception as e:
                            st.error(f" Error: {e}")
                
                # Show CCU details
                if st.session_state.get(f"viewing_ccu_{ccu.id}", False):
                    with st.container():
                        st.markdown("**CCU Details:**")
                        detail_col1, detail_col2 = st.columns(2)
                        with detail_col1:
                            st.write(f"**Address:** {ccu.address or 'N/A'}")
                            st.write(f"**Phone:** {ccu.phone or 'N/A'}")
                            st.write(f"**Fax:** {ccu.fax or 'N/A'}")
                        with detail_col2:
                            st.write(f"**Email:** {ccu.email or 'N/A'}")
                            st.write(f"**Care Coordinator:** {ccu.care_coordinator_name or 'N/A'}")
                
                # Inline edit form
                if st.session_state.get(f"editing_ccu_{ccu.id}", False):
                    with st.form(f"edit_ccu_form_{ccu.id}"):
                        edit_name = st.text_input("CCU Name", value=ccu.name)
                        edit_address = st.text_input("Address", value=ccu.address or "")
                        edit_phone = st.text_input("Phone", value=ccu.phone or "")
                        edit_fax = st.text_input("Fax", value=ccu.fax or "")
                        edit_email = st.text_input("Email", value=ccu.email or "")
                        edit_coordinator = st.text_input("Care Coordinator Name", value=ccu.care_coordinator_name or "")
                        col_x, col_y = st.columns(2)
                        with col_x:
                            if st.form_submit_button("Save"):
                                try:
                                    crud_ccus.update_ccu(
                                        db, ccu.id, edit_name, st.session_state.username, st.session_state.user_id,
                                        address=edit_address or None,
                                        phone=edit_phone or None,
                                        fax=edit_fax or None,
                                        email=edit_email or None,
                                        care_coordinator_name=edit_coordinator or None
                                    )
                                    st.session_state[f"editing_ccu_{ccu.id}"] = False
                                    st.success(f" Updated CCU details")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f" Error: {str(e)}")
                        with col_y:
                            if st.form_submit_button(" Cancel"):
                                st.session_state[f"editing_ccu_{ccu.id}"] = False
                                st.rerun()
                
                st.divider()
        else:
            st.info("No CCUs found. Add your first CCU above.")
    
    db.close()


def render_historian():
    """Render the Historian widget in the sidebar"""
    # Professional header with blue+white gradient
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #00506b, #3CA5AA); padding: 0.75rem 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            <div class="white-header-text" style="font-size: 1.5rem; font-weight: 700; margin: 0; text-align: center; text-transform: uppercase; letter-spacing: 0.05em;">Historian</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    db = SessionLocal()
    try:
        # Get recent activities (last 10)
        recent_activities = crud_activity_logs.get_activity_logs(
            db=db, 
            limit=10,
            username=None  # Show all history as requested
        )
        
        # Professional box container        # Display the historian box
        st.markdown("""
        <div style="border-radius: 0.5rem; overflow: hidden; margin-top: 0.5rem; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);">
            <div style="background-color: #00506b; padding: 10px 15px;">
                <div class="white-header-text" style="margin: 0; font-size: 1.2rem; font-weight: bold;">Recent Activity</div>
            </div>
            <div style="background-color: #FFFFFF; padding: 1rem;">
        """, unsafe_allow_html=True)

        if recent_activities:
            for idx, activity in enumerate(recent_activities):
                # Build the complete HTML for the entry
                entry_html = f"""
<div style="display: flex; margin-bottom: 1rem;">
    <div style="flex-grow: 1;">
        <div style="font-weight: 700; color: #1e3a5f; font-size: 1rem; margin-bottom: 2px;">
            {activity.description}
        </div>
        <div style="color: #6B7280; font-size: 0.85rem; margin-bottom: 5px;">
            {utc_to_local(activity.timestamp).strftime('%m/%d/%Y %I:%M %p')}
        </div>
        <div style="display: inline-block; background-color: #3CA5AA; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; margin-bottom: 8px;">
            {format_time_ago(activity.timestamp)}
        </div>
        
        <div style="background-color: #F3F4F6; padding: 8px; border-radius: 0px; font-size: 0.9rem; color: #4B5563;">
            <b>User:</b> {activity.username}
        </div>
"""

                if activity.new_value and activity.old_value:
                    changes = format_changes(activity.old_value, activity.new_value)
                    if changes:
                        for field, old, new in changes:
                            entry_html += f"""
<div style="margin-top: 4px;">
    <span style="font-weight: 600;">{field}:</span> ({old}) → ({new})
</div>
"""
                
                entry_html += """
    </div>
</div>
"""
                
                # Remove newlines to prevent Markdown from interpreting indentation as code blocks
                st.markdown(entry_html.replace('\n', ''), unsafe_allow_html=True)
                
                # Divider between entries (not after last)
                if idx < len(recent_activities) - 1:
                    st.divider()
        else:
            st.markdown(
                '<p style="text-align: center; color: #6B7280; margin: 1rem 0;">No recent activity.</p>',
                unsafe_allow_html=True
            )
        
        st.markdown('</div></div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading historian: {str(e)}")
        # Fallback empty container
        st.markdown('<div style="background: #FFFFFF; border: 2px solid #00506b; border-radius: 0.5rem; padding: 1rem; margin-top: 0.5rem;">Error loading data</div>', unsafe_allow_html=True)
    finally:
        db.close()
