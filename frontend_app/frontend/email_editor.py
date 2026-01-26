import streamlit as st
from app.db import SessionLocal
from app.crud import crud_email_templates

def view_email_editor():
    """UI for editing notification templates"""
    st.markdown('<div class="main-header">Email Template Editor</div>', unsafe_allow_html=True)
    
    if st.session_state.user_role != "admin":
        st.error("Access Denied.")
        return

    db = SessionLocal()
    
    try:
        templates = crud_email_templates.get_templates(db)
        template_map = {t.slug: t for t in templates}
        
        # 1. Select Template
        st.markdown("### Select notification to edit")
        slug_options = list(template_map.keys())
        selected_slug = st.selectbox("Notification Type", slug_options, 
                                     format_func=lambda x: x.replace('_', ' ').title())
        
        if selected_slug:
            t = template_map[selected_slug]
            
            with st.form(f"edit_template_{selected_slug}"):
                st.markdown(f"#### Editing: **{selected_slug.replace('_', ' ').title()}**")
                
                new_subject = st.text_input("Email Subject", value=t.subject)
                new_body = st.text_area("Email Body (Text)", value=t.body, height=300)
                
                # Help text for placeholders
                st.info("""
                **Available Placeholders:**
                - {name} : Full Name of lead
                - {phone} : Phone number
                - {status} : Current status
                - {referral_type} : referral type (for referrals)
                - {ccu_name} : Assigned CCU
                - {payor_name} : Payor name
                - {created_date} : Creation date
                """)
                
                if st.form_submit_button("SAVE TEMPLATE", type="primary"):
                    crud_email_templates.update_template(db, selected_slug, new_subject, new_body)
                    st.success(f"Custom template for '{selected_slug}' has been saved!")
                    st.toast("Template Updated Successfully", icon="✅")
                    # Clear cache/rerun if needed
            
            # --- PREVIEW SECTION ---
            st.divider()
            st.markdown("### Live Preview (Draft)")
            with st.expander("Show Preview", expanded=True):
                # Dummy data for preview
                preview_data = {
                    "name": "John Doe",
                    "phone": "(555) 012-3456",
                    "dob": "01/01/1980",
                    "status": "Intro Call",
                    "referral_type": "Regular",
                    "ccu_name": "Lake County CCU",
                    "ccu_phone": "555-1111",
                    "ccu_fax": "555-2222",
                    "ccu_address": "123 Maple St, Libertyville, IL",
                    "ccu_coordinator": "Jane Smith",
                    "payor_name": "Aetna",
                    "payor_suboption": "Standard",
                    "source": "Web",
                    "created_date": "01/27/2026",
                    "days_since_auth": "5",
                    "auth_received_date": "01/22/2026"
                }
                
                try:
                    p_subject = new_subject.format(**preview_data)
                    p_body = new_body.format(**preview_data)
                    
                    st.markdown(f"**Subject:** {p_subject}")
                    st.markdown("**Body:**")
                    st.code(p_body, language="text")
                except Exception as e:
                    st.warning(f"Preview calculation error (likely a placeholder typo): {e}")

    finally:
        db.close()
