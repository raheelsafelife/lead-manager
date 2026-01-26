"""
Dashboard page: Main dashboard view and user dashboards
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
from app.crud import crud_users, crud_leads, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus, crud_mcos
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email
# from frontend.common ... moved inside dashboard() to prevent hot-reload ImportError

import plotly.graph_objects as go
import plotly.express as px

# Helper to display drill down
def show_drill_down(filtered_df, title):
    if not filtered_df.empty:
        st.markdown(f"**Drill Down: {title} ({len(filtered_df)})**")
        display_cols = ['first_name', 'last_name', 'phone', 'source', 'last_contact_status', 'staff_name', 'created_at', 'ccu_name']
        cols = [c for c in display_cols if c in filtered_df.columns]
        st.dataframe(filtered_df[cols], width="stretch")
    else:
        st.info("No detailed records found.")

def dashboard():
    """Main dashboard view"""
    from frontend.common import prepare_lead_data_for_email, get_leads_cached, get_stats_cached, clear_leads_cache, render_download_csv
    db = SessionLocal()
    
    # Load all leads for drill-down mapping
    all_leads_list = crud_leads.list_leads(db, limit=10000)
    df_all_leads = pd.DataFrame([l.__dict__ for l in all_leads_list])
    
    # Pre-map CCU names
    ccus = crud_ccus.get_all_ccus(db)
    ccu_map = {c.id: c.name for c in ccus}
    
    if not df_all_leads.empty:
        if '_sa_instance_state' in df_all_leads.columns:
            df_all_leads = df_all_leads.drop('_sa_instance_state', axis=1)
        df_all_leads['ccu_name'] = df_all_leads['ccu_id'].map(ccu_map).fillna("N/A")
        df_all_leads['month_str'] = pd.to_datetime(df_all_leads['created_at']).dt.strftime('%Y-%m')

    st.markdown(f'<div class="main-header">PERFORMANCE METRICS DASHBOARD</div>', unsafe_allow_html=True)
    
    # Session Status Messages
    if 'success_msg' in st.session_state:
        msg = st.session_state.pop('success_msg'); st.toast(msg, icon="✅"); st.success(f"**{msg}**")
    if 'error_msg' in st.session_state:
        msg = st.session_state.pop('error_msg'); st.toast(msg, icon="❌"); st.error(f"**{msg}**")

    st.markdown(f"Welcome, **{st.session_state.username}**!")
    
    if st.button("Logout", key="logout"):
        from frontend.common import clear_session_token; clear_session_token()
        st.session_state.authenticated = False; st.rerun()
    
    st.divider()
    
    if st.session_state.user_role == "admin":
        if st.button("View All User Dashboards", width="stretch", type="primary"):
            st.session_state.show_user_dashboards = True; st.rerun()
    
    show_cumulative = (st.session_state.user_role == "admin" or (st.session_state.user_role != "admin" and st.session_state.stats_view_mode == "cumulative"))
    
    # UPDATED: Improved config for maximize/PNG export
    chart_config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d'], # Remove distracting selection tools
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'safelife_chart',
            'height': 800,
            'width': 1200,
            'scale': 2
        }
    }

    # --- TOP KPIS ---
    if show_cumulative:
        stats = get_stats_cached('get_basic_counts')
        active_cnt = db.query(crud_leads.models.Lead).filter(crud_leads.models.Lead.active_client == True).count()
    else:
        stats = get_stats_cached('get_user_stats', st.session_state.username)
        active_cnt = stats.get("active_clients", 0)
        stats["total_users"] = "N/A"
    
    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1: st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["total_leads"]}</div><div class="stat-label">{"Total Leads" if show_cumulative else "Your Leads"}</div></div>', unsafe_allow_html=True)
    with col_k2: st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["total_users"] if show_cumulative else active_cnt}</div><div class="stat-label">{"Total Users" if show_cumulative else "Your Referrals"}</div></div>', unsafe_allow_html=True)
    with col_k3: st.markdown(f'<div class="stat-card"><div class="stat-number">{active_cnt}</div><div class="stat-label">Referrals</div></div>', unsafe_allow_html=True)
    
    st.divider()

    # --- 1. TOP GRAPHS ---
    col_t1, col_t2 = st.columns(2)
    if show_cumulative:
        with col_t1:
            st.markdown("<h4 style='font-weight: bold; color: #111827;'>Leads by Staff</h4>", unsafe_allow_html=True)
            staff_data = get_stats_cached('leads_by_staff')
            if staff_data:
                df = pd.DataFrame(staff_data)
                fig = px.bar(df, x='staff_name', y='count', color_discrete_sequence=['#00506b'])
                fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
                event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="staff_cum_chart", config=chart_config)
                render_download_csv(df_all_leads, "staff_leads_all.csv")
                if event.selection and event.selection['points']:
                    sel = event.selection['points'][0]['x']
                    show_drill_down(df_all_leads[df_all_leads['staff_name'] == sel], f"Staff: {sel}")
        with col_t2:
            st.markdown("<h4 style='font-weight: bold; color: #111827;'>Leads by Source</h4>", unsafe_allow_html=True)
            source_data = get_stats_cached('leads_by_source')
            if source_data:
                df = pd.DataFrame(source_data)
                fig = px.bar(df, x='source', y='count', color_discrete_sequence=['#00506b'])
                fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
                event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="source_cum_chart", config=chart_config)
                render_download_csv(df_all_leads, "source_leads_all.csv")
                if event.selection and event.selection['points']:
                    sel = event.selection['points'][0]['x']
                    show_drill_down(df_all_leads[df_all_leads['source'] == sel], f"Source: {sel}")
    else:
        # INDIVIDUAL TOP GRAPHS
        user_leads = df_all_leads[df_all_leads['staff_name'] == st.session_state.username] if not df_all_leads.empty else pd.DataFrame()
        with col_t1:
            st.markdown("<h4 style='font-weight: bold; color: #111827;'>Your Monthly Lead Flow</h4>", unsafe_allow_html=True)
            m_data = get_stats_cached('leads_by_month_for_user', st.session_state.username)
            if m_data:
                df = pd.DataFrame(m_data)
                fig = px.line(df, x='month', y='count', markers=True, color_discrete_sequence=['#00506b'])
                fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True, key="ind_month", config=chart_config)
                render_download_csv(user_leads, "your_monthly_leads.csv")
        with col_t2:
            st.markdown("<h4 style='font-weight: bold; color: #111827;'>Your Content Sources</h4>", unsafe_allow_html=True)
            if not user_leads.empty:
                s_counts = user_leads['source'].value_counts().reset_index()
                fig = px.bar(s_counts, x='source', y='count', color_discrete_sequence=['#00506b'])
                fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
                event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="ind_source_chart", config=chart_config)
                render_download_csv(user_leads, "your_source_breakdown.csv")
                if event.selection and event.selection['points']:
                    sel = event.selection['points'][0]['x']
                    show_drill_down(user_leads[user_leads['source'] == sel], f"Source: {sel}")

    st.divider()

    # --- 2. DETAILED REFERRAL DISTRIBUTION ---
    if show_cumulative:
        st.markdown("<h3 style='text-align: center; color: #00506b;'>Detailed Referral Distribution</h3>", unsafe_allow_html=True)
        segments = get_stats_cached('get_referral_segments_by_ccu')
        g_col1, g_col2 = st.columns(2)
        df_raw_sent = df_all_leads[(df_all_leads['last_contact_status'] == "Referral Sent") & (df_all_leads['active_client'] == True)]
        df_raw_conf = df_all_leads[(df_all_leads['care_status'] == "Care Start") & (df_all_leads['active_client'] == True)]
        
        with g_col1:
            st.markdown("<h4 style='font-weight: bold; color: #111827;'>Referrals sent by CCU</h4>", unsafe_allow_html=True)
            df_p = pd.DataFrame(segments['sent']).sort_values(by='count', ascending=False) if segments['sent'] else pd.DataFrame()
            if not df_p.empty:
                fig = px.bar(df_p, x='ccu_name', y='count', color_discrete_sequence=['#00506b'])
                fig.update_layout(height=400, xaxis_title="CCU", yaxis_title="Count", paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', clickmode='event+select')
                event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="sent_ccu_chart", config=chart_config)
                render_download_csv(df_raw_sent, "referrals_sent_detailed.csv")
                if event.selection and event.selection['points']:
                    sel = event.selection['points'][0]['x']
                    show_drill_down(df_raw_sent[df_raw_sent['ccu_name'] == sel], f"Referrals Sent: {sel}")
            else: st.info("No data")
        with g_col2:
            st.markdown("<h4 style='font-weight: bold; color: #111827;'>Authorizations received from CCUs</h4>", unsafe_allow_html=True)
            df_p = pd.DataFrame(segments['confirmed']).sort_values(by='count', ascending=False) if segments['confirmed'] else pd.DataFrame()
            if not df_p.empty:
                fig = px.bar(df_p, x='ccu_name', y='count', color_discrete_sequence=['#3CA5AA'])
                fig.update_layout(height=400, xaxis_title="CCU", yaxis_title="Count", paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', clickmode='event+select')
                event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="conf_ccu_chart", config=chart_config)
                render_download_csv(df_raw_conf, "authorizations_received.csv")
                if event.selection and event.selection['points']:
                    sel = event.selection['points'][0]['x']
                    show_drill_down(df_raw_conf[df_raw_conf['ccu_name'] == sel], f"Authorizations: {sel}")
            else: st.info("No data")

    # --- 3. STATUS LOGS SECTION ---
    st.divider()
    col_s1, col_s2 = st.columns(2)
    user_target = df_all_leads[df_all_leads['staff_name'] == st.session_state.username] if not show_cumulative else df_all_leads

    with col_s1:
        title = "Your Leads by Status" if not show_cumulative else "Leads by Status"
        st.markdown(f"<h4 style='font-weight: bold; color: #111827;'>{title}</h4>", unsafe_allow_html=True)
        if not user_target.empty:
            df_val = user_target['last_contact_status'].value_counts().reset_index()
            fig = px.bar(df_val, x='last_contact_status', y='count', color_discrete_sequence=['#00506b'])
            fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="status_chart_bot", config=chart_config)
            render_download_csv(user_target, "status_breakdown.csv")
            if event.selection and event.selection['points']:
                sel = event.selection['points'][0]['x']
                show_drill_down(user_target[user_target['last_contact_status'] == sel], f"Status: {sel}")

    with col_s2:
        title = "Your Monthly Flow" if not show_cumulative else "Monthly Leads (All)"
        st.markdown(f"<h4 style='font-weight: bold; color: #111827;'>{title}</h4>", unsafe_allow_html=True)
        if show_cumulative:
            m_data = get_stats_cached('monthly_leads')
            if m_data:
                df = pd.DataFrame(m_data); fig = px.scatter(df, x='month', y='count', color_discrete_sequence=['#00506b'])
                fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True, key="mon_leads", config=chart_config)
                render_download_csv(df_all_leads, "monthly_leads_all.csv")
        else:
            m_data = get_stats_cached('leads_by_month_for_user', st.session_state.username)
            if m_data:
                df = pd.DataFrame(m_data); fig = px.scatter(df, x='month', y='count', color_discrete_sequence=['#00506b'])
                fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True, key="mon_leads_ind", config=chart_config)
                render_download_csv(user_target, "your_monthly_flow.csv")

    col_s3, col_s4 = st.columns(2)
    with col_s3:
        title = "Your Event Leads" if not show_cumulative else "Event Leads"
        st.markdown(f"<h4 style='font-weight: bold; color: #111827;'>{title}</h4>", unsafe_allow_html=True)
        ev_leads = user_target[user_target['source'] == "Event"]
        if not ev_leads.empty:
            e_data = ev_leads['event_name'].value_counts().reset_index()
            fig = px.bar(e_data, x='event_name', y='count', color_discrete_sequence=['#00506b'])
            fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="evt_leads_chart", config=chart_config)
            render_download_csv(ev_leads, "event_leads_detailed.csv")
            if event.selection and event.selection['points']:
                sel = event.selection['points'][0]['x']
                show_drill_down(ev_leads[ev_leads['event_name'] == sel], f"Event: {sel}")
        else: st.info("No event leads recorded")

    with col_s4:
        title = "Your WOM Breakdown" if not show_cumulative else "Word of Mouth Breakdown"
        st.markdown(f"<h4 style='font-weight: bold; color: #111827;'>{title}</h4>", unsafe_allow_html=True)
        wom_leads = user_target[user_target['source'] == "Word of Mouth"]
        if not wom_leads.empty:
            w_data = wom_leads['word_of_mouth_type'].value_counts().reset_index()
            fig = px.bar(w_data, x='word_of_mouth_type', y='count', color_discrete_sequence=['#3CA5AA'])
            fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="wom_ind_chart", config=chart_config)
            render_download_csv(wom_leads, "wom_leads_detailed.csv")
            if event.selection and event.selection['points']:
                sel = event.selection['points'][0]['x']
                show_drill_down(wom_leads[wom_leads['word_of_mouth_type'] == sel], f"WOM: {sel}")
        else: st.info("No word of mouth leads recorded")

    col_s5, col_s6 = st.columns(2)
    with col_s5:
        title = "Your Priority Mix" if not show_cumulative else "Priority Distribution"
        st.markdown(f"<h4 style='font-weight: bold; color: #111827;'>{title}</h4>", unsafe_allow_html=True)
        if not user_target.empty:
            p_data = user_target['priority'].value_counts().reset_index()
            fig = px.bar(p_data, x='priority', y='count', color_discrete_sequence=['#00506b'])
            fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="pri_stat_chart", config=chart_config)
            render_download_csv(user_target, "priority_distribution.csv")
            if event.selection and event.selection['points']:
                sel = event.selection['points'][0]['x']
                show_drill_down(user_target[user_target['priority'] == sel], f"Priority: {sel}")

    with col_s6:
        title = "Your Auth Status" if not show_cumulative else "Authorization Status"
        st.markdown(f"<h4 style='font-weight: bold; color: #111827;'>{title}</h4>", unsafe_allow_html=True)
        if not user_target.empty:
            auth_map = {True: "Authorized", False: "Pending"}
            user_target_auth = user_target.copy()
            user_target_auth['auth_label'] = user_target_auth['authorization_received'].map(auth_map)
            auth_counts = user_target_auth['auth_label'].value_counts().reset_index()
            fig = px.bar(auth_counts, x='auth_label', y='count', color_discrete_sequence=['#3CA5AA'])
            fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title="", yaxis_title="Count", clickmode='event+select')
            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="auth_stat_chart", config=chart_config)
            render_download_csv(user_target, "auth_status_detailed.csv")
            if event.selection and event.selection['points']:
                sel = event.selection['points'][0]['x']
                show_drill_down(user_target_auth[user_target_auth['auth_label'] == sel], f"Auth: {sel}")

    # --- 4. LEAD PIPELINE ANALYTICS ---
    st.divider()
    st.markdown("""
    <div style="background: linear-gradient(90deg, #00506b 0%, #3CA5AA 100%); padding: 20px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); color: white !important;">
        <h1 style="text-align: center; margin: 0; letter-spacing:0.08em; text-transform:uppercase; font-weight: 800; color: white !important;">
            <span style="color: white !important; font-weight: 900 !important; text-shadow: 0px 0px 5px rgba(0,0,0,0.2);">LEAD PIPELINE ANALYTICS</span>
        </h1>
    </div>
    """, unsafe_allow_html=True)
    
    leads_target = df_all_leads if show_cumulative else df_all_leads[df_all_leads['staff_name'] == st.session_state.username]
    all_refs_df = leads_target[leads_target['active_client'] == True]
    all_pending_df = leads_target[leads_target['active_client'] == False]
    care_start_df = all_refs_df[all_refs_df['care_status'] == "Care Start"]
    not_start_df = all_refs_df[all_refs_df['care_status'] == "Not Start"]
    pending_conv_df = all_refs_df[~all_refs_df['care_status'].isin(["Care Start", "Not Start"])]

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("<div style='background-color: #FFFFFF; padding: 15px; border-radius: 12px; border: 1px solid #E5E7EB;'><h3 style='color: #00506b; text-align: center; margin-bottom: 10px;'>Lead Confirmation</h3><p style='color: #6B7280; text-align: center; font-size: 12px;'>Leads marked as referral</p></div>", unsafe_allow_html=True)
        fig = go.Figure(data=[go.Pie(labels=['Referrals', 'Pending'], values=[len(all_refs_df), len(all_pending_df)], hole=0.4, marker_colors=['#00506b', '#B5E8F7'])])
        fig.update_layout(height=350, margin=dict(t=20, b=80, l=20, r=20), modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA'),
                          legend=dict(orientation="h", y=-0.2, x=0.5, xanchor='center'))
        st.plotly_chart(fig, use_container_width=True, key="conf_pie", config=chart_config)
        render_download_csv(leads_target, "lead_confirmation_data.csv")
        
        # Confirmation Buttons locally under col_p1
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Referrals", width="stretch", key="btn_ref_bot") and not all_refs_df.empty: show_drill_down(all_refs_df, "Your Referrals")
        with b2:
            if st.button("Pending", width="stretch", key="btn_pend_bot") and not all_pending_df.empty: show_drill_down(all_pending_df, "Your Pending Leads")

    with col_p2:
        st.markdown("<div style='background-color: #FFFFFF; padding: 15px; border-radius: 12px; border: 1px solid #3CA5AA;'><h3 style='color: #111827; text-align: center; margin-bottom: 10px;'>Lead Conversion</h3><p style='color: #6B7280; text-align: center; font-size: 12px;'>Leads converted to care</p></div>", unsafe_allow_html=True)
        fig = go.Figure(data=[go.Pie(labels=['Care Start', 'Not Start', 'Pending'], values=[len(care_start_df), len(not_start_df), len(pending_conv_df)], hole=0.4, marker_colors=['#00506b', '#3CA5AA', '#E5E7EB'])])
        fig.update_layout(height=350, margin=dict(t=20, b=80, l=20, r=20), modebar=dict(bgcolor='rgba(0,0,0,0)', color='#3CA5AA'),
                          legend=dict(orientation="h", y=-0.2, x=0.5, xanchor='center'))
        st.plotly_chart(fig, use_container_width=True, key="conv_pie", config=chart_config)
        render_download_csv(all_refs_df, "lead_conversion_data.csv")

        # Conversion Buttons locally under col_p2
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Care Start", width="stretch", key="btn_cs_bot") and not care_start_df.empty: show_drill_down(care_start_df, "Care Starts")
        with b2:
            if st.button("Not Start", width="stretch", key="btn_ns_bot") and not not_start_df.empty: show_drill_down(not_start_df, "Not Starts")
        with b3:
            if st.button("Pending Care", width="stretch", key="btn_cp_bot") and not pending_conv_df.empty: show_drill_down(pending_conv_df, "Pending Conversion")

    # Rate Cards
    cr_rate = (len(all_refs_df) / len(leads_target) * 100) if len(leads_target) > 0 else 0
    cv_rate = (len(care_start_df) / len(all_refs_df) * 100) if len(all_refs_df) > 0 else 0
    st.markdown(f"""
        <div style="background: #FFFFFF; padding: 20px; border-radius: 15px; margin-top: 20px; border: 1px solid #E5E7EB; box-shadow: 0 4px 10px rgba(15,23,42,0.04);">
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div style="flex: 1; padding: 15px; border-right: 1px solid #E5E7EB;">
                    <span style="color: #111827; font-size: 32px; font-weight: bold;">{cr_rate:.1f}%</span>
                    <br><span style="color: #4B5563; font-size: 14px;">{"Your Confirmation Rate" if not show_cumulative else "Confirmation Rate"}</span>
                </div>
                <div style="flex: 1; padding: 15px;">
                    <span style="color: #3CA5AA; font-size: 32px; font-weight: bold;">{cv_rate:.1f}%</span>
                    <br><span style="color: #4B5563; font-size: 14px;">{"Your Conversion Rate" if not show_cumulative else "Conversion Rate"}</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    db.close()

def discovery_tool():
    """Discovery tool for custom analysis"""
    from frontend.common import render_download_csv
    db = SessionLocal()
    all_leads_list = crud_leads.list_leads(db, limit=10000)
    df_all_leads = pd.DataFrame([l.__dict__ for l in all_leads_list])
    if not df_all_leads.empty and '_sa_instance_state' in df_all_leads.columns:
        df_all_leads = df_all_leads.drop('_sa_instance_state', axis=1)
    
    st.markdown('<div class="main-header">LEAD DISCOVERY TOOL</div>', unsafe_allow_html=True)
    if df_all_leads.empty:
        st.warning("No data"); db.close(); return

    is_admin = st.session_state.user_role == "admin"
    analysis_df = df_all_leads if is_admin else df_all_leads[df_all_leads['staff_name'] == st.session_state.username]
    
    ccus = crud_ccus.get_all_ccus(db)
    ccu_map = {c.id: c.name for c in ccus}
    analysis_df['ccu_name'] = analysis_df['ccu_id'].map(ccu_map).fillna("N/A")
    
    feature_map = {
        "Lead Source": "source",
        "Staff Name": "staff_name",
        "Contact Status": "last_contact_status",
        "Priority": "priority",
        "CCU": "ccu_name",
        "Care Status": "care_status",
        "Active Client": "active_client",
        "Referral Type": "referral_type",
        "City": "city",
        "Authorization": "authorization_received",
        "Medicaid Status": "medicaid_status"
    }
    
    col_d1, col_d2 = st.columns(2)
    with col_d1: fx = st.selectbox("Split By (X-Axis):", options=list(feature_map.keys()), key="dsc_x")
    with col_d2: fc = st.selectbox("Compare Against (Color):", options=["None"] + list(feature_map.keys()), index=0, key="dsc_c")
    
    cx = feature_map[fx]; cc = feature_map[fc] if fc != "None" else None
    plot_df = analysis_df.copy()
    plot_df[cx] = plot_df[cx].fillna("N/A").astype(str)
    if cc:
        if cc == cx: cc = None
        else: plot_df[cc] = plot_df[cc].fillna("N/A").astype(str)
    
    chart_config = {'displayModeBar': True, 'displaylogo': False}
    if cc:
        agg = plot_df.groupby([cx, cc]).size().reset_index(name='Count')
        fig = px.bar(agg, x=cx, y='Count', color=cc, barmode='group', text='Count')
    else:
        agg = plot_df.groupby(cx).size().reset_index(name='Count')
        fig = px.bar(agg, x=cx, y='Count', color_discrete_sequence=['#00506b'], text='Count')
    
    fig.update_layout(paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF', xaxis_title=fx, yaxis_title="Lead Count", legend=dict(orientation="h", y=-0.2, x=0.5, xanchor='center'))
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="discovery_chart", config=chart_config)
    render_download_csv(analysis_df, "discovery_leads_detailed.csv")
    
    if event.selection and event.selection['points']:
        sel_val = event.selection['points'][0]['x']
        drill = analysis_df[analysis_df[cx].fillna("N/A").astype(str) == sel_val]
        if cc:
            sel_color = event.selection['points'][0].get('legendgroup')
            if sel_color: drill = drill[drill[cc].fillna("N/A").astype(str) == sel_color]
        show_drill_down(drill, f"Discovery: {fx}={sel_val}")
    db.close()

def view_all_user_dashboards():
    """Admin view for all staff dashboards"""
    from frontend.common import render_download_csv
    st.markdown('<div class="main-header">ALL USER DASHBOARDS</div>', unsafe_allow_html=True)
    if st.button("Back"): st.session_state.show_user_dashboards = False; st.rerun()
    db = SessionLocal(); approved = crud_users.get_approved_users(db)
    all_leads_list = crud_leads.list_leads(db, limit=10000)
    df_all_leads = pd.DataFrame([l.__dict__ for l in all_leads_list])
    if not df_all_leads.empty and '_sa_instance_state' in df_all_leads.columns: df_all_leads = df_all_leads.drop('_sa_instance_state', axis=1)

    for u in approved:
        with st.expander(f"{u.username} Dashboard"):
            user_leads = df_all_leads[df_all_leads['staff_name'] == u.username] if not df_all_leads.empty else pd.DataFrame()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Total Leads:** {len(user_leads)}")
                if not user_leads.empty:
                    s_data = user_leads['source'].value_counts().reset_index()
                    fig = px.bar(s_data, x='source', y='count', color_discrete_sequence=['#00506b'], title="Source")
                    fig.update_layout(height=150, margin=dict(t=30, b=0, l=0, r=0), showlegend=False); st.plotly_chart(fig, use_container_width=True)
                    render_download_csv(user_leads, f"{u.username}_leads.csv")
            with col2:
                refs = len(user_leads[user_leads['active_client'] == True])
                st.markdown(f"**Referrals:** {refs}")
                if not user_leads.empty:
                    st_data = user_leads['last_contact_status'].value_counts().reset_index()
                    fig = px.bar(st_data, x='last_contact_status', y='count', color_discrete_sequence=['#3CA5AA'], title="Status")
                    fig.update_layout(height=150, margin=dict(t=30, b=0, l=0, r=0), showlegend=False); st.plotly_chart(fig, use_container_width=True)
    db.close()
