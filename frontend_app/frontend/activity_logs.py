"""
Activity Logs page: View activity history
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
from frontend.common import prepare_lead_data_for_email, render_time

from datetime import timedelta

def view_activity_logs():
    """Professional Activity Logs page with advanced filtering and beautiful UI"""
    st.markdown('<div class="main-header">Activity Logs</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    from app.crud import crud_activity_logs
    from app.utils.activity_logger import (
        format_time_ago, get_time_color, get_action_icon, 
        get_action_label, get_entity_badge_color, format_changes
    )
    from datetime import datetime, timedelta
    
    # Filters Section
    st.markdown("### Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Date range filter
        date_options = ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom Range"]
        date_filter = st.selectbox("**Date Range**", date_options)
        
        start_date = None
        end_date = None
        
        if date_filter == "Today":
            start_date = datetime.now().replace(hour=0, minute=0, second=0)
        elif date_filter == "Last 7 Days":
            start_date = datetime.now() - timedelta(days=7)
        elif date_filter == "Last 30 Days":
            start_date = datetime.now() - timedelta(days=30)
        elif date_filter == "Custom Range":
            col_a, col_b = st.columns(2)
            with col_a:
                start_date = st.date_input("From", value=datetime.now() - timedelta(days=7))
            with col_b:
                end_date = st.date_input("To", value=datetime.now())
    
    with col2:
        # User filter
        if st.session_state.user_role == "admin":
            # Get all users for the dropdown
            all_users = crud_users.get_all_users(db)
            user_options = ["All Users"] + [u.username for u in all_users]
            
            user_filter = st.selectbox("**User**", user_options)
            if user_filter == "All Users":
                user_filter = None
        else:
            user_filter = st.session_state.username
            st.info(f"Showing: {user_filter}")
    
    with col3:
        # Action type filter
        action_types = [
            "All Actions",
            "LEAD_CREATED",
            "LEAD_UPDATED", 
            "LEAD_DELETED",
            "REFERRAL_MARKED",
            "REFERRAL_UNMARKED",
            "STATUS_CHANGED"
        ]
        action_filter = st.selectbox("**Action Type**", action_types)
        if action_filter == "All Actions":
            action_filter = None
    
    with col4:
        # Entity type filter
        entity_types = ["All Types", "Lead", "User", "Event"]
        entity_filter = st.selectbox("**Entity Type**", entity_types)
        if entity_filter == "All Types":
            entity_filter = None
    
    # Search box
    col_search, col_client = st.columns(2)
    with col_search:
        search_query = st.text_input("**General Search (keywords)**", "")
    with col_client:
        client_search = st.text_input("**Client Search (Lead Name)**", "")
        
    # Combine search logic
    final_search = search_query
    if client_search:
        final_search = client_search
    
    st.divider()
    
    # Get filtered activities
    activities = crud_activity_logs.get_activity_logs(
        db=db,
        limit=100,
        username=user_filter,
        action_type=action_filter,
        entity_type=entity_filter,
        start_date=start_date,
        end_date=end_date,
        search_keywords=final_search if final_search else None
    )
    
    # Display count and Export
    col_count, col_export = st.columns([3, 1])
    with col_count:
        total_count = len(activities)
        st.write(f"**Showing {total_count} activities**")
    
    with col_export:
        if activities:
            # Prepare data for CSV
            export_data = []
            for activity in activities:
                export_data.append({
                    "Timestamp": utc_to_local(activity.timestamp, st.session_state.get('user_timezone')).strftime("%Y-%m-%d %H:%M:%S"),
                    "User": activity.username,
                    "Action": activity.action_type,
                    "Entity Type": activity.entity_type,
                    "Entity Name": activity.entity_name,
                    "Description": activity.description,
                    "Details": activity.new_value if activity.new_value else ""
                })
            
            df_export = pd.DataFrame(export_data)
            csv = df_export.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Export CSV",
                data=csv,
                file_name=f"activity_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv"
            )

    
    if activities:
        for activity in activities:
            # Get visual elements
            label = get_action_label(activity.action_type)
            time_ago_html = render_time(activity.timestamp, style="ago")
            time_full_html = render_time(activity.timestamp)
            time_color = get_time_color(activity.timestamp)
            entity_color = get_entity_badge_color(activity.entity_type)
            
            # Create activity card
            with st.container():
                # Header row
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.markdown(f"### {label}")
                
                with col2:
                    # Entity badge
                    if activity.entity_type:
                        if entity_color == "blue":
                            st.info(f"{activity.entity_type}")
                        elif entity_color == "green":
                            st.success(f"{activity.entity_type}")
                        elif entity_color == "purple":
                            st.warning(f"{activity.entity_type}")
                        else:
                            st.write(f"{activity.entity_type}")
                
                with col3:
                    # Time with color coding
                    st.markdown(f"**Time:** {time_ago_html}", unsafe_allow_html=True)
                    st.markdown(f"<span style='font-size: 0.85rem; color: #6B7280;'>{time_full_html}</span>", unsafe_allow_html=True)
                
                # Details row
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.write(f"**By:** {activity.username}")
                    if activity.entity_name:
                        st.write(f"**Entity:** {activity.entity_name}")
                
                with col2:
                    st.write(f"**Description:** {activity.description}")
                    
                    # Show changes if available
                    if activity.old_value and activity.new_value:
                        changes = format_changes(activity.old_value, activity.new_value)
                        if changes:
                            st.markdown("**Changes:**")
                            for field, old_val, new_val in changes:
                                st.write(f"  - **{field}:** {old_val} -> {new_val}")
                
                st.divider()
    else:
        st.info("No activities found matching your filters")
    
    db.close()
