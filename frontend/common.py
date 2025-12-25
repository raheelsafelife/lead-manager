"""
Common utilities, CSS styles, and shared functions for Lead Manager.
"""
import streamlit as st
from app.db import SessionLocal
from app.utils.activity_logger import utc_to_local
import extra_streamlit_components as pyc


# Initialize CookieManager
def get_cookie_manager():
    if 'cookie_manager' not in st.session_state:
        st.session_state.cookie_manager = pyc.CookieManager()
    return st.session_state.cookie_manager


# Global CSS styles (SafeLife UI theme)
GLOBAL_CSS = """
<style>
    /* Import Montserrat from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;800&display=swap');

    html, body, [class^="css"], .stApp  {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                     Arial, 'Source Sans Pro', system-ui, sans-serif;
        background-color: #F9F9F9 !important;
        color: #111827 !important;
    }

    /* Primary brand colors */
    :root {
        --safelife-deep-blue: #00506b;
        --safelife-green: #59B976;
        --safelife-aqua: #3CA5AA;
        --safelife-soft-gray: #F9F9F9;
        --safelife-blue-light: #B5E8F7;
        --safelife-blue-extra-light: #DFF8FF;
        --required-star-pink: #59B976;
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
        background: linear-gradient(90deg, var(--safelife-deep-blue), var(--safelife-aqua));
        padding: 1.5rem 2rem;
        border-radius: 0.75rem;
    }
    
    /* Signup and Forgot Password headers - black text */
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

    /* Buttons – larger, high-contrast CTAs */
    button, .stButton > button, .stForm button, .stForm button[type="submit"] {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        border-radius: 10px;
        border: none;
        padding: 0.75rem 2.0rem;
        background: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
        box-shadow: 0 3px 10px rgba(0, 74, 107, 0.35);
        font-size: 1.05rem;
        letter-spacing: 0.03em;
    }
    
    /* Ensure all button text is white */
    button *, .stButton > button *, .stForm button *, .stForm button[type="submit"] *, button p, .stButton > button p {
        color: #FFFFFF !important;
    }

    /* Primary buttons (active/selected state) - blue background with white text */
    .stButton > button[kind="primary"],
    .stForm button[kind="primary"] {
        background: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
        border: none !important;
    }

    /* Secondary buttons - aqua background with white text */
    .stButton > button[kind="secondary"],
    .stForm button[kind="secondary"] {
        background: var(--safelife-aqua) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 3px 10px rgba(60, 165, 170, 0.35);
    }

    /* Form fields + selectboxes */
    .stTextInput input,
    .stPasswordInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 0.6rem !important;
        border: 1px solid #E5E7EB !important;
        background-color: #FFFFFF !important;
        color: #111827 !important;
        box-shadow: none !important;
        font-weight: 700 !important;
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
    
    /* Force white text for specific headers */
    .white-header-text, .white-header-text * {
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
</style>
"""


def init_session_state():
    """Initialize all session state variables"""
    cookie_manager = get_cookie_manager()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        
        # Check for persistent session in cookies
        auth_cookie = cookie_manager.get(cookie='lead_manager_auth')
        if auth_cookie:
            try:
                import json
                user_data = json.loads(auth_cookie)
                st.session_state.authenticated = True
                st.session_state.username = user_data.get('username')
                st.session_state.user_role = user_data.get('role')
                st.session_state.user_id = user_data.get('user_id')
                # Optional: Refresh scheduler if newly logged in via cookie
            except Exception:
                pass

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


def clear_login_cookies():
    """Clear login cookies on logout"""
    cookie_manager = get_cookie_manager()
    cookie_manager.delete('lead_manager_auth')


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
