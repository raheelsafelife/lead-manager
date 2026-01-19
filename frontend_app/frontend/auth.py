"""
Authentication pages: Login, Signup, Forgot Password
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import streamlit as st
from app.db import SessionLocal
from app.crud import crud_users, crud_activity_logs
from app.schemas import UserCreate
from frontend.common import get_logo_path


def signup():
    """Signup page for new users"""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<div class="main-header main-header-signup">CREATE ACCOUNT</div>', unsafe_allow_html=True)
    
    with st.form("signup_form"):
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">User ID (Unique Identifier)<span class="required-star">*</span></label>', unsafe_allow_html=True)
        user_id = st.text_input("User ID (Unique Identifier)", help="Enter a unique identifier for this user", label_visibility="collapsed")
        
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Username<span class="required-star">*</span></label>', unsafe_allow_html=True)
        username = st.text_input("Username", label_visibility="collapsed")
        
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Email<span class="required-star">*</span></label>', unsafe_allow_html=True)
        email = st.text_input("Email", label_visibility="collapsed")
        
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Password<span class="required-star">*</span></label>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", label_visibility="collapsed")
        
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Confirm Password<span class="required-star">*</span></label>', unsafe_allow_html=True)
        confirm_password = st.text_input("Confirm Password", type="password", label_visibility="collapsed")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Sign Up", type="primary", width="stretch")
        with col2:
            back = st.form_submit_button("Back to Login", type="secondary", width="stretch")
        
        if back:
            st.session_state.show_signup = False
            st.rerun()
        
        if submit:
            if not all([user_id, username, email, password]):
                st.error("**Please fill in all fields**")
            elif password != confirm_password:
                st.error("**Passwords do not match**")
            elif len(password) < 6:
                st.error("**Password must be at least 6 characters**")
            elif '@' not in email:
                st.error("**Please enter a valid email**")
            else:
                db = SessionLocal()
                try:
                    existing_user_id = crud_users.get_user_by_user_id(db, user_id)
                    if existing_user_id:
                        st.error("**User ID already taken. Please use a unique identifier.**")
                    else:
                        existing_user = crud_users.get_user_by_username(db, username)
                        if existing_user:
                            st.error("**Username already taken**")
                        else:
                            existing_email = crud_users.get_user_by_email(db, email)
                            if existing_email:
                                st.error("**Email already registered**")
                            else:
                                user_data = UserCreate(
                                    user_id=user_id,
                                    username=username,
                                    email=email,
                                    password=password,
                                    role="user"
                                )
                                user = crud_users.create_user(db, user_data)
                                st.toast("Account created successfully!", icon="✅")
                                st.success("**Account created successfully.**")
                                st.info("Your account is now pending admin approval.")
                                st.session_state.show_signup = False
                                st.rerun()
                except Exception as e:
                    st.error(f"**Error creating account: {e}**")
                finally:
                    db.close()
    
    st.markdown('</div>', unsafe_allow_html=True)


def login():
    """Login page"""
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

    st.image(get_logo_path(), width=400)
    
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
    
    st.markdown(
        """
        <div class="main-header" style="font-size: 4rem !important; text-align: center; margin-bottom: 1rem;">
            LEADS MANAGER
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    with st.form("login_form"):
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Username<span class="required-star">*</span></label>', unsafe_allow_html=True)
        username = st.text_input("Username", label_visibility="collapsed").strip()
        
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Password<span class="required-star">*</span></label>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", label_visibility="collapsed").strip()
        
        submit = st.form_submit_button("Login", width="stretch")
        
        if submit:
            # Validation with toast notifications
            if not username:
                st.toast("Username Required - Please enter your username", icon="❌")
                st.error("**Username Required - Please enter your username**")
            elif not password:
                st.toast("Password Required - Please enter your password", icon="❌")
                st.error("**Password Required - Please enter your password**")
            else:
                try:
                    db = SessionLocal()
                    user = crud_users.authenticate_user(db, username, password)
                
                    if user == "pending":
                        st.toast("Account Pending Approval - Contact an administrator", icon="⏳")
                        st.warning("Your account is pending admin approval. Please contact an admin.")
                    elif user:
                        st.session_state.authenticated = True
                        st.session_state.username = user.username
                        st.session_state.user_role = user.role
                        st.session_state.db_user_id = user.id
                        st.session_state.employee_id = user.user_id
                        
                        # Create secure session token in database
                        from frontend.common import set_session_token
                        from app.crud import crud_session_tokens
                        token = crud_session_tokens.create_session_token(db, user.id, days_valid=7)
                        set_session_token(token)
                        
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
                        
                        st.toast(f"Welcome back, {user.username}!", icon="👋")
                        st.success("**Login successful.** Redirecting...")
                        st.rerun()
                    else:
                        st.toast("Login Failed - Incorrect username or password", icon="❌")
                        st.error("**Invalid credentials. Please check your username and password.**")
                except Exception as e:
                    st.toast(f"Login Error - {str(e)}", icon="❌")
                    st.error(f"**Database connection error: {str(e)}**")
                    st.info("Check if Railway Volume is correctly mounted at /app/data")
                finally:
                    if 'db' in locals():
                        db.close()
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sign Up", width="stretch", type="primary"):
            st.session_state.show_signup = True
            st.session_state.show_forgot_password = False
            st.rerun()
    with col2:
        if st.button("Forgot Password?", width="stretch", type="secondary"):
            st.session_state.show_forgot_password = True
            st.session_state.show_signup = False
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def forgot_password():
    """Forgot password page - creates reset request for admin"""
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<div class="main-header main-header-forgot">FORGOT PASSWORD</div>', unsafe_allow_html=True)
    st.info("Enter your username to request a password reset. An admin will review and reset your password.")
    
    with st.form("forgot_password_form"):
        st.markdown('<label style="font-weight: 700; color: #000000; font-size: 0.95rem;">Username<span class="required-star">*</span></label>', unsafe_allow_html=True)
        username = st.text_input("Username", label_visibility="collapsed")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Request Reset", type="primary", width="stretch")
        with col2:
            back = st.form_submit_button("Back to Login", type="secondary", width="stretch")
        
        if back:
            st.session_state.show_forgot_password = False
            st.rerun()
        
        if submit:
            if not username:
                st.error("**Please enter your username**")
            else:
                db = SessionLocal()
                try:
                    user = crud_users.request_password_reset(db, username)
                    if user:
                        st.toast("Reset Requested", icon="✅")
                        st.success("**Password reset requested.**")
                        st.info("Your request has been sent to administrators for review.")
                        st.session_state.show_forgot_password = False
                        st.rerun()
                    else:
                        st.error("**Username not found**")
                except Exception as e:
                    st.error(f"**Error: {e}**")
                finally:
                    db.close()
    
    st.markdown('</div>', unsafe_allow_html=True)
