import streamlit as st
import sys
import os
from pathlib import Path

# 0. ULTRA-FAST PAGE CONFIGURATION (Must be the very first Streamlit command)
# Avoid importing heavy modules here to minimize the "Streamlit Crown" flash on refresh

# Pre-computed base64 logo for near-instant application
try:
    # Add the current directory to path to ensure assets_base64 is found
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    if _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)
    from assets_base64 import LOGO_BASE64
except Exception:
    # Fallback if the file is missing or import fails
    LOGO_BASE64 = "favicon.svg"

# Branding handled via Dockerfile patch and page config
st.set_page_config(
    page_title="Lead Manager",
    page_icon="./favicon.svg?v=15",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. PATH CONFIGURATION
# Add backend to Python path for importing backend modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# 2. HEAVY IMPORTS (Import after branding is applied)
from frontend.common import get_logo_path, init_session_state, inject_custom_css, handle_active_modal
from frontend.auth import login, signup, forgot_password
from frontend.dashboard import dashboard, view_all_user_dashboards, discovery_tool
from frontend.view_leads import view_leads, mark_referral_page
from frontend.add_lead import add_lead
from frontend.referrals_sent import view_referrals
from frontend.referral_confirm import referral_confirm
from frontend.referral_reports import referral_reports
from frontend.activity_logs import view_activity_logs
from frontend.user_management import admin_panel, update_password, render_historian, user_profile_page
from app.crud import crud_users, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus
from app.db import SessionLocal
from app.email_scheduler import start_scheduler

@st.cache_resource
def init_scheduler():
    """Initialize the email scheduler once"""
    start_scheduler()



def main():
    """Main application logic - Router"""
    # Inject custom CSS/JS immediately
    inject_custom_css()
    
    # 1. Initialize session state (includes token validation and robust warm-up)
    # This handles the cookie-sync retry loop internally to ensure cookies are populated.
    init_session_state()
    
    # 2. Render Top Bar (Relocated Notifications, User Info, Search)
    from frontend.common import render_top_bar
    render_top_bar()
    
    # 0. TARGETED RELOADING (SAFELY)
    # This ensures backend changes are picked up locally WITHOUT the AWS crash bug
    import importlib
    import app.crud.crud_leads as crud_leads
    import app.crud.crud_users as crud_users
    import app.crud.crud_notifications as crud_notifications
    import app.utils.security as security
    importlib.reload(crud_leads)
    importlib.reload(crud_users)
    importlib.reload(crud_notifications)
    importlib.reload(security)

    # 0.5 PROGRAMMATIC NAVIGATION
    # Sync URL query params with session state at the very start of main()
    # This allows links like ?p=View+Leads to actually switch the page
    url_p = st.query_params.get('p')
    if url_p and url_p != st.session_state.get('main_navigation'):
        st.session_state['main_navigation'] = url_p
        
    if '_navigate_to' in st.session_state:
        new_page = st.session_state.pop('_navigate_to')
        st.session_state['main_navigation'] = new_page
        st.query_params['p'] = new_page
    
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
        # Render modals at the end of the script to ensure page-level button logic
        # has a chance to clear triggers (Ghost Popup Prevention)
        
        # Sidebar navigation
        with st.sidebar:
            # Company logo above the Navigation title
            st.image(get_logo_path("sidebar_logo.png"), width=250)
            st.markdown("")  # small spacer
            st.title("Navigation")
            
            # Base pages
            pages = ["Dashboard", "Lead Discovery", "Add Lead", "View Leads", "Referrals Sent", "Authorizations", "Activity Logs"]
            
            # Admin panel for admins
            if st.session_state.user_role == "admin":
                pages.append("User Management")
            
            # Ensure main_navigation is initialized
            if "main_navigation" not in st.session_state:
                st.session_state.main_navigation = "Dashboard"

            def handle_nav_change():
                """Callback when main navigation changes via sidebar"""
                if getattr(st.session_state, "_sidebar_radio", None):
                    st.session_state.main_navigation = st.session_state._sidebar_radio
                
                # Clear all stray query parameters (like target_id or search terms) to prevent leakage
                st.query_params.clear()
                # Persist current page in URL so refresh restores the same page
                st.query_params['p'] = st.session_state.main_navigation
                # Clear any sub-page state when navigating to a new main page
                st.session_state.current_page = None
                
                # CRITICAL: Auto-clear the top search bar when navigating away
                st.session_state['_clear_topbar_search'] = True
                
                # CRITICAL: Auto-clear ALL page-level search input boxes so stale
                # search terms don't bleed into the newly selected page.
                search_input_keys = [
                    # View Leads page
                    'search_name_input',
                    'search_id_input',
                    'search_staff_input',
                    'search_source_input',
                    # Referrals Sent page
                    'ref_search_name_input',
                    'search_id_input_ref',
                    'ref_search_staff_input',
                    'ref_search_source_input',
                    # Authorizations page
                    'conf_search_name_input',
                    'search_id_input_conf',
                    'conf_search_staff_input',
                    'conf_search_source_input',
                    # Top-bar partial query param state
                    'topbar_search_input',
                    # Prevent global_search_term from carrying over too
                    'global_search_term',
                ]
                for key in search_input_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                
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
            
            # Determine the index for the radio button. If we are on a hidden page (User Profile), index=None.
            active_page = st.session_state.main_navigation
            nav_index = pages.index(active_page) if active_page in pages else None
            
            # Decouple the radio key to safely allow hidden pages
            st.radio("Go to", pages, index=nav_index, key="_sidebar_radio", on_change=handle_nav_change)
            
            # No legacy navigation enforcement needed below. 
            # The callback handles the reset logic efficiently.
            
            st.divider()
            render_historian()
            
            
            # API Health Check Diagnostic
            from frontend.common import render_api_status
            render_api_status()
        
        # Route to selected page
        # Check for hidden pages first (not in navigation)
        
        # Use session state instead of sidebar radio value strictly, supporting hidden pages
        page = st.session_state.main_navigation
        
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
        elif page == "Authorizations":
            referral_confirm()
        elif page == "Activity Logs":
            view_activity_logs()
        elif page == "User Profile":
            user_profile_page()
        elif page == "User Management":
            if st.session_state.user_role == "admin":
                admin_panel()
            else:
                st.error("Access denied. Admin only.")
        elif page == "Notifications":
            from frontend.common import render_notification_center
            db = SessionLocal()
            try:
                render_notification_center(db, st.session_state.db_user_id)
            finally:
                db.close()

        # --- MODAL RENDERING (POST-ROUTING) ---
        # Calling this at the absolute end ensures that if a button was clicked 
        # (like "Care Start") and cleared the modal triggers, we DON'T show the modal.
        handle_active_modal()



if __name__ == "__main__":
    init_scheduler()
    main()
