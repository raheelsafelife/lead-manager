"""
Common utilities, CSS styles, and shared functions for Lead Manager.
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import streamlit as st
from app.db import SessionLocal
from app.utils.activity_logger import utc_to_local
import extra_streamlit_components as pyc
import os

def get_logo_path():
    """Find the logo file in multiple possible locations"""
    base_path = Path(__file__).parent.parent.parent
    possible_paths = [
        os.path.join(base_path, "icon1.png"),
        "icon1.png",
        "frontend_app/icon1.png",
        "/app/icon1.png"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return "icon1.png" # Fallback


# Initialize CookieManager
def get_cookie_manager():
    """Ensure CookieManager is rendered exactly once per script execution"""
    # Use st.session_state for the object, but we MUST render it every run
    # To avoid DuplicateKeyError, we track if we've already rendered it this run
    if not hasattr(st, "_cm_rendered_this_run"):
        st._cm_rendered_this_run = pyc.CookieManager(key="lead_manager_auth_system_v1")
    return st._cm_rendered_this_run


# Global CSS styles (SafeLife UI theme)
GLOBAL_CSS = """
<style>
    /* Import Montserrat from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;800&display=swap');

    html, body, [class^="css"], .stApp  {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                     Arial, 'Source Sans Pro', system-ui, sans-serif;
        background-color: #FFFFFF !important;
        color: #111827 !important;
    }

    /* Hide Streamlit header (Deploy button, Rerun status) but KEEP the sidebar toggle */
    header { 
        visibility: hidden !important; 
        background: transparent !important;
    }
    
    [data-testid="stHeader"] { 
        visibility: hidden !important; 
        background: transparent !important;
    }

    footer { visibility: hidden !important; }
    .stDeployButton { display: none !important; }
    #MainMenu { visibility: hidden !important; }

    /* Force the sidebar collapse/expand buttons to be visible */
    [data-testid="stHeader"] button,
    [data-testid="stSidebar"] button[aria-label="Collapse sidebar"],
    button[data-testid="stExpandSidebarButton"] {
        visibility: visible !important;
    }

    /* Primary brand colors */
    :root {
        --safelife-deep-blue: #00506b;
        --safelife-green: #59B976;
        --safelife-aqua: #3CA5AA;
        --safelife-soft-gray: #F9F9F9;
        --safelife-blue-light: #B5E8F7;
        --safelife-blue-extra-light: #DFF8FF;
        --required-star-pink: #3CA5AA;
    }
    
    /* Square alerts/info boxes */
    .stAlert {
        border-radius: 0px !important;
    }

    /* Authentication container - separate from main app */
    .auth-container {
        background: #FFFFFF;
        padding: 2.5rem;
        border-radius: 1rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        max-width: 500px;
        margin: 2rem auto;
    }

    /* Required field star indicator */
    .required-star {
        color: var(--required-star-pink);
        font-weight: 700;
        margin-left: 0.2rem;
    }

    /* Form labels - bold and black */
    .stTextInput label, 
    .stPasswordInput label,
    .stSelectbox label,
    .stTextArea label,
    .stNumberInput label,
    .stDateInput label,
    label {
        font-weight: 700 !important;
        color: #000000 !important;
        font-size: 0.95rem !important;
    }

    /* Main page headers */
    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: 1.5rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        text-align: center;
        background-color: var(--safelife-aqua);
        padding: 1.5rem 2rem;
        border-radius: 0.75rem;
    }
    
    /* Fix Expanders (Leads, Payors, CCUs) - Ensure headers are NEVER black */
    [data-testid="stExpander"], .stExpander {
        border: 1px solid var(--safelife-aqua) !important;
        border-radius: 0.75rem !important;
        background-color: #FFFFFF !important;
        transition: all 0.3s ease !important;
    }
    
    /* Header/Summary of the expander */
    [data-testid="stExpander"] > details > summary,
    [data-testid="stExpander"] > div:first-child,
    .stExpander > div:first-child {
        background-color: #F9FAFB !important;
        color: #111827 !important;
        border-radius: 0.75rem 0.75rem 0 0 !important;
    }

    /* Ensure NO BLACK background on hover or selection */
    [data-testid="stExpander"] > details > summary:hover,
    [data-testid="stExpander"] > details[open] > summary {
        background-color: var(--safelife-blue-extra-light) !important;
        color: var(--safelife-deep-blue) !important;
    }

    /* Icon and Text colors inside expander headers */
    [data-testid="stExpander"] svg,
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span {
        color: #111827 !important;
        fill: #111827 !important;
    }
    
    /* Force Aqua for the border even when open */
    [data-testid="stExpander"] > details {
        border: none !important;
    }

    .main-header-signup,
    .main-header-forgot {
        color: #000000 !important;
    }
    
    .main-header-signup *,
    .main-header-forgot * {
        color: #000000 !important;
    }

    .main-header .main-subtitle {
        display: block;
        margin-top: 0.35rem;
        font-size: 1rem;
        font-weight: 600;
        text-transform: none;
        letter-spacing: 0.02em;
    }

    /* Stat cards */
    .stat-card {
        background: #FFFFFF;
        padding: 1.3rem 1.5rem;
        border-radius: 0.75rem;
        border-left: 5px solid var(--safelife-deep-blue);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
    }

    .stat-number {
        font-size: 2.1rem;
        font-weight: 700;
        color: var(--safelife-deep-blue);
    }

    .stat-label {
        font-size: 0.8rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    
    /* Make all subheaders bold and black */
    h2, h3, .stSubheader, .stSubheader > div, .stSubheader > div > div {
        font-weight: 700 !important;
        color: #000000 !important;
    }
    
    /* Ensure all subheader text is black */
    h2 *, h3 *, .stSubheader *, .stSubheader > div *, .stSubheader > div > div * {
        color: #000000 !important;
    }

    /* Buttons – aqua background with white text */
    button, .stButton > button, .stForm button, .stForm button[type="submit"] {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        border-radius: 10px;
        border: none;
        padding: 0.75rem 2.0rem;
        background: var(--safelife-aqua) !important;
        color: #FFFFFF !important;
        box-shadow: 0 3px 10px rgba(60, 165, 170, 0.35);
        font-size: 1.05rem;
        letter-spacing: 0.03em;
    }
    
    /* Ensure all button text is white */
    button *, .stButton > button *, .stForm button *, .stForm button[type="submit\"] *, button p, .stButton > button p {
        color: #FFFFFF !important;
    }

    /* Primary buttons (active/selected state) - deep blue background with white text */
    .stButton > button[kind="primary"],
    .stForm button[kind="primary"] {
        background: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    /* Ensure primary button text stays white */
    .stButton > button[kind="primary"] *,
    .stForm button[kind="primary"] * {
        color: #FFFFFF !important;
    }

    /* Secondary buttons - aqua background with white text */
    .stButton > button[kind="secondary"],
    .stForm button[kind="secondary"] {
        background: var(--safelife-aqua) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 3px 10px rgba(60, 165, 170, 0.35);
    }

    /* GLOBAL RADIO BUTTON STYLING (Professional Overrides) */
    
    /* 1. Base circle styling (Solid Aqua for unselected) */
    [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        border-color: var(--safelife-aqua) !important;
        background-color: var(--safelife-aqua) !important;
        box-shadow: none !important;
    }
    
    /* 2. Unselected State (Force solid Aqua) */
    [data-testid="stRadio"] label[data-baseweb="radio"]:not(:has(input:checked)) > div:first-child {
        background-color: var(--safelife-aqua) !important;
        border-color: var(--safelife-aqua) !important;
    }
    
    /* 3. Selected/Active State (Force solid Deep Blue) */
    [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {
        background-color: var(--safelife-deep-blue) !important;
        border-color: var(--safelife-deep-blue) !important;
    }
    
    /* 4. Ensure internal dot doesn't create weird artifacts */
    [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child > div {
        background-color: transparent !important;
    }
    [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {
        background-color: #FFFFFF !important; /* Small white dot in center of blue circle for active */
        width: 4px !important;
        height: 4px !important;
    }

    /* Fix for radio button option labels - make them black and bold */
    div[data-testid="stRadio"] label,
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] label div,
    div[data-testid="stRadio"] label span {
        color: #111827 !important;
        font-weight: 700 !important;
        -webkit-text-fill-color: #111827 !important;
        opacity: 1 !important;
    }

    /* Form fields + selectboxes - WHITE backgrounds with BLACK text (Professional Look) */
    .stTextInput input,
    .stPasswordInput input,
    .stTextArea textarea,
    .stNumberInput input,
    .stDateInput input,
    .stTimeInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stSelectbox select,
    div[data-baseweb="base-input"],
    div[data-baseweb="input"],
    .stTextInput > div,
    .stNumberInput > div,
    .stTextArea > div,
    input[type="text"],
    input[type="password"],
    input[type="number"],
    input[type="email"],
    input[type="date"],
    textarea,
    select {
        border-radius: 0.6rem !important;
        border: 1px solid var(--safelife-aqua) !important;
        background-color: #FFFFFF !important;
        color: #111827 !important;
        box-shadow: none !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    
    /* PROFESSIONAL INPUT FOCUS - AQUA BORDER (Replaces default black) */
    .stTextInput input:focus,
    .stPasswordInput input:focus,
    .stTextArea textarea:focus,
    .stNumberInput input:focus,
    .stDateInput input:focus,
    .stSelectbox div[data-baseweb="select"]:focus,
    .stSelectbox div[data-baseweb="select"]:focus-within,
    [data-baseweb="input"] > div:focus-within {
        border-color: var(--safelife-aqua) !important;
        box-shadow: 0 0 0 2px rgba(60, 165, 170, 0.25) !important;
        outline: none !important;
    }
    
    /* Target the focus state of the wrapper too to prevent black outline */
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="base-input"]:focus-within,
    .stTextInput > div:focus-within,
    .stNumberInput > div:focus-within,
    .stTextArea > div:focus-within,
    [data-baseweb="select"]:focus-within {
        border-color: var(--safelife-aqua) !important;
        box-shadow: 0 0 0 2px rgba(60, 165, 170, 0.25) !important;
        outline: none !important;
    }
    
    /* Global fix for Streamlit's default focus ring (black/gray) */
    *:focus, *:focus-visible, *:active {
        outline: none !important;
        border-color: var(--safelife-aqua) !important;
    }
    
    /* Force specific streamlit internal div borders to Aqua */
    [data-baseweb="input"] {
        border: 1px solid var(--safelife-aqua) !important;
    }
    
    /* Ensure text visibility in input fields on focus */
    input:focus, textarea:focus {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: var(--safelife-aqua) !important;
    }
    
    /* Ensure no double borders or inner borders */
    [data-baseweb="base-input"] input,
    [data-baseweb="input"] input {
        border: none !important;
    }
    
    /* Input placeholder text - subtle gray */
    .stTextInput input::placeholder,
    .stPasswordInput input::placeholder,
    .stTextArea textarea::placeholder,
    input::placeholder,
    textarea::placeholder {
        color: #9CA3AF !important;
    }
    
    /* Date picker calendar - white background with aqua header */
    .stDateInput div[data-baseweb="popover"],
    [data-baseweb="popover"],
    div[data-baseweb="calendar"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border-radius: 8px !important;
        color: #111827 !important;
    }
    
    /* Target the calendar days and grid */
    [data-baseweb="calendar"] div,
    [data-baseweb="calendar"] button,
    [data-baseweb="calendar"] *:not(.aqua-header) {
        background-color: #FFFFFF !important;
        color: #111827 !important;
    }
    
    /* Ensure the header navigation stays aqua/professional */
    div[data-baseweb="calendar"] > div:first-child,
    div[data-baseweb="calendar"] > div:first-child * {
        background-color: var(--safelife-aqua) !important;
        color: white !important;
    }
    
    /* Fix for the black squares in the grid */
    [data-baseweb="calendar"] [aria-roledescription="button"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F3F4F6 !important;
    }
    
    /* Selected day - deep blue background */
    [data-baseweb="calendar"] [aria-selected="true"] {
        background-color: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
    }
    
    /* Dropdown menus - white background with high contrast */
    .stSelectbox ul,
    .stSelectbox li,
    [role="listbox"],
    [role="option"] {
        background-color: #FFFFFF !important;
        color: #111827 !important;
    }

    /* Dataframes / tables */
    .stDataFrame, .stTable {
        background-color: #FFFFFF;
        border-radius: 0.75rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }
    
    /* Sidebar navigation links - black text */
    section[data-testid="stSidebar"] a,
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] * {
        color: #000000 !important;
    }

    /* General titles/subheaders - all headings black and bold */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif;
        color: #000000 !important;
        font-weight: 700 !important;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #FFFFFF;
        border-radius: 10px 10px 0 0;
        gap: 2px;
        padding: 10px 20px;
        font-weight: 700 !important;
        color: #6B7280;
        border: 1px solid #E5E7EB;
        border-bottom: none;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
        border: none;
    }
    
    /* Force white text for specific headers (with sidebar override) */
    .white-header-text, .white-header-text *, 
    section[data-testid="stSidebar"] .white-header-text,
    section[data-testid="stSidebar"] .white-header-text * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    /* Hide "Press Enter to submit" hint */
    div[data-testid="InputInstructions"] > span:nth-child(1) {
        display: none;
    }
    
    [data-testid="InputInstructions"] {
        display: none !important;
    }

    /* Priority Tag Styles */
    .priority-tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        color: white !important;
        font-weight: 700;
        font-size: 0.75rem;
        text-transform: uppercase;
        margin-right: 5px;
    }
    .priority-high { background-color: #FF4B4B !important; }
    .priority-medium { background-color: #FFD700 !important; color: #000000 !important; }
    .priority-low { background-color: #28A745 !important; }

    /* Plotly Modebar Styling - Pill/Capsule shape for icons (RHS look) */
    .modebar-btn {
        border-radius: 20px !important;
        padding: 4px 10px !important;
        margin: 2px 2px !important;
        background-color: #00506b !important;
        transition: all 0.2s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: auto !important;
    }
    
    .modebar-btn:hover {
        background-color: #3CA5AA !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
    }
    
    .modebar-btn path {
        fill: #FFFFFF !important;
    }

    .modebar-group {
        background-color: transparent !important;
        padding: 5px !important;
        display: inline-flex !important;
        align-items: center !important;
    }
    
    /* Ensure Plotly chart areas don't clip the modebar */
    .plot-container .modebar {
        padding-top: 5px !important;
        padding-right: 5px !important;
    }
</style>
"""


def init_session_state():
    """Initialize all session state variables with improved persistence"""
    cookie_manager = get_cookie_manager()
    
    # Initialize basic auth state if missing
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.has_checked_cookie = False

    # Persistent Session Check:
    if not st.session_state.authenticated:
        auth_cookie = cookie_manager.get(cookie='lead_manager_auth')
        
        if auth_cookie:
            try:
                import json
                user_data = json.loads(auth_cookie)
                st.session_state.authenticated = True
                st.session_state.username = user_data.get('username')
                st.session_state.user_role = user_data.get('role')
                st.session_state.user_id = user_data.get('user_id')
                
                # RESTORE PAGE: Check if there's a saved page cookie
                page_cookie = cookie_manager.get(cookie='lead_manager_page')
                if page_cookie:
                    st.session_state.main_navigation = page_cookie
                
                st.rerun()
            except Exception:
                pass
        else:
            if not st.session_state.has_checked_cookie:
                import time
                time.sleep(0.3)
                st.session_state.has_checked_cookie = True
                st.rerun()

    # Ensure main_navigation is initialized for the radio button
    if 'main_navigation' not in st.session_state:
        st.session_state.main_navigation = "Dashboard"

    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'show_signup' not in st.session_state:
        st.session_state.show_signup = False
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'stats_view_mode' not in st.session_state:
        st.session_state.stats_view_mode = 'individual'
    if 'show_user_dashboards' not in st.session_state:
        st.session_state.show_user_dashboards = False
    
    # Start email scheduler (runs once per session)
    if 'email_scheduler_started' not in st.session_state:
        st.session_state.email_scheduler_started = False
        if st.session_state.authenticated:
            try:
                from app.email_scheduler import start_scheduler
                start_scheduler()
                st.session_state.email_scheduler_started = True
            except Exception as e:
                pass  # Scheduler error won't break the app


def save_login_to_cookies(user_id, username, role):
    """Save user login info to browser cookies for persistence"""
    cookie_manager = get_cookie_manager()
    import json
    user_data = {
        'user_id': user_id,
        'username': username,
        'role': role
    }
    # Set cookie for 7 days
    cookie_manager.set('lead_manager_auth', json.dumps(user_data), max_age=60*60*24*7)

def save_page_to_cookies(page_name):
    """Save current navigation page to cookies"""
    cookie_manager = get_cookie_manager()
    cookie_manager.set('lead_manager_page', page_name, max_age=60*60*24*7)

def clear_login_cookies():
    """Clear login and page cookies on logout"""
    cookie_manager = get_cookie_manager()
    cookie_manager.delete('lead_manager_auth')
    cookie_manager.delete('lead_manager_page')


def inject_custom_css():
    """Inject global CSS styles"""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def prepare_lead_data_for_email(lead, db):
    """Prepare comprehensive lead data dictionary for email reminders"""
    lead_data = {
        'id': lead.id,
        'first_name': lead.first_name,
        'last_name': lead.last_name,
        'phone': lead.phone,
        'email': 'N/A',
        'city': lead.city,
        'zip_code': lead.zip_code,
        'dob': str(lead.dob) if lead.dob else 'N/A',
        'medicaid_no': lead.medicaid_no,
        'source': lead.source,
        'event_name': lead.event_name,
        'word_of_mouth_type': lead.word_of_mouth_type,
        'other_source_type': lead.other_source_type,
        'staff_name': lead.staff_name,
        'created_by': lead.created_by,
        'last_contact_status': lead.last_contact_status,
        'last_contact_date': str(utc_to_local(lead.last_contact_date)) if lead.last_contact_date else 'N/A',
        'active_client': lead.active_client,
        'referral_type': lead.referral_type,
        'e_contact_name': lead.e_contact_name,
        'e_contact_relation': lead.e_contact_relation,
        'e_contact_phone': lead.e_contact_phone,
        'comments': lead.comments,
    }
    
    # Add payor information
    if lead.agency:
        lead_data['agency_name'] = lead.agency.name
    else:
        lead_data['agency_name'] = 'N/A'
    
    # Add agency suboption information
    if lead.agency_suboption:
        lead_data['agency_suboption_name'] = lead.agency_suboption.name
    else:
        lead_data['agency_suboption_name'] = ''
    
    # Add CCU information
    if lead.ccu:
        lead_data['ccu_name'] = lead.ccu.name
        lead_data['ccu_address'] = lead.ccu.address or ''
        lead_data['ccu_phone'] = lead.ccu.phone or ''
        lead_data['ccu_fax'] = lead.ccu.fax or ''
        lead_data['ccu_email'] = lead.ccu.email or ''
        lead_data['ccu_coordinator'] = lead.ccu.care_coordinator_name or ''
    else:
        lead_data['ccu_name'] = 'N/A'
        lead_data['ccu_address'] = ''
        lead_data['ccu_phone'] = ''
        lead_data['ccu_fax'] = ''
        lead_data['ccu_email'] = ''
        lead_data['ccu_coordinator'] = ''
    
    return lead_data



def get_priority_tag(priority):
    """Returns HTML for a color-coded priority tag"""
    p_class = "priority-medium"
    if priority == "High":
        p_class = "priority-high"
    elif priority == "Low":
        p_class = "priority-low"
    
    return f'<span class="priority-tag {p_class}">{priority}</span>'


def render_api_status():
    """Diagnostic tool to check if the FastAPI backend is running.
    Simplified: Shows only a green/red circle in the sidebar.
    """
    import urllib.request
    import os
    
    # Use the environment variable if available, otherwise default to local
    backend_url = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8003")
    
    st.sidebar.markdown("---")
    
    try:
        # Ping the health endpoint
        with urllib.request.urlopen(f"{backend_url}/health", timeout=3) as response:
            if response.getcode() == 200:
                st.sidebar.markdown("### 🟢")
            else:
                st.sidebar.markdown("### 🔴")
    except Exception:
        st.sidebar.markdown("### 🔴")
