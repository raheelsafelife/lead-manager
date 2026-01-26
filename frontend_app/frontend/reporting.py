import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.db import SessionLocal
from app import services_stats

def view_reporting():
    """Admin Reporting Dashboard"""
    st.markdown('<div class="main-header">Admin Reporting Dashboard</div>', unsafe_allow_html=True)
    
    if st.session_state.user_role != "admin":
        st.error("Access Denied: Administrator role required.")
        return

    db = SessionLocal()
    
    try:
        # --- TOP LEVEL KPI CARDS ---
        counts = services_stats.get_basic_counts(db)
        performance_data = services_stats.get_staff_performance(db)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total System Leads</div>
                <div class="stat-number">{counts['total_leads']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            total_referrals = sum(p['total_referrals'] for p in performance_data)
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Referrals</div>
                <div class="stat-number">{total_referrals}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            avg_rate = round((total_referrals / counts['total_leads'] * 100), 1) if counts['total_leads'] > 0 else 0
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Avg. Conversion Rate</div>
                <div class="stat-number">{avg_rate}%</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class="stat-card" style="border-left-color: #3b82f6;">
                <div class="stat-label">Active Staff</div>
                <div class="stat-number">{len(performance_data)}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- STAFF PERFORMANCE CHARTS ---
        st.markdown("### Staff Performance Analytics")
        
        pf_df = pd.DataFrame(performance_data)
        
        c1, c2 = st.columns(2)
        
        with c1:
            # Bar chart: Total Leads vs Referrals
            fig_leads = go.Figure(data=[
                go.Bar(name='Total Leads', x=pf_df['staff_name'], y=pf_df['total_leads'], marker_color='#3CA5AA'),
                go.Bar(name='Referrals', x=pf_df['staff_name'], y=pf_df['total_referrals'], marker_color='#00506b')
            ])
            fig_leads.update_layout(
                title="Leads Output by Staff",
                barmode='group',
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_leads, use_container_width=True)
            
        with c2:
            # Bar chart: Conversion Rates
            fig_rate = px.bar(
                pf_df, 
                x='staff_name', 
                y='conversion_rate', 
                title="Staff Conversion Rate (%)",
                text='conversion_rate',
                color_discrete_sequence=['#59B976']
            )
            fig_rate.update_traces(texttemplate='%{text}%', textposition='outside')
            fig_rate.update_layout(height=400, yaxis_range=[0, 100])
            st.plotly_chart(fig_rate, use_container_width=True)
            
        st.divider()
        
        # --- SYSTEM DISTRIBUTION ---
        st.markdown("### System-Wide Distribution")
        dist = services_stats.get_system_wide_distribution(db)
        
        d1, d2, d3 = st.columns(3)
        
        with d1:
            # Pie: Status
            status_df = pd.DataFrame(dist['status'])
            fig_status = px.pie(status_df, values='value', names='label', title="Status Distribution", hole=0.4)
            fig_status.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_status, use_container_width=True)
            
        with d2:
            # Pie: Source
            source_df = pd.DataFrame(dist['source'])
            fig_source = px.pie(source_df, values='value', names='label', title="Lead Sources", hole=0.4)
            fig_source.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_source, use_container_width=True)
            
        with d3:
            # Pie: Priority
            priority_df = pd.DataFrame(dist['priority'])
            fig_priority = px.pie(priority_df, values='value', names='label', title="Priority Levels", hole=0.4)
            fig_priority.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_priority, use_container_width=True)

        # --- DATA TABLE ---
        st.divider()
        st.markdown("### Detailed Performance Table")
        st.dataframe(
            pf_df.rename(columns={
                "staff_name": "Staff Member",
                "total_leads": "Total Leads",
                "total_referrals": "Total Referrals",
                "conversion_rate": "Conversion Rate %"
            }),
            use_container_width=True,
            hide_index=True
        )

    finally:
        db.close()
