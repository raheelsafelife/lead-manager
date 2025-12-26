"""
Dashboard page: Main dashboard view and user dashboards
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
from app.db import SessionLocal
from app import services_stats
from app.crud import crud_users, crud_leads, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_mcos
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
from frontend.common import prepare_lead_data_for_email

import plotly.graph_objects as go
import plotly.express as px

# Helper to display drill down
def show_drill_down(filtered_df, title):
    if not filtered_df.empty:
        st.markdown(f"**Drill Down: {title} ({len(filtered_df)})**")
        # Select relevant columns for display
        display_cols = ['first_name', 'last_name', 'phone', 'source', 'last_contact_status', 'staff_name', 'created_at']
        # Only show cols that exist
        cols = [c for c in display_cols if c in filtered_df.columns]
        st.dataframe(filtered_df[cols], width="stretch")
    else:
        st.info("No detailed records found.")

def dashboard():
    """Main dashboard view"""
    db = SessionLocal()
    
    # Load all leads once for drill-down capabilities
    # We use a dataframe for easier filtering
    all_leads_list = crud_leads.list_leads(db, limit=10000)
    df_all_leads = pd.DataFrame([l.__dict__ for l in all_leads_list])
    # Clean up sqlalchemy state objects from dict
    if not df_all_leads.empty:
        if '_sa_instance_state' in df_all_leads.columns:
            df_all_leads = df_all_leads.drop('_sa_instance_state', axis=1)

    st.markdown(f'<div class="main-header">PERFORMANCE METRICS DASHBOARD</div>', unsafe_allow_html=True)
    st.markdown(f"Welcome, **{st.session_state.username}**!")
    
    # Logout button
    if st.button("Logout", key="logout"):
        # Log logout
        if st.session_state.username:
            crud_activity_logs.create_activity_log(
                db=db,
                user_id=st.session_state.user_id,
                username=st.session_state.username,
                action_type="USER_LOGOUT",
                entity_type="User",
                entity_id=st.session_state.user_id,
                entity_name=st.session_state.username,
                description=f"User '{st.session_state.username}' logged out",
                keywords="auth,logout"
            )
            
        # Clear cookies for persistence
        from frontend.common import clear_login_cookies
        clear_login_cookies()
            
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.rerun()
    
    st.divider()
    
    # Admin button to view all user dashboards
    if st.session_state.user_role == "admin":
        if st.button("View All User Dashboards", width="stretch", type="primary"):
            st.session_state.show_user_dashboards = True
            st.rerun()
    
    # Toggle buttons for regular users (not admin)
    if st.session_state.user_role != "admin":
        st.subheader("View Mode")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "My Performance",
                width="stretch",
                type="primary" if st.session_state.stats_view_mode == "individual" else "secondary"
            ):
                st.session_state.stats_view_mode = "individual"
                st.rerun()
        
        with col2:
            if st.button(
                " Safelife Performance",
                width="stretch",
                type="primary" if st.session_state.stats_view_mode == "cumulative" else "secondary"
            ):
                st.session_state.stats_view_mode = "cumulative"
                st.rerun()
        
        st.divider()
    
    # Determine which stats to show based on role and view mode
    show_cumulative = (st.session_state.user_role == "admin" or 
                      (st.session_state.user_role != "admin" and st.session_state.stats_view_mode == "cumulative"))
    
    # Global chart config for clean UI: remove all buttons except Camera (toImage)
    chart_config = {
        'displayModeBar': True, # Show bar on hover for the camera button
        'displaylogo': False,
        'modeBarButtonsToRemove': [
            'zoom', 'zoom2d', 'pan', 'pan2d', 
            'select', 'select2d', 
            'lasso', 'lasso2d', 
            'zoomIn', 'zoomIn2d', 'zoomOut', 'zoomOut2d', 
            'autoScale', 'autoScale2d', 
            'resetScale', 'resetScale2d',
            'hoverClosestCartesian', 'hoverCompareCartesian',
            'toggleSpikelines'
        ]
    }

    # Role-based statistics
    if show_cumulative:
        st.subheader("All Users Statistics" if st.session_state.user_role == "admin" else "Cumulative Statistics (All Users)")
        stats = services_stats.get_basic_counts(db)
        active_leads = db.query(crud_leads.models.Lead).filter(crud_leads.models.Lead.active_client == True).count()
    else:
        st.subheader(f"Your Statistics ({st.session_state.username})")
        stats = services_stats.get_user_stats(db, st.session_state.username)
        active_leads = stats.get("active_clients", 0)
        # Add total_users for consistency
        stats["total_users"] = "N/A"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats['total_leads']}</div>
            <div class="stat-label">{'Total Leads' if show_cumulative else 'Your Leads'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if show_cumulative:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats['total_users']}</div>
                <div class="stat-label">Total Users</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{active_leads}</div>
                <div class="stat-label">Your Referrals</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{active_leads}</div>
            <div class="stat-label">Referrals</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Charts - Show all graphs for both views
    col1, col2 = st.columns(2)

    if show_cumulative:
        # Show all staff data (cumulative view)
        with col1:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Leads by Staff</h4>", unsafe_allow_html=True)
            staff_data = services_stats.leads_by_staff(db)
            if staff_data:
                df_staff = pd.DataFrame(staff_data)
                fig_staff = px.bar(df_staff, x='staff_name', y='count', 
                                 category_orders={'staff_name': df_staff['staff_name'].tolist()},
                                 color_discrete_sequence=['#00506b'])
                # Style modebar: white bg, aqua icons
                fig_staff.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_staff = st.plotly_chart(fig_staff, width="stretch", on_select="rerun", selection_mode="points", key="staff_chart", config=chart_config)
                
                if event_staff.selection and event_staff.selection['points']:
                    selected_staff = event_staff.selection['points'][0]['x']
                    # Filter global leads
                    if not df_all_leads.empty:
                        drill = df_all_leads[df_all_leads['staff_name'] == selected_staff]
                        show_drill_down(drill, f"Staff: {selected_staff}")
            else:
                st.info("No data available")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Leads by Source</h4>", unsafe_allow_html=True)
            source_data = services_stats.leads_by_source(db)
            if source_data:
                df_source = pd.DataFrame(source_data)
                fig_source = px.bar(df_source, x='source', y='count', color_discrete_sequence=['#00506b'])
                fig_source.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_source = st.plotly_chart(fig_source, width="stretch", on_select="rerun", selection_mode="points", key="source_chart_cum", config=chart_config)
                
                if event_source.selection and event_source.selection['points']:
                    selected_source = event_source.selection['points'][0]['x']
                    # Filter global leads
                    if not df_all_leads.empty:
                        drill = df_all_leads[df_all_leads['source'] == selected_source]
                        show_drill_down(drill, f"Source: {selected_source}")
            else:
                st.info("No data available")
    else:
        # Regular user sees their own comprehensive data
        with col1:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Your Monthly Leads</h4>", unsafe_allow_html=True)
            monthly_data = services_stats.leads_by_month_for_user(db, st.session_state.username)
            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data)
                fig_monthly = px.line(df_monthly, x='month', y='count', markers=True, color_discrete_sequence=['#00506b'])
                fig_monthly.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_monthly = st.plotly_chart(fig_monthly, width="stretch", on_select="rerun", selection_mode="points", key="monthly_chart_ind", config=chart_config)
                
                if event_monthly.selection and event_monthly.selection['points']:
                    selected_month = event_monthly.selection['points'][0]['x']
                    # Filter: Match month string
                    if not df_all_leads.empty:
                        # Ensure created_at is datetime
                        df_all_leads['month_str'] = pd.to_datetime(df_all_leads['created_at']).dt.strftime('%Y-%m')
                        drill = df_all_leads[
                            (df_all_leads['month_str'] == selected_month) & 
                            (df_all_leads['staff_name'] == st.session_state.username)
                        ]
                        show_drill_down(drill, f"Month: {selected_month}")
            else:
                st.info("No leads yet")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Your Leads by Source</h4>", unsafe_allow_html=True)
            source_data = services_stats.leads_by_source_for_user(db, st.session_state.username)
            if source_data:
                df_source = pd.DataFrame(source_data)
                fig_source_ind = px.bar(df_source, x='source', y='count', color_discrete_sequence=['#00506b'])
                fig_source_ind.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_source_ind = st.plotly_chart(fig_source_ind, width="stretch", on_select="rerun", selection_mode="points", key="source_chart_ind", config=chart_config)

                if event_source_ind.selection and event_source_ind.selection['points']:
                    selected_source = event_source_ind.selection['points'][0]['x']
                    if not df_all_leads.empty:
                        drill = df_all_leads[
                            (df_all_leads['source'] == selected_source) & 
                            (df_all_leads['staff_name'] == st.session_state.username)
                        ]
                        show_drill_down(drill, f"Source: {selected_source}")
            else:
                st.info("No leads yet")

    # Additional graphs for all users
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Leads by Status</h4>", unsafe_allow_html=True)
        try:
            if show_cumulative:
                status_data = services_stats.leads_by_status(db)
            else:
                # For users in individual view, filter status by their leads
                results = (
                    db.query(crud_leads.models.Lead.last_contact_status, func.count(crud_leads.models.Lead.id))
                    .filter(crud_leads.models.Lead.staff_name == st.session_state.username)
                    .group_by(crud_leads.models.Lead.last_contact_status)
                    .all()
                )
                status_data = [{"status": r[0], "count": r[1]} for r in results]

            if status_data:
                df_status = pd.DataFrame(status_data)
                fig_status = px.bar(df_status, x='status', y='count', color_discrete_sequence=['#00506b'])
                fig_status.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_status = st.plotly_chart(fig_status, width="stretch", on_select="rerun", selection_mode="points", key="status_chart", config=chart_config)
                
                if event_status.selection and event_status.selection['points']:
                    selected_status = event_status.selection['points'][0]['x']
                    if not df_all_leads.empty:
                        if show_cumulative:
                            drill = df_all_leads[df_all_leads['last_contact_status'] == selected_status]
                        else:
                            drill = df_all_leads[
                                (df_all_leads['last_contact_status'] == selected_status) &
                                (df_all_leads['staff_name'] == st.session_state.username)
                            ]
                        show_drill_down(drill, f"Status: {selected_status}")
            else:
                st.info("No data available")
        except Exception as e:
            st.error(f"Error loading status data: {str(e)}")

    with col2:
        if show_cumulative:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Monthly Leads (All)</h4>", unsafe_allow_html=True)
            monthly_data = services_stats.monthly_leads(db)
        else:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Your Monthly Trend</h4>", unsafe_allow_html=True)
            monthly_data = services_stats.leads_by_month_for_user(db, st.session_state.username)

        if monthly_data:
            df_monthly = pd.DataFrame(monthly_data)
            fig_monthly_trend = px.line(df_monthly, x='month', y='count', markers=True, color_discrete_sequence=['#00506b'])
            fig_monthly_trend.update_layout(
                clickmode='event+select',
                modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
            )
            
            event_monthly_trend = st.plotly_chart(fig_monthly_trend, width="stretch", on_select="rerun", selection_mode="points", key="monthly_chart_trend", config=chart_config)
            
            if event_monthly_trend.selection and event_monthly_trend.selection['points']:
                selected_month = event_monthly_trend.selection['points'][0]['x']
                if not df_all_leads.empty:
                    df_all_leads['month_str'] = pd.to_datetime(df_all_leads['created_at']).dt.strftime('%Y-%m')
                    if show_cumulative:
                        drill = df_all_leads[df_all_leads['month_str'] == selected_month]
                    else:
                        drill = df_all_leads[
                            (df_all_leads['month_str'] == selected_month) &
                            (df_all_leads['staff_name'] == st.session_state.username)
                        ]
                    show_drill_down(drill, f"Month: {selected_month}")
        else:
            st.info("No data available")

    # Additional comprehensive graphs
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Event Leads</h4>", unsafe_allow_html=True)
        if show_cumulative:
            event_data = services_stats.leads_by_event(db)
        else:
            # Filter events by user
            results = (
                db.query(crud_leads.models.Lead.event_name, func.count(crud_leads.models.Lead.id))
                .filter(crud_leads.models.Lead.staff_name == st.session_state.username)
                .filter(crud_leads.models.Lead.event_name.isnot(None))
                .group_by(crud_leads.models.Lead.event_name)
                .all()
            )
            event_data = [{"event_name": r[0], "count": r[1]} for r in results]

        if event_data:
            df_events = pd.DataFrame(event_data)
            fig_event = px.bar(df_events, x='event_name', y='count', color_discrete_sequence=['#00506b'])
            fig_event.update_layout(
                clickmode='event+select',
                modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
            )
            
            event_chart = st.plotly_chart(fig_event, width="stretch", on_select="rerun", selection_mode="points", key="event_chart", config=chart_config)
            
            if event_chart.selection and event_chart.selection['points']:
                selected_event = event_chart.selection['points'][0]['x']
                if not df_all_leads.empty:
                    if show_cumulative:
                        drill = df_all_leads[df_all_leads['event_name'] == selected_event]
                    else:
                        drill = df_all_leads[
                            (df_all_leads['event_name'] == selected_event) &
                            (df_all_leads['staff_name'] == st.session_state.username)
                        ]
                    show_drill_down(drill, f"Event: {selected_event}")
        else:
            st.info("No event leads yet")

    with col2:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Word of Mouth Breakdown</h4>", unsafe_allow_html=True)
        if show_cumulative:
            wom_data = services_stats.word_of_mouth_breakdown(db)
        else:
            # Filter word of mouth by user
            results = (
                db.query(crud_leads.models.Lead.word_of_mouth_type, func.count(crud_leads.models.Lead.id))
                .filter(crud_leads.models.Lead.staff_name == st.session_state.username)
                .filter(crud_leads.models.Lead.word_of_mouth_type.isnot(None))
                .group_by(crud_leads.models.Lead.word_of_mouth_type)
                .all()
            )
            wom_data = [{"type": r[0], "count": r[1]} for r in results]

        if wom_data:
            df_wom = pd.DataFrame(wom_data)
            fig_wom = px.bar(df_wom, x='type', y='count', color_discrete_sequence=['#00506b'])
            fig_wom.update_layout(
                clickmode='event+select',
                modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
            )
            
            event_wom = st.plotly_chart(fig_wom, width="stretch", on_select="rerun", selection_mode="points", key="wom_chart", config=chart_config)
            
            if event_wom.selection and event_wom.selection['points']:
                selected_type = event_wom.selection['points'][0]['x']
                if not df_all_leads.empty:
                    if show_cumulative:
                        drill = df_all_leads[df_all_leads['word_of_mouth_type'] == selected_type]
                    else:
                        drill = df_all_leads[
                            (df_all_leads['word_of_mouth_type'] == selected_type) &
                            (df_all_leads['staff_name'] == st.session_state.username)
                        ]
                    show_drill_down(drill, f"WOM Type: {selected_type}")
        else:
            st.info("No word of mouth leads yet")

    # Comprehensive Referral Dashboard for Users
    if not show_cumulative and active_leads > 0:
        st.divider()
        st.markdown("## **YOUR REFERRALS DASHBOARD**")

        # Referral Statistics Row
        col1, col2, col3, col4 = st.columns(4)

        # Get referral stats
        authorized_count = db.query(crud_leads.models.Lead).filter(
            crud_leads.models.Lead.staff_name == st.session_state.username,
            crud_leads.models.Lead.active_client == True,
            crud_leads.models.Lead.authorization_received == True
        ).count()

        care_started_count = db.query(crud_leads.models.Lead).filter(
            crud_leads.models.Lead.staff_name == st.session_state.username,
            crud_leads.models.Lead.active_client == True,
            crud_leads.models.Lead.care_status == "Care Start"
        ).count()

        pending_auth_count = db.query(crud_leads.models.Lead).filter(
            crud_leads.models.Lead.staff_name == st.session_state.username,
            crud_leads.models.Lead.active_client == True,
            crud_leads.models.Lead.authorization_received == False
        ).count()

        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{active_leads}</div>
                <div class="stat-label">Total Referrals</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{authorized_count}</div>
                <div class="stat-label">Authorized</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{care_started_count}</div>
                <div class="stat-label">Care Started</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{pending_auth_count}</div>
                <div class="stat-label">Pending Auth</div>
            </div>
            """, unsafe_allow_html=True)

        # Referral Charts
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Your Referral Trend</h4>", unsafe_allow_html=True)
            referral_monthly = services_stats.referrals_by_month_for_user(db, st.session_state.username)
            if referral_monthly:
                df_ref_monthly = pd.DataFrame(referral_monthly)
                fig_ref_monthly = px.line(df_ref_monthly, x='month', y='count', markers=True, color_discrete_sequence=['#00506b'])
                fig_ref_monthly.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_ref_monthly = st.plotly_chart(fig_ref_monthly, width="stretch", on_select="rerun", selection_mode="points", key="ref_monthly_chart", config=chart_config)
                
                if event_ref_monthly.selection and event_ref_monthly.selection['points']:
                    selected_month = event_ref_monthly.selection['points'][0]['x']
                    if not df_all_leads.empty:
                        drill = df_all_leads[
                            (df_all_leads['month_str'] == selected_month) &
                            (df_all_leads['staff_name'] == st.session_state.username) &
                            (df_all_leads['active_client'] == True)
                        ]
                        show_drill_down(drill, f"Referral Trend: {selected_month}")
            else:
                st.info("No referrals yet")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Referral Status</h4>", unsafe_allow_html=True)
            ref_status_data = services_stats.referrals_by_status_for_user(db, st.session_state.username)
            if ref_status_data:
                df_ref_status = pd.DataFrame(ref_status_data)
                fig_ref_status = px.bar(df_ref_status, x='status', y='count', color_discrete_sequence=['#00506b'])
                fig_ref_status.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_ref_status = st.plotly_chart(fig_ref_status, width="stretch", on_select="rerun", selection_mode="points", key="ref_status_chart", config=chart_config)
                
                if event_ref_status.selection and event_ref_status.selection['points']:
                    selected_status = event_ref_status.selection['points'][0]['x']
                    if not df_all_leads.empty:
                        drill = df_all_leads[
                            (df_all_leads['last_contact_status'] == selected_status) &
                            (df_all_leads['staff_name'] == st.session_state.username) &
                            (df_all_leads['active_client'] == True)
                        ]
                        show_drill_down(drill, f"Referral Status: {selected_status}")
            else:
                st.info("No referral status data")

        # More Referral Charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("**Authorization Status**")
            auth_data = services_stats.referrals_by_authorization_for_user(db, st.session_state.username)
            if auth_data:
                df_auth = pd.DataFrame(auth_data)
                fig_auth = px.bar(df_auth, x='authorized', y='count', color_discrete_sequence=['#00506b'])
                fig_auth.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_auth = st.plotly_chart(fig_auth, width="stretch", on_select="rerun", selection_mode="points", key="auth_chart", config=chart_config)
                
                if event_auth.selection and event_auth.selection['points']:
                    # Labels: 'Authorized', 'Pending'
                    selected_auth_label = event_auth.selection['points'][0]['x']
                    is_authorized = (selected_auth_label == "Authorized")
                    
                    if not df_all_leads.empty:
                        drill = df_all_leads[
                            (df_all_leads['authorization_received'] == is_authorized) &
                            (df_all_leads['staff_name'] == st.session_state.username) &
                            (df_all_leads['active_client'] == True)
                        ]
                        show_drill_down(drill, f"Auth Status: {selected_auth_label}")
            else:
                st.info("No authorization data")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Care Status</h4>", unsafe_allow_html=True)
            care_data = services_stats.referrals_by_care_status_for_user(db, st.session_state.username)
            if care_data:
                df_care = pd.DataFrame(care_data)
                fig_care = px.bar(df_care, x='care_status', y='count', color_discrete_sequence=['#00506b'])
                fig_care.update_layout(
                    clickmode='event+select',
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                )
                
                event_care = st.plotly_chart(fig_care, width="stretch", on_select="rerun", selection_mode="points", key="care_chart", config=chart_config)
                
                if event_care.selection and event_care.selection['points']:
                    selected_care = event_care.selection['points'][0]['x']
                    if not df_all_leads.empty:
                        drill = df_all_leads[
                            (df_all_leads['care_status'] == selected_care) &
                            (df_all_leads['staff_name'] == st.session_state.username) &
                            (df_all_leads['active_client'] == True)
                        ]
                        show_drill_down(drill, f"Care Status: {selected_care}")
            else:
                st.info("No care status data")

    # Referral-specific graphs
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Referral Status</h4>", unsafe_allow_html=True)
        if show_cumulative:
            # Show all referrals by status
            referral_status_data = services_stats.referral_status_breakdown(db)
        else:
            # Show user's referrals by status
            results = (
                db.query(crud_leads.models.Lead.last_contact_status, func.count(crud_leads.models.Lead.id))
                .filter(crud_leads.models.Lead.staff_name == st.session_state.username)
                .filter(crud_leads.models.Lead.active_client == True)
                .group_by(crud_leads.models.Lead.last_contact_status)
                .all()
            )
            referral_status_data = [{"status": r[0], "count": r[1]} for r in results]

        if referral_status_data:
            df_ref_status = pd.DataFrame(referral_status_data)
            fig_ref_status_shared = px.bar(df_ref_status, x='status', y='count', color_discrete_sequence=['#00506b'])
            fig_ref_status_shared.update_layout(
                clickmode='event+select',
                modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
            )
            
            event_ref_status_shared = st.plotly_chart(fig_ref_status_shared, width="stretch", on_select="rerun", selection_mode="points", key="ref_status_shared_chart", config=chart_config)
            
            if event_ref_status_shared.selection and event_ref_status_shared.selection['points']:
                selected_status = event_ref_status_shared.selection['points'][0]['x']
                if not df_all_leads.empty:
                    base_df = df_all_leads.copy()
                    base_df = base_df[base_df['active_client'].astype(bool) == True]
                    if not show_cumulative:
                        base_df = base_df[base_df['staff_name'] == st.session_state.username]
                    
                    drill = base_df[base_df['last_contact_status'] == selected_status]
                    show_drill_down(drill, f"Referral Status: {selected_status}")
        else:
            st.info("No referral data yet")

    with col2:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Authorization Status</h4>", unsafe_allow_html=True)
        if show_cumulative:
            # Show authorization status for all referrals
            auth_results = (
                db.query(crud_leads.models.Lead.authorization_received, func.count(crud_leads.models.Lead.id))
                .filter(crud_leads.models.Lead.active_client == True)
                .group_by(crud_leads.models.Lead.authorization_received)
                .all()
            )
        else:
            # Show authorization status for user's referrals
            auth_results = (
                db.query(crud_leads.models.Lead.authorization_received, func.count(crud_leads.models.Lead.id))
                .filter(crud_leads.models.Lead.staff_name == st.session_state.username)
                .filter(crud_leads.models.Lead.active_client == True)
                .group_by(crud_leads.models.Lead.authorization_received)
                .all()
            )

        auth_data = []
        for auth_status, count in auth_results:
            status_name = "Authorized" if auth_status else "Pending Authorization"
            auth_data.append({"status": status_name, "count": count})

        if auth_data:
            df_auth = pd.DataFrame(auth_data)
            fig_auth_shared = px.bar(df_auth, x='status', y='count', color_discrete_sequence=['#00506b'])
            fig_auth_shared.update_layout(
                clickmode='event+select',
                modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
            )
            
            event_auth_shared = st.plotly_chart(fig_auth_shared, width="stretch", on_select="rerun", selection_mode="points", key="auth_shared_chart", config=chart_config)
            
            if event_auth_shared.selection and event_auth_shared.selection['points']:
                selected_status = event_auth_shared.selection['points'][0]['x']
                is_authorized = (selected_status == "Authorized")
                
                if not df_all_leads.empty:
                    base_df = df_all_leads.copy()
                    # First filter for referrals only
                    base_df = base_df[base_df['active_client'].astype(bool) == True]
                    if not show_cumulative:
                        base_df = base_df[base_df['staff_name'] == st.session_state.username]
                    
                    # Filter by authorization status
                    drill = base_df[base_df['authorization_received'].astype(bool) == is_authorized]
                    show_drill_down(drill, f"Auth Status: {selected_status}")
        else:
            st.info("No referral data yet")

    # End of user referral dashboard conditional block

    st.divider()

    # Lead Confirmation & Conversion Pie Charts
    st.markdown("""
    <div style="background: linear-gradient(90deg, #00506b 0%, #3CA5AA 100%); 
                padding: 20px; 
                border-radius: 15px; 
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);">
        <h2 style="text-align: center; color: #FFFFFF; margin-bottom: 5px; letter-spacing:0.08em; text-transform:uppercase; font-weight: 800;">
                    Lead Pipeline Analytics
        </h2>
        <p style="text-align: center; color: #E5E7EB; font-size: 14px; font-weight: 500;">
            Track lead progression through your pipeline
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # Get lead data for charts
    # Reuse leads loaded at top of function
    all_leads = all_leads_list

    if show_cumulative:
        leads_for_chart = all_leads
    else:
        leads_for_chart = [l for l in all_leads if l.staff_name == st.session_state.username]

    total_leads = len(leads_for_chart)
    referrals = len([l for l in leads_for_chart if l.active_client == True])
    not_referrals = total_leads - referrals

    # For pie chart, always use all leads for consistent view
    all_total_leads = len(all_leads)
    all_referrals = len([l for l in all_leads if l.active_client == True])
    all_not_referrals = all_total_leads - all_referrals
    
    care_start = len([l for l in leads_for_chart if l.care_status == "Care Start"])
    not_start = len([l for l in leads_for_chart if l.care_status == "Not Start"])
    pending = total_leads - care_start - not_start
    
    # 1. Lead Confirmation (Donut Chart)
    with col1:
        st.markdown("""
            <div style="background-color: #FFFFFF; 
                    padding: 15px; 
                    border-radius: 12px;
                    border: 1px solid #E5E7EB;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);">
            <h3 style="color: #00506b !important; text-align: center; margin-bottom: 10px; font-weight: bold;">
                Lead Confirmation
            </h3>
            <p style="color: #6B7280; text-align: center; font-size: 12px;">
                Leads marked as referral
            </p>
            </div>
        """, unsafe_allow_html=True)
        
        import plotly.graph_objects as go

        if total_leads > 0:
            try:
                fig_confirm = go.Figure(data=[go.Pie(
                    labels=['Referrals', 'Pending'],
                    values=[all_referrals, all_not_referrals],
                    hole=0.4,
                    sort=False, # Maintain order for reliable click matching
                    marker_colors=['#00506b', '#B5E8F7'],  # Deep Blue and Light Blue
                    textinfo='label+percent',
                    textfont=dict(size=14, color=['#FFFFFF', '#000000']), # White on dark blue, black on light blue
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>"
                )])
                
                if not df_all_leads.empty:
                    df_all_leads['month_str'] = pd.to_datetime(df_all_leads['created_at']).dt.strftime('%Y-%m')

                fig_confirm.update_layout(
                    showlegend=True,
                    clickmode='event+select',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=12)
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=60, l=20, r=20),
                    height=350,
                    modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA'),
                    annotations=[dict(
                        text=f'<b>{all_referrals}</b><br>Referrals',
                        x=0.5, y=0.5,
                        font_size=18,
                        font_family='Montserrat',
                        showarrow=False
                    )]
                )
                
                
                st.plotly_chart(fig_confirm, width="stretch", key="confirm_chart", config=chart_config)
                
                # Drill-down buttons
                st.markdown("**Drill Down:**")
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("📊 View Referrals", key="btn_referrals", width="stretch"):
                        # Toggle: if already showing referrals, hide it; otherwise show it
                        if st.session_state.get('drill_down_active') == 'referrals':
                            st.session_state['drill_down_active'] = None
                        else:
                            st.session_state['drill_down_active'] = 'referrals'
                        st.rerun()
                
                with col_btn2:
                    if st.button("📊 View Pending", key="btn_pending", width="stretch"):
                        # Toggle: if already showing pending, hide it; otherwise show it
                        if st.session_state.get('drill_down_active') == 'pending':
                            st.session_state['drill_down_active'] = None
                        else:
                            st.session_state['drill_down_active'] = 'pending'
                        st.rerun()
                
                # Show drill-down based on session state
                if st.session_state.get('drill_down_active') == 'referrals':
                    if not df_all_leads.empty:
                        base_df = df_all_leads.copy()
                        if not show_cumulative:
                            base_df = base_df[base_df['staff_name'] == st.session_state.username]
                        drill = base_df[base_df['active_client'].astype(bool) == True]
                        show_drill_down(drill, "Confirmation: Referrals")
                elif st.session_state.get('drill_down_active') == 'pending':
                    if not df_all_leads.empty:
                        base_df = df_all_leads.copy()
                        if not show_cumulative:
                            base_df = base_df[base_df['staff_name'] == st.session_state.username]
                        drill = base_df[base_df['active_client'].astype(bool) == False]
                        show_drill_down(drill, "Confirmation: Pending")

            except Exception as e:
                st.error(f"Error creating pie chart: {e}")
        else:
            st.info("No leads to display in pie chart")
            
            # Stats below chart
            st.markdown(f"""
            <div style="display: flex; justify-content: space-around; margin-top: 10px;">
                <div style="text-align: center;">
                    <span style="color: #00d4ff; font-size: 24px; font-weight: bold;">{all_referrals}</span>
                    <br><span style="color: #4B5563; font-size: 12px; font-weight: 500;">Referrals</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #ff6b6b; font-size: 24px; font-weight: bold;">{all_not_referrals}</span>
                    <br><span style="color: #4B5563; font-size: 12px; font-weight: 500;">Pending</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #64748b; font-size: 24px; font-weight: bold;">{all_total_leads}</span>
                    <br><span style="color: #4B5563; font-size: 12px; font-weight: 500;">Total Leads</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #FFFFFF; 
                    padding: 15px; 
                    border-radius: 12px;
                    border: 1px solid #3CA5AA;
                    box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06);">
            <h3 style="color: #00506b; text-align: center; margin-bottom: 10px;">
                 Lead Conversion
            </h3>
                <p style="color: #6B7280; text-align: center; font-size: 12px;">
                Leads converted to care
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if total_leads > 0:
            fig_convert = go.Figure(data=[go.Pie(
                labels=['Care Start', 'Not Start', 'Pending'],
                values=[care_start, not_start, pending],
                hole=0.4,
                sort=False, # Important: keep order consistent for click logic
                marker_colors=['#00506b', '#3CA5AA', '#E5E7EB'],
                textinfo='label+percent', # Maintained for hover context, but texttemplate takes precedence
                texttemplate='%{label}<br>%{percent}', # Force label and percent
                textposition='auto',
                # Labels: ['Care Start', 'Not Start', 'Pending']
                # Colors: [Deep Blue (White Text), Teal (Deep Blue Text), Gray (Teal Text)]
                textfont=dict(size=14, color=['#FFFFFF', '#00506b', '#3CA5AA']), 
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>"
            )])
            
            fig_convert.update_layout(
                showlegend=True,
                clickmode='event+select',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=12)
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=60, l=20, r=20),
                height=350,
                modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA'),
                annotations=[dict(
                    text=f'<b>{care_start}</b><br>Active',
                    x=0.5, y=0.5,
                    font_size=16,
                    showarrow=False
                )]
            )
            
            
            st.plotly_chart(fig_convert, width="stretch", key="convert_chart", config=chart_config)
            
            # Drill-down buttons
            st.markdown("**Drill Down:**")
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("📊 Care Start", key="btn_care_start", width="stretch"):
                    if st.session_state.get('drill_down_conv') == 'care_start':
                        st.session_state['drill_down_conv'] = None
                    else:
                        st.session_state['drill_down_conv'] = 'care_start'
                    st.rerun()
            
            with col_btn2:
                if st.button("📊 Not Start", key="btn_not_start", width="stretch"):
                    if st.session_state.get('drill_down_conv') == 'not_start':
                        st.session_state['drill_down_conv'] = None
                    else:
                        st.session_state['drill_down_conv'] = 'not_start'
                    st.rerun()
            
            with col_btn3:
                if st.button("📊 Pending", key="btn_conv_pending", width="stretch"):
                    if st.session_state.get('drill_down_conv') == 'conv_pending':
                        st.session_state['drill_down_conv'] = None
                    else:
                        st.session_state['drill_down_conv'] = 'conv_pending'
                    st.rerun()
            
            # Show drill-down based on session state
            if st.session_state.get('drill_down_conv') == 'care_start':
                if not df_all_leads.empty:
                    base_df = df_all_leads.copy()
                    if not show_cumulative:
                        base_df = base_df[base_df['staff_name'] == st.session_state.username]
                    if 'care_status' in base_df.columns:
                        base_df['care_status'] = base_df['care_status'].astype(str)
                    drill = base_df[base_df['care_status'] == "Care Start"]
                    show_drill_down(drill, "Conversion: Care Start")
            elif st.session_state.get('drill_down_conv') == 'not_start':
                if not df_all_leads.empty:
                    base_df = df_all_leads.copy()
                    if not show_cumulative:
                        base_df = base_df[base_df['staff_name'] == st.session_state.username]
                    if 'care_status' in base_df.columns:
                        base_df['care_status'] = base_df['care_status'].astype(str)
                    drill = base_df[base_df['care_status'] == "Not Start"]
                    show_drill_down(drill, "Conversion: Not Start")
            elif st.session_state.get('drill_down_conv') == 'conv_pending':
                if not df_all_leads.empty:
                    base_df = df_all_leads.copy()
                    if not show_cumulative:
                        base_df = base_df[base_df['staff_name'] == st.session_state.username]
                    if 'care_status' in base_df.columns:
                        base_df['care_status'] = base_df['care_status'].astype(str)
                    drill = base_df[~base_df['care_status'].isin(["Care Start", "Not Start"])]
                    show_drill_down(drill, "Conversion: Pending")

            
            # Stats below chart
            st.markdown(f"""
            <div style="display: flex; justify-content: space-around; margin-top: 10px;">
                <div style="text-align: center;">
                    <span style="color: #00506b; font-size: 24px; font-weight: bold;">{care_start}</span>
                    <br><span style="color: #4B5563; font-size: 12px; font-weight: 500;">Care Start</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #3CA5AA; font-size: 24px; font-weight: bold;">{not_start}</span>
                    <br><span style="color: #4B5563; font-size: 12px; font-weight: 500;">Not Start</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #64748b; font-size: 24px; font-weight: bold;">{pending}</span>
                    <br><span style="color: #4B5563; font-size: 12px; font-weight: 500;">Pending</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No leads to display")
    
    # Conversion Rate Summary
    if total_leads > 0:
        confirmation_rate = (referrals / total_leads) * 100 if total_leads > 0 else 0
        conversion_rate = (care_start / referrals) * 100 if referrals > 0 else 0
        
        st.markdown(f"""
        <div style="background: #FFFFFF; 
                    padding: 20px; 
                    border-radius: 15px; 
                    margin-top: 20px;
                    border: 1px solid #E5E7EB;
                    box-shadow: 0 4px 10px rgba(15,23,42,0.04);">
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div style="flex: 1; padding: 15px; border-right: 1px solid #E5E7EB;">
                    <span style="color: #00506b; font-size: 32px; font-weight: bold;">{confirmation_rate:.1f}%</span>
                    <br><span style="color: #4B5563; font-size: 14px;">Confirmation Rate</span>
                    <br><span style="color: #6B7280; font-size: 11px;">Leads → Referrals</span>
                </div>
                <div style="flex: 1; padding: 15px;">
                    <span style="color: #3CA5AA; font-size: 32px; font-weight: bold;">{conversion_rate:.1f}%</span>
                    <br><span style="color: #4B5563; font-size: 14px;">Conversion Rate</span>
                    <br><span style="color: #6B7280; font-size: 11px;">Referrals → Care Start</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    db.close()

def discovery_tool():
    """Standalone page for custom lead exploratory analysis"""
    db = SessionLocal()
    
    # Load all leads once for drill-down and analysis
    all_leads_list = crud_leads.list_leads(db, limit=10000)
    df_all_leads = pd.DataFrame([l.__dict__ for l in all_leads_list])
    if not df_all_leads.empty and '_sa_instance_state' in df_all_leads.columns:
        df_all_leads = df_all_leads.drop('_sa_instance_state', axis=1)

    st.markdown('<div class="main-header">LEAD DISCOVERY TOOL</div>', unsafe_allow_html=True)
    
    st.info("💡 **Discover Hidden Patterns:** Select any two features to cross-reference and analyze your leads.")
    
    # Check for empty data
    if df_all_leads.empty:
        st.warning("No lead data available for analysis.")
        db.close()
        return

    # Role-based filtering
    is_admin = st.session_state.user_role == "admin"
    if not is_admin:
        analysis_df = df_all_leads[df_all_leads['staff_name'] == st.session_state.username].copy()
    else:
        analysis_df = df_all_leads.copy()

    if analysis_df.empty:
        st.info("You don't have any leads to analyze yet.")
        db.close()
        return

    # Global chart config
    chart_config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': [
            'zoom', 'zoom2d', 'pan', 'pan2d', 'select', 'select2d', 
            'lasso', 'lasso2d', 'zoomIn', 'zoomIn2d', 'zoomOut', 'zoomOut2d', 
            'autoScale', 'autoScale2d', 'resetScale', 'resetScale2d',
            'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'
        ]
    }

    # Load mappings for IDs to Names
    ccus = crud_ccus.get_all_ccus(db)
    mcos = crud_mcos.get_all_mcos(db)
    agencies = crud_agencies.get_all_agencies(db)
    
    ccu_map = {c.id: c.name for c in ccus}
    mco_map = {m.id: m.name for m in mcos}
    agency_map = {a.id: a.name for a in agencies}
    
    # Pre-calculate mapping columns to avoid issues with groupby
    analysis_df['ccu_name'] = analysis_df['ccu_id'].map(ccu_map).fillna("N/A")
    analysis_df['mco_name'] = analysis_df['mco_id'].map(mco_map).fillna("N/A")
    analysis_df['agency_name'] = analysis_df['agency_id'].map(agency_map).fillna("N/A")

    # Feature definitions
    feature_map = {
        "Lead Source": "source",
        "Staff Name": "staff_name",
        "Last Contact Status": "last_contact_status",
        "Priority": "priority",
        "Care Status": "care_status",
        "City": "city",
        "Zip Code": "zip_code",
        "Medicaid Status": "medicaid_status",
        "Referral Type": "referral_type",
        "Event Name": "event_name",
        "MCO": "mco_name",
        "CCU": "ccu_name",
        "Agency": "agency_name"
    }

    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        feature_x_label = st.selectbox("Split By (X-Axis):", options=list(feature_map.keys()), index=0, key="disc_feat_x")
    with col_ctrl2:
        feature_color_label = st.selectbox("Compare Against (Colors):", options=["None"] + list(feature_map.keys()), index=4, key="disc_feat_c")

    col_x = feature_map[feature_x_label]
    col_color = feature_map[feature_color_label] if feature_color_label != "None" else None

    # CRASH GUARD: If same column is selected, treat it as None grouping to avoid reset_index conflict
    if col_color and col_x == col_color:
        col_color = None
        st.warning(f"Note: Cannot group '{feature_x_label}' by itself. Showing total counts instead.")

    # Data Preparation
    plot_df = analysis_df.copy()
    plot_df[col_x] = plot_df[col_x].fillna("N/A").astype(str)
    
    if col_color:
        plot_df[col_color] = plot_df[col_color].fillna("N/A").astype(str)
        # Aggregation with group
        agg_data = plot_df.groupby([col_x, col_color]).size().reset_index(name='Lead Count')
        
        fig = px.bar(
            agg_data, 
            x=col_x, 
            y='Lead Count', 
            color=col_color,
            barmode='group',
            color_discrete_sequence=px.colors.qualitative.Prism,
            labels={col_x: feature_x_label, col_color: feature_color_label}
        )
    else:
        # Simple aggregation
        agg_data = plot_df.groupby(col_x).size().reset_index(name='Lead Count')
        
        fig = px.bar(
            agg_data, 
            x=col_x, 
            y='Lead Count',
            color_discrete_sequence=['#00506b'],
            labels={col_x: feature_x_label}
        )

        fig.update_layout(
            clickmode='event+select',
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
            margin=dict(t=20, b=80, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
        )

    selection = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points", key="discovery_chart_main", config=chart_config)

    # Drill Down Logic
    if selection.selection and selection.selection['points']:
        point = selection.selection['points'][0]
        val_x = str(point['x'])
        
        drill_df = plot_df[plot_df[col_x] == val_x]
        drill_title = f"{feature_x_label}: {val_x}"
        
        if col_color:
            try:
                # Get color value from the specific bar clicked
                curve_idx = point['curveNumber']
                val_color = fig.data[curve_idx].name
                drill_df = drill_df[drill_df[col_color] == val_color]
                drill_title += f" | {feature_color_label}: {val_color}"
            except:
                pass
        
        st.divider()
        show_drill_down(drill_df, drill_title)


def view_all_user_dashboards():
    """View dashboard statistics for all users"""
    st.markdown('<div class="main-header">ALL USER DASHBOARDS</div>', unsafe_allow_html=True)
    
    if st.button("← Back to Main Dashboard"):
        st.session_state.show_user_dashboards = False
        st.rerun()
    
    db = SessionLocal()
    
    # Get all approved users
    approved_users = crud_users.get_approved_users(db)
    
    # Get all leads for efficient filtering
    all_leads = crud_leads.list_leads(db, limit=10000)
    df_all_leads = pd.DataFrame([l.__dict__ for l in all_leads])
    if not df_all_leads.empty and '_sa_instance_state' in df_all_leads.columns:
        df_all_leads = df_all_leads.drop('_sa_instance_state', axis=1)

    if not approved_users:
        st.info("No users found")
        db.close()
        return
    
    st.write(f"**Total Users:** {len(approved_users)}")
    st.divider()
    
    # Chart config
    chart_config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': [
            'zoom', 'zoom2d', 'pan', 'pan2d', 'select', 'select2d', 
            'lasso', 'lasso2d', 'zoomIn', 'zoomIn2d', 'zoomOut', 'zoomOut2d', 
            'autoScale', 'autoScale2d', 'resetScale', 'resetScale2d',
            'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'
        ]
    }
    
    # Display dashboard for each user
    for user in approved_users:
        with st.expander(f"{user.username} ({user.role})", expanded=False):
            # Filter leads for this user
            user_leads = [l for l in all_leads if l.staff_name == user.username]
            
            # Stats values
            total_leads = len(user_leads)
            active_leads = len([l for l in user_leads if l.active_client])
            conversion_rate = (active_leads / total_leads * 100) if total_leads > 0 else 0
            
            # Display stats cards
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{total_leads}</div>
                    <div class="stat-label">Total Leads</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{active_leads}</div>
                    <div class="stat-label">Referrals</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number" style="color: #3CA5AA;">{conversion_rate:.1f}%</div>
                    <div class="stat-label">Conversion Rate</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            # --- PIE CHARTS FOR USER ---
            st.markdown("<h4 style='text-align: center; color: #00506b;'>Pipeline Performance</h4>", unsafe_allow_html=True)
            
            col_p1, col_p2 = st.columns(2)
            
            # Confirmation Pie Data
            referrals_count = active_leads
            not_referrals_count = total_leads - referrals_count
            
            # Conversion Pie Data
            care_start = len([l for l in user_leads if l.care_status == "Care Start"])
            not_start = len([l for l in user_leads if l.care_status == "Not Start"])
            pending = total_leads - care_start - not_start
            
            with col_p1:
                st.markdown("**Lead Confirmation**")
                if total_leads > 0:
                    fig_confirm = go.Figure(data=[go.Pie(
                        labels=['Referrals', 'Pending'],
                        values=[referrals_count, not_referrals_count],
                        hole=0.4,
                        sort=False,
                        marker_colors=['#00506b', '#B5E8F7'],
                        textinfo='label+percent',
                        textposition='auto',
                        textfont=dict(size=12, color=['#FFFFFF', '#000000']),
                        hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>"
                    )])
                    fig_confirm.update_layout(
                        showlegend=True,
                        margin=dict(t=0, b=0, l=0, r=0),
                        height=250,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        clickmode='event+select',
                        modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA'),
                        legend=dict(orientation="h", y=-0.1)
                    )
                    st.plotly_chart(fig_confirm, width="stretch", config=chart_config, key=f"pie_conf_{user.id}")
                    
                    # Drill-down buttons
                    st.markdown("**Drill Down:**")
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button("📊 Referrals", key=f"btn_ref_{user.id}", width="stretch"):
                            # Toggle drill-down
                            session_key = f'drill_admin_conf_{user.id}'
                            if st.session_state.get(session_key) == 'referrals':
                                st.session_state[session_key] = None
                            else:
                                st.session_state[session_key] = 'referrals'
                            st.rerun()
                    
                    with col_btn2:
                        if st.button("📊 Pending", key=f"btn_pend_{user.id}", width="stretch"):
                            # Toggle drill-down
                            session_key = f'drill_admin_conf_{user.id}'
                            if st.session_state.get(session_key) == 'pending':
                                st.session_state[session_key] = None
                            else:
                                st.session_state[session_key] = 'pending'
                            st.rerun()
                    
                    # Show drill-down based on session state
                    session_key = f'drill_admin_conf_{user.id}'
                    if st.session_state.get(session_key) == 'referrals':
                        user_leads_df = df_all_leads[df_all_leads['staff_name'] == user.username].copy() if not df_all_leads.empty else pd.DataFrame()
                        if not user_leads_df.empty:
                            drill = user_leads_df[user_leads_df['active_client'].astype(bool) == True]
                            show_drill_down(drill, f"{user.username} - Confirmation: Referrals")
                    elif st.session_state.get(session_key) == 'pending':
                        user_leads_df = df_all_leads[df_all_leads['staff_name'] == user.username].copy() if not df_all_leads.empty else pd.DataFrame()
                        if not user_leads_df.empty:
                            drill = user_leads_df[user_leads_df['active_client'].astype(bool) == False]
                            show_drill_down(drill, f"{user.username} - Confirmation: Pending")


                else:
                    st.caption("No data")

            with col_p2:
                st.markdown("**Lead Conversion**")
                if total_leads > 0:
                    fig_convert = go.Figure(data=[go.Pie(
                        labels=['Care Start', 'Not Start', 'Pending'],
                        values=[care_start, not_start, pending],
                        hole=0.4,
                        sort=False,
                        marker_colors=['#00506b', '#3CA5AA', '#E5E7EB'],
                        textinfo='label+percent',
                        texttemplate='%{label}<br>%{percent}',
                        textposition='auto',
                        textfont=dict(size=12, color=['#FFFFFF', '#00506b', '#3CA5AA']),
                        hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>"
                    )])
                    fig_convert.update_layout(
                        showlegend=True,
                        margin=dict(t=0, b=0, l=0, r=0),
                        height=250,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        clickmode='event+select',
                        modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA'),
                        legend=dict(orientation="h", y=-0.1)
                    )
                    st.plotly_chart(fig_convert, width="stretch", config=chart_config, key=f"pie_conv_{user.id}")
                    
                    # Drill-down buttons
                    st.markdown("**Drill Down:**")
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if st.button("📊 Care Start", key=f"btn_cs_{user.id}", width="stretch"):
                            session_key = f'drill_admin_conv_{user.id}'
                            if st.session_state.get(session_key) == 'care_start':
                                st.session_state[session_key] = None
                            else:
                                st.session_state[session_key] = 'care_start'
                            st.rerun()
                    
                    with col_btn2:
                        if st.button("📊 Not Start", key=f"btn_ns_{user.id}", width="stretch"):
                            session_key = f'drill_admin_conv_{user.id}'
                            if st.session_state.get(session_key) == 'not_start':
                                st.session_state[session_key] = None
                            else:
                                st.session_state[session_key] = 'not_start'
                            st.rerun()
                    
                    with col_btn3:
                        if st.button("📊 Pending", key=f"btn_cp_{user.id}", width="stretch"):
                            session_key = f'drill_admin_conv_{user.id}'
                            if st.session_state.get(session_key) == 'conv_pending':
                                st.session_state[session_key] = None
                            else:
                                st.session_state[session_key] = 'conv_pending'
                            st.rerun()
                    
                    # Show drill-down based on session state
                    session_key = f'drill_admin_conv_{user.id}'
                    if st.session_state.get(session_key) == 'care_start':
                        user_leads_df = df_all_leads[df_all_leads['staff_name'] == user.username].copy() if not df_all_leads.empty else pd.DataFrame()
                        if not user_leads_df.empty:
                            if 'care_status' in user_leads_df.columns:
                                user_leads_df['care_status'] = user_leads_df['care_status'].astype(str)
                            drill = user_leads_df[user_leads_df['care_status'] == "Care Start"]
                            show_drill_down(drill, f"{user.username} - Conversion: Care Start")
                    elif st.session_state.get(session_key) == 'not_start':
                        user_leads_df = df_all_leads[df_all_leads['staff_name'] == user.username].copy() if not df_all_leads.empty else pd.DataFrame()
                        if not user_leads_df.empty:
                            if 'care_status' in user_leads_df.columns:
                                user_leads_df['care_status'] = user_leads_df['care_status'].astype(str)
                            drill = user_leads_df[user_leads_df['care_status'] == "Not Start"]
                            show_drill_down(drill, f"{user.username} - Conversion: Not Start")
                    elif st.session_state.get(session_key) == 'conv_pending':
                        user_leads_df = df_all_leads[df_all_leads['staff_name'] == user.username].copy() if not df_all_leads.empty else pd.DataFrame()
                        if not user_leads_df.empty:
                            if 'care_status' in user_leads_df.columns:
                                user_leads_df['care_status'] = user_leads_df['care_status'].astype(str)
                            drill = user_leads_df[~user_leads_df['care_status'].isin(["Care Start", "Not Start"])]
                            show_drill_down(drill, f"{user.username} - Conversion: Pending")

                else:
                    st.caption("No data")

            st.divider()
            
            # --- OTHER CHARTS (Plotly) ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("<h5 style='color: #00506b;'>Monthly Leads</h5>", unsafe_allow_html=True)
                monthly_data = services_stats.leads_by_month_for_user(db, user.username)
                if monthly_data:
                    df_monthly = pd.DataFrame(monthly_data)
                    fig_monthly = px.line(df_monthly, x='month', y='count', markers=True, color_discrete_sequence=['#00506b'])
                    fig_monthly.update_layout(
                        clickmode='event+select',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=250,
                        margin=dict(t=10, b=10, l=10, r=10),
                        modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                    )
                    event_monthly = st.plotly_chart(fig_monthly, width="stretch", on_select="rerun", selection_mode="points", config=chart_config, key=f"line_{user.id}")
                    
                    if event_monthly.selection and event_monthly.selection['points']:
                        selected_month = event_monthly.selection['points'][0]['x']
                        user_leads_df = df_all_leads[df_all_leads['staff_name'] == user.username] if not df_all_leads.empty else pd.DataFrame()
                        if not user_leads_df.empty:
                            user_leads_df['month_str'] = pd.to_datetime(user_leads_df['created_at']).dt.strftime('%Y-%m')
                            drill = user_leads_df[user_leads_df['month_str'] == selected_month]
                            show_drill_down(drill, f"{user.username} - Month: {selected_month}")
                else:
                    st.caption("No leads yet")
            
            with col2:
                st.markdown("<h5 style='color: #00506b;'>Leads by Source</h5>", unsafe_allow_html=True)
                source_data = services_stats.leads_by_source_for_user(db, user.username)
                if source_data:
                    df_source = pd.DataFrame(source_data)
                    fig_source = px.bar(df_source, x='source', y='count', color_discrete_sequence=['#00506b'])
                    fig_source.update_layout(
                        clickmode='event+select',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        height=250,
                        margin=dict(t=10, b=10, l=10, r=10),
                        modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA')
                    )
                    event_source = st.plotly_chart(fig_source, width="stretch", on_select="rerun", selection_mode="points", config=chart_config, key=f"bar_src_{user.id}")
                    
                    if event_source.selection and event_source.selection['points']:
                        selected_source = event_source.selection['points'][0]['x']
                        user_leads_df = df_all_leads[df_all_leads['staff_name'] == user.username] if not df_all_leads.empty else pd.DataFrame()
                        if not user_leads_df.empty:
                            drill = user_leads_df[user_leads_df['source'] == selected_source]
                            show_drill_down(drill, f"{user.username} - Source: {selected_source}")
                else:
                    st.caption("No leads yet")
            
    db.close()
