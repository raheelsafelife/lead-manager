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
    LOGO_BASE64 = "2.png.jpeg"

st.set_page_config(
    page_title="Lead Manager",
    page_icon=LOGO_BASE64,
    layout="wide",
    initial_sidebar_state="expanded"
)

# BRANDING LOCKER: Aggressively force title and favicon to stop Streamlit flash
st.markdown(f"""
    <script>
    (function() {{
        const title = "Lead Manager";
        const favicon = "{LOGO_BASE64}";
        
        const forceBranding = () => {{
            if (document.title !== title) document.title = title;
            let link = document.querySelector("link[rel*='icon']");
            if (!link) {{
                link = document.createElement('link');
                link.rel = 'shortcut icon';
                document.head.appendChild(link);
            }}
            if (link.href !== favicon) link.href = favicon;
        }};

        // Run immediately and then frequently for the first 3 seconds
        forceBranding();
        const interval = setInterval(forceBranding, 50);
        setTimeout(() => clearInterval(interval), 3000);
    }})();
    </script>
    """, unsafe_allow_html=True)

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
    # Inject custom CSS/JS immediately
    inject_custom_css()
    
    # Initialize session state (includes token validation)
    init_session_state()
    
    # 0. TARGETED RELOADING (SAFELY)
    # This ensures backend changes are picked up locally WITHOUT the AWS crash bug
    import importlib
    import app.crud.crud_leads as crud_leads
    importlib.reload(crud_leads)

    # 0.5 PROGRAMMATIC NAVIGATION
    # Widgets cannot have their session state key set after they render.
    # Use _navigate_to as an intermediate flag, applied HERE before the sidebar radio renders.
    if '_navigate_to' in st.session_state:
        st.session_state['main_navigation'] = st.session_state.pop('_navigate_to')
    
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
            
            # Add Update Password for regular users only (admins have it in User Management)
            if st.session_state.user_role != "admin":
                pages.append("Update Password")
            
            # Add admin panel for admins
            if st.session_state.user_role == "admin":
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
        elif page == "Authorizations":
            referral_confirm()
        elif page == "Activity Logs":
            view_activity_logs()
        elif page == "Update Password":
            update_password()
        elif page == "User Management":
            if st.session_state.user_role == "admin":
                admin_panel()
            else:
                st.error("Access denied. Admin only.")

        # --- MODAL RENDERING (POST-ROUTING) ---
        # Calling this at the absolute end ensures that if a button was clicked 
        # (like "Care Start") and cleared the modal triggers, we DON'T show the modal.
        handle_active_modal()



if __name__ == "__main__":
    init_scheduler()
    main()
