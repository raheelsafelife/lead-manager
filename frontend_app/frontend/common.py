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
from app.crud import crud_session_tokens
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

    html, body, [class^="css"], .stApp  {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                     Arial, 'Source Sans Pro', system-ui, sans-serif;
        background-color: #FFFFFF !important;
        color: #111827 !important;
        animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    /* Modal Backdrop Layer */
    .modal-backdrop {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background-color: rgba(0, 0, 0, 0) !important;
        z-index: 0 !important;
        pointer-events: none !important;
        transition: background-color 0.3s ease !important;
    }

    body:has(.modal-marker) .modal-backdrop {
        background-color: rgba(0, 0, 0, 0.4) !important;
        z-index: 999990 !important;
        pointer-events: auto !important;
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
        min-width: 450px !important;
        padding: 1rem 1.5rem !important;
        border-radius: 14px !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
        border-left: 10px solid !important;
        background: white !important;
        color: #111827 !important;
        z-index: 1000000 !important;
        animation: toastSlideIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards !important;
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
    }
    .stButton > button:active {
        transform: scale(0.96) !important;
    }

    /* MODAL STYLING - FULL WIDTH & OVERLAY APPROACH */
    
    /* Ensure the main app content stays full width when modal is active */
    body:has(.modal-marker) [data-testid="stAppViewContainer"],
    body:has(.modal-marker) [data-testid="stMain"],
    body:has(.modal-marker) .main,
    body:has(.modal-marker) .block-container {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 100% !important;
        margin: 0 !important;
    }

    /* Modal backdrop - dark semi-transparent overlay */
    .modal-backdrop {
        position: fixed !important;
        z-index: 999998 !important;
        left: 0 !important;
        top: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background-color: rgba(0, 0, 0, 0.4) !important; /* Semi-transparent dark overlay */
        display: none !important;
        pointer-events: auto !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }

    /* Show backdrop when modal is active */
    body:has(.modal-marker) .modal-backdrop {
        display: block !important;
    }

    /* Target the Streamlit container that has our marker */
    /* This is the actual modal dialog box */
    [data-testid="stVerticalBlock"]:has(.modal-marker) {
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        width: 95% !important;
        max-width: 420px !important;
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
        z-index: 999999 !important; /* Above everything */
        padding: 0 !important;
        overflow-y: auto !important; /* Allow internal scrolling if too tall */
        max-height: 95vh !important; /* Don't exceed screen height */
        pointer-events: auto !important; /* Re-enable for the dialog box */
        animation: modalFadeIn 0.3s ease-out !important;
        gap: 0 !important;
        margin: 0 !important;
        filter: none !important;
    }

    /* Force interactive state for buttons inside the modal */
    [data-testid="stVerticalBlock"]:has(.modal-marker) button {
        pointer-events: auto !important;
        cursor: pointer !important;
    }

    /* Modal fade-in animation - Centered */
    @keyframes modalFadeIn {
        from { 
            opacity: 0; 
            transform: translate(-50%, -48%);
        }
        to { 
            opacity: 1; 
            transform: translate(-50%, -50%);
        }
    }

    /* Modal fade-in animation - Top Aligned */
    @keyframes modalFadeInTop {
        from { 
            opacity: 0; 
            transform: translate(-50%, 10px);
        }
        to { 
            opacity: 1; 
            transform: translate(-50%, 0);
        }
    }

    /* Transition the header to the Slate Teal design */
    .modal-header {
        background-color: #28646E !important; /* Slate Teal from Screenshot */
        padding: 1.5rem !important;
        text-align: center !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }

    .modal-icon {
        font-size: 3.5rem !important;
        color: white !important;
        margin-bottom: 0.25rem !important;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)) !important;
    }

    .modal-title {
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        margin: 0 !important;
        line-height: 1.2 !important;
    }

    .modal-body {
        padding: 2rem 1.75rem !important;
        color: #1F2937 !important;
        font-size: 1.1rem !important;
        text-align: center !important;
        background-color: white !important;
        line-height: 1.5 !important;
    }

    /* Indicator (Lightbulb Notice) */
    .modal-indicator {
        margin-top: 1.25rem !important;
        font-size: 1rem !important;
        color: #4B5563 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.5rem !important;
    }

    /* Footer styled with columns inside */
    [data-testid="stVerticalBlock"]:has(.modal-marker) > div:last-child {
        background-color: white !important;
        padding: 1.25rem 1.75rem 2rem 1.75rem !important;
        margin-top: 0 !important;
        border-top: 1px solid #F3F4F6 !important;
    }

    /* Button Styling to match Screenshot */
    [data-testid="stVerticalBlock"]:has(.modal-marker) button {
        height: 48px !important;
        border-radius: 8px !important;
        text-transform: uppercase !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }

    /* CANCEL Button: Bordered White with Slate Teal Text */
    [data-testid="stVerticalBlock"]:has(.modal-marker) button:not([kind="primary"]) {
        background-color: #FFFFFF !important;
        border: 1px solid #28646E !important; /* Border matches header Slate Teal */
    }

    [data-testid="stVerticalBlock"]:has(.modal-marker) button:not([kind="primary"]) p {
        color: #28646E !important; /* Text matches header Slate Teal */
    }

    [data-testid="stVerticalBlock"]:has(.modal-marker) button:not([kind="primary"]):hover {
        background-color: #F0F7F8 !important;
        border-color: #034D61 !important;
    }

    [data-testid="stVerticalBlock"]:has(.modal-marker) button:not([kind="primary"]):hover p {
        color: #034D61 !important;
    }

    /* ACTION/DELETE Button: Dark Teal with White Text */
    [data-testid="stVerticalBlock"]:has(.modal-marker) button[kind="primary"] {
        background-color: #034D61 !important; /* Dark Teal from Image */
        border: none !important;
    }

    [data-testid="stVerticalBlock"]:has(.modal-marker) button[kind="primary"] p {
        color: #FFFFFF !important;
    }

    [data-testid="stVerticalBlock"]:has(.modal-marker) button[kind="primary"]:hover {
        background-color: #023D4D !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }

    .modal-marker { display: none !important; }

    /* For Larger Form Modals (Edit Lead) */
    body:has(.modal-marker.form-modal) [data-testid="stVerticalBlock"]:has(.modal-marker) {
        max-width: 700px !important;
        top: 2.5vh !important;
        transform: translateX(-50%) !important; /* Reset Y-translation for top alignment */
        max-height: 95vh !important;
        animation: modalFadeInTop 0.3s ease-out !important;
    }

    body:has(.modal-marker.form-modal) .modal-body {
        text-align: left !important;
        padding: 1.5rem !important;
    }

    /* Type Specific Colors if needed */
    .modal-marker.warning ~ .modal-header { background-color: #EA580C !important; }
    .modal-marker.error ~ .modal-header { background-color: #991B1B !important; }
    .modal-marker.info ~ .modal-header { background-color: #0369A1 !important; }

    @keyframes delayedShow {
        0% { opacity: 0; visibility: hidden; }
        95% { opacity: 0; visibility: hidden; }
        100% { opacity: 1; visibility: visible; pointer-events: auto; }
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


def init_session_state():
    """Initialize all session state variables with secure token-based persistence"""
    db = SessionLocal()
    
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

    # Ensure main_navigation is initialized for the radio button
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
    
    # Timezone Detection - Force Central Time as requested
    st.session_state.user_timezone = "America/Chicago"
    
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


def render_confirmation_modal(title, message, icon="🗑️", type="info", confirm_label="DELETE", cancel_label="CANCEL", key_prefix="modal", indicator=None):
    """
    Renders a centered professional teal-header modal based on a screenshot.
    Uses CSS :has selector to style the entire container.
    Returns True if confirmed, False if cancelled, None if no action.
    """
    # Create the backdrop
    st.markdown('<div class="modal-backdrop"></div>', unsafe_allow_html=True)
    
    with st.container():
        # Marker for CSS targeting
        st.markdown(f'<div class="modal-marker {type}"></div>', unsafe_allow_html=True)
        
        # Header (Centered Icon + Title)
        st.markdown(f"""
        <div class="modal-header">
            <div class="modal-icon">{icon}</div>
            <div class="modal-title">{title}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Body (Message + Optional Indicator)
        indicator_html = f'<div class="modal-indicator">💡 {indicator}</div>' if indicator else ""
        st.markdown(f"""
        <div class="modal-body">
            {message}
            {indicator_html}
        </div>
        """, unsafe_allow_html=True)
        
        # Footer Buttons
        footer_col1, footer_col2 = st.columns([1, 1])
        action = None
        with footer_col1:
            if st.button(cancel_label, key=f"{key_prefix}_cancel", use_container_width=True):
                action = False
        with footer_col2:
            if st.button(confirm_label, key=f"{key_prefix}_confirm", type="primary", use_container_width=True):
                action = True
                
        return action


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
                st.sidebar.markdown("**System: Live**")
            else:
                st.sidebar.markdown("**System: Offline**")
    except Exception:
        st.sidebar.markdown("**System: Offline**")
