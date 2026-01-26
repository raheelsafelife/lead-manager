"""
Lead Manager - Main Application Entry Point (Brain)
This file serves as the router and imports page modules from frontend folder.
"""
import sys
from pathlib import Path

# Add backend to Python path for importing backend modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Lead Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import page modules from frontend folder
from frontend.common import init_session_state, inject_custom_css, get_logo_path, handle_active_modal
from frontend.auth import login, signup, forgot_password
from frontend.dashboard import dashboard, view_all_user_dashboards, discovery_tool
from frontend.view_leads import view_leads, mark_referral_page
from frontend.add_lead import add_lead
from frontend.referrals_sent import view_referrals
from frontend.referral_confirm import referral_confirm
from frontend.activity_logs import view_activity_logs
from frontend.user_management import admin_panel, update_password, render_historian
from app.crud import crud_users, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus
from app.db import SessionLocal
from app.email_scheduler import start_scheduler

@st.cache_resource
def init_scheduler():
    """Initialize the email scheduler once"""
    start_scheduler()



def main():
    """Main application logic - Router"""
    # Force module reload to pick up changes in backend modules (AttributeError & InvalidRequestError Fix)
    import sys
    from importlib import reload
    import app.services_stats as services_stats
    reload(services_stats) # FORCE RELOAD FOR ADMIN METRICS
    
    # Include app.db to ensure Base metadata is refreshed, preventing "Table already defined" errors
    modules_to_reload = [k for k in list(sys.modules.keys()) if 'app.models' in k or 'backend.app.models' in k or 'app.db' in k or 'crud_' in k]
    for mod in list(modules_to_reload):
        if mod in sys.modules:
            del sys.modules[mod]
            
    # Inject custom CSS/JS immediately
    inject_custom_css()
    
    # Initialize session state (includes token validation)
    init_session_state()
    
    # Check authentication
    if not st.session_state.authenticated:
        if st.session_state.show_signup:
            signup()
        elif st.session_state.show_forgot_password:
            forgot_password()
        else:
            login()
    else:
        # --- CENTRALIZED MODAL RENDERING ---
        # Render modals at the absolute top of the DOM before page layout
        db = SessionLocal()
        handle_active_modal(db)
        db.close()
        
        # Sidebar navigation
        with st.sidebar:
            # Company logo above the Navigation title
            st.image(get_logo_path(), width=250)
            st.markdown("")  # small spacer
            st.title("Navigation")
            
            # Base pages
            pages = ["Dashboard", "Lead Discovery", "Add Lead", "View Leads", "Referrals Sent", "Referral Confirm", "Activity Logs"]
            
            # Add Update Password for regular users only (admins have it in User Management)
            if st.session_state.user_role != "admin":
                pages.append("Update Password")
            
            # Add admin panel for admins
            if st.session_state.user_role == "admin":
                pages.append("Admin Reporting")
                pages.append("Email Template Editor")
                pages.append("CCU & Provider Mgmt")
                pages.append("User Management")
            
            # Ensure main_navigation is initialized
            if "main_navigation" not in st.session_state:
                st.session_state.main_navigation = "Dashboard"

            def handle_nav_change():
                """Callback when main navigation changes"""
                # Clear any sub-page state when navigating to a new main page
                st.session_state.current_page = None
                
                # CRITICAL: Clear ALL modal state on navigation to prevent ghost popups
                st.session_state.pop('active_modal', None)
                st.session_state.modal_open = False
                st.session_state.modal_action = None
                st.session_state.modal_lead_id = None
                st.session_state.modal_lead_name = None
                st.session_state.modal_data = {}
                st.session_state.show_delete_modal = False
                
                # Clear edit state
                for key in list(st.session_state.keys()):
                    if key.startswith('editing_'):
                        del st.session_state[key]
            
            # Additional check: If Mark Referral Page is active, ensure we don't accidentally navigate away
            # unless the user explicitly clicked.
            # But relying on on_change handles the explicit click nicely.
            
            page = st.radio("Go to", pages, key="main_navigation", on_change=handle_nav_change)
            
            # No legacy navigation enforcement needed below. 
            # The callback handles the reset logic efficiently.
            
            # Show user info
            st.divider()
            st.markdown(f"<div style='background-color: #f1f5f9; padding: 10px; border-radius: 5px; border-left: 4px solid #0f172a;'>", unsafe_allow_html=True)
            st.markdown(f"<p style='margin:0; font-size:0.9rem;'><b>Username:</b> {st.session_state.username}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='margin:0; font-size:0.9rem;'><b>Employee ID:</b> {st.session_state.employee_id or 'N/A'}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='margin:0; font-size:0.8rem; color: #64748b;'><b>Role:</b> {st.session_state.user_role}</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.divider()
            render_historian()
            
            # API Health Check Diagnostic
            from frontend.common import render_api_status
            render_api_status()
        
        # Route to selected page
        # Check for hidden pages first (not in navigation)
        if st.session_state.get('current_page') == 'Mark Referral Page':
            mark_referral_page()
        elif page == "Dashboard":
            # Check if admin wants to view all user dashboards
            if st.session_state.user_role == "admin" and st.session_state.show_user_dashboards:
                if st.button("Back to Dashboard"):
                    st.session_state.show_user_dashboards = False
                    st.rerun()
                st.divider()
                view_all_user_dashboards()
            else:
                dashboard()
        elif page == "View Leads":
            view_leads()
        elif page == "Add Lead":
            add_lead()
        elif page == "Lead Discovery":
            discovery_tool()
        elif page == "Referrals Sent":
            view_referrals()
        elif page == "Referral Confirm":
            referral_confirm()
        elif page == "Activity Logs":
            view_activity_logs()
        elif page == "Update Password":
            update_password()
        elif page == "Admin Reporting":
            if st.session_state.user_role == "admin":
                try:
                    from frontend.reporting import view_reporting
                    view_reporting()
                except ImportError:
                    st.error("Admin Reporting module is not yet deployed.")
                    if st.button("Back to Dashboard"): st.rerun()
            else:
                st.error("Access denied.")
        elif page == "Email Template Editor":
            if st.session_state.user_role == "admin":
                try:
                    from frontend.email_editor import view_email_editor
                    view_email_editor()
                except ImportError:
                    st.error("Email Editor module is not yet deployed.")
                    if st.button("Back to Dashboard"): st.rerun()
            else:
                st.error("Access denied.")
        elif page == "CCU & Provider Mgmt":
            if st.session_state.user_role == "admin":
                try:
                    from frontend.ccu_management import view_ccu_management
                    view_ccu_management()
                except ImportError:
                    st.error("CCU Management module is not yet deployed.")
                    if st.button("Back to Dashboard"): st.rerun()
            else:
                st.error("Access denied.")
        elif page == "User Management":
            if st.session_state.user_role == "admin":
                admin_panel()
            else:
                st.error("Access denied. Admin only.")



if __name__ == "__main__":
    init_scheduler()
    main()
