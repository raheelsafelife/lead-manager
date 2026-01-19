"""
User Management page: Admin panel, password updates, historian
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
from app.crud import crud_users, crud_leads, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_mcos, crud_agency_suboptions
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email, render_time, render_confirmation_modal


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
                            user_id=st.session_state.db_user_id,
                            new_password=new_password,
                            performer_username=st.session_state.username,
                            performer_id=st.session_state.db_user_id
                        )
                        
                        if updated_user:
                            st.toast("✅ Password updated successfully!", icon="✅")
                            st.success("✅ **Password updated successfully!**")
                        else:
                            st.error(" Failed to update password")
                except Exception as e:
                    st.error(f" Error: {e}")
                finally:
                    db.close()


def admin_panel():
    """Admin panel for user management"""
    # Display persistent status messages if they exist
    if 'success_msg' in st.session_state:
        msg = st.session_state.pop('success_msg')
        st.toast(msg, icon="✅")
        st.success(msg)
    if 'error_msg' in st.session_state:
        msg = st.session_state.pop('error_msg')
        st.toast(msg, icon="❌")
        st.error(msg)

    st.markdown('<div class="main-header"> User Management</div>', unsafe_allow_html=True)
    
    db = SessionLocal()

    # --- TOP-LEVEL MODAL RENDERING ---
    if 'active_modal' in st.session_state:
        m = st.session_state['active_modal']
        action = render_confirmation_modal(
            title=m['title'],
            message=m['message'],
            icon=m['icon'],
            type=m['type'],
            confirm_label=m['confirm_label'],
            key_prefix=f"admin_{m['target_id']}"
        )
        
        if action is True:
            if m['modal_type'] == 'approve_user':
                crud_users.approve_user(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                st.session_state['success_msg'] = f"✅ Success! User has been approved."
            elif m['modal_type'] == 'reject_user':
                crud_users.reject_user(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                st.session_state['success_msg'] = f"❌ User has been rejected."
            elif m['modal_type'] == 'delete_agency':
                crud_agencies.delete_agency(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                st.session_state['success_msg'] = f"✅ Success! Payor has been deleted."
            elif m['modal_type'] == 'delete_ccu':
                crud_ccus.delete_ccu(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                st.session_state['success_msg'] = f"✅ Success! CCU has been deleted."
            elif m['modal_type'] == 'update_password':
                # Password update logic
                p = st.session_state.get('pending_password_update')
                if p:
                    crud_users.update_user_credentials(
                        db=db,
                        user_id=st.session_state.db_user_id,
                        new_password=p['new_password'],
                        performer_username=st.session_state.username,
                        performer_id=st.session_state.db_user_id
                    )
                    st.session_state['success_msg'] = "✅ Password updated successfully!"
                    del st.session_state['pending_password_update']
            
            del st.session_state['active_modal']
            st.rerun()
        elif action is False:
            del st.session_state['active_modal']
            st.rerun()

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
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Pending User Approvals</h4>", unsafe_allow_html=True)
        pending_users = crud_users.get_pending_users(db)
        
        if pending_users:
            for user in pending_users:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Username:</span> {user.username}", unsafe_allow_html=True)
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Email:</span> {user.email}", unsafe_allow_html=True)
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Requested:</span> {render_time(user.created_at)}", unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("Approve", key=f"approve_{user.id}", type="primary", width="stretch"):
                            st.session_state[f"confirm_approve_{user.id}"] = True
                            st.rerun()
                    
                    with col3:
                        if st.button("Reject", key=f"reject_{user.id}", type="primary", width="stretch"):
                            st.session_state[f"confirm_reject_{user.id}"] = True
                            st.rerun()

                    if st.session_state.get(f"confirm_approve_{user.id}", False):
                        st.session_state['active_modal'] = {
                            'modal_type': 'approve_user',
                            'target_id': user.id,
                            'title': 'Approve User?',
                            'message': f"Do you want to approve user <strong>{user.username}</strong>?",
                            'icon': '✅',
                            'type': 'info',
                            'confirm_label': 'APPROVE'
                        }
                        del st.session_state[f"confirm_approve_{user.id}"]
                        st.rerun()

                    if st.session_state.get(f"confirm_reject_{user.id}", False):
                        st.session_state['active_modal'] = {
                            'modal_type': 'reject_user',
                            'target_id': user.id,
                            'title': 'Reject User?',
                            'message': f"Are you sure you want to reject <strong>{user.username}</strong>?<br><br><span style='color: #DC2626; font-weight: bold;'>⚠️ This user will not be able to login.</span>",
                            'icon': '❌',
                            'type': 'error',
                            'confirm_label': 'REJECT'
                        }
                        del st.session_state[f"confirm_reject_{user.id}"]
                        st.rerun()
                        st.markdown("<br>", unsafe_allow_html=True)
                    
                    st.divider()
        else:
            st.info("No pending user approvals")
    
    with tab2:
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Password Reset Requests</h4>", unsafe_allow_html=True)
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
                                    crud_users.admin_reset_password(db, user.id, new_password, st.session_state.username, st.session_state.db_user_id)
                                    st.toast(f"✅ Password reset for {user.username}!", icon="✅")
                                    st.success(f"✅ **Password reset** for {user.username}!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f" Error: {e}")
                    
                    st.divider()
        else:
            st.info("No password reset requests")
    
    with tab3:
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Approved Users</h4>", unsafe_allow_html=True)
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
                            st.markdown(f"<span style='color: #6B7280;'>Created: {render_time(user.created_at)}</span>", unsafe_allow_html=True)
                        
                        with col2:
                            if st.button(" Edit", key=f"edit_{user.id}"):
                                st.session_state[f"editing_user_{user.id}"] = True
                                st.rerun()
                        
                        with col3:
                            # Delete functionality removed as per user request
                            pass
                        
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
                                        crud_users.admin_update_username(db, user.id, new_username, st.session_state.username, st.session_state.db_user_id)
                                    
                                    # Update User ID
                                    if new_user_id_val != (user.user_id or ""):
                                        crud_users.admin_update_user_id(db, user.id, new_user_id_val, st.session_state.username, st.session_state.db_user_id)
                                    
                                    # Update email
                                    if new_email != user.email:
                                        crud_users.admin_update_email(db, user.id, new_email, st.session_state.username, st.session_state.db_user_id)
                                    
                                    # Update role
                                    if new_role != user.role:
                                        crud_users.update_user_role(db, user.id, new_role, st.session_state.username, st.session_state.db_user_id)
                                    
                                    # Update password
                                    if new_password:
                                        crud_users.admin_reset_password(db, user.id, new_password, st.session_state.username, st.session_state.db_user_id)
                                    st.session_state[f"editing_user_{user.id}"] = False
                                    st.toast(f"✅ User '{user.username}' updated!", icon="✅")
                                    st.success("✅ **Updated Successfully!**")
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
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Create New User</h4>", unsafe_allow_html=True)
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
                    missing = []
                    if not new_username: missing.append("Username")
                    if not new_user_id: missing.append("Employee ID")
                    if not new_email: missing.append("Email")
                    if not new_password: missing.append("Password")
                    if not confirm_password: missing.append("Confirm Password")
                    st.toast(f"❌ Missing Information: {', '.join(missing)}", icon="❌")
                    st.error(f"❌ **Missing Information** - Please fill in: {', '.join(missing)}")
                elif new_password != confirm_password:
                    st.toast("❌ Password Mismatch", icon="❌")
                    st.error("❌ **Password Mismatch** - Confirmation password doesn't match. Please re-enter.")
                elif len(new_password) < 6:
                    st.toast("❌ Password Too Short", icon="❌")
                    st.error("❌ **Password Too Short** - Password must be at least 6 characters long")
                elif '@' not in new_email:
                    st.toast("❌ Invalid Email", icon="❌")
                    st.error("❌ **Invalid Email** - Please enter a valid email address")
                else:
                    try:
                        # Check if username or email already exists
                        existing_user = crud_users.get_user_by_username(db, new_username)
                        if existing_user:
                            st.toast("❌ Username Conflict", icon="❌")
                            st.error(f"❌ **Username Conflict** - '{new_username}' is already taken. Please choose a different username.")
                        else:
                            existing_email = crud_users.get_user_by_email(db, new_email)
                            if existing_email:
                                st.toast("❌ Email Already Registered", icon="❌")
                                st.error(f"❌ **Email Already Registered** - '{new_email}' is already in use. Please use a different email.")
                            else:
                                # Check for existing User ID
                                existing_uid = crud_users.get_user_by_user_id(db, new_user_id)
                                if existing_uid:
                                    st.toast("❌ Employee ID Conflict", icon="❌")
                                    st.error(f"❌ **Employee ID Conflict** - Employee ID '{new_user_id}' is already assigned to {existing_uid.username}. Please use a unique ID.")
                                else:
                                    # Create user with is_approved=True
                                    user_data = UserCreate(
                                        username=new_username,
                                        email=new_email,
                                        password=new_password,
                                        role=new_role,
                                        user_id=new_user_id
                                    )
                                    user = crud_users.create_user(db, user_data, st.session_state.username, st.session_state.db_user_id)
                                    # Auto-approve the user
                                    crud_users.approve_user(db, user.id, st.session_state.username, st.session_state.db_user_id)
                                    st.toast(f"✅ User '{new_username}' created successfully!", icon="✅")
                                    st.success(f"✅ **User Created Successfully!** - '{new_username}' has been added to the system.")
                                    st.info(f"📝 **Details:** Employee ID: {new_user_id} | Email: {new_email} | Role: {new_role}")
                    except Exception as e:
                        st.toast(f"❌ Error creating user: {str(e)}", icon="❌")
                        st.error(f"❌ **User Creation Failed** - Could not create user: {str(e)}")
    
    with tab5:
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Change My Password</h4>", unsafe_allow_html=True)
        st.write(f"Updating password for: **{st.session_state.username}**")
        
        with st.form("admin_update_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password (min 6 characters)", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submit = st.form_submit_button(" Update Password")
            
            if submit:
                # Validation
                if not all([current_password, new_password, confirm_password]):
                    missing = []
                    if not current_password: missing.append("Current Password")
                    if not new_password: missing.append("New Password")
                    if not confirm_password: missing.append("Confirm Password")
                    st.toast(f"❌ Missing Fields: {', '.join(missing)}", icon="❌")
                    st.error(f"❌ **Missing Fields** - Please fill in: {', '.join(missing)}")
                elif new_password != confirm_password:
                    st.toast("❌ New Passwords Mismatch", icon="❌")
                    st.error("❌ **Password Mismatch** - New passwords do not match. Please re-enter.")
                elif len(new_password) < 6:
                    st.toast("❌ Password Too Short", icon="❌")
                    st.error("❌ **Password Too Short** - Password must be at least 6 characters long")
                else:
                    try:
                        # Verify current password
                        user = crud_users.authenticate_user(db, st.session_state.username, current_password)
                        
                        if not user or user == "pending":
                            st.toast("❌ Current Password Incorrect", icon="❌")
                            st.error("❌ **Incorrect Password** - Current password is incorrect. Please try again.")
                        else:
                            # Trigger confirmation modal
                            st.session_state['pending_password_update'] = {"new_password": new_password}
                            st.session_state['active_modal'] = {
                                'modal_type': 'update_password',
                                'target_id': st.session_state.db_user_id,
                                'title': 'Update Password?',
                                'message': "Are you sure you want to change your password?",
                                'icon': '🔒',
                                'type': 'info',
                                'confirm_label': 'UPDATE'
                            }
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
    
    with tab6:
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Manage Payor</h4>", unsafe_allow_html=True)
        st.write("Add, edit, or delete payors that users can select when creating external referrals.")
        
        # Add new agency
        with st.expander(" Add New Payor", expanded=False):
            with st.form("add_agency_admin_form"):
                new_agency_name = st.text_input("Payor Name", placeholder="e.g. IDoA, MCO, DCFS...")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_agency = st.form_submit_button(" Add Payor", width="stretch", type="primary")
                with col_btn2:
                    st.form_submit_button(" Cancel", width="stretch")
                
                if submit_agency and new_agency_name:
                    try:
                        existing = crud_agencies.get_agency_by_name(db, new_agency_name)
                        if existing:
                            st.error(f" Agency '{new_agency_name}' already exists")
                        else:
                            crud_agencies.create_agency(db, new_agency_name, st.session_state.username, st.session_state.db_user_id)
                            st.toast(f"✅ Payor '{new_agency_name}' added!", icon="✅")
                            st.success(f"✅ **Success!** Payor '{new_agency_name}' added successfully!")
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
                    st.markdown(f"<span style='color: #6B7280; font-size: 0.85rem;'>Created: {render_time(agency.created_at)} by {agency.created_by}</span>", unsafe_allow_html=True)
                with col2:
                    if st.button("Delete", key=f"del_agency_admin_{agency.id}", help=f"Delete {agency.name}", type="primary"):
                        st.session_state[f"confirm_del_agency_{agency.id}"] = True
                        st.rerun()

                if st.session_state.get(f"confirm_del_agency_{agency.id}", False):
                    st.session_state['active_modal'] = {
                        'modal_type': 'delete_agency',
                        'target_id': agency.id,
                        'title': 'Delete Payor?',
                        'message': f"Are you sure you want to delete payor <strong>{agency.name}</strong>?<br><br><span style='color: #6B7280;'>⚠️ This may affect associated leads.</span>",
                        'icon': '🗑️',
                        'type': 'error',
                        'confirm_label': 'DELETE'
                    }
                    del st.session_state[f"confirm_del_agency_{agency.id}"]
                    st.rerun()
                
                # Suboptions removed as per request
                # suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=agency.id)
                # ... check git history if needed
                
                st.divider()
        else:
            st.info("No agencies found. Add your first agency above.")
    
    with tab7:
        st.markdown("<h4 style='font-weight: bold; color: #111827;'>Manage CCUs</h4>", unsafe_allow_html=True)
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
                    submit_ccu = st.form_submit_button(" Add CCU", width="stretch", type="primary")
                with col_btn2:
                    st.form_submit_button(" Cancel", width="stretch")
                
                if submit_ccu and new_ccu_name:
                    try:
                        existing = crud_ccus.get_ccu_by_name(db, new_ccu_name)
                        if existing:
                            st.error(f" CCU '{new_ccu_name}' already exists")
                        else:
                            crud_ccus.create_ccu(
                                db, new_ccu_name, st.session_state.username, st.session_state.db_user_id,
                                address=new_ccu_address or None,
                                phone=new_ccu_phone or None,
                                fax=new_ccu_fax or None,
                                email=new_ccu_email or None,
                                care_coordinator_name=new_ccu_coordinator or None
                            )
                            st.toast(f"✅ CCU '{new_ccu_name}' added!", icon="✅")
                            st.success(f"✅ **Success!** CCU '{new_ccu_name}' added successfully!")
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
                    st.markdown(f"<span style='color: #6B7280; font-size: 0.85rem;'>Created: {render_time(ccu.created_at)} by {ccu.created_by}</span>", unsafe_allow_html=True)
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
                        st.session_state[f"confirm_del_ccu_{ccu.id}"] = True
                        st.rerun()

                if st.session_state.get(f"confirm_del_ccu_{ccu.id}", False):
                    st.session_state['active_modal'] = {
                        'modal_type': 'delete_ccu',
                        'target_id': ccu.id,
                        'title': 'Delete CCU?',
                        'message': f"Are you sure you want to delete CCU <strong>{ccu.name}</strong>?",
                        'indicator': 'This may affect associated referrals.',
                        'icon': '🗑️',
                        'type': 'error',
                        'confirm_label': 'DELETE'
                    }
                    del st.session_state[f"confirm_del_ccu_{ccu.id}"]
                    st.rerun()
                
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
                                        db, ccu.id, edit_name, st.session_state.username, st.session_state.db_user_id,
                                        address=edit_address or None,
                                        phone=edit_phone or None,
                                        fax=edit_fax or None,
                                        email=edit_email or None,
                                        care_coordinator_name=edit_coordinator or None
                                    )
                                    st.session_state[f"editing_ccu_{ccu.id}"] = False
                                    st.toast(f"✅ CCU '{edit_name}' updated!", icon="✅")
                                    st.success(f"✅ **Success!** Updated CCU details")
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
    # Professional header with solid aqua background
    st.markdown(
        """
        <div style="background: #3CA5AA; padding: 0.75rem 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            <div class="white-header-text" style="font-size: 1.5rem; font-weight: 700; margin: 0; text-align: center; text-transform: uppercase; letter-spacing: 0.05em; color: #FFFFFF !important;">Historian</div>
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
            <div style="background-color: #3CA5AA; padding: 10px 15px; border-radius: 0.35rem 0.35rem 0 0;">
                <div class="white-header-text" style="margin: 0; font-size: 1.2rem; font-weight: bold; color: #FFFFFF !important;">Recent Activity</div>
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
            {render_time(activity.timestamp)}
        </div>
        <div style="margin-bottom: 8px;">
            {render_time(activity.timestamp, style='ago', is_badge=True)}
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
    <span style="font-weight: 600;">{field}:</span> ({old}) -> ({new})
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
        st.markdown('<div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-left: 5px solid #EF4444; border-radius: 0.5rem; padding: 1rem; margin-top: 0.5rem;">Error loading data</div>', unsafe_allow_html=True)
    finally:
        db.close()
