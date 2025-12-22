<<<<<<< HEAD
"""
Lead Manager - Main Application Entry Point (Brain)
This file serves as the router and imports page modules from frontend folder.
"""
import streamlit as st

# Page configuration - must be first Streamlit command
=======
import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
from app.db import SessionLocal
from app.db import SessionLocal
from app import crud_users, crud_leads, services_stats, crud_activity_logs, crud_agencies, crud_email_reminders, crud_ccus
from sqlalchemy import func
from app.schemas import UserCreate, LeadCreate, LeadUpdate
from app.utils.activity_logger import format_time_ago, get_action_icon, get_action_label, format_changes, utc_to_local
from app.utils.email_service import send_referral_reminder, send_lead_reminder_email

# Page configuration
>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
st.set_page_config(
    page_title="Lead Manager",
    layout="wide",
    initial_sidebar_state="expanded"
)

<<<<<<< HEAD
# Import page modules from frontend folder
from frontend.common import init_session_state, inject_custom_css
from frontend.auth import login, signup, forgot_password
from frontend.dashboard import dashboard, view_all_user_dashboards, discovery_tool
from frontend.view_leads import view_leads, mark_referral_page
from frontend.add_lead import add_lead
from frontend.referrals_sent import view_referrals
from frontend.referral_confirm import referral_confirm
from frontend.activity_logs import view_activity_logs
from frontend.user_management import admin_panel, update_password, render_historian
from app.email_scheduler import start_scheduler

@st.cache_resource
def init_scheduler():
    """Initialize the email scheduler once"""
    start_scheduler()



def main():
    """Main application logic - Router"""
    # Initialize session state
    init_session_state()
    
    # Inject custom CSS
    inject_custom_css()
    
    # Check authentication
=======
# Global SafeLife UI theme (from brand book)
st.markdown("""
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
    
    /* Filter button section headers - ensure black */
    div[data-testid="stVerticalBlock"] h3,
    div[data-testid="stVerticalBlock"] .stSubheader {
        color: #000000 !important;
    }
    
    /* All text in subheader containers */
    .element-container .stSubheader,
    .element-container .stSubheader * {
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
        color: #FFFFFF !important;  /* White text on blue buttons */
        box-shadow: 0 3px 10px rgba(0, 74, 107, 0.35);
        font-size: 1.05rem;
        letter-spacing: 0.03em;
    }
    
    /* Ensure all button text is white */
    button *, .stButton > button *, .stForm button *, .stForm button[type="submit"] *, button p, .stButton > button p {
        color: #FFFFFF !important;
    }
    
    /* Form submit buttons - blue background with white text */
    .stForm button[type="submit"], 
    form button[type="submit"],
    .stForm .stButton > button {
        background: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    .stForm button[type="submit"]:hover,
    form button[type="submit"]:hover,
    .stForm .stButton > button:hover {
        background: #005f8a !important;
        color: #FFFFFF !important;
    }
    
    /* Login form button specifically - white text */
    form#login_form button {
        background: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
    }
    
    form#login_form button * {
        color: #FFFFFF !important;
    }
    
    form#login_form button:hover {
        background: #005f8a !important;
        color: #FFFFFF !important;
    }
    
    form#login_form button:hover * {
        color: #FFFFFF !important;
    }

    /* Primary buttons (active/selected state) - blue background with white text */
    .stButton > button[kind="primary"],
    .stForm button[kind="primary"] {
        background: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    .stButton > button[kind="primary"] * ,
    .stForm button[kind="primary"] * {
        color: #FFFFFF !important;
    }

    /* Hover / active state – keep primary buttons blue with white text */
    .stButton > button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:active,
    .stButton > button[kind="primary"]:focus,
    .stForm button[kind="primary"]:hover,
    .stForm button[kind="primary"]:active,
    .stForm button[kind="primary"]:focus {
        background: #005f8a !important;
        color: #FFFFFF !important;
        border-color: #005f8a !important;
    }

    .stButton > button[kind="primary"]:hover * ,
    .stButton > button[kind="primary"]:active * ,
    .stButton > button[kind="primary"]:focus * ,
    .stForm button[kind="primary"]:hover * ,
    .stForm button[kind="primary"]:active * ,
    .stForm button[kind="primary"]:focus * {
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
    
    .stButton > button[kind="secondary"] *,
    .stForm button[kind="secondary"] * {
        color: #FFFFFF !important;
    }
    
    .stButton > button[kind="secondary"]:hover,
    .stForm button[kind="secondary"]:hover {
        background: #2d8a8f !important;
        color: #FFFFFF !important;
    }

    /* Form fields + selectboxes (login + all pages) */
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

    .stTextInput input::placeholder,
    .stPasswordInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #9CA3AF !important;
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

    /* Ensure all normal text/sub-headings use near-black for readability */
    p, span, li, label, .stMarkdown, .stText, .stCaption, .stRadio, .stCheckbox,
    .stSelectbox, .stMultiSelect, .stDataFrame, .stTable {
        color: #111827 !important;
    }

    /* Streamlit charts - use aqua color for bars */
    [data-testid="stVegaLiteChart"] {
        --vega-background: transparent;
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
        font-weight: 700 !important; /* Bold text */
        color: #6B7280; /* Gray text for inactive */
        border: 1px solid #E5E7EB;
        border-bottom: none;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--safelife-deep-blue) !important;
        color: #FFFFFF !important; /* White text for active */
        border: none;
    }
    
    /* Force white text for specific headers */
    .white-header-text, .white-header-text * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
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
    try:
        from app.email_scheduler import start_scheduler
        start_scheduler()
        st.session_state.email_scheduler_started = True
    except Exception as e:
        pass  # Scheduler error won't break the app


def prepare_lead_data_for_email(lead, db):
    """Prepare comprehensive lead data dictionary for email reminders"""
    lead_data = {
        'id': lead.id,
        'first_name': lead.first_name,
        'last_name': lead.last_name,
        'phone': lead.phone,
        'email': 'N/A',  # Lead model doesn't have email field
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


def signup():
    """Signup page for new users"""
    # Wrap signup in authentication container
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header main-header-signup">CREATE ACCOUNT</div>', unsafe_allow_html=True)
    
    with st.form("signup_form"):
        # User ID with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">User ID (Unique Identifier)<span class="required-star">*</span></label>', unsafe_allow_html=True)
        user_id = st.text_input("User ID (Unique Identifier)", help="Enter a unique identifier for this user", label_visibility="collapsed")
        
        # Username with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Username<span class="required-star">*</span></label>', unsafe_allow_html=True)
        username = st.text_input("Username", label_visibility="collapsed")
        
        # Email with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Email<span class="required-star">*</span></label>', unsafe_allow_html=True)
        email = st.text_input("Email", label_visibility="collapsed")
        
        # Password with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Password<span class="required-star">*</span></label>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", label_visibility="collapsed")
        
        # Confirm Password with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Confirm Password<span class="required-star">*</span></label>', unsafe_allow_html=True)
        confirm_password = st.text_input("Confirm Password", type="password", label_visibility="collapsed")
        
        col1, col2 = st.columns(2)
        with col1:
            # Blue button (primary)
            submit = st.form_submit_button("Sign Up", type="primary", use_container_width=True)
        with col2:
            # Aqua button (secondary)
            back = st.form_submit_button("Back to Login", type="secondary", use_container_width=True)
        
        if back:
            st.session_state.show_signup = False
            st.rerun()
        
        if submit:
            # Validation
            if not all([user_id, username, email, password]):
                st.error(" Please fill in all fields")
            elif password != confirm_password:
                st.error(" Passwords do not match")
            elif len(password) < 6:
                st.error(" Password must be at least 6 characters")
            elif '@' not in email:
                st.error(" Please enter a valid email")
            else:
                db = SessionLocal()
                try:
                    # Check if user_id already exists
                    existing_user_id = crud_users.get_user_by_user_id(db, user_id)
                    if existing_user_id:
                        st.error(" User ID already taken. Please use a unique identifier.")
                    else:
                        # Check if username or email already exists
                        existing_user = crud_users.get_user_by_username(db, username)
                        if existing_user:
                            st.error(" Username already taken")
                        else:
                            existing_email = crud_users.get_user_by_email(db, email)
                            if existing_email:
                                st.error(" Email already registered")
                            else:
                                # Create user
                                user_data = UserCreate(
                                    user_id=user_id,
                                    username=username,
                                    email=email,
                                    password=password,
                                    role="user"  # Default role
                                )
                                user = crud_users.create_user(db, user_data)
                                st.success("Account created successfully.")
                                st.info("Your account is pending admin approval. You will be able to login once approved.")
                                st.session_state.show_signup = False
                except Exception as e:
                    st.error(f"Error creating account: {e}")
                finally:
                    db.close()
    
    st.markdown('</div>', unsafe_allow_html=True)


def login():
    """Login page"""
    # Inject Login-specific CSS
    st.markdown("""
        <style>
        [data-testid="stForm"] {
            background: #FFFFFF;
            padding: 2.5rem;
            border-radius: 1rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
            width: 100%;
            margin: 2rem auto;
            border: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # Company logo - Large and Left Aligned
    st.image("icon1.png", width=400)
    
    # Slogan just below logo, matching width (400px)
    st.markdown(
        """
        <div style="width: 400px; text-align: center; margin-top: -10px; margin-bottom: 2rem;">
            <p style="color: var(--safelife-deep-blue); font-size: 1.2rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; margin: 0;">
                Keeping You Home, Keeping You Safe!
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Updated title "LEADS MANAGER" - Enhanced Size
    st.markdown(
        """
        <div class="main-header" style="font-size: 4rem !important; text-align: center; margin-bottom: 1rem;">
            LEADS MANAGER
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Login Form (Styled via CSS [data-testid="stForm"])
    with st.form("login_form"):
        # Username with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Username<span class="required-star">*</span></label>', unsafe_allow_html=True)
        username = st.text_input("Username", label_visibility="collapsed")
        
        # Password with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Password<span class="required-star">*</span></label>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", label_visibility="collapsed")
        
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            db = SessionLocal()
            user = crud_users.authenticate_user(db, username, password)
            
            if user == "pending":
                st.warning("Your account is pending admin approval. Please wait for approval before logging in.")
            elif user:
                st.session_state.authenticated = True
                st.session_state.username = user.username
                st.session_state.user_role = user.role
                st.session_state.user_id = user.id
                
                # Log login
                crud_activity_logs.create_activity_log(
                    db=db,
                    user_id=user.id,
                    username=user.username,
                    action_type="USER_LOGIN",
                    entity_type="User",
                    entity_id=user.id,
                    entity_name=user.username,
                    description=f"User '{user.username}' logged in",
                    keywords="auth,login"
                )
                
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid credentials")
            
            db.close()
    
    # Signup and Forgot Password links
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        # Blue button (primary)
        if st.button("Sign Up", use_container_width=True, type="primary"):
            st.session_state.show_signup = True
            st.session_state.show_forgot_password = False
            st.rerun()
    with col2:
        # Aqua button (secondary)
        if st.button("Forgot Password?", use_container_width=True, type="secondary"):
            st.session_state.show_forgot_password = True
            st.session_state.show_signup = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def forgot_password():
    """Forgot password page - creates reset request for admin"""
    # Wrap forgot password in authentication container
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="main-header main-header-forgot">FORGOT PASSWORD</div>', unsafe_allow_html=True)
    
    st.info("Enter your username to request a password reset. An admin will review and reset your password.")
    
    with st.form("forgot_password_form"):
        # Username with pink required star
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Username<span class="required-star">*</span></label>', unsafe_allow_html=True)
        username = st.text_input("Username", label_visibility="collapsed")
        
        col1, col2 = st.columns(2)
        with col1:
            # Blue button (primary)
            submit = st.form_submit_button("Request Reset", type="primary", use_container_width=True)
        with col2:
            # Aqua button (secondary)
            back = st.form_submit_button("Back to Login", type="secondary", use_container_width=True)
        
        if back:
            st.session_state.show_forgot_password = False
            st.rerun()
        
        if submit:
            if not username:
                st.error("Please enter your username")
            else:
                db = SessionLocal()
                try:
                    user = crud_users.request_password_reset(db, username)
                    
                    if user:
                        st.success("Password reset requested.")
                        st.info("Your request has been sent to administrators. They will reset your password shortly.")
                        st.session_state.show_forgot_password = False
                    else:
                        st.error("Username not found")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    db.close()
    
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard():
    """Main dashboard view"""
    db = SessionLocal()
    
    # Header
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
            
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.rerun()
    
    st.divider()
    
    # Admin button to view all user dashboards
    if st.session_state.user_role == "admin":
        if st.button("View All User Dashboards", use_container_width=True, type="primary"):
            st.session_state.show_user_dashboards = True
            st.rerun()
    
    # Toggle buttons for regular users (not admin)
    if st.session_state.user_role != "admin":
        st.subheader("View Mode")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "My Performance",
                use_container_width=True,
                type="primary" if st.session_state.stats_view_mode == "individual" else "secondary"
            ):
                st.session_state.stats_view_mode = "individual"
                st.rerun()
        
        with col2:
            if st.button(
                " Safelife Performance",
                use_container_width=True,
                type="primary" if st.session_state.stats_view_mode == "cumulative" else "secondary"
            ):
                st.session_state.stats_view_mode = "cumulative"
                st.rerun()
        
        st.divider()
    
    # Determine which stats to show based on role and view mode
    show_cumulative = (st.session_state.user_role == "admin" or 
                      (st.session_state.user_role != "admin" and st.session_state.stats_view_mode == "cumulative"))
    
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
                <div class="stat-label">Your Referral s</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{active_leads}</div>
            <div class="stat-label">Referral s</div>
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
                st.bar_chart(df_staff.set_index('staff_name')['count'], color='#00506b')
            else:
                st.info("No data available")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Leads by Source</h4>", unsafe_allow_html=True)
            source_data = services_stats.leads_by_source(db)
            if source_data:
                df_source = pd.DataFrame(source_data)
                st.bar_chart(df_source.set_index('source')['count'], color='#00506b')
            else:
                st.info("No data available")
    else:
        # Regular user sees their own comprehensive data
        with col1:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Your Monthly Leads</h4>", unsafe_allow_html=True)
            monthly_data = services_stats.leads_by_month_for_user(db, st.session_state.username)
            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data)
                st.line_chart(df_monthly.set_index('month')['count'], color='#00506b')
            else:
                st.info("No leads yet")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Your Leads by Source</h4>", unsafe_allow_html=True)
            source_data = services_stats.leads_by_source_for_user(db, st.session_state.username)
            if source_data:
                df_source = pd.DataFrame(source_data)
                st.bar_chart(df_source.set_index('source')['count'], color='#00506b')
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
                st.bar_chart(df_status.set_index('status')['count'], color='#00506b')
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
            st.line_chart(df_monthly.set_index('month')['count'], color='#00506b')
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
            st.bar_chart(df_events.set_index('event_name')['count'], color='#00506b')
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
            st.bar_chart(df_wom.set_index('type')['count'], color='#00506b')
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
                st.line_chart(df_ref_monthly.set_index('month')['count'], color='#00506b')
            else:
                st.info("No referrals yet")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Referral Status</h4>", unsafe_allow_html=True)
            ref_status_data = services_stats.referrals_by_status_for_user(db, st.session_state.username)
            if ref_status_data:
                df_ref_status = pd.DataFrame(ref_status_data)
                st.bar_chart(df_ref_status.set_index('status')['count'], color='#00506b')
            else:
                st.info("No referral status data")

        # More Referral Charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("**Authorization Status**")
            auth_data = services_stats.referrals_by_authorization_for_user(db, st.session_state.username)
            if auth_data:
                df_auth = pd.DataFrame(auth_data)
                st.bar_chart(df_auth.set_index('authorized')['count'], color='#00506b')
            else:
                st.info("No authorization data")

        with col2:
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Care Status</h4>", unsafe_allow_html=True)
            care_data = services_stats.referrals_by_care_status_for_user(db, st.session_state.username)
            if care_data:
                df_care = pd.DataFrame(care_data)
                st.bar_chart(df_care.set_index('care_status')['count'], color='#00506b')
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
            st.bar_chart(df_ref_status.set_index('status')['count'], color='#00506b')
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
            st.bar_chart(df_auth.set_index('status')['count'], color='#00506b')
        else:
            st.info("No referral data yet")

    # End of user referral dashboard conditional block

    st.divider()

    # Lead Confirmation & Conversion Pie Charts
    st.markdown("""
    <div style="background: #FFFFFF; 
                padding: 20px; 
                border-radius: 15px; 
                margin-bottom: 20px;
                border: 1px solid #E5E7EB;">
        <h2 style="text-align: center; color: #00506b; margin-bottom: 5px; letter-spacing:0.08em; text-transform:uppercase;">
                    Lead Pipeline Analytics
        </h2>
        <p style="text-align: center; color: #6B7280; font-size: 14px;">
            Track lead progression through your pipeline
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    # Get lead data for charts
    all_leads = crud_leads.list_leads(db, limit=10000)

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

        if all_total_leads > 0:
            try:
                fig_confirm = go.Figure(data=[go.Pie(
                    labels=['<b>Referrals</b>', '<b>Pending</b>'],
                    values=[all_referrals, all_not_referrals],
                    hole=0.4,
                    marker_colors=['#00506b', '#B5E8F7'],  # Deep Blue and Light Blue
                    textinfo='label+percent',
                    textfont=dict(size=16, color='#000000', family='Montserrat'),
                    textposition='auto',  # Auto positioning for best readability
                    insidetextorientation='horizontal',
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>"
                )])

                fig_confirm.update_layout(
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5,
                        font=dict(color='#000000', size=12)
                    ),
                    paper_bgcolor='#FFFFFF',
                    plot_bgcolor='#FFFFFF',
                    margin=dict(t=20, b=60, l=20, r=20),
                    height=350,
                    annotations=[dict(
                        text=f'<b style="color: #00506b;">{all_referrals}</b><br><span style="color: #6B7280;">Referrals</span>',
                        x=0.5, y=0.5,
                        font_size=18,
                        font_color='#00506b',
                        font_family='Montserrat',
                        showarrow=False
                    )]
                )

                st.plotly_chart(fig_confirm, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating pie chart: {e}")
        else:
            st.info("No leads to display in pie chart")
            
            # Stats below chart
            st.markdown(f"""
            <div style="display: flex; justify-content: space-around; margin-top: 10px;">
                <div style="text-align: center;">
                    <span style="color: #00d4ff; font-size: 24px; font-weight: bold;">{all_referrals}</span>
                    <br><span style="color: #888; font-size: 12px;">Referrals</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #ff6b6b; font-size: 24px; font-weight: bold;">{all_not_referrals}</span>
                    <br><span style="color: #888; font-size: 12px;">Pending</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #64748b; font-size: 24px; font-weight: bold;">{all_total_leads}</span>
                    <br><span style="color: #888; font-size: 12px;">Total Leads</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #FFFFFF; 
                    padding: 15px; 
                    border-radius: 12px;
                    border: 1px solid #4ade80;
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
                marker_colors=['#4ade80', '#f97316', '#64748b'],
                textinfo='label+percent',
                textfont=dict(size=14, color='white'),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>"
            )])
            
            fig_convert.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5,
                    font=dict(color='#111827', size=12)
                ),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='#FFFFFF',
                margin=dict(t=20, b=60, l=20, r=20),
                height=350,
                annotations=[dict(
                    text=f'<b>{care_start}</b><br>Active',
                    x=0.5, y=0.5,
                    font_size=16,
                    font_color='#4ade80',
                    showarrow=False
                )]
            )
            
            st.plotly_chart(fig_convert, use_container_width=True)
            
            # Stats below chart
            st.markdown(f"""
            <div style="display: flex; justify-content: space-around; margin-top: 10px;">
                <div style="text-align: center;">
                    <span style="color: #4ade80; font-size: 24px; font-weight: bold;">{care_start}</span>
                    <br><span style="color: #888; font-size: 12px;">Care Start</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #f97316; font-size: 24px; font-weight: bold;">{not_start}</span>
                    <br><span style="color: #888; font-size: 12px;">Not Start</span>
                </div>
                <div style="text-align: center;">
                    <span style="color: #64748b; font-size: 24px; font-weight: bold;">{pending}</span>
                    <br><span style="color: #888; font-size: 12px;">Pending</span>
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
                    <span style="color: #59B976; font-size: 32px; font-weight: bold;">{conversion_rate:.1f}%</span>
                    <br><span style="color: #4B5563; font-size: 14px;">Conversion Rate</span>
                    <br><span style="color: #6B7280; font-size: 11px;">Referrals → Care Start</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    
    db.close()

def view_leads():
    """View and manage leads"""
    st.markdown('<div class="main-header">Manage Leads</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Initialize status filter in session state
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = "All"
    
    # Initialize my leads filter
    if 'show_only_my_leads' not in st.session_state:
        st.session_state.show_only_my_leads = True  # Default to showing only user's leads
    
    # Toggle buttons for regular users to switch between My Leads and All Leads
    if st.session_state.user_role != "admin":
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>View Mode</h4>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "My Leads",
                use_container_width=True,
                type="primary" if st.session_state.show_only_my_leads else "secondary"
            ):
                st.session_state.show_only_my_leads = True
                st.rerun()
        
        with col2:
            if st.button(
                "All Leads",
                use_container_width=True,
                type="primary" if not st.session_state.show_only_my_leads else "secondary"
            ):
                st.session_state.show_only_my_leads = False
                st.rerun()
        
        st.divider()
    
    # Contact Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Filter by Contact Status</h4>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button("Intro Call", use_container_width=True, 
                    type="primary" if st.session_state.status_filter == "Intro Call" else "secondary"):
            st.session_state.status_filter = "Intro Call"
            st.rerun()
    
    with col2:
        if st.button("Follow Up", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "Follow Up" else "secondary"):
            st.session_state.status_filter = "Follow Up"
            st.rerun()
    
    with col3:
        if st.button("No Response", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "No Response" else "secondary"):
            st.session_state.status_filter = "No Response"
            st.rerun()
    
    with col4:
        if st.button("Intake Call", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "Intake Call" else "secondary"):
            st.session_state.status_filter = "Intake Call"
            st.rerun()
    
    with col5:
        if st.button("Inactive", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "Inactive" else "secondary"):
            st.session_state.status_filter = "Inactive"
            st.rerun()
    
    with col6:
        if st.button("All", use_container_width=True,
                    type="primary" if st.session_state.status_filter == "All" else "secondary"):
            st.session_state.status_filter = "All"
            st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3 = st.columns(3)
    with col1:
        search_name = st.text_input("**Search by name**")
    with col2:
        filter_staff = st.text_input("**Filter by staff**")
    with col3:
        filter_source = st.text_input("**Filter by source**")
    
    # Get leads
    leads = crud_leads.list_leads(db, limit=100)
    
    # Apply 'Show Only My Leads' filter for regular users
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_leads:
        leads = [l for l in leads if l.staff_name == st.session_state.username]
    
    # Apply contact status filter
    if st.session_state.status_filter != "All":
        leads = [l for l in leads if l.last_contact_status == st.session_state.status_filter]
    
    # Apply other filters
    if search_name:
        leads = [l for l in leads if search_name.lower() in f"{l.first_name} {l.last_name}".lower()]
    if filter_staff:
        leads = [l for l in leads if filter_staff.lower() in l.staff_name.lower()]
    if filter_source:
        leads = [l for l in leads if filter_source.lower() in l.source.lower()]
    
    # Show count with filter info
    filter_info = f"Status: {st.session_state.status_filter}"
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_leads:
        filter_info += f" | Showing: My Leads Only"
    st.write(f"**Showing {len(leads)} leads ({filter_info})**")
    
    # Display leads
    if leads:
        for lead in leads:
            with st.expander(f"{lead.first_name} {lead.last_name} - {lead.staff_name}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {lead.id}")
                    st.write(f"**Name:** {lead.first_name} {lead.last_name}")
                    st.write(f"**Staff:** {lead.staff_name}")
                    st.write(f"**Source:** {lead.source}")
                    st.write(f"**Phone:** {lead.phone}")
                    st.write(f"**City:** {lead.city or 'N/A'}")
                
                with col2:
                    st.write(f"**Status:** {lead.last_contact_status}")
                    st.write(f"**Referral:** {'Yes' if lead.active_client else 'No'}")
                    st.write(f"**Created:** {utc_to_local(lead.created_at).strftime('%Y-%m-%d')}")
                    st.write(f"**Updated:** {utc_to_local(lead.updated_at).strftime('%Y-%m-%d')}")
                    if lead.comments:
                        st.write(f"**Comments:** {lead.comments}")
                
                # Creator/Updater Info
                st.divider()
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    if lead.created_by:
                        st.markdown(f"**Created by: {lead.created_by} on {utc_to_local(lead.created_at).strftime('%m/%d/%Y at %I:%M %p')}**")
                    else:
                        st.markdown(f"**Created on {utc_to_local(lead.created_at).strftime('%m/%d/%Y')}**")
                
                with info_col2:
                    if lead.updated_by:
                        st.markdown(f"**Last updated by: {lead.updated_by} on {utc_to_local(lead.updated_at).strftime('%m/%d/%Y at %I:%M %p')}**")
                    else:
                        st.markdown(f"**Last updated on {utc_to_local(lead.updated_at).strftime('%m/%d/%Y')}**")
                
                # Permission check for edit/delete
                can_modify = (st.session_state.user_role == "admin" or 
                             lead.staff_name == st.session_state.username)
                
                if not can_modify:
                    st.warning(" You can only edit/delete your own leads")
                
                # Action buttons row
                col1, col2, col_email, col3, col4 = st.columns([0.8, 0.8, 1.2, 1.5, 1.5])
                with col1:
                    if can_modify and st.button(" Edit", key=f"edit_{lead.id}"):
                        st.session_state[f'editing_{lead.id}'] = True
                        st.rerun()
                with col2:
                    if can_modify and st.button(" Delete", key=f"delete_{lead.id}"):
                        crud_leads.delete_lead(db, lead.id, st.session_state.username, st.session_state.get('user_id'))
                        st.success(" Lead deleted")
                        st.rerun()
                with col_email:
                    # Email reminder button - only show if not inactive or referral
                    if lead.last_contact_status != "Inactive" and not lead.active_client:
                        if st.button("📧 Send Reminder", key=f"email_{lead.id}"):
                            st.session_state[f'sending_email_{lead.id}'] = True
                            st.rerun()
                    else:
                        if lead.active_client:
                            st.caption("Is Referral")
                        else:
                            st.caption("Inactive")
                
                # Email sending section
                if st.session_state.get(f'sending_email_{lead.id}', False):
                    st.divider()
                    st.write("**📧 Send Reminder Email**")
                    
                    # Get user's email
                    user = crud_users.get_user_by_username(db, st.session_state.username)
                    default_email = user.email if user else ""
                    
                    with st.form(f"email_form_{lead.id}"):
                        recipient_email = st.text_input("Recipient Email", value=default_email, 
                                                       help="Enter the email address to receive the reminder")
                        
                        col_send, col_cancel = st.columns(2)
                        with col_send:
                            send_btn = st.form_submit_button(" Send Email", type="primary")
                        with col_cancel:
                            cancel_btn = st.form_submit_button(" Cancel")
                        
                        if cancel_btn:
                            st.session_state[f'sending_email_{lead.id}'] = False
                            st.rerun()
                        
                        if send_btn:
                            if not recipient_email:
                                st.error(" Please enter a recipient email")
                            else:
                                try:
                                    # Prepare lead data
                                    lead_data = prepare_lead_data_for_email(lead, db)
                                    
                                    # Send email
                                    success = send_lead_reminder_email(lead_data, recipient_email)
                                    
                                    if success:
                                        # Record the email reminder
                                        crud_email_reminders.create_reminder(
                                            db=db,
                                            lead_id=lead.id,
                                            recipient_email=recipient_email,
                                            subject=f"Lead Reminder: {lead.first_name} {lead.last_name}",
                                            sent_by=st.session_state.username,
                                            status="sent"
                                        )
                                        st.success(f" Reminder email sent to {recipient_email}!")
                                        st.session_state[f'sending_email_{lead.id}'] = False
                                        st.rerun()
                                    else:
                                        # Record failed attempt
                                        crud_email_reminders.create_reminder(
                                            db=db,
                                            lead_id=lead.id,
                                            recipient_email=recipient_email,
                                            subject=f"Lead Reminder: {lead.first_name} {lead.last_name}",
                                            sent_by=st.session_state.username,
                                            status="failed",
                                            error_message="Email service error"
                                        )
                                        st.error(" Failed to send email. Please check email configuration.")
                                except Exception as e:
                                    st.error(f" Error: {str(e)}")
                    
                    # Show email history for this lead
                    reminders = crud_email_reminders.get_reminders_by_lead(db, lead.id)
                    if reminders:
                        st.caption(f"Email History ({len(reminders)} sent):")
                        for reminder in reminders[:3]:  # Show last 3
                            status_icon = "" if reminder.status == "sent" else ""
                            st.caption(f"{status_icon} {utc_to_local(reminder.sent_at).strftime('%m/%d/%Y %I:%M %p')} → {reminder.recipient_email}")
                
                with col3:
                    # Toggle Referral button
                    if can_modify:
                        if not lead.active_client:
                            # Not a referral yet -> Navigate to Mark Referral page
                            if st.button("Mark Referral", key=f"mark_ref_btn_{lead.id}"):
                                st.session_state['mark_referral_lead_id'] = lead.id
                                st.session_state['current_page'] = 'Mark Referral Page'
                                st.rerun()
                        else:
                            # Already a referral -> Show Unmark button
                            if st.button("Unmark Referral", key=f"unmark_ref_{lead.id}", type="primary"):
                                update_data = LeadUpdate(active_client=False, referral_type=None)
                                crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                                st.success(" Unmarked as Referral!")
                                st.rerun()
                
                with col4:
                    # History button
                    if st.button("History", key=f"history_{lead.id}"):
                        # Toggle history view
                        key = f"show_history_{lead.id}"
                        st.session_state[key] = not st.session_state.get(key, False)
                        st.rerun()
                
                # History View
                if st.session_state.get(f"show_history_{lead.id}", False):
                    st.info(f"Activity History for {lead.first_name} {lead.last_name}")
                    history_logs = crud_activity_logs.get_lead_history(db, lead.id)
                    
                    if history_logs:
                        for log in history_logs:
                            label = get_action_label(log.action_type)
                            time_ago = format_time_ago(log.timestamp)
                            
                            with st.container():
                                st.markdown(f"**{label}** - {time_ago}")
                                st.caption(f"By **{log.username}** on {utc_to_local(log.timestamp).strftime('%m/%d/%Y at %I:%M %p')}")
                                
                                if log.description:
                                    st.write(log.description)
                                
                                if log.old_value and log.new_value:
                                    changes = format_changes(log.old_value, log.new_value)
                                    if changes:
                                        for field, old_val, new_val in changes:
                                            st.caption(f"• {field}: {old_val} → {new_val}")
                                st.divider()
                    else:
                        st.caption("No history recorded yet.")

                
                # Edit form (shown when Edit button is clicked)
                if st.session_state.get(f'editing_{lead.id}', False):
                    st.divider()
                    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Edit Lead</h4>", unsafe_allow_html=True)
                    
                    with st.form(f"edit_form_{lead.id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_staff_name = st.text_input("**Staff Name** *", value=lead.staff_name)
                            edit_first_name = st.text_input("**First Name** *", value=lead.first_name)
                            edit_last_name = st.text_input("**Last Name** *", value=lead.last_name)
                            edit_source = st.selectbox("**Source** *", 
                                                      ["HHN", "Web", "Referral", "Event", "Other"],
                                                      index=["HHN", "Web", "Referral", "Event", "Other"].index(lead.source) if lead.source in ["HHN", "Web", "Referral", "Event", "Other"] else 0)
                            edit_phone = st.text_input("**Phone** *", value=lead.phone)
                            edit_city = st.text_input("**City**", value=lead.city or "")
                            edit_zip_code = st.text_input("**Zip Code**", value=lead.zip_code or "")
                        
                        
                        with col2:
                            edit_status = st.selectbox("**Contact Status**", 
                                                      ["Intro Call", "Follow Up", "No Response", "Intake Call", "Inactive"],
                                                      index=["Intro Call", "Follow Up", "No Response", "Intake Call", "Inactive"].index(lead.last_contact_status) if lead.last_contact_status in ["Intro Call", "Follow Up", "No Response", "Intake Call", "Inactive"] else 0)
                            edit_dob = st.date_input("**Date of Birth**", value=lead.dob)
                            edit_medicaid_no = st.text_input("**Medicaid Number**", value=lead.medicaid_no or "")
                            edit_e_contact_name = st.text_input("**Emergency Contact Name**", value=lead.e_contact_name or "")
                            edit_e_contact_phone = st.text_input("**Emergency Contact Phone**", value=lead.e_contact_phone or "")
                            edit_comments = st.text_area("**Comments**", value=lead.comments or "")
                        
                        st.divider()
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            save = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
                        with col2:
                            cancel = st.form_submit_button(" Cancel", use_container_width=True)
                        
                        if save:
                            update_data = LeadUpdate(
                                staff_name=edit_staff_name,
                                first_name=edit_first_name,
                                last_name=edit_last_name,
                                source=edit_source,
                                phone=edit_phone,
                                city=edit_city or None,
                                zip_code=edit_zip_code or None,
                                active_client=lead.active_client,  # Keep unchanged - use Toggle button instead
                                last_contact_status=edit_status,
                                dob=edit_dob if edit_dob else None,
                                medicaid_no=edit_medicaid_no or None,
                                e_contact_name=edit_e_contact_name or None,
                                e_contact_phone=edit_e_contact_phone or None,
                                comments=edit_comments or None
                            )
                            
                            crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                            st.session_state[f'editing_{lead.id}'] = False
                            st.success(" Lead updated successfully!")
                            st.rerun()
                        
                        if cancel:
                            st.session_state[f'editing_{lead.id}'] = False
                            st.rerun()
    else:
        st.info("No leads found")
    
    db.close()


def mark_referral_page():
    """Hidden page for marking a lead as referral with Payor and CCU selection"""
    st.markdown('<div class="main-header">Mark Referral</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Get the lead ID from session state
    lead_id = st.session_state.get('mark_referral_lead_id')
    
    if not lead_id:
        st.warning(" No lead selected. Please go to View Leads and click 'Mark Referral' on a lead.")
        if st.button("Go to View Leads"):
            st.session_state['current_page'] = None
            st.rerun()
        db.close()
        return
    
    # Get the lead
    lead = crud_leads.get_lead(db, lead_id)
    
    if not lead:
        st.error(" Lead not found")
        if st.button("Go to View Leads"):
            st.session_state['current_page'] = None
            st.session_state['mark_referral_lead_id'] = None
            st.rerun()
        db.close()
        return
    
    # Back button
    if st.button("Back to Referrals"):
        st.session_state['current_page'] = None
        st.session_state['mark_referral_lead_id'] = None
        st.rerun()
    
    st.divider()
    
    # Show lead details
    st.markdown(f"<h4 style='font-weight: bold; color: #00506b;'>{lead.first_name} {lead.last_name}</h4>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**ID:** {lead.id}")
        st.write(f"**Staff:** {lead.staff_name}")
        st.write(f"**Phone:** {lead.phone}")
        st.write(f"**Source:** {lead.source}")
    with col2:
        st.write(f"**Status:** {lead.last_contact_status}")
        st.write(f"**City:** {lead.city or 'N/A'}")
        st.write(f"**Medicaid #:** {lead.medicaid_no or 'N/A'}")
    
    st.divider()
    
    # Referral Type Selection
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Select Referral Type and Payor</h4>", unsafe_allow_html=True)
    
    ref_type = st.radio("**Referral Type:**", ["Regular", "Interim"], horizontal=True)
    
    st.divider()
    
    # Payor Selection
    st.write("**Payor:**")
    agencies = crud_agencies.get_all_agencies(db)
    agency_options = {a.name: a.id for a in agencies}
    
    if not agencies:
        st.warning(" No payors available.")
        selected_agency_name = "None"
    else:
        agency_list = ["None"] + list(agency_options.keys())
        selected_agency_name = st.selectbox("Select Payor", agency_list, label_visibility="collapsed")
    
    final_agency_id = agency_options.get(selected_agency_name) if selected_agency_name != "None" else None
    
    # Payor Suboption Selection (if agency selected)
    final_agency_suboption_id = None
    if final_agency_id:
        from app import crud_agency_suboptions
        suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=final_agency_id)
        
        if suboptions:
            st.write("**Suboption:**")
            suboption_options = {s.name: s.id for s in suboptions}
            suboption_list = ["None"] + list(suboption_options.keys())
            selected_suboption_name = st.selectbox("Select suboption", suboption_list, label_visibility="collapsed")
            
            if selected_suboption_name != "None":
                final_agency_suboption_id = suboption_options.get(selected_suboption_name)
    
    st.divider()
    
    # CCU Selection
    st.write("**CCU Details:**")
    from app import crud_ccus
    ccus = crud_ccus.get_all_ccus(db)
    ccu_options = {c.name: c.id for c in ccus}
    
    selected_ccu_id = None
    if not ccus:
        st.info(" No CCUs available.")
    else:
        ccu_list = ["None"] + list(ccu_options.keys())
        selected_ccu_name = st.selectbox("Select CCU", ccu_list, label_visibility="collapsed")
        
        if selected_ccu_name != "None":
            selected_ccu_id = ccu_options.get(selected_ccu_name)
    
    st.divider()
    
    # Action Buttons
    col_confirm, col_cancel = st.columns(2)
    
    with col_confirm:
        if st.button("Confirm", type="primary", use_container_width=True):
            update_data = LeadUpdate(
                active_client=True,
                referral_type=ref_type,
                agency_id=final_agency_id,
                agency_suboption_id=final_agency_suboption_id,
                ccu_id=selected_ccu_id
            )
            crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
            
            # Send email reminder
            try:
                current_user = crud_users.get_user_by_username(db, st.session_state.username)
                if current_user and current_user.email:
                    payor_str = selected_agency_name if selected_agency_name != "None" else None
                    payor_suboption_str = None
                    if final_agency_suboption_id:
                        from app import crud_agency_suboptions
                        suboption = crud_agency_suboptions.get_suboption_by_id(db, final_agency_suboption_id)
                        if suboption:
                            payor_suboption_str = suboption.name
                    
                    ccu_details = {}
                    if selected_ccu_id:
                        ccu = crud_ccus.get_ccu_by_id(db, selected_ccu_id)
                        if ccu:
                            ccu_details = {
                                'ccu_name': ccu.name,
                                'ccu_address': ccu.address,
                                'ccu_email': ccu.email,
                                'ccu_fax': ccu.fax,
                                'ccu_phone': ccu.phone,
                                'ccu_coordinator': ccu.care_coordinator_name
                            }
                    
                    send_referral_reminder(
                        current_user.email,
                        st.session_state.username,
                        f"{lead.first_name} {lead.last_name}",
                        lead.id,
                        payor_name=payor_str,
                        payor_suboption=payor_suboption_str,
                        phone=lead.phone,
                        source=lead.source,
                        **ccu_details
                    )
            except Exception as e:
                pass  # Silent fail for email
            
            st.success(f" Marked as {ref_type} Referral!")
            st.session_state['current_page'] = None
            st.session_state['mark_referral_lead_id'] = None
            st.rerun()
    
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.session_state['current_page'] = None
            st.session_state['mark_referral_lead_id'] = None
            st.rerun()
    
    db.close()


def view_referrals():
    """View and manage referrals only"""
    st.markdown('<div class="main-header">Referrals</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Initialize status filter in session state
    if 'referral_status_filter' not in st.session_state:
        st.session_state.referral_status_filter = "All"
    
    # Initialize my referrals filter
    if 'show_only_my_referrals' not in st.session_state:
        st.session_state.show_only_my_referrals = True  # Default to showing only user's referrals
    
    # Toggle buttons for regular users to switch between My Referrals and All Referrals
    if st.session_state.user_role != "admin":
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>View Mode</h4>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "My Referrals",
                use_container_width=True,
                type="primary" if st.session_state.show_only_my_referrals else "secondary"
            ):
                st.session_state.show_only_my_referrals = True
                st.rerun()
        
        with col2:
            if st.button(
                "All Referrals",
                use_container_width=True,
                type="primary" if not st.session_state.show_only_my_referrals else "secondary"
            ):
                st.session_state.show_only_my_referrals = False
                st.rerun()
        
        st.divider()
    
    # Contact Status Filter Buttons
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Filter by Contact Status</h4>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button("Intro Call", use_container_width=True, 
                    type="primary" if st.session_state.referral_status_filter == "Intro Call" else "secondary"):
            st.session_state.referral_status_filter = "Intro Call"
            st.rerun()
    
    with col2:
        if st.button("Follow Up", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "Follow Up" else "secondary"):
            st.session_state.referral_status_filter = "Follow Up"
            st.rerun()
    
    with col3:
        if st.button("No Response", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "No Response" else "secondary"):
            st.session_state.referral_status_filter = "No Response"
            st.rerun()
    
    with col4:
        if st.button("Intake Call", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "Intake Call" else "secondary"):
            st.session_state.referral_status_filter = "Intake Call"
            st.rerun()
    
    with col5:
        if st.button("Inactive", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "Inactive" else "secondary"):
            st.session_state.referral_status_filter = "Inactive"
            st.rerun()
    
    with col6:
        if st.button("All", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "All" else "secondary"):
            st.session_state.referral_status_filter = "All"
            st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3 = st.columns(3)
    with col1:
        search_name = st.text_input("**Search by name**")
    with col2:
        filter_staff = st.text_input("**Filter by staff**")
    with col3:
        filter_source = st.text_input("**Filter by source**")
        
    # Referral Type Filter Buttons
    st.write("**Filter by Referral Type:**")
    col_t1, col_t2, col_t3 = st.columns([1, 1, 3])
    
    # Initialize referral type filter
    if 'referral_type_filter' not in st.session_state:
        st.session_state.referral_type_filter = "All"
        
    with col_t1:
        if st.button("Regular", type="primary" if st.session_state.referral_type_filter == "Regular" else "secondary", key="filter_reg"):
            st.session_state.referral_type_filter = "Regular"
            st.rerun()
            
    with col_t2:
        if st.button("Interim", type="primary" if st.session_state.referral_type_filter == "Interim" else "secondary", key="filter_int"):
            st.session_state.referral_type_filter = "Interim"
            st.rerun()
            
    with col_t3:
        if st.button("All Types", type="primary" if st.session_state.referral_type_filter == "All" else "secondary", key="filter_all_types"):
            st.session_state.referral_type_filter = "All"
            st.rerun()
    
    # Payor Filter
    st.write("**Filter by Payor:**")
    agencies = crud_agencies.get_all_agencies(db)
    
    if 'payor_filter' not in st.session_state:
        st.session_state.payor_filter = "All"
    
    if agencies:
        agency_names = ["All"] + [a.name for a in agencies]
        selected_payor = st.selectbox("Select Payor", agency_names, index=agency_names.index(st.session_state.payor_filter) if st.session_state.payor_filter in agency_names else 0, key="payor_filter_select")
        
        if selected_payor != st.session_state.payor_filter:
            st.session_state.payor_filter = selected_payor
            st.rerun()
    else:
        st.info("No payors available. Add payors in User Management -> Payor.")
    
    # CCU Filter
    st.write("**Filter by CCU:**")
    from app import crud_ccus
    
    ccus = crud_ccus.get_all_ccus(db)
    
    if 'ccu_filter' not in st.session_state:
        st.session_state.ccu_filter = "All"
    
    if ccus:
        ccu_names = ["All"] + [c.name for c in ccus]
        selected_ccu = st.selectbox("Select CCU", ccu_names, index=ccu_names.index(st.session_state.ccu_filter) if st.session_state.ccu_filter in ccu_names else 0, key="ccu_filter_select")
        
        if selected_ccu != st.session_state.ccu_filter:
            st.session_state.ccu_filter = selected_ccu
            st.rerun()
    else:
        st.info("No CCUs available. Add CCUs in User Management -> CCU.")
    
    st.divider()
    
    # Get all leads
    leads = crud_leads.list_leads(db, limit=1000)
    
    # FILTER: Only show referrals (active_client = True)
    leads = [l for l in leads if l.active_client == True]
    
    # Apply 'Show Only My Referrals' filter for regular users
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_referrals:
        leads = [l for l in leads if l.staff_name == st.session_state.username]
    
    # Apply contact status filter
    if st.session_state.referral_status_filter != "All":
        leads = [l for l in leads if l.last_contact_status == st.session_state.referral_status_filter]
    
    # Apply other filters
    if search_name:
        leads = [l for l in leads if search_name.lower() in f"{l.first_name} {l.last_name}".lower()]
    if filter_staff:
        leads = [l for l in leads if filter_staff.lower() in l.staff_name.lower()]
    if filter_source:
        leads = [l for l in leads if filter_source.lower() in l.source.lower()]
        
    # Apply Payor filter
    if st.session_state.payor_filter != "All":
        leads = [l for l in leads if l.agency and l.agency.name == st.session_state.payor_filter]
    
    # Apply CCU filter
    if st.session_state.ccu_filter != "All":
        leads = [l for l in leads if l.ccu and l.ccu.name == st.session_state.ccu_filter]
    
    # Apply Referral Type filter
    if st.session_state.referral_type_filter != "All":
        leads = [l for l in leads if l.referral_type == st.session_state.referral_type_filter]
    
    # Show count with filter info
    filter_info = f"Status: {st.session_state.referral_status_filter}"
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_referrals:
        filter_info += f" | Showing: My Referrals Only"
    st.write(f"**Showing {len(leads)} referrals** ({filter_info})")
    
    # Display referrals
    if leads:
        for lead in leads:
            with st.expander(f"{lead.first_name} {lead.last_name} - {lead.staff_name}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {lead.id}")
                    st.write(f"**Name:** {lead.first_name} {lead.last_name}")
                    st.write(f"**Staff:** {lead.staff_name}")
                    st.write(f"**Source:** {lead.source}")
                    st.write(f"**Phone:** {lead.phone}")
                    st.write(f"**City:** {lead.city or 'N/A'}")
                
                with col2:
                    st.write(f"**Status:** {lead.last_contact_status}")
                    st.success(f"**Referral:** Yes ({lead.referral_type or 'Regular'})")
                    if lead.agency:
                        st.info(f"**Payor:** {lead.agency.name}")
                    if lead.ccu:
                        st.info(f"**CCU:** {lead.ccu.name}")
                    # Authorization Status
                    if lead.authorization_received:
                        soc_str = lead.soc_date.strftime('%m/%d/%Y') if lead.soc_date else 'Not Set'
                        st.success(f"**Auth:** Received | **Care:** {lead.care_status or 'N/A'} | **SOC:** {soc_str}")
                    else:
                        st.warning("**Auth:** Pending")
                    st.write(f"**Created:** {utc_to_local(lead.created_at).strftime('%Y-%m-%d')}")
                    st.write(f"**Updated:** {utc_to_local(lead.updated_at).strftime('%Y-%m-%d')}")
                    if lead.comments:
                        st.write(f"**Comments:** {lead.comments}")
                
                # Creator/Updater Info
                st.divider()
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    if lead.created_by:
                        st.markdown(f"**Created by: {lead.created_by} on {utc_to_local(lead.created_at).strftime('%m/%d/%Y at %I:%M %p')}**")
                    else:
                        st.markdown(f"**Created on {utc_to_local(lead.created_at).strftime('%m/%d/%Y')}**")
                
                with info_col2:
                    if lead.updated_by:
                        st.markdown(f"**Last updated by: {lead.updated_by} on {utc_to_local(lead.updated_at).strftime('%m/%d/%Y at %I:%M %p')}**")
                    else:
                        st.markdown(f"**Last updated on {utc_to_local(lead.updated_at).strftime('%m/%d/%Y')}**")
                
                # Permission check for edit/delete
                can_modify = (st.session_state.user_role == "admin" or 
                             lead.staff_name == st.session_state.username)
                
                if not can_modify:
                    st.warning(" You can only edit/delete your own referrals")
                
                # Action buttons
                col1, col2, col3, col4 = st.columns([1.0, 1.0, 2.0, 2.0])
                with col1:
                    if can_modify and st.button(" Edit", key=f"edit_ref_{lead.id}"):
                        st.session_state[f'editing_{lead.id}'] = True
                        st.rerun()
                with col2:
                    if can_modify and st.button(" Delete", key=f"delete_ref_{lead.id}"):
                        crud_leads.delete_lead(db, lead.id, st.session_state.username, st.session_state.get('user_id'))
                        st.success(" Referral deleted")
                        st.rerun()
                with col3:
                    # Show automatic email status
                    if lead.last_contact_status != "Inactive":
                        schedule = "6h x 2 days" if lead.referral_type == "Interim" else "24h x 7 days"
                        st.caption(f"Auto-emails: {schedule}")
                    else:
                        st.caption("Inactive - No emails")
                
                # Show email history for this referral
                reminders = crud_email_reminders.get_reminders_by_lead(db, lead.id)
                if reminders:
                    st.caption(f" Email History ({len(reminders)} sent):")
                    for reminder in reminders[:3]:  # Show last 3
                        status_icon = "" if reminder.status == "sent" else ""
                        st.caption(f"{status_icon} {utc_to_local(reminder.sent_at).strftime('%m/%d/%Y %I:%M %p')} -> {reminder.recipient_email}")
                
                with col3:
                    # Unmark Referral button (always shows unmark since we're in referrals view)
                    if can_modify:
                        if st.button("Unmark Referral", key=f"unmark_ref_{lead.id}", type="primary"):
                            # Toggle the referral status to False
                            update_data = LeadUpdate(
                                staff_name=lead.staff_name,
                                first_name=lead.first_name,
                                last_name=lead.last_name,
                                source=lead.source,
                                phone=lead.phone,
                                city=lead.city,
                                zip_code=lead.zip_code,
                                active_client=False,  # Unmark as referral
                                last_contact_status=lead.last_contact_status,
                                dob=lead.dob,
                                medicaid_no=lead.medicaid_no,
                                e_contact_name=lead.e_contact_name,
                                e_contact_phone=lead.e_contact_phone,
                                comments=lead.comments
                            )
                            crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                            st.success(f" Lead unmarked as Referral!")
                            st.rerun()
                
                with col4:
                    # History button and Authorization Received button side by side
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("History", key=f"history_ref_{lead.id}"):
                            # Toggle history view
                            key = f"show_history_ref_{lead.id}"
                            st.session_state[key] = not st.session_state.get(key, False)
                            st.rerun()
                    
                    with btn_col2:
                        # Authorization Received button - toggleable
                        if lead.authorization_received:
                            # Show unmark button if already authorized
                            if st.button("Unmark Auth", key=f"unmark_auth_ref_{lead.id}",
                                       help="Remove authorization received status"):
                                update_data = LeadUpdate(authorization_received=False)
                                updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                                if updated_lead:
                                    st.warning(f" Authorization unmarked for {lead.first_name} {lead.last_name}")
                                    st.rerun()
                                else:
                                    st.error(" Failed to unmark authorization")
                        else:
                            # Show mark as received button if not authorized
                            if st.button("Authorization Received", key=f"auth_ref_{lead.id}",
                                       help="Mark this referral as having received authorization"):
                                # Mark authorization as received
                                update_data = LeadUpdate(authorization_received=True)
                                updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                                if updated_lead:
                                    st.success(f" Authorization marked as received for {lead.first_name} {lead.last_name}")

                                    # Send authorization confirmation email
                                    try:
                                        # Get user email
                                        user = crud_users.get_user_by_username(db, st.session_state.username)
                                        if user and user.email:
                                            # Prepare referral data for email
                                            agency_name = "N/A"
                                            if lead.agency_id:
                                                agency = crud_agencies.get_agency(db, lead.agency_id)
                                                if agency:
                                                    agency_name = agency.name

                                            auth_data = {
                                                'name': f"{lead.first_name} {lead.last_name}",
                                                'phone': lead.phone,
                                                'creator': lead.created_by,
                                                'created_date': lead.created_at.strftime('%m/%d/%Y'),
                                                'referral_type': lead.referral_type or 'Regular',
                                                'payor_name': agency_name,
                                                'auth_date': datetime.utcnow().strftime('%m/%d/%Y %I:%M %p')
                                            }

                                            # Send authorization confirmation email
                                            from app.utils.email_service import send_authorization_confirmation_email
                                            success = send_authorization_confirmation_email(auth_data, user.email)

                                            if success:
                                                st.info(" Authorization confirmation email sent")
                                            else:
                                                st.warning(" Authorization marked but email failed to send")
                                    except Exception as e:
                                        st.warning(" Authorization marked but email failed to send")

                                    # Store lead id and navigate to Referral Confirm page
                                    st.session_state['referral_confirm_lead_id'] = lead.id
                                    st.session_state['current_page'] = 'Referral Confirm'
                                    st.rerun()
                                else:
                                    st.error(" Failed to mark authorization as received")
                
                # History View
                if st.session_state.get(f"show_history_ref_{lead.id}", False):
                    st.info(f"Activity History for {lead.first_name} {lead.last_name}")
                    history_logs = crud_activity_logs.get_lead_history(db, lead.id)
                    
                    if history_logs:
                        for log in history_logs:
                            label = get_action_label(log.action_type)
                            time_ago = format_time_ago(log.timestamp)
                            
                            with st.container():
                                st.markdown(f"**{label}** - {time_ago}")
                                st.caption(f"By **{log.username}** on {utc_to_local(log.timestamp).strftime('%m/%d/%Y at %I:%M %p')}")
                                
                                if log.description:
                                    st.write(log.description)
                                
                                if log.old_value and log.new_value:
                                    changes = format_changes(log.old_value, log.new_value)
                                    if changes:
                                        for field, old_val, new_val in changes:
                                            st.caption(f"• {field}: {old_val} -> {new_val}")
                                st.divider()
                    else:
                        st.caption("No history recorded yet.")

                
                # Edit form (shown when Edit button is clicked)
                if st.session_state.get(f'editing_{lead.id}', False):
                    st.divider()
                    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Edit Referral</h4>", unsafe_allow_html=True)
                    
                    with st.form(f"edit_ref_form_{lead.id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_staff_name = st.text_input("**Staff Name** *", value=lead.staff_name)
                            edit_first_name = st.text_input("**First Name** *", value=lead.first_name)
                            edit_last_name = st.text_input("**Last Name** *", value=lead.last_name)
                            edit_source = st.selectbox("**Source** *", 
                                                      ["HHN", "Web", "Referral", "Event", "Other"],
                                                      index=["HHN", "Web", "Referral", "Event", "Other"].index(lead.source) if lead.source in ["HHN", "Web", "Referral", "Event", "Other"] else 0)
                            edit_phone = st.text_input("**Phone** *", value=lead.phone)
                            edit_city = st.text_input("**City**", value=lead.city or "")
                            edit_zip_code = st.text_input("**Zip Code**", value=lead.zip_code or "")
                            
                            # Payor Selection (only if active client)
                            edit_agency_id = None
                            edit_ccu_id = None
                            if lead.active_client:
                                from app import crud_ccus
                                agencies = crud_agencies.get_all_agencies(db)
                                agency_options = {a.name: a.id for a in agencies}
                                current_agency_name = lead.agency.name if lead.agency else "None"
                                edit_agency_name = st.selectbox("**Payor**", ["None"] + list(agency_options.keys()), 
                                                              index=(["None"] + list(agency_options.keys())).index(current_agency_name) if current_agency_name in agency_options else 0)
                                
                                # Get payor ID
                                edit_agency_id = agency_options.get(edit_agency_name) if edit_agency_name != "None" else None
                                
                                # Payor Suboption Selection (if agency selected)
                                edit_agency_suboption_id = None
                                if edit_agency_id:
                                    from app import crud_agency_suboptions
                                    suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=edit_agency_id)
                                    
                                    if suboptions:
                                        suboption_options = {s.name: s.id for s in suboptions}
                                        current_suboption_name = lead.agency_suboption.name if lead.agency_suboption else "None"
                                        edit_suboption_name = st.selectbox("**Suboption**", ["None"] + list(suboption_options.keys()),
                                                                          index=(["None"] + list(suboption_options.keys())).index(current_suboption_name) if current_suboption_name in suboption_options else 0)
                                        edit_agency_suboption_id = suboption_options.get(edit_suboption_name) if edit_suboption_name != "None" else None
                                
                                # CCU Selection
                                ccus = crud_ccus.get_all_ccus(db)
                                ccu_options = {c.name: c.id for c in ccus}
                                current_ccu_name = lead.ccu.name if lead.ccu else "None"
                                
                                if ccus:
                                    edit_ccu_name = st.selectbox("**CCU**", ["None"] + list(ccu_options.keys()),
                                                               index=(["None"] + list(ccu_options.keys())).index(current_ccu_name) if current_ccu_name in ccu_options else 0)
                                    edit_ccu_id = ccu_options.get(edit_ccu_name) if edit_ccu_name != "None" else None
                        
                        
                        with col2:
                            edit_status = st.selectbox("Contact Status", 
                                                      ["Intro Call", "Follow Up", "No Response", "Intake Call", "Inactive"],
                                                      index=["Intro Call", "Follow Up", "No Response", "Intake Call", "Inactive"].index(lead.last_contact_status) if lead.last_contact_status in ["Intro Call", "Follow Up", "No Response", "Intake Call", "Inactive"] else 0)
                            edit_dob = st.date_input("Date of Birth", value=lead.dob)
                            edit_medicaid_no = st.text_input("Medicaid Number", value=lead.medicaid_no or "")
                            edit_e_contact_name = st.text_input("Emergency Contact Name", value=lead.e_contact_name or "")
                            edit_e_contact_phone = st.text_input("Emergency Contact Phone", value=lead.e_contact_phone or "")
                            edit_comments = st.text_area("Comments", value=lead.comments or "")
                        
                        st.divider()
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            save = st.form_submit_button("Save Changes", use_container_width=True, type="primary")
                        with col2:
                            cancel = st.form_submit_button(" Cancel", use_container_width=True)
                        
                        if save:
                            update_data = LeadUpdate(
                                staff_name=edit_staff_name,
                                first_name=edit_first_name,
                                last_name=edit_last_name,
                                source=edit_source,
                                phone=edit_phone,
                                city=edit_city or None,
                                zip_code=edit_zip_code or None,
                                active_client=True,  # Keep as referral
                                last_contact_status=edit_status,
                                dob=edit_dob if edit_dob else None,
                                medicaid_no=edit_medicaid_no or None,
                                e_contact_name=edit_e_contact_name or None,
                                e_contact_relation=None,
                                e_contact_phone=edit_e_contact_phone or None,
                                comments=edit_comments or None,
                                agency_id=edit_agency_id,
                                agency_suboption_id=edit_agency_suboption_id,
                                ccu_id=edit_ccu_id
                            )
                            
                            crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                            st.session_state[f'editing_{lead.id}'] = False
                            st.success(" Referral updated successfully!")
                            st.rerun()
                        
                        if cancel:
                            st.session_state[f'editing_{lead.id}'] = False
                            st.rerun()
    else:
        st.info("No referrals found")
    
    db.close()


def display_referral_confirm(lead, db, highlight=False):
    """Helper function to display a single referral in the confirm page"""

    # Show care status indicator in the expander title
    care_indicator = ""
    if lead.care_status == "Care Start":
        care_indicator = ""
    elif lead.care_status == "Not Start":
        care_indicator = ""
    else:
        care_indicator = ""

    # Highlight if this is the focused referral
    expander_title = f"{care_indicator} {lead.first_name} {lead.last_name} - {lead.staff_name}"
    if highlight:
        expander_title = f"{expander_title}"

    with st.expander(expander_title, expanded=highlight):

        # Show authorization received info if applicable
        if lead.authorization_received:
            # Find when authorization was received from activity logs
            auth_received_time = None
            try:
                history_logs = crud_activity_logs.get_lead_history(db, lead.id)
                for log in history_logs:
                    if log.old_value and log.new_value:
                        try:
                            old_val = json.loads(log.old_value) if isinstance(log.old_value, str) else log.old_value
                            new_val = json.loads(log.new_value) if isinstance(log.new_value, str) else log.new_value

                            # Check if authorization_received changed from False to True
                            if (isinstance(old_val, dict) and isinstance(new_val, dict) and
                                old_val.get('authorization_received') == False and
                                new_val.get('authorization_received') == True):
                                auth_received_time = log.timestamp
                                break
                        except (json.JSONDecodeError, TypeError):
                            continue
            except Exception:
                pass

            # Show prominent authorization confirmation
            st.info("**AUTHORIZATION CONFIRMED** - This referral has received authorization and is ready for care coordination")
            st.markdown("---")
            st.markdown("## **AUTHORIZATION RECEIVED**")
            st.markdown("---")

            if auth_received_time:
                st.success(f"**Authorization Received:** {utc_to_local(auth_received_time).strftime('%m/%d/%Y at %I:%M %p')}")
            else:
                st.success("**Authorization Received**")

            # Authorization toggle button
            st.write("**Authorization Status:**")
            auth_col1, auth_col2 = st.columns(2)

            with auth_col1:
                if st.button("Mark Authorized", key=f"mark_auth_confirm_{lead.id}",
                           type="primary" if not lead.authorization_received else "secondary",
                           use_container_width=True,
                           disabled=lead.authorization_received):
                    update_data = LeadUpdate(authorization_received=True)
                    updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                    if updated_lead:
                        st.success(" Authorization marked as received")
                        st.rerun()
                    else:
                        st.error(" Failed to mark authorization")

            with auth_col2:
                if st.button("Unmark Authorized", key=f"unmark_auth_confirm_{lead.id}",
                           type="secondary" if lead.authorization_received else "primary",
                           use_container_width=True,
                           disabled=not lead.authorization_received):
                    update_data = LeadUpdate(authorization_received=False)
                    updated_lead = crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))

                    if updated_lead:
                        st.warning(" Authorization unmarked")
                        st.rerun()
                    else:
                        st.error(" Failed to unmark authorization")

            st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** {lead.id}")
            st.write(f"**Staff:** {lead.staff_name}")
            st.write(f"**Phone:** {lead.phone}")
            st.write(f"**Source:** {lead.source}")
            if lead.agency:
                st.info(f"**Payor:** {lead.agency.name}")
            if lead.ccu:
                st.info(f"**CCU:** {lead.ccu.name}")

        with col2:
            st.write(f"**Status:** {lead.last_contact_status}")
            st.success(f"**Referral Type:** {lead.referral_type or 'Regular'}")
            st.write(f"**City:** {lead.city or 'N/A'}")
            st.write(f"**Medicaid #:** {lead.medicaid_no or 'N/A'}")

        st.divider()

        # Show current SOC status if already set
        if lead.care_status:
            soc_str = lead.soc_date.strftime('%m/%d/%Y') if lead.soc_date else 'Not Set'
            if lead.care_status == "Care Start":
                st.success(f" **Care Status:** {lead.care_status} | **SOC:** {soc_str}")
            else:
                st.warning(f" **Care Status:** {lead.care_status}")
        else:
            st.warning(" Care status not set yet")

        st.divider()

        # Action Buttons: Care Start, Not Start, History
        st.write("**Select Care Status:**")
        col_start, col_not_start, col_history = st.columns(3)

        with col_start:
            if st.button("Care Start", key=f"care_start_{lead.id}", type="primary", use_container_width=True):
                # Auto-fetch today's date as SOC
                today = date.today()
                update_data = LeadUpdate(
                    care_status="Care Start",
                    soc_date=today
                )
                crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                st.success(f" Care Started! SOC: {today.strftime('%m/%d/%Y')}")
                st.rerun()

        with col_not_start:
            if st.button("Not Start", key=f"not_start_{lead.id}", type="secondary", use_container_width=True):
                update_data = LeadUpdate(
                    care_status="Not Start",
                    soc_date=None
                )
                crud_leads.update_lead(db, lead.id, update_data, st.session_state.username, st.session_state.get('user_id'))
                st.warning(" Care Not Started")
                st.rerun()

        with col_history:
            if st.button("History", key=f"history_confirm_{lead.id}", use_container_width=True):
                st.session_state[f'show_confirm_history_{lead.id}'] = not st.session_state.get(f'show_confirm_history_{lead.id}', False)
                st.rerun()

        # History View - Show last 5 updates only
        if st.session_state.get(f'show_confirm_history_{lead.id}', False):
            st.divider()
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Last 5 Updates</h4>", unsafe_allow_html=True)
            history_logs = crud_activity_logs.get_lead_history(db, lead.id)

            if history_logs:
                # Limit to last 5 entries
                for log in history_logs[:5]:
                    label = get_action_label(log.action_type)
                    time_ago = format_time_ago(log.timestamp)

                    with st.container():
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            st.write(f"**{label}**")
                            if log.description:
                                st.caption(log.description[:100] + "..." if len(log.description) > 100 else log.description)
                        with col2:
                            st.caption(time_ago)
                        st.divider()
            else:
                st.caption("No activity history available.")


def referral_confirm():
    """Referral Confirm page - Shows all clients with authorization received"""
    st.markdown('<div class="main-header">Referral Confirm</div>', unsafe_allow_html=True)

    db = SessionLocal()

    # Get all leads with authorization received
    all_leads = crud_leads.list_leads(db, limit=1000)

    # Filter: Only referrals (active_client = True) with authorization_received = True
    authorized_referrals = [l for l in all_leads if l.active_client == True and l.authorization_received == True]

    # Check if we should focus on a specific referral
    specific_lead_id = st.session_state.get('referral_confirm_lead_id')
    if specific_lead_id:
        # Find the specific lead
        specific_lead = None
        for lead in authorized_referrals:
            if lead.id == specific_lead_id:
                specific_lead = lead
                break

        if specific_lead:
            # Show the specific referral first with a highlight
            st.success(f"**Focused Referral: {specific_lead.first_name} {specific_lead.last_name}**")
            st.divider()

            # Display the specific referral
            display_referral_confirm(specific_lead, db, highlight=True)

            # Clear the specific lead ID after displaying
            del st.session_state['referral_confirm_lead_id']

            st.divider()
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>All Other Authorized Referrals</h4>", unsafe_allow_html=True)

            # Remove the specific lead from the list to avoid duplication
            authorized_referrals = [l for l in authorized_referrals if l.id != specific_lead_id]
        else:
            # Clear the invalid lead ID if referral not found
            if 'referral_confirm_lead_id' in st.session_state:
                del st.session_state['referral_confirm_lead_id']

    # Show count
    st.write(f"**Total Clients with Authorization: {len(authorized_referrals)}**")
    
    st.divider()
    
    # Filter buttons for Care Status
    st.write("**Filter by Care Status:**")
    
    # Initialize filter in session state
    if 'confirm_care_filter' not in st.session_state:
        st.session_state.confirm_care_filter = "All"
    
    col_all, col_start, col_not_start = st.columns(3)
    
    with col_all:
        if st.button("All", key="filter_all", type="primary" if st.session_state.confirm_care_filter == "All" else "secondary", use_container_width=True):
            st.session_state.confirm_care_filter = "All"
            st.rerun()
    
    with col_start:
        if st.button("Care Start", key="filter_care_start", type="primary" if st.session_state.confirm_care_filter == "Care Start" else "secondary", use_container_width=True):
            st.session_state.confirm_care_filter = "Care Start"
            st.rerun()
    
    with col_not_start:
        if st.button("Not Start", key="filter_not_start", type="primary" if st.session_state.confirm_care_filter == "Not Start" else "secondary", use_container_width=True):
            st.session_state.confirm_care_filter = "Not Start"
            st.rerun()
    
    st.divider()
    
    # Apply filter
    if st.session_state.confirm_care_filter == "Care Start":
        authorized_referrals = [l for l in authorized_referrals if l.care_status == "Care Start"]
    elif st.session_state.confirm_care_filter == "Not Start":
        authorized_referrals = [l for l in authorized_referrals if l.care_status == "Not Start"]
    
    # Show filtered count
    st.caption(f"Showing: {len(authorized_referrals)} clients ({st.session_state.confirm_care_filter})")
    
    if not authorized_referrals:
        st.info("No clients match the selected filter.")
        st.caption("Go to Referrals and click 'Authorization Received' on a referral to mark it as authorized.")
        db.close()
        return
    
    # Display each authorized referral
    for lead in authorized_referrals:
        display_referral_confirm(lead, db)
    
    db.close()


def add_lead():
    """Add new lead"""
    st.markdown('<div class="main-header"> Add New Lead</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Source Selection OUTSIDE form for dynamic updates
    st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Lead Source</h4>", unsafe_allow_html=True)
    source = st.selectbox("**Source** *", [
        "Home Health Notify",
        "Web",
        "External Referral",
        "Event",
        "Word of Mouth",
        "Other"
    ])
    
    # Conditional fields based on source (OUTSIDE form)
    event_name = None
    word_of_mouth_type = None
    other_source_type = None
    agency_id = None
    agency_suboption_id = None
    ccu_id = None
    
    if source == "Event":
        # Get all events from database
        from app import crud_events
        events = crud_events.get_all_events(db)
        event_names = [e.event_name for e in events]
        
        # Create columns for event selection and management
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if not event_names:
                st.warning(" No events available.")
                if st.session_state.user_role == "admin":
                    st.info("Add events using the panel on the right")
            else:
                event_name = st.selectbox("**Select Event** *", event_names, key="event_name_select")
        
        # Event Management Panel (Admin Only) - Right next to event selection
        with col2:
            if st.session_state.user_role == "admin":
                st.markdown("**Manage Events**")
                
                # Add new event
                with st.expander(" Add", expanded=False):
                    with st.form("add_event_form"):
                        new_event_name = st.text_input("**Event Name**", label_visibility="collapsed", placeholder="Event name...")
                        submit_event = st.form_submit_button("Add Event", use_container_width=True)
                        
                        if submit_event:
                            if not new_event_name:
                                st.error(" Enter name")
                            else:
                                try:
                                    existing = crud_events.get_event_by_name(db, new_event_name)
                                    if existing:
                                        st.error(f" Already exists")
                                    else:
                                        crud_events.create_event(db, new_event_name, st.session_state.username, st.session_state.get('user_id'))
                                        st.success(f" Added!")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f" Error: {e}")
                
                # Edit/Delete events
                if events:
                    with st.expander(" Edit/Delete", expanded=False):
                        for event in events:
                            col_a, col_b = st.columns([3, 2])
                            with col_a:
                                st.write(f"**{event.event_name}**")
                            with col_b:
                                if st.button("", key=f"del_{event.id}", help="Delete"):
                                    try:
                                        crud_events.delete_event(db, event.id, st.session_state.username, st.session_state.get('user_id'))
                                        st.success("Deleted!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                            
                            # Inline edit
                            if st.session_state.get(f"editing_event_{event.id}", False):
                                with st.form(f"edit_form_{event.id}"):
                                    new_name = st.text_input("New name", value=event.event_name)
                                    col_x, col_y = st.columns(2)
                                    with col_x:
                                        if st.form_submit_button("Save"):
                                            try:
                                                crud_events.update_event(db, event.id, new_name, st.session_state.username, st.session_state.get('user_id'))
                                                st.session_state[f"editing_event_{event.id}"] = False
                                                st.rerun()
                                            except Exception as e:
                                                st.error(str(e))
                                    with col_y:
                                        if st.form_submit_button(""):
                                            st.session_state[f"editing_event_{event.id}"] = False
                                            st.rerun()
                            
                            st.divider()
    
    elif source == "External Referral":
        # Get all agencies from database
        from app import crud_ccus
        agencies = crud_agencies.get_all_agencies(db)
        agency_names = [a.name for a in agencies]
        
        # Initialize variables
        agency_id = None
        agency_suboption_id = None
        
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Select Payor</h4>", unsafe_allow_html=True)
        
        if not agency_names:
            st.warning(" No payors available.")
            if st.session_state.user_role == "admin":
                st.info("Add payors using User Management -> Payor")
            selected_agency_name = None
            agency_id = None
        else:
            agency_list = ["None", "Other (Add New)"] + agency_names
            selected_agency_name = st.selectbox("**Select Payor**", agency_list, key="agency_name_select")
            
            # If "Other" is selected, show button to add new agency (ADMIN ONLY)
            if selected_agency_name == "Other (Add New)":
                if st.session_state.user_role == "admin":
                    st.info("Click the button below to add a new payor")
                    if st.button(" Add New Payor", key="add_new_agency_btn", type="primary"):
                        st.session_state['show_agency_form'] = True
                        st.rerun()
                else:
                    st.warning(" Only admins can add new payors. Please contact your administrator.")
                    st.info("You can find existing payors in the dropdown or contact admin.")
                    selected_agency_name = "None"
            elif selected_agency_name != "None":
                # Get the agency ID
                agency_id = None
                for agency in agencies:
                    if agency.name == selected_agency_name:
                        agency_id = agency.id
                        break
            else:
                agency_id = None
        
        # Show payor add form if triggered (ADMIN ONLY)
        if st.session_state.get('show_agency_form', False) and st.session_state.user_role == "admin":
            with st.form("add_new_agency_form"):
                st.write("**Add New Payor:**")
                new_agency_name = st.text_input("**Payor Name**", placeholder="e.g. IDoA, MCO, DCFS...")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_new_agency = st.form_submit_button(" Add Payor", use_container_width=True, type="primary")
                with col_btn2:
                    cancel_new_agency = st.form_submit_button(" Cancel", use_container_width=True)
                
                if submit_new_agency and new_agency_name:
                    try:
                        existing = crud_agencies.get_agency_by_name(db, new_agency_name)
                        if existing:
                            st.error(f" '{new_agency_name}' already exists")
                        else:
                            crud_agencies.create_agency(db, new_agency_name, st.session_state.username, st.session_state.get('user_id'))
                            st.success(f" '{new_agency_name}' added successfully!")
                            st.session_state['show_agency_form'] = False
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
                
                if cancel_new_agency:
                    st.session_state['show_agency_form'] = False
                    st.rerun()
        
        # Reset agency_id if "Other" is still selected
        if selected_agency_name == "Other (Add New)":
            agency_id = None
        
        # Payor Suboption Selection (if agency selected and agency_id exists)
        if agency_id:
            from app import crud_agency_suboptions
            suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=agency_id)
            
            if suboptions:
                st.write("**Select Suboption:**")
                suboption_names = [s.name for s in suboptions]
                suboption_list = ["None"] + suboption_names
                selected_suboption_name = st.selectbox("**Select suboption**", suboption_list, key="agency_suboption_select", label_visibility="collapsed")
                
                if selected_suboption_name != "None":
                    for suboption in suboptions:
                        if suboption.name == selected_suboption_name:
                            agency_suboption_id = suboption.id
                            break
        
        st.divider()
        
        # CCU Selection ()
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Select CCU</h4>", unsafe_allow_html=True)
        ccu_id = None
        
        # Get ALL CCUs (not filtered by agency)
        ccus = crud_ccus.get_all_ccus(db)
        ccu_names = [c.name for c in ccus]
        
        if not ccu_names:
            st.info(" No CCUs available.")
            if st.button(" Add CCU", key="add_ccu_btn", type="secondary"):
                st.session_state['show_ccu_form'] = True
                st.rerun()
        else:
            ccu_list = ["None", "Other (Add New)"] + ccu_names
            selected_ccu_name = st.selectbox("**Select CCU**", ccu_list, key="ccu_name_select", label_visibility="collapsed")
            
            # If "Other" is selected, show add button
            if selected_ccu_name == "Other (Add New)":
                st.info("Click below to add a new CCU")
                if st.button(" Add New CCU", key="add_new_ccu_btn", type="secondary"):
                    st.session_state['show_ccu_form'] = True
                    st.rerun()
            elif selected_ccu_name != "None":
                # Get the CCU ID
                for ccu in ccus:
                    if ccu.name == selected_ccu_name:
                        ccu_id = ccu.id
                        break
        
        # Show CCU add form if triggered (ALL USERS CAN ADD)
        if st.session_state.get('show_ccu_form', False):
            with st.form("add_new_ccu_form"):
                st.write("**Add New CCU:**")
                new_ccu_name = st.text_input("**CCU Name** *", placeholder="e.g. CCU North, CCU South...")
                new_ccu_address = st.text_input("**Address**", placeholder="e.g. 123 Main St, Chicago, IL")
                new_ccu_phone = st.text_input("**Phone**", placeholder="e.g. (555) 123-4567")
                new_ccu_fax = st.text_input("**Fax**", placeholder="e.g. (555) 123-4568")
                new_ccu_email = st.text_input("**Email**", placeholder="e.g. contact@ccu.com")
                new_ccu_coordinator = st.text_input("**Care Coordinator Name (Optional)**", placeholder="e.g. John Doe")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_new_ccu = st.form_submit_button(" Add CCU", use_container_width=True, type="primary")
                with col_btn2:
                    cancel_new_ccu = st.form_submit_button(" Cancel", use_container_width=True)
                
                if submit_new_ccu and new_ccu_name:
                    try:
                        # Check if CCU exists
                        existing = crud_ccus.get_ccu_by_name(db, new_ccu_name)
                        if existing:
                            st.error(f" CCU '{new_ccu_name}' already exists")
                        else:
                            crud_ccus.create_ccu(
                                db, new_ccu_name, st.session_state.username, st.session_state.get('user_id'),
                                address=new_ccu_address or None,
                                phone=new_ccu_phone or None,
                                fax=new_ccu_fax or None,
                                email=new_ccu_email or None,
                                care_coordinator_name=new_ccu_coordinator or None
                            )
                            st.success(f" CCU '{new_ccu_name}' added successfully!")
                            st.session_state['show_ccu_form'] = False
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
                
                if cancel_new_ccu:
                    st.session_state['show_ccu_form'] = False
                    st.rerun()
                
    elif source == "Word of Mouth":
        word_of_mouth_type = st.selectbox("**Word of Mouth Type** *", [
            "Caregiver",
            "Community",
            "Client"
        ], key="wom_type_input")
    elif source == "Other":
        other_source_type = st.text_input("**Specify Source Type** *", value="", key="other_type_input")
    
    st.divider()
    
    # Main form with other fields
    with st.form("add_lead_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Staff assignment based on role
            if st.session_state.user_role == "admin":
                staff_name = st.text_input("**Staff Name** *", value="")
            else:
                staff_name = st.session_state.username
                st.info(f" Lead will be created by : **{staff_name}**")
            
            first_name = st.text_input("**First Name** *", value="")
            last_name = st.text_input("**Last Name** *", value="")
            phone = st.text_input("**Phone** *", value="")
            city = st.text_input("**City**")
            zip_code = st.text_input("**Zip Code**")
        
        with col2:
            last_contact_status = st.selectbox("**Contact Status**", 
                                              ["Intro Call", "Follow Up", "No Response", "Intake Call", "Inactive"])
            dob = st.date_input("**Date of Birth**", value=None)
            medicaid_no = st.text_input("**Medicaid Number**")
            e_contact_name = st.text_input("**Emergency Contact Name**")
            e_contact_phone = st.text_input("**Emergency Contact Phone**")
            comments = st.text_area("**Comments**")
        
        st.divider()
       
        submit = st.form_submit_button("Save Lead", use_container_width=True, type="primary")

        
        if submit:
            # Validation
            required_fields = [staff_name, first_name, last_name, source, phone]
            if source == "Event" and not event_name:
                st.error(" Please select an Event")
                db.close()
                return
            elif source == "External Referral" and not agency_id:
                st.error(" Please select a Payor")
                db.close()
                return
            elif source == "Other" and not other_source_type:
                st.error(" Please specify Source Type")
                db.close()
                return
            
            if not all(required_fields):
                st.error(" Please fill in all required fields (*)")
            else:
                # Check for duplicate lead
                existing_lead = crud_leads.check_duplicate_lead(db, first_name, last_name, phone)
                if existing_lead:
                    st.error(f" A lead with the same name and phone number already exists!")
                    st.warning(f"**Existing Lead:** {existing_lead.first_name} {existing_lead.last_name} (ID: {existing_lead.id})")
                    st.info(f"Created on: {utc_to_local(existing_lead.created_at).strftime('%m/%d/%Y %I:%M %p')}")
                    st.info(f"Created by: {existing_lead.created_by or 'Unknown'}")
                    st.info(f"Status: {existing_lead.last_contact_status}")
                    st.info("Please update the existing lead instead of creating a duplicate.")
                    db.close()
                    return
                
                try:
                    lead_data = LeadCreate(
                        staff_name=staff_name,
                        first_name=first_name,
                        last_name=last_name,
                        source=source,
                        event_name=event_name,
                        word_of_mouth_type=word_of_mouth_type,
                        other_source_type=other_source_type,
                        phone=phone,
                        city=city or None,
                        zip_code=zip_code or None,
                        active_client=False,  # Default to non-referral
                        last_contact_status=last_contact_status,
                        dob=dob if dob else None,
                        medicaid_no=medicaid_no or None,
                        e_contact_name=e_contact_name or None,
                        e_contact_phone=e_contact_phone or None,
                        comments=comments or None,
                        agency_id=agency_id,
                        agency_suboption_id=agency_suboption_id,
                        ccu_id=ccu_id
                    )
                    lead = crud_leads.create_lead(db, lead_data, st.session_state.username, st.session_state.get('user_id'))
                    st.success(f" Lead created successfully! (ID: {lead.id})")
                    
                    # Auto-send email to lead creator (always for non-inactive leads)
                    if lead.last_contact_status != "Inactive":
                        user = crud_users.get_user_by_username(db, st.session_state.username)
                        if user and user.email:
                            try:
                                # Check if this is a referral or regular lead
                                if lead.active_client:  # Is a referral
                                    from app.utils.email_service import send_referral_reminder_email
                                    
                                    # Get payor (payor) information
                                    agency_name = "N/A"
                                    agency_suboption = ""
                                    if lead.agency_id:
                                        agency = crud_agencies.get_agency(db, lead.agency_id)
                                        if agency:
                                            agency_name = agency.name
                                    
                                    if lead.agency_suboption_id:
                                        from app.crud_agency_suboptions import get_suboption_by_id
                                        suboption = get_suboption_by_id(db, lead.agency_suboption_id)
                                        if suboption:
                                            agency_suboption = suboption.name
                                    
                                    # Get CCU information
                                    ccu_name = "N/A"
                                    ccu_phone = "N/A"
                                    ccu_fax = "N/A"
                                    ccu_email = "N/A"
                                    ccu_address = "N/A"
                                    ccu_coordinator = "N/A"
                                    if lead.ccu_id:
                                        ccu = crud_ccus.get_ccu_by_id(db, lead.ccu_id)
                                        if ccu:
                                            ccu_name = ccu.name
                                            ccu_phone = ccu.phone if ccu.phone else "N/A"
                                            ccu_fax = ccu.fax if ccu.fax else "N/A"
                                            ccu_email = ccu.email if ccu.email else "N/A"
                                            ccu_address = ccu.address if ccu.address else "N/A"
                                            ccu_coordinator = ccu.care_coordinator_name if ccu.care_coordinator_name else "N/A"
                                    
                                    # Prepare referral info
                                    referral_info = {
                                        'name': f"{lead.first_name} {lead.last_name}",
                                        'phone': lead.phone,
                                        'dob': str(lead.dob) if lead.dob else 'N/A',
                                        'creator': st.session_state.username,
                                        'created_date': utc_to_local(lead.created_at).strftime('%m/%d/%Y'),
                                        'status': lead.last_contact_status,
                                        'referral_type': lead.referral_type if lead.referral_type else 'Regular',
                                        'payor_name': agency_name,
                                        'payor_suboption': agency_suboption,
                                        'ccu_name': ccu_name,
                                        'ccu_phone': ccu_phone,
                                        'ccu_fax': ccu_fax,
                                        'ccu_email': ccu_email,
                                        'ccu_address': ccu_address,
                                        'ccu_coordinator': ccu_coordinator
                                    }
                                    
                                    # Send referral email
                                    auto_email_success = send_referral_reminder_email(referral_info, user.email)
                                    email_subject = f"New Referral [{referral_info['referral_type']}]: {lead.first_name} {lead.last_name}"
                                    
                                else:  # Regular lead
                                    from app.utils.email_service import send_simple_lead_email
                                    
                                    # Prepare simple lead info
                                    lead_info = {
                                        'name': f"{lead.first_name} {lead.last_name}",
                                        'phone': lead.phone,
                                        'creator': st.session_state.username,
                                        'dob': str(lead.dob) if lead.dob else 'N/A',
                                        'source': lead.source,
                                        'status': lead.last_contact_status,
                                        'created_date': utc_to_local(lead.created_at).strftime('%m/%d/%Y')
                                    }
                                    
                                    # Send simple email
                                    auto_email_success = send_simple_lead_email(lead_info, user.email)
                                    email_subject = f"New Lead: {lead.first_name} {lead.last_name}"
                                
                                if auto_email_success:
                                    # Record the auto email
                                    crud_email_reminders.create_reminder(
                                        db=db,
                                        lead_id=lead.id,
                                        recipient_email=user.email,
                                        subject=email_subject,
                                        sent_by="system",
                                        status="sent"
                                    )
                                    st.info(f"Auto-reminder email sent to {user.email}")
                                else:
                                    # Record failed attempt
                                    crud_email_reminders.create_reminder(
                                        db=db,
                                        lead_id=lead.id,
                                        recipient_email=user.email,
                                        subject=email_subject,
                                        sent_by="system",
                                        status="failed",
                                        error_message="Email service error"
                                    )
                            except Exception as auto_email_error:
                                pass  # Don't show error for auto-email, it's background
                    
                except Exception as e:
                    st.error(f" Error: {e}")
    
    db.close()


def view_activity_logs():
    """Professional Activity Logs page with advanced filtering and beautiful UI"""
    st.markdown('<div class="main-header">Activity Logs</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    from app import crud_activity_logs
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
                    "Timestamp": utc_to_local(activity.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
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
            time_str = format_time_ago(activity.timestamp)
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
                    if time_color == "success":
                        st.success(f"{time_str}")
                    elif time_color == "info":
                        st.info(f"{time_str}")
                    else:
                        st.write(f"{time_str}")
                
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
                                st.write(f"  • **{field}:** {old_val} -> {new_val}")
                
                st.divider()
    else:
        st.info("No activities found matching your filters")
    
    db.close()


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
                            user_id=st.session_state.user_id,
                            new_password=new_password,
                            performer_username=st.session_state.username,
                            performer_id=st.session_state.user_id
                        )
                        
                        if updated_user:
                            st.success(" Password updated successfully!")
                        else:
                            st.error(" Failed to update password")
                except Exception as e:
                    st.error(f" Error: {e}")
                finally:
                    db.close()


def view_all_user_dashboards():
    """View dashboard statistics for all users"""
    st.markdown('<div class="main-header">ALL USER DASHBOARDS</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Get all approved users
    approved_users = crud_users.get_approved_users(db)
    
    if not approved_users:
        st.info("No users found")
        db.close()
        return
    
    st.write(f"**Total Users:** {len(approved_users)}")
    st.divider()
    
    # Display dashboard for each user
    for user in approved_users:
        with st.expander(f"{user.username} ({user.role})", expanded=False):
            # Get user statistics
            stats = services_stats.get_user_stats(db, user.username)
            active_leads = stats.get("active_clients", 0)
            
            # Display stats cards
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{stats['total_leads']}</div>
                    <div class="stat-label">Total Leads</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{active_leads}</div>
                    <div class="stat-label">Referral s</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Calculate conversion rate
                conversion_rate = (active_leads / stats['total_leads'] * 100) if stats['total_leads'] > 0 else 0
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{conversion_rate:.1f}%</div>
                    <div class="stat-label">Conversion Rate</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            # Charts for this user
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Monthly Leads</h4>", unsafe_allow_html=True)
                monthly_data = services_stats.leads_by_month_for_user(db, user.username)
                if monthly_data:
                    df_monthly = pd.DataFrame(monthly_data)
                    st.line_chart(df_monthly.set_index('month')['count'])
                else:
                    st.info("No leads yet")
            
            with col2:
                st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Leads by Source</h4>", unsafe_allow_html=True)
                source_data = services_stats.leads_by_source_for_user(db, user.username)
                if source_data:
                    df_source = pd.DataFrame(source_data)
                    st.bar_chart(df_source.set_index('source')['count'])
                else:
                    st.info("No leads yet")
            
            # Status breakdown
            st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Leads by Status</h4>", unsafe_allow_html=True)
            results = (
                db.query(crud_leads.models.Lead.last_contact_status, func.count(crud_leads.models.Lead.id))
                .filter(crud_leads.models.Lead.staff_name == user.username)
                .group_by(crud_leads.models.Lead.last_contact_status)
                .all()
            )
            status_data = [{"status": r[0], "count": r[1]} for r in results]
            
            if status_data:
                df_status = pd.DataFrame(status_data)
                st.dataframe(df_status, use_container_width=True)
            else:
                st.info("No data available")
    
    db.close()


def admin_panel():
    """Admin panel for user management"""
    st.markdown('<div class="main-header"> User Management</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
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
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Pending User Approvals</h4>", unsafe_allow_html=True)
        pending_users = crud_users.get_pending_users(db)
        
        if pending_users:
            for user in pending_users:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Username:</span> {user.username}", unsafe_allow_html=True)
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Email:</span> {user.email}", unsafe_allow_html=True)
                        st.markdown(f"<span style='font-weight: 900; color: black;'>Requested:</span> {utc_to_local(user.created_at).strftime('%Y-%m-%d %H:%M')}", unsafe_allow_html=True)
                    
                    with col2:
                        if st.button("Approve", key=f"approve_{user.id}", type="primary", use_container_width=True):
                            crud_users.approve_user(db, user.id, st.session_state.username, st.session_state.user_id)
                            st.success(f"Approved {user.username}")
                            st.rerun()
                    
                    with col3:
                        if st.button("Reject", key=f"reject_{user.id}", type="primary", use_container_width=True):
                            crud_users.reject_user(db, user.id, st.session_state.username, st.session_state.user_id)
                            st.info(f"Rejected {user.username}")
                            st.rerun()
                    
                    st.divider()
        else:
            st.info("No pending user approvals")
    
    with tab2:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Password Reset Requests</h4>", unsafe_allow_html=True)
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
                                    crud_users.admin_reset_password(db, user.id, new_password, st.session_state.username, st.session_state.user_id)
                                    st.success(f" Password reset for {user.username}!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f" Error: {e}")
                    
                    st.divider()
        else:
            st.info("No password reset requests")
    
    with tab3:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Approved Users</h4>", unsafe_allow_html=True)
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
                            st.markdown(f"<span style='font-weight: 900; color: black;'>ID:</span> {user.id} | <span style='font-weight: 900; color: black;'>Username:</span> {user.username} | <span style='font-weight: 900; color: black;'>Email:</span> {user.email} | <span style='font-weight: 900; color: black;'>Role:</span> {user.role}", unsafe_allow_html=True)
                            st.caption(f"Created: {utc_to_local(user.created_at).strftime('%Y-%m-%d')}")
                        
                        with col2:
                            if st.button(" Edit", key=f"edit_{user.id}"):
                                st.session_state[f"editing_user_{user.id}"] = True
                                st.rerun()
                        
                        with col3:
                            if st.button(" Delete", key=f"del_{user.id}"):
                                crud_users.delete_user(db, user.id, st.session_state.username, st.session_state.user_id)
                                st.success(f"Deleted {user.username}")
                                st.rerun()
                        
                        st.divider()
                
                # Edit form
                if editing:
                    with st.form(f"edit_user_form_{user.id}"):
                        st.write(f"Editing **{user.username}**")
                        new_username = st.text_input("Username", value=user.username, key=f"edit_username_{user.id}")
                        new_email = st.text_input("Email", value=user.email, key=f"edit_email_{user.id}")
                        new_role = st.selectbox("Role", ["user", "admin"], index=0 if user.role == "user" else 1, key=f"edit_role_{user.id}")
                        new_password = st.text_input("New Password (leave blank to keep current)", type="password")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.form_submit_button("Save"):
                                try:
                                    # Update username
                                    if new_username != user.username:
                                        crud_users.admin_update_username(db, user.id, new_username, st.session_state.username, st.session_state.user_id)
                                    
                                    # Update email
                                    if new_email != user.email:
                                        crud_users.admin_update_email(db, user.id, new_email, st.session_state.username, st.session_state.user_id)
                                    
                                    # Update role
                                    if new_role != user.role:
                                        crud_users.update_user_role(db, user.id, new_role, st.session_state.username, st.session_state.user_id)
                                    
                                    # Update password
                                    if new_password:
                                        crud_users.admin_reset_password(db, user.id, new_password, st.session_state.username, st.session_state.user_id)
                                    st.session_state[f"editing_user_{user.id}"] = False
                                    st.success("Updated!")
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
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Create New User</h4>", unsafe_allow_html=True)
        st.info(" Users created here are automatically approved and can login immediately.")
        
        with st.form("create_user_form"):
            new_username = st.text_input("Username *")
            new_email = st.text_input("Email *")
            new_password = st.text_input("Password (min 6 characters) *", type="password")
            confirm_password = st.text_input("Confirm Password *", type="password")
            new_role = st.selectbox("Role *", ["user", "admin"])
            
            submit = st.form_submit_button(" Create User")
            
            if submit:
                # Validation
                if not all([new_username, new_email, new_password, confirm_password]):
                    st.error(" Please fill in all fields")
                elif new_password != confirm_password:
                    st.error(" Passwords do not match")
                elif len(new_password) < 6:
                    st.error(" Password must be at least 6 characters")
                elif '@' not in new_email:
                    st.error(" Please enter a valid email")
                else:
                    try:
                        # Check if username or email already exists
                        existing_user = crud_users.get_user_by_username(db, new_username)
                        if existing_user:
                            st.error(f" Username '{new_username}' already exists")
                        else:
                            existing_email = crud_users.get_user_by_email(db, new_email)
                            if existing_email:
                                st.error(f" Email '{new_email}' already registered")
                            else:
                                # Create user with is_approved=True
                                user_data = UserCreate(
                                    username=new_username,
                                    email=new_email,
                                    password=new_password,
                                    role=new_role
                                )
                                user = crud_users.create_user(db, user_data, st.session_state.username, st.session_state.user_id)
                                # Auto-approve the user
                                crud_users.approve_user(db, user.id, st.session_state.username, st.session_state.user_id)
                                st.success(f" User '{new_username}' created successfully!")
                                st.info(f"Email: {new_email} | Role: {new_role}")
                                st.balloons()
                    except Exception as e:
                        st.error(f" Error creating user: {e}")
    
    with tab5:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Change My Password</h4>", unsafe_allow_html=True)
        st.write(f"Updating password for: **{st.session_state.username}**")
        
        with st.form("admin_update_password_form"):
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
                    try:
                        # Verify current password
                        user = crud_users.authenticate_user(db, st.session_state.username, current_password)
                        
                        if not user or user == "pending":
                            st.error(" Current password is incorrect")
                        else:
                            # Update password
                            updated_user = crud_users.update_user_credentials(
                                db=db,
                                user_id=st.session_state.user_id,
                                new_password=new_password,
                                performer_username=st.session_state.username,
                                performer_id=st.session_state.user_id
                            )
                            
                            if updated_user:
                                st.success(" Password updated successfully!")
                            else:
                                st.error(" Failed to update password")
                    except Exception as e:
                        st.error(f" Error: {e}")
    
    with tab6:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Manage Payor</h4>", unsafe_allow_html=True)
        st.write("Add, edit, or delete payors that users can select when creating external referrals.")
        
        # Add new agency
        with st.expander(" Add New Payor", expanded=False):
            with st.form("add_agency_admin_form"):
                new_agency_name = st.text_input("Payor Name", placeholder="e.g. IDoA, MCO, DCFS...")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    submit_agency = st.form_submit_button(" Add Payor", use_container_width=True, type="primary")
                with col_btn2:
                    st.form_submit_button(" Cancel", use_container_width=True)
                
                if submit_agency and new_agency_name:
                    try:
                        existing = crud_agencies.get_agency_by_name(db, new_agency_name)
                        if existing:
                            st.error(f" Agency '{new_agency_name}' already exists")
                        else:
                            crud_agencies.create_agency(db, new_agency_name, st.session_state.username, st.session_state.user_id)
                            st.success(f" Agency '{new_agency_name}' added successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f" Error: {e}")
        
        st.divider()
        
        # List all agencies
        agencies = crud_agencies.get_all_agencies(db)
        if agencies:
            st.write(f"**Total Agencies: {len(agencies)}**")
            st.divider()
            
            from app import crud_ccus, crud_mcos
            
            from app import crud_agency_suboptions
            
            for agency in agencies:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"<span style='font-size: 16px;'>**{agency.name}**</span>", unsafe_allow_html=True)
                    st.caption(f"Created: {utc_to_local(agency.created_at).strftime('%Y-%m-%d %H:%M')} by {agency.created_by}")
                with col2:
                    if st.button("Delete", key=f"del_agency_admin_{agency.id}", help=f"Delete {agency.name}", type="primary"):
                        try:
                            crud_agencies.delete_agency(db, agency.id, st.session_state.username, st.session_state.user_id)
                            st.success(f" Deleted '{agency.name}'")
                            st.rerun()
                        except Exception as e:
                            st.error(f" Error: {e}")
                
                # Show suboptions for this agency
                suboptions = crud_agency_suboptions.get_all_suboptions(db, agency_id=agency.id)
                if suboptions or True:  # Always show to allow adding
                    with st.expander(f"Suboptions for {agency.name} ({len(suboptions)})", expanded=False):
                        # Add new suboption
                        with st.form(f"add_suboption_form_{agency.id}"):
                            new_suboption_name = st.text_input("Suboption Name", placeholder="e.g., INH2502076", key=f"new_suboption_{agency.id}")
                            col_btn1, col_btn2 = st.columns([1, 1])
                            with col_btn1:
                                submit_suboption = st.form_submit_button(" Add", use_container_width=True, type="primary")
                            with col_btn2:
                                st.form_submit_button(" Cancel", use_container_width=True)
                            
                            if submit_suboption and new_suboption_name:
                                try:
                                    existing = crud_agency_suboptions.get_suboption_by_name_and_agency(db, new_suboption_name, agency.id)
                                    if existing:
                                        st.error(f" '{new_suboption_name}' already exists for this agency")
                                    else:
                                        crud_agency_suboptions.create_suboption(db, new_suboption_name, agency.id, st.session_state.username, st.session_state.user_id)
                                        st.success(f" Added '{new_suboption_name}'")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f" Error: {e}")
                        
                        # List existing suboptions
                        if suboptions:
                            st.write(f"**Existing Suboptions:**")
                            for suboption in suboptions:
                                col_a, col_b, col_c = st.columns([3, 1, 1])
                                with col_a:
                                    st.markdown(f"{suboption.name}")
                                with col_b:
                                    if st.button("Edit", key=f"edit_suboption_{suboption.id}", help="Edit", type="primary"):
                                        st.session_state[f"editing_suboption_{suboption.id}"] = not st.session_state.get(f"editing_suboption_{suboption.id}", False)
                                        st.rerun()
                                with col_c:
                                    if st.button("Delete", key=f"del_suboption_{suboption.id}", help="Delete", type="primary"):
                                        try:
                                            crud_agency_suboptions.delete_suboption(db, suboption.id, st.session_state.username, st.session_state.user_id)
                                            st.success(f" Deleted '{suboption.name}'")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f" Error: {e}")
                                
                                # Inline edit form
                                if st.session_state.get(f"editing_suboption_{suboption.id}", False):
                                    with st.form(f"edit_suboption_form_{suboption.id}"):
                                        new_name = st.text_input("New name", value=suboption.name)
                                        col_x, col_y = st.columns(2)
                                        with col_x:
                                            if st.form_submit_button("Save"):
                                                try:
                                                    crud_agency_suboptions.update_suboption(db, suboption.id, new_name, st.session_state.username, st.session_state.user_id)
                                                    st.session_state[f"editing_suboption_{suboption.id}"] = False
                                                    st.success(f" Updated")
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f" Error: {str(e)}")
                                        with col_y:
                                            if st.form_submit_button(" Cancel"):
                                                st.session_state[f"editing_suboption_{suboption.id}"] = False
                                                st.rerun()
                                
                                st.divider()
                        else:
                            st.caption("No suboptions added yet.")
                
                st.divider()
        else:
            st.info("No agencies found. Add your first agency above.")
    
    with tab7:
        st.markdown("<h4 style='font-weight: bold; color: #00506b;'>Manage CCUs</h4>", unsafe_allow_html=True)
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
                    submit_ccu = st.form_submit_button(" Add CCU", use_container_width=True, type="primary")
                with col_btn2:
                    st.form_submit_button(" Cancel", use_container_width=True)
                
                if submit_ccu and new_ccu_name:
                    try:
                        existing = crud_ccus.get_ccu_by_name(db, new_ccu_name)
                        if existing:
                            st.error(f" CCU '{new_ccu_name}' already exists")
                        else:
                            crud_ccus.create_ccu(
                                db, new_ccu_name, st.session_state.username, st.session_state.user_id,
                                address=new_ccu_address or None,
                                phone=new_ccu_phone or None,
                                fax=new_ccu_fax or None,
                                email=new_ccu_email or None,
                                care_coordinator_name=new_ccu_coordinator or None
                            )
                            st.success(f" CCU '{new_ccu_name}' added successfully!")
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
                    st.caption(f"Created: {utc_to_local(ccu.created_at).strftime('%Y-%m-%d %H:%M')} by {ccu.created_by}")
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
                        try:
                            crud_ccus.delete_ccu(db, ccu.id, st.session_state.username, st.session_state.user_id)
                            st.success(f" Deleted CCU '{ccu.name}'")
                            st.rerun()
                        except Exception as e:
                            st.error(f" Error: {e}")
                
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
                                        db, ccu.id, edit_name, st.session_state.username, st.session_state.user_id,
                                        address=edit_address or None,
                                        phone=edit_phone or None,
                                        fax=edit_fax or None,
                                        email=edit_email or None,
                                        care_coordinator_name=edit_coordinator or None
                                    )
                                    st.session_state[f"editing_ccu_{ccu.id}"] = False
                                    st.success(f" Updated CCU details")
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
    # Professional header with blue+white gradient
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #00506b, #3CA5AA); padding: 0.75rem 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            <div class="white-header-text" style="font-size: 1.5rem; font-weight: 700; margin: 0; text-align: center; text-transform: uppercase; letter-spacing: 0.05em;">Historian</div>
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
        <div style="border: 1px solid #00506b; border-radius: 0.5rem; overflow: hidden; margin-top: 0.5rem; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);">
            <div style="background-color: #00506b; padding: 10px 15px;">
                <div class="white-header-text" style="margin: 0; font-size: 1.2rem; font-weight: bold;">Recent Activity</div>
            </div>
            <div style="background-color: #FFFFFF; padding: 1rem;">
        """, unsafe_allow_html=True)

        if recent_activities:
            for idx, activity in enumerate(recent_activities):
                # Build the complete HTML for the entry
                entry_html = f"""
<div style="display: flex; margin-bottom: 1rem;">
    <div style="margin-right: 10px; display: flex; flex-direction: column; align-items: center;">
        <div style="width: 2px; background-color: #E5E7EB; flex-grow: 1; margin-top: 5px;"></div>
    </div>
    <div style="flex-grow: 1;">
        <div style="font-weight: 700; color: #1e3a5f; font-size: 1rem; margin-bottom: 2px;">
            {activity.description}
        </div>
        <div style="color: #6B7280; font-size: 0.85rem; margin-bottom: 5px;">
            {utc_to_local(activity.timestamp).strftime('%m/%d/%Y %I:%M %p')}
        </div>
        <div style="display: inline-block; background-color: #3CA5AA; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; margin-bottom: 8px;">
            {format_time_ago(activity.timestamp)}
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
    <span style="font-weight: 600;">{field}:</span> ({old}) → ({new})
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
        st.markdown('<div style="background: #FFFFFF; border: 2px solid #00506b; border-radius: 0.5rem; padding: 1rem; margin-top: 0.5rem;">Error loading data</div>', unsafe_allow_html=True)
    finally:
        db.close()


def inject_custom_css():
    """Inject global CSS styles"""
    st.markdown("""
        <style>
        /* Global Green Asterisk for required fields */
        .required-star {
            color: #59B976 !important;
        }
        
        /* Square Alert Boxes (Info, Success, Warning, Error) */
        .stAlert {
            border-radius: 0px !important;
        }
        
        /* Square Buttons & Bold Text */
        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            border-radius: 0px !important;
            font-weight: bold !important;
        }
        
        /* Bold Input Labels */
        .stTextInput label, .stSelectbox label, .stNumberInput label, .stDateInput label, .stTextArea label, .stTimeInput label, .stRadio label {
            font-weight: bold !important;
            color: #000000 !important;
        }

        /* Sidebar Navigation Bold */
        [data-testid="stSidebar"] [role="radiogroup"] label p {
            font-weight: bold !important;
            font-size: 1rem !important;
        }

        /* Tabs Styling (User Management) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .stTabs [data-baseweb="tab"] p {
            font-weight: bold !important;
            font-size: 1rem !important;
        }
        .stTabs [aria-selected="true"] {
            color: #00506b !important;
            border-bottom: 2px solid #00506b !important;
        }
        .stTabs [aria-selected="false"] {
            color: #31333F !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #00506b;
        }

        /* Bold Expander Headers */
        [data-testid="stExpander"] summary p {
            font-weight: bold !important;
            font-size: 1rem !important;
            color: #000000 !important;
        }
        
        /* Ensure strong tags are bold */
        strong {
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)


def main():
    """Main application logic"""
    inject_custom_css()
>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
    if not st.session_state.authenticated:
        if st.session_state.show_signup:
            signup()
        elif st.session_state.show_forgot_password:
            forgot_password()
        else:
            login()
    else:
        # Sidebar navigation
        with st.sidebar:
            # Company logo above the Navigation title
            st.image("icon1.png", width=250)
            st.markdown("")  # small spacer
            st.title("Navigation")
            
            # Base pages
<<<<<<< HEAD
            pages = ["Dashboard", "View Leads", "Add Lead", "Lead Discovery", "Referrals Sent", "Referral Confirm", "Activity Logs"]
=======
            pages = ["Dashboard", "View Leads", "Add Lead", "Referrals Sent", "Referral Confirm", "Activity Logs"]
>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
            
            # Add Update Password for regular users only (admins have it in User Management)
            if st.session_state.user_role != "admin":
                pages.append("Update Password")
            
            # Add admin panel for admins
            if st.session_state.user_role == "admin":
                pages.append("User Management")
            
<<<<<<< HEAD
            # Ensure main_navigation is initialized
            if "main_navigation" not in st.session_state:
                st.session_state.main_navigation = "Dashboard"

            def handle_nav_change():
                """Callback when main navigation changes"""
                # Clear any sub-page state when navigating to a new main page
                st.session_state.current_page = None
            
            # Additional check: If Mark Referral Page is active, ensure we don't accidentally navigate away
            # unless the user explicitly clicked.
            # But relying on on_change handles the explicit click nicely.
            
            page = st.radio("Go to", pages, key="main_navigation", on_change=handle_nav_change)
            
            # No legacy navigation enforcement needed below. 
            # The callback handles the reset logic efficiently.
=======
            # Check if we should select Referral Confirm page
            if st.session_state.get('current_page') == 'Referral Confirm':
                default_index = pages.index("Referral Confirm")
            else:
                default_index = 0
            
            page = st.radio("Go to", pages, index=default_index)
            
            # Only clear current_page if user actively clicks a navigation option
            # Don't clear if it's a hidden page (like Mark Referral Page)
            current_page = st.session_state.get('current_page')
            if current_page and current_page not in ['Mark Referral Page', 'Referral Confirm']:
                pass  # Don't clear hidden pages
            elif page != "Referral Confirm" and current_page == 'Referral Confirm':
                st.session_state['current_page'] = None
>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
            
            # Show user info
            st.divider()
            st.write(f"**User:** {st.session_state.username}")
<<<<<<< HEAD
=======

>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
            st.write(f"**Role:** {st.session_state.user_role}")
            
            st.divider()
            render_historian()
        
        # Route to selected page
        # Check for hidden pages first (not in navigation)
        if st.session_state.get('current_page') == 'Mark Referral Page':
            mark_referral_page()
        elif page == "Dashboard":
            # Check if admin wants to view all user dashboards
            if st.session_state.user_role == "admin" and st.session_state.show_user_dashboards:
<<<<<<< HEAD
=======
                # Show back button
>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
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
<<<<<<< HEAD
        elif page == "Lead Discovery":
            discovery_tool()
=======
>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
        elif page == "Referrals Sent":
            view_referrals()
        elif page == "Referral Confirm":
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

<<<<<<< HEAD

if __name__ == "__main__":
    init_scheduler()
=======
if __name__ == "__main__":
>>>>>>> 3877e88bb4b78e4133e1abf9a7b9f6258c629c6c
    main()
