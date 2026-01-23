"""
Common utilities, CSS styles, and shared functions for Lead Manager.
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import streamlit as st
from app.db import SessionLocal, engine
from app.utils.activity_logger import utc_to_local
from app.crud import crud_session_tokens # crud_leads moved to local import
from app import services_stats
from streamlit.components.v1 import html
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


# Token-based session management (secure, database-backed)
def get_session_token():
    """Get the session token from URL query params"""
    query_params = st.query_params
    return query_params.get("token", None)

def set_session_token(token: str):
    """Store the session token in URL query params for persistence"""
    st.query_params["token"] = token

def clear_session_token():
    """Remove the session token from URL query params"""
    if "token" in st.query_params:
        del st.query_params["token"]


# Global CSS styles (SafeLife UI theme)
GLOBAL_CSS = """
<style>
    /* Import Montserrat from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;800&display=swap');

    html, body, .stApp  {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                     Arial, 'Source Sans Pro', system-ui, sans-serif;
        background-color: #FFFFFF !important;
        color: #111827 !important;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
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

    /* Suppress transient Streamlit errors and warnings highly aggressively */
    /* We use a delay of 0.8s which is enough to hide all typical developmental "re-rendering" glitches */
    /* EXCEPT for our custom toasts which we want to see immediately */
    [data-testid="stNotification"], 
    .stException, 
    [data-testid="stFormWarning"],
    [data-testid="stStatusWidget"] {
        /* Immediate visibility for critical alerts */
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    /* PREMIUM INDICATOR STYLING */
    
    /* Make Alert boxes much more professional and modern */
    [data-testid="stNotification"] .stAlert {
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        padding: 1rem 1.25rem !important;
        border-radius: 12px !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        background-color: #f0fdf4 !important; /* Soft emerald green tint for success alert */
    }

    [data-testid="stNotification"] .stAlert:has(div[data-testid="stIcon"] span:contains("✅")) {
        background-color: #f0fdf4 !important;
        border-left: 5px solid #10b981 !important;
    }

    /* Make Toasts (Pop-ups) prominent and professional with premium emerald theme */
    [data-testid="stToast"] {
        min-width: 520px !important;
        max-width: 700px !important;
        padding: 1.25rem 2rem !important;
        border-radius: 16px !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important; /* Force bold */
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
        border-left: 12px solid !important;
        background: white !important;
        color: #111827 !important;
        z-index: 2147483647 !important; /* Max Z-Index for toasts too */
        animation: toastSlideIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards !important;
    }

    [data-testid="stToast"] p, [data-testid="stToast"] span, [data-testid="stToast"] div {
        font-weight: 700 !important; /* Thick bold text */
    }

    @keyframes toastSlideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    /* Toast color coding based on icon */
    [data-testid="stToast"]:has(div[data-testid="stIcon"] span:contains("✅")) {
        border-left-color: #10b981 !important; /* Success emerald Green */
    }
    [data-testid="stToast"]:has(div[data-testid="stIcon"] span:contains("❌")) {
        border-left-color: #ef4444 !important; /* Error Red */
    }
    [data-testid="stToast"]:has(div[data-testid="stIcon"] span:contains("⏳")) {
        border-left-color: #f59e0b !important; /* Warning Amber */
    }

    /* Style the confirmation "Double Check" boxes if they are inside buttons/dialogs */
    .stButton > button {
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    
    /* Force primary buttons to be Deep Blue (Chicago/SafeLife branding) */
    .stButton > button[kind="primary"] {
        background-color: #00506b !important;
        border: none !important;
    }
    
    /* Ultra-strong override for all button text containers */
    .stButton button p, .stButton button span, .stButton button label {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    
    .stButton > button:active {
        transform: scale(0.96) !important;
    }

    /* --- PROFESSIONAL MODAL SYSTEM (NATIVE ST.DIALOG) --- */
    
    /* Target the Streamlit Dialog container to match our theme */
    div[data-testid="stDialog"] div[role="dialog"] {
        border-radius: 14px !important;
        overflow: hidden !important;
        padding: 0 !important;
        border: none !important;
        box-shadow: 0 25px 80px rgba(0,0,0,0.55) !important;
    }

    /* Professional header style for use inside dialogs */
    .modal-dialog-header {
      background: #1f6f73;
      color: #fff;
      text-align: center;
      padding: 24px 20px;
      font-weight: 900;
      font-size: 22px;
      letter-spacing: 1px;
      margin: -1rem -1rem 1rem -1rem; /* Negative margin to fill the dialog top */
    }

    .modal-icon {
      font-size: 52px;
      margin-bottom: 10px;
      display: block;
      font-weight: bold;
    }

    .modal-body-content {
      padding: 10px 15px 25px 15px;
      text-align: center;
      font-weight: 700;
      font-size: 18px;
      color: #1f2937;
      line-height: 1.6;
    }
    
    .modal-body-content b, .modal-body-content strong {
        font-weight: 900 !important;
    }

    /* Prevent flashing of unstyled content during reloads */
    .stApp {
        animation: smoothStart 0.4s ease-out;
    }
    
    @keyframes smoothStart {
        from { opacity: 0; transform: translateY(5px); }
        to { opacity: 1; transform: translateY(0); }
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

    /* Force Lead Pipeline Analytics heading to white - multiple selectors for maximum override */
    div[style*="linear-gradient(90deg, #00506b 0%, #3CA5AA 100%)"] h2,
    div[style*="linear-gradient"] h2,
    .stMarkdown h2,
    h2 {
        color: #FFFFFF !important;
    }
    
    /* Override any Streamlit default h2 styling in markdown blocks */
    [data-testid="stMarkdownContainer"] h2 {
        color: inherit !important;
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

    /* Buttons - aqua background with white text */
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
    button *, .stButton > button *, .stForm button *, .stForm button[type="submit"] *, button p, .stButton > button p, button span, button div {
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
    
    /* Local Time and Relative Time styles */
    .local-time {
        display: inline;
    }
    .local-time.badge {
        display: inline-block;
        background-color: #3CA5AA;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        color: #FFFFFF !important;
    }
</style>
"""


def close_modal():
    """Clear any active modal from session state and rerun.
    CRITICAL: All state must be cleared BEFORE st.rerun() to prevent race conditions."""
    
    # STEP 1: Clear ALL modal state variables (order matters - clear before rerun)
    st.session_state.pop('active_modal', None)
    st.session_state.show_delete_modal = False
    st.session_state.modal_open = False
    st.session_state.modal_action = None
    st.session_state.modal_lead_id = None
    st.session_state.modal_lead_name = None
    st.session_state.modal_data = {}
    
    # STEP 2: Clear any edit state that might persist
    for key in list(st.session_state.keys()):
        if key.startswith('editing_'):
            del st.session_state[key]
    
    # STEP 3: Force a rerun ONLY after all state is cleared
    st.rerun()


# --- PERFORMANCE OPTIMIZATION LAYER ---
# Note: We don't cache SQLAlchemy ORM objects as they don't serialize well with st.cache_data
# Instead, we use eager loading (joinedload) for performance optimization

def get_leads_cached(include_deleted=False):
    """Optimized retrieval of leads with eager-loaded relationships.
    Uses joinedload for performance instead of caching."""
    from app.crud import crud_leads
    db = SessionLocal()
    try:
        if include_deleted:
            return crud_leads.list_deleted_leads(db, limit=1000)
        else:
            return crud_leads.list_leads(db, limit=1000)
    finally:
        db.close()

def clear_leads_cache():
    """Placeholder for cache invalidation (no-op since we removed caching)"""
    pass

@st.cache_data(ttl=300) # Stats can live longer
def get_stats_cached(func_name, *args, **kwargs):
    """Generic cached wrapper for services_stats functions"""
    db = SessionLocal()
    try:
        func = getattr(services_stats, func_name)
        return func(db, *args, **kwargs)
    finally:
        db.close()


def init_session_state():
    """Initialize all session state variables with secure token-based persistence"""
    db = SessionLocal()
    
    # --- PAGE FILTER STATE (PERSISTENCE FIX) ---
    if 'main_navigation' not in st.session_state:
        st.session_state.main_navigation = "Dashboard"
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'db_user_id' not in st.session_state:
        st.session_state.db_user_id = None
    if 'employee_id' not in st.session_state:
        st.session_state.employee_id = None
    if 'show_signup' not in st.session_state:
        st.session_state.show_signup = False
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    if 'stats_view_mode' not in st.session_state:
        st.session_state.stats_view_mode = 'individual'
    if 'show_user_dashboards' not in st.session_state:
        st.session_state.show_user_dashboards = False
    
    # --- MODAL STABILITY STATE (CHICAGO FIX) ---
    if 'modal_open' not in st.session_state:
        st.session_state.modal_open = False
    if 'modal_action' not in st.session_state:
        st.session_state.modal_action = None
    if 'modal_lead_id' not in st.session_state:
        st.session_state.modal_lead_id = None
    if 'modal_lead_name' not in st.session_state:
        st.session_state.modal_lead_name = None
    if 'modal_data' not in st.session_state:
        st.session_state.modal_data = {}
    
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = "All"
    if 'priority_filter' not in st.session_state:
        st.session_state.priority_filter = "All"
    if 'show_only_my_leads' not in st.session_state:
        st.session_state.show_only_my_leads = True
    if 'active_inactive_filter' not in st.session_state:
        st.session_state.active_inactive_filter = "Active"
    if 'show_deleted_leads' not in st.session_state:
        st.session_state.show_deleted_leads = False
    
    # Referrals Filters
    if 'referral_status_filter' not in st.session_state:
        st.session_state.referral_status_filter = "All"
    if 'show_only_my_referrals' not in st.session_state:
        st.session_state.show_only_my_referrals = True
    if 'referral_active_inactive_filter' not in st.session_state:
        st.session_state.referral_active_inactive_filter = "Active"
    if 'show_deleted_referrals' not in st.session_state:
        st.session_state.show_deleted_referrals = False
    if 'referral_type_filter' not in st.session_state:
        st.session_state.referral_type_filter = "All"
    if 'referral_priority_filter' not in st.session_state:
        st.session_state.referral_priority_filter = "All"
    if 'payor_filter' not in st.session_state:
        st.session_state.payor_filter = "All"
    if 'ccu_filter' not in st.session_state:
        st.session_state.ccu_filter = "All"

    # Confirmations Filters
    if 'confirm_payor_filter' not in st.session_state:
        st.session_state.confirm_payor_filter = "All"
    if 'confirm_ccu_filter' not in st.session_state:
        st.session_state.confirm_ccu_filter = "All"
    if 'confirm_care_filter' not in st.session_state:
        st.session_state.confirm_care_filter = "All"
    
    # Timezone Detection - Force Central Time as requested
    st.session_state.user_timezone = "America/Chicago"

    try:
        # Initialize basic auth state if missing
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

        # Secure Token-Based Session Check
        if not st.session_state.authenticated:
            token = get_session_token()
            
            if token:
                # Validate token against database
                user = crud_session_tokens.validate_token(db, token)
                
                if user:
                    # Token is valid - auto-login
                    st.session_state.authenticated = True
                    st.session_state.username = user.username
                    st.session_state.user_role = user.role
                    st.session_state.db_user_id = user.id
                    st.session_state.employee_id = user.user_id
                    st.rerun()
                else:
                    # Token is invalid or expired - clear it
                    clear_session_token()
    finally:
        db.close()
    
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
    
    db.close()



def inject_custom_css():
    """Inject global CSS styles and time fix JS"""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    inject_time_fix_script()


def inject_time_fix_script():
    """Inject a professional, high-reliability script for timezone localization"""
    st.markdown("""
        <script>
        (function() {
            if (window._uiEngineRunning) return;
            window._uiEngineRunning = true;

            const formatLocal = (utc, style) => {
                const date = new Date(utc.includes('T') ? (utc.includes('Z') ? utc : utc + 'Z') : utc);
                if (isNaN(date.getTime())) return null;
                
                const tzOptions = { timeZone: 'America/Chicago' };
                
                if (style === 'ago') {
                    // Get current time in Central Time for accurate relative comparison
                    const nowInCST = new Date(new Date().toLocaleString('en-US', tzOptions));
                    const dateInCST = new Date(date.toLocaleString('en-US', tzOptions));
                    
                    const diff = Math.floor((new Date() - date) / 1000);
                    if (diff < 60) return "Just now";
                    if (diff < 3600) return `${Math.floor(diff/60)} minutes ago`;
                    
                    const today = new Date(nowInCST); today.setHours(0,0,0,0);
                    const timeStr = date.toLocaleString('en-US', {
                        ...tzOptions,
                        hour: '2-digit', minute: '2-digit', hour12: true
                    });
                    
                    if (dateInCST >= today) return `Today at ${timeStr}`;
                    return date.toLocaleString('en-US', {
                        ...tzOptions,
                        month: '2-digit', day: '2-digit', year: 'numeric',
                        hour: '2-digit', minute: '2-digit', hour12: true
                    });
                }
                
                return date.toLocaleString('en-US', {
                    ...tzOptions,
                    month: '2-digit', day: '2-digit', year: 'numeric',
                    hour: '2-digit', minute: '2-digit', hour12: true
                });
            };

            const runFix = () => {
                const elms = document.querySelectorAll('.local-time');
                elms.forEach(el => {
                    const utc = el.getAttribute('data-utc');
                    const style = el.getAttribute('data-style');
                    if (!utc) return;
                    
                    const newText = formatLocal(utc, style);
                    if (newText && (el.innerText !== newText || el.innerText.includes('UTC'))) {
                        el.innerText = newText;
                        el.dataset.processed = "true";
                    }
                });
            };

            // Global Singleton Processor
            window.processTimeFix = runFix;

            // Scroll Lock Logic
            window.setScrollLock = (locked) => {
                document.body.style.overflow = locked ? 'hidden' : '';
                const mainContainer = document.querySelector('[data-testid="stAppViewContainer"]');
                if (mainContainer) mainContainer.style.overflow = locked ? 'hidden' : 'auto';
            };
            
            // Aggressive Polling + Observer
            setInterval(runFix, 1000);
            new MutationObserver(runFix).observe(document.body, {childList:true, subtree:true});
            
            // Try to reach parent if in iframe (Streamlit component behavior)
            try {
                if (window.parent && window.parent.document !== document) {
                    new MutationObserver(runFix).observe(window.parent.document.body, {childList:true, subtree:true});
                }
            } catch(e) {}
            
            runFix();
        })();
        </script>
    """, unsafe_allow_html=True)


def render_time(dt, style='datetime', is_badge=False):
    """
    Returns HTML for a timestamp that will be automatically localized by JS.
    styles: 'datetime' (default), 'ago' (relative time)
    """
    if not dt:
        return "N/A"
    
    # Ensure it's treated as Central Time (CST/CDT) in Python-side fallback
    from app.utils.activity_logger import utc_to_local
    fallback_text = ""
    # Hardcode CST for this user as requested
    cst_dt = utc_to_local(dt, 'America/Chicago')
    if style == 'ago':
        from app.utils.activity_logger import format_time_ago
        fallback_text = format_time_ago(dt, 'America/Chicago')
    else:
        fallback_text = cst_dt.strftime("%m/%d/%Y %I:%M %p (CST)")
    
    cls = "local-time"
    if is_badge:
        cls += " badge"
        
    # Standard HTML part
    html = f'<span class="{cls}" data-utc="{dt.isoformat()}" data-style="{style}">{fallback_text}</span>'
    
    # Universal Trigger: A hidden element that executes the fix logic whenever it loads
    # This ensures conversion even if global scripts are delayed or throttled
    trigger = f'<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" style="display:none" onload="if(window.processTimeFix)window.processTimeFix()">'
    
    return html + trigger


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
        'last_contact_date': str(utc_to_local(lead.last_contact_date, 'America/Chicago')) if lead.last_contact_date else 'N/A',
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


def open_modal(modal_type, target_id, title=None, message=None, **kwargs):
    """Set the active modal in session state and rerun"""
    st.session_state['active_modal'] = {
        'modal_type': modal_type,
        'target_id': target_id,
        'title': title,
        'message': message,
        **kwargs
    }
    st.rerun()




@st.dialog("Action Required")
def confirmation_modal_dialog(db, m):
    """
    Native Streamlit dialog for general confirmation actions.
    """
    title = m.get('title', 'Confirm Action')
    message = m.get('message', 'Are you sure?')
    icon = m.get('icon', '🗑️')
    confirm_label = m.get('confirm_label', 'CONFIRM')
    indicator = m.get('indicator')
    
    indicator_html = f'<div style="margin-top:15px; font-size:0.9rem; color:#6b7280; font-weight:700;">💡 {indicator}</div>' if indicator else ""
    
    # Custom Header
    st.markdown(f"""
    <div class="modal-dialog-header">
      <div class="modal-icon">{icon}</div>
      {title}
    </div>
    <div class="modal-body-content">
      {message}
      {indicator_html}
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        # Action-scoped unique key for CANCEL button
        if st.button("CANCEL", use_container_width=True, key=f"dialog_cancel_{m['modal_type']}_{m['target_id']}"):
            close_modal()
    with c2:
        # Action-scoped unique key for CONFIRM button
        if st.button(confirm_label, type="primary", use_container_width=True, key=f"dialog_confirm_{m['modal_type']}_{m['target_id']}"):
            # Execute backend action directly here
            from app.crud import crud_leads, crud_users, crud_agencies, crud_ccus, crud_events
            
            success = False
            msg = ""
            
            if m['modal_type'] == 'perm_delete':
                if crud_leads.delete_lead(db, m['target_id'], st.session_state.username, st.session_state.get('db_user_id'), permanent=True):
                    msg = "Success! Lead has been permanently removed."
                    success = True
            elif m['modal_type'] == 'soft_delete':
                if crud_leads.delete_lead(db, m['target_id'], st.session_state.username, st.session_state.get('db_user_id'), permanent=False):
                    msg = "Success! Lead moved to Recycle Bin."
                    success = True
            elif m['modal_type'] == 'soft_delete_ref':
                if crud_leads.delete_lead(db, m['target_id'], st.session_state.username, st.session_state.get('db_user_id'), permanent=False):
                    msg = "Success! Referral moved to Recycle Bin."
                    success = True
            elif m['modal_type'] == 'restore_ref':
                if crud_leads.restore_lead(db, m['target_id'], st.session_state.username, st.session_state.get('db_user_id')):
                    msg = "Success! Referral has been restored."
                    success = True
            elif m['modal_type'] == 'perm_delete_ref':
                if crud_leads.delete_lead(db, m['target_id'], st.session_state.username, st.session_state.get('db_user_id'), permanent=True):
                    msg = "Success! Referral has been permanently removed."
                    success = True
            elif m['modal_type'] == 'mark_ref_confirm':
                st.session_state['mark_referral_lead_id'] = m['target_id']
                st.session_state['current_page'] = 'Mark Referral Page'
                st.toast("Heading to Mark Referral Page...")
                success = True # Close modal
            elif m['modal_type'] == 'approve_user':
                crud_users.approve_user(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                msg = "Success! User has been approved."
                success = True
            elif m['modal_type'] == 'reject_user':
                crud_users.reject_user(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                msg = "Success! User request has been rejected."
                success = True
            elif m['modal_type'] == 'delete_agency':
                crud_agencies.delete_agency(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                msg = "Success! Payor has been deleted."
                success = True
            elif m['modal_type'] == 'delete_ccu':
                crud_ccus.delete_ccu(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                msg = "Success! CCU has been deleted."
                success = True
            elif m['modal_type'] == 'delete_event':
                crud_events.delete_event(db, m['target_id'], st.session_state.username, st.session_state.db_user_id)
                msg = "Success! Event has been deleted."
                success = True
            elif m['modal_type'] == 'auth_received':
                from app.schemas import LeadUpdate
                update_data = LeadUpdate(authorization_received=True)
                if crud_leads.update_lead(db, m['target_id'], update_data, st.session_state.username, st.session_state.get('db_user_id')):
                    msg = "Success! Authorization marked as received."
                    success = True
            elif m['modal_type'] == 'unmark_ref':
                from app.schemas import LeadUpdate
                update_data = LeadUpdate(active_client=False, referral_type=None)
                if crud_leads.update_lead(db, m['target_id'], update_data, st.session_state.username, st.session_state.get('db_user_id')):
                    msg = "Success! Client has been unmarked as a referral."
                    success = True
            elif m['modal_type'] == 'update_password':
                new_pwd = st.session_state.get('pending_password_update', {}).get('new_password')
                if new_pwd:
                    if crud_users.update_user_credentials(db, m['target_id'], new_pwd, st.session_state.username, st.session_state.db_user_id):
                        msg = "Success! Your password has been updated."
                        success = True
                        st.session_state.pop('pending_password_update', None)
                    else:
                        st.error("**Failed to update password**")
            
            if success:
                if msg: st.session_state['success_msg'] = msg
                clear_leads_cache()
                close_modal()

@st.dialog("Delete Lead")
def show_delete_modal_dialog(db, lead_id, name):
    """
    Native Streamlit dialog for the special delete lead action from view_leads.
    """
    st.markdown(f"""
    <div class="modal-dialog-header">
      <div class="modal-icon">🗑️</div>
      DELETE LEAD?
    </div>
    <div class="modal-body-content">
      Are you sure you want to delete <b>{name}</b>?<br><br>
      💡 It will be moved to the Recycle Bin.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("CANCEL", use_container_width=True, key=f"dialog_cancel_delete_lead_{lead_id}"):
            st.session_state.show_delete_modal = False
            st.rerun()
    with col2:
        if st.button("DELETE", type="primary", use_container_width=True, key=f"dialog_confirm_delete_lead_{lead_id}"):
            from app.crud import crud_leads
            if crud_leads.delete_lead(db, lead_id, st.session_state.username, st.session_state.get('db_user_id'), permanent=False):
                st.session_state['success_msg'] = f"Success! Lead '{name}' moved to Recycle Bin."
                clear_leads_cache()
            st.session_state.show_delete_modal = False
            st.rerun()

@st.dialog("Edit Lead", width="large")
def show_edit_modal_dialog(db, m):
    """
    Native Streamlit dialog for editing a lead.
    """
    from app.crud import crud_leads, crud_agencies, crud_ccus, crud_events
    from app.schemas import LeadUpdate
    from datetime import datetime

    st.markdown(f"""
    <div class="modal-dialog-header">
      <div class="modal-icon">📝</div>
      Edit Lead: {m["title"]}
    </div>
    """, unsafe_allow_html=True)
            
    # Fetch lead data for form
    lead = m['lead_data']
    # Remove st.form to allow immediate reactivity for toggle and selectboxes
    # with st.form(f"edit_lead_modal_form_{m['target_id']}"):  <-- Removed
    col1, col2 = st.columns(2)
    with col1:
        new_first = st.text_input("First Name", value=str(lead.get('first_name') or ""), key=f"edit_first_{m['target_id']}")
        new_last = st.text_input("Last Name", value=str(lead.get('last_name') or ""), key=f"edit_last_{m['target_id']}")
        new_phone = st.text_input("Phone", value=str(lead.get('phone') or ""), key=f"edit_phone_{m['target_id']}")
        new_staff = st.text_input("Staff Name", value=str(lead.get('staff_name') or ""), key=f"edit_staff_{m['target_id']}")
        # Source Dropdown
        source_options = ["Home Health Notify", "Web", "Direct Through CCU", "Event", "Word of Mouth", "Transfer", "Other"]
        current_src = lead.get('source', 'Other')
        src_idx = source_options.index(current_src) if current_src in source_options else source_options.index("Other")
        new_source = st.selectbox("Source", source_options, index=src_idx, key=f"edit_source_{m['target_id']}")
        
        # Conditional Source Fields
        new_event_name = lead.get('event_name')
        new_soc_date = lead.get('soc_date')
        new_other_source = lead.get('other_source_type')
        new_word_of_mouth = lead.get('word_of_mouth_type')
        
        if new_source == "Event":
            events = crud_events.get_all_events(db)
            event_list = [e.event_name for e in events]
            curr_event = lead.get('event_name')
            e_idx = event_list.index(curr_event) if curr_event in event_list else 0
            new_event_name = st.selectbox("Select Event", event_list, index=e_idx, key=f"edit_event_{m['target_id']}")
        elif new_source == "Transfer":
            new_soc_date = st.date_input("SOC Date", value=lead.get('soc_date') or datetime.now().date(), key=f"edit_soc_{m['target_id']}", format="MM/DD/YYYY")
        elif new_source == "Other":
            new_other_source = st.text_input("Specify Source", value=str(lead.get('other_source_type') or ""), key=f"edit_other_src_{m['target_id']}")
        elif new_source == "Word of Mouth":
            wom_options = ["Caregiver", "Community", "Client", "Staff"]
            curr_wom = lead.get('word_of_mouth_type')
            w_idx = wom_options.index(curr_wom) if curr_wom in wom_options else 0
            new_word_of_mouth = st.selectbox("Type", wom_options, index=w_idx, key=f"edit_wom_{m['target_id']}")

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
        new_street = st.text_input("Street", value=str(lead.get('street') or ""), key=f"edit_street_{m['target_id']}")
        new_city = st.text_input("City", value=str(lead.get('city') or ""), key=f"edit_city_{m['target_id']}")
        new_state = st.text_input("State", value=str(lead.get('state') or "IL"), max_chars=2, key=f"edit_state_{m['target_id']}")
        new_zip = st.text_input("Zip Code", value=str(lead.get('zip_code') or ""), key=f"edit_zip_{m['target_id']}")
        
    with col2:
        status_options = ["Intro Call", "Follow Up", "No Response", "Referral Sent", "Inactive"]
        current_status = lead.get('last_contact_status', 'Intro Call')
        # Normalize for matching
        if current_status == "Active": current_status = "Intro Call"
        status_idx = status_options.index(current_status) if current_status in status_options else 0
        new_status = st.selectbox("Status", status_options, index=status_idx, key=f"edit_status_{m['target_id']}")
        
        priority_options = ["High", "Medium", "Low"]
        current_priority = lead.get('priority', 'Medium')
        priority_index = priority_options.index(current_priority) if current_priority in priority_options else 1
        new_priority = st.selectbox("Priority", priority_options, index=priority_index, key=f"edit_priority_{m['target_id']}")
        
        dob_value = lead.get('dob')
        if isinstance(dob_value, str) and dob_value:
            try:
                from datetime import date as dt_date
                dob_value = datetime.strptime(dob_value, '%Y-%m-%d').date()
            except:
                dob_value = None
        
        from datetime import date
        
        # Callback for age calculation in edit modal
        def on_edit_dob_change():
            dob_key = f"edit_dob_{m['target_id']}"
            age_key = f"edit_age_{m['target_id']}"
            if st.session_state.get(dob_key):
                today = date.today()
                dob = st.session_state[dob_key]
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                st.session_state[age_key] = age

        new_dob = st.date_input("Date of Birth", value=dob_value if dob_value else None, min_value=date(1900, 1, 1), max_value=date.today(), key=f"edit_dob_{m['target_id']}", on_change=on_edit_dob_change, format="MM/DD/YYYY")
        new_age = st.number_input("Age / Year", min_value=0, max_value=3000, value=int(lead.get('age') or 0), key=f"edit_age_{m['target_id']}")
        new_medicaid = st.text_input("Medicaid #", value=str(lead.get('medicaid_no') or ""), key=f"edit_medicaid_{m['target_id']}")
        
        new_e_name = st.text_input("Emergency Contact", value=str(lead.get('e_contact_name') or ""), key=f"edit_ename_{m['target_id']}")
        new_e_relation = st.text_input("Relation", value=str(lead.get('e_contact_relation') or ""), key=f"edit_erelation_{m['target_id']}")
        new_e_phone = st.text_input("Emergency Phone", value=str(lead.get('e_contact_phone') or ""), key=f"edit_ephone_{m['target_id']}")
    
    new_comments = st.text_area("Comments", value=str(lead.get('comments') or ""), height=100, key=f"edit_comments_{m['target_id']}")
    
    # --- GLOBAL ENTITY UPDATES (CCU / PAYOR) ---
    enable_global = st.checkbox("Edit CCU/Payor", value=False, key=f"enable_entity_mgmt_{m['target_id']}")
    
    if enable_global:
        st.divider()
        ent_col1, ent_col2 = st.columns(2)
        
        # PAYOR (AGENCY)
        with ent_col1:
            agencies = crud_agencies.get_all_agencies(db)
            agency_map = {a.name: a.id for a in agencies}
            agency_list = ["None"] + list(agency_map.keys())
            
            curr_agency_id = lead.get('agency_id')
            curr_agency_name = "None"
            if curr_agency_id:
                for name, aid in agency_map.items():
                    if aid == curr_agency_id:
                        curr_agency_name = name
                        break
            
            new_agency_name_sel = st.selectbox("Payor", agency_list, index=agency_list.index(curr_agency_name), key=f"edit_agency_sel_{m['target_id']}")
            new_agency_id = agency_map.get(new_agency_name_sel)
            
            if new_agency_id:
                exp_a_key = f"expand_a_edit_{m['target_id']}_{new_agency_id}"
                if exp_a_key not in st.session_state:
                    st.session_state[exp_a_key] = False
                    
                with st.expander(f"Edit {new_agency_name_sel} (Globally)", expanded=st.session_state[exp_a_key]):
                    agency_obj = crud_agencies.get_agency(db, new_agency_id)
                    u_a_addr = st.text_input("Payor Address", value=agency_obj.address or "", key=f"global_a_addr_{new_agency_id}")
                    u_a_phone = st.text_input("Payor Phone", value=agency_obj.phone or "", key=f"global_a_phone_{new_agency_id}")
                    u_a_fax = st.text_input("Payor Fax", value=getattr(agency_obj, 'fax', '') or "", key=f"global_a_fax_{new_agency_id}")
                    u_a_email = st.text_input("Payor Email", value=agency_obj.email or "", key=f"global_a_email_{new_agency_id}")
                    if st.button("Update Payor Details", key=f"global_a_save_{new_agency_id}"):
                        crud_agencies.update_agency(db, new_agency_id, new_agency_name_sel, st.session_state.username, st.session_state.get('db_user_id'), 
                                                   address=u_a_addr, phone=u_a_phone, fax=u_a_fax, email=u_a_email)
                        st.session_state[exp_a_key] = False
                        st.success(f"**Global Update Successful!** Payor '{new_agency_name_sel}' has been updated locally and across all leads.")
                        st.toast(f"Payor Updated Globally!", icon="✅")
                        # st.rerun() removed to keep popup open

        # CCU
        with ent_col2:
            ccus = crud_ccus.get_all_ccus(db)
            ccu_map = {c.name: c.id for c in ccus}
            ccu_list = ["None"] + list(ccu_map.keys())
            
            curr_ccu_id = lead.get('ccu_id')
            curr_ccu_name = "None"
            if curr_ccu_id:
                for name, cid in ccu_map.items():
                    if cid == curr_ccu_id:
                        curr_ccu_name = name
                        break
                        
            new_ccu_name_sel = st.selectbox("CCU", ccu_list, index=ccu_list.index(curr_ccu_name), key=f"edit_ccu_sel_{m['target_id']}")
            new_ccu_id = ccu_map.get(new_ccu_name_sel)
            
            if new_ccu_id:
                exp_c_key = f"expand_c_edit_{m['target_id']}_{new_ccu_id}"
                if exp_c_key not in st.session_state:
                    st.session_state[exp_c_key] = False
                    
                with st.expander(f"Edit {new_ccu_name_sel} (Globally)", expanded=st.session_state[exp_c_key]):
                    ccu_obj = crud_ccus.get_ccu_by_id(db, new_ccu_id)
                    u_c_addr = st.text_input("CCU Address", value=ccu_obj.address or "", key=f"global_c_addr_{new_ccu_id}")
                    u_c_phone = st.text_input("CCU Phone", value=ccu_obj.phone or "", key=f"global_c_phone_{new_ccu_id}")
                    u_c_fax = st.text_input("CCU Fax", value=getattr(ccu_obj, 'fax', '') or "", key=f"global_c_fax_{new_ccu_id}")
                    u_c_email = st.text_input("CCU Email", value=getattr(ccu_obj, 'email', '') or "", key=f"global_c_email_{new_ccu_id}")
                    u_c_coord = st.text_input("Coordinator", value=ccu_obj.care_coordinator_name or "", key=f"global_c_coord_{new_ccu_id}")
                    if st.button("Update CCU Details", key=f"global_c_save_{new_ccu_id}"):
                        crud_ccus.update_ccu(db, new_ccu_id, new_ccu_name_sel, st.session_state.username, st.session_state.get('db_user_id'), 
                                            address=u_c_addr, phone=u_c_phone, fax=u_c_fax, email=u_c_email, care_coordinator_name=u_c_coord)
                        st.session_state[exp_c_key] = False
                        st.success(f"**Global Update Successful!** CCU '{new_ccu_name_sel}' has been updated locally and across all leads.")
                        st.toast(f"CCU Updated Globally!", icon="✅")
                        # st.rerun() removed to keep popup open
    else:
        new_agency_id = lead.get('agency_id')
        new_ccu_id = lead.get('ccu_id')
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("CANCEL", use_container_width=True, key=f"edit_cancel_{m['target_id']}"):
            close_modal() # Custom helper from common.py
    with c2:
        if st.button("SAVE CHANGES", type="primary", use_container_width=True, key=f"edit_save_{m['target_id']}"):
                # Update dictionary
                update_dict = {
                    "first_name": new_first,
                    "last_name": new_last,
                    "phone": new_phone,
                    "staff_name": new_staff,
                    "source": new_source,
                    "event_name": new_event_name,
                    "soc_date": new_soc_date,
                    "other_source_type": new_other_source,
                    "word_of_mouth_type": new_word_of_mouth,
                    "city": new_city,
                    "street": new_street,
                    "state": new_state,
                    "zip_code": new_zip,
                    "last_contact_status": new_status,
                    "priority": new_priority,
                    "dob": new_dob,
                    "medicaid_no": new_medicaid,
                    "e_contact_name": new_e_name,
                    "e_contact_relation": new_e_relation,
                    "e_contact_phone": new_e_phone,
                    "active_client": lead.get('active_client'),
                    "comments": new_comments,
                    "age": new_age if new_age > 0 else None,
                    "agency_id": new_agency_id,
                    "ccu_id": new_ccu_id
                }
                schema_data = LeadUpdate(**update_dict)
                crud_leads.update_lead(db, m['target_id'], schema_data, st.session_state.username, st.session_state.get('db_user_id'))
                st.session_state['success_msg'] = f"Success! Lead '{new_first} {new_last}' updated successfully!"
                clear_leads_cache()
                close_modal()

def handle_active_modal(db):
    """
    Centralized handler for all active modals in the application.
    (Updated with Stability Refactor logic + Ghost Popup Prevention)
    """
    
    # 0. ULTRA-DEFENSIVE: Detect and clear stale/incomplete modal state BEFORE processing
    # This prevents ghost popups from incomplete state left over from previous interactions
    has_modal_open = st.session_state.get('modal_open', False)
    has_modal_action = st.session_state.get('modal_action')
    has_active_modal = 'active_modal' in st.session_state
    has_show_delete = st.session_state.get('show_delete_modal', False)
    
    # helper to wipe EVERYTHING
    def _wipe_all_modal_state():
        st.session_state.modal_open = False
        st.session_state.modal_action = None
        st.session_state.modal_lead_id = None
        st.session_state.modal_lead_name = None
        st.session_state.modal_data = {}
        st.session_state.pop('active_modal', None)
        st.session_state.show_delete_modal = False

    # If modal_open is True but modal_action is None/empty, it's stale state - clear it
    if has_modal_open and not has_modal_action and not has_active_modal and not has_show_delete:
        _wipe_all_modal_state()
        return
    
    # 1. SPECIAL DELETE MODAL (legacy support for view_leads.py)
    if st.session_state.get('show_delete_modal', False):
        # Consume the trigger immediately
        lead_id = st.session_state.get('delete_lead_id')
        name = st.session_state.get('delete_lead_name', 'Unknown')
        _wipe_all_modal_state() # Wipe all triggers before showing dialog
        show_delete_modal_dialog(db, lead_id, name)
        return

    # 2. HANDLE GENERIC ACTIVE_MODAL (Action-Scoped Priority)
    m = None
    
    # CRITICAL: Only process modal if modal_open is True AND modal_action is set
    # This prevents ghost popups from stale state
    if st.session_state.get('modal_open', False) and st.session_state.get('modal_action'):
         # Priority: Map action-scoped state to 'm' for compatibility
         m = {
             'modal_type': st.session_state.modal_action,
             'target_id': st.session_state.modal_lead_id,
             'title': st.session_state.modal_lead_name or st.session_state.modal_data.get('title'),
             'lead_data': st.session_state.modal_data.get('lead_data'),
             'icon': st.session_state.modal_data.get('icon'),
             'type': st.session_state.modal_data.get('type'),
             'confirm_label': st.session_state.modal_data.get('confirm_label'),
             'cancel_label': st.session_state.modal_data.get('cancel_label'),
             'indicator': st.session_state.modal_data.get('indicator'),
             'message': st.session_state.modal_data.get('message')
         }
         # CRITICAL: Wipe ALL triggers now that we've captured the data
         _wipe_all_modal_state()
         
    elif 'active_modal' in st.session_state:
         # Fallback: Legacy dictionary (consume it immediately)
         m = st.session_state.pop('active_modal')
         # Ensure we also clear the other keys just in case
         _wipe_all_modal_state()
    else:
         # No modal to show - ensure all modal state is cleared
         _wipe_all_modal_state()
         return
    
    if not m:
        return
    
    # DEBUG LOGGING
    print(f"[DEBUG] Modal Triggered: action={m.get('modal_type')}, id={m.get('target_id')}")
    
    # Dispatch to specific dialog functions
    if m['modal_type'] == 'save_edit_modal':
        show_edit_modal_dialog(db, m)
    else:
        confirmation_modal_dialog(db, m)


def render_confirmation_modal(title, message, icon="🗑️", type="info", confirm_label="DELETE", cancel_label="CANCEL", target_id="modal", indicator=None, modal_type='soft_delete'):
    """
    Triggers a confirmation modal by setting isolated session state variables.
    """
    # 1. HARD RESET any previous modal state to prevent ghosting
    st.session_state.modal_open = False
    st.session_state.modal_action = None
    st.session_state.modal_lead_id = None
    st.session_state.modal_data = {}
    st.session_state.pop('active_modal', None)
    
    # 2. Set new state
    st.session_state.modal_open = True
    st.session_state.modal_action = modal_type
    st.session_state.modal_lead_id = target_id
    st.session_state.modal_data = {
        'title': title,
        'message': message,
        'icon': icon,
        'type': type,
        'confirm_label': confirm_label,
        'cancel_label': cancel_label,
        'indicator': indicator
    }
    
    # 3. Maintain legacy dictionary for backward compatibility
    st.session_state['active_modal'] = {
        'modal_type': modal_type,
        'title': title,
        'message': message,
        'icon': icon,
        'type': type,
        'confirm_label': confirm_label,
        'target_id': target_id,
        'indicator': indicator
    }
    
    st.rerun()
    return None


def render_api_status():
    """Diagnostic tool to check if the FastAPI backend is running."""
    import urllib.request
    import os
    
    backend_url = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8003")
    st.sidebar.markdown("---")
    
    try:
        with urllib.request.urlopen(f"{backend_url}/health", timeout=3) as response:
            if response.getcode() == 200:
                st.sidebar.markdown("**System: Live**")
            else:
                st.sidebar.markdown("**System: Offline**")
    except:
        st.sidebar.markdown("**System: Offline**")
