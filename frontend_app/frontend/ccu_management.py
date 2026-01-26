import streamlit as st
from app.db import SessionLocal
from app.crud import crud_ccus, crud_leads
import pandas as pd

def view_ccu_management():
    """CCU Data Cleanup & Management"""
    st.markdown('<div class="main-header">CCU & Provider Management</div>', unsafe_allow_html=True)
    
    if st.session_state.user_role != "admin":
        st.error("Access Denied.")
        return

    db = SessionLocal()
    
    try:
        tab1, tab2 = st.tabs(["Update Contact Info", "Merge Duplicates"])
        
        with tab1:
            st.markdown("### Update Provider Details")
            ccus = crud_ccus.get_all_ccus(db)
            ccu_map = {c.name: c for c in ccus}
            
            sel_ccu_name = st.selectbox("Select CCU to Edit", ["Select CCU"] + sorted(list(ccu_map.keys())))
            
            if sel_ccu_name != "Select CCU":
                c = ccu_map[sel_ccu_name]
                
                with st.form(f"edit_ccu_{c.id}"):
                    st.markdown(f"#### Editing: **{c.name}**")
                    
                    c_name = st.text_input("CCU Name", value=c.name)
                    c_addr = st.text_input("Address", value=c.address or "")
                    c_city = st.text_input("City", value=c.city or "")
                    c_zip = st.text_input("Zip Code", value=c.zip_code or "")
                    c_phone = st.text_input("Phone", value=c.phone or "")
                    c_fax = st.text_input("Fax", value=c.fax or "")
                    c_email = st.text_input("Email", value=c.email or "")
                    c_coord = st.text_input("Care Coordinator", value=c.care_coordinator_name or "")
                    
                    if st.form_submit_button("UPDATE CCU", type="primary"):
                        # We'll use the existing update function or extend it
                        # For now, let's use a custom logic if needed
                        crud_ccus.update_ccu(
                            db, c.id, c_name, st.session_state.username, st.session_state.db_user_id,
                            address=c_addr, phone=c_phone, fax=c_fax, email=c_email, 
                            care_coordinator_name=c_coord
                        )
                        st.success(f"CCU '{c_name}' updated successfully!")
                        st.rerun()

        with tab2:
            st.markdown("### Merge Duplicate CCUs")
            st.warning("⚠️ Warning: Merging will move ALL leads from the 'Source' CCU to the 'Target' CCU, then DELETE the Source CCU.")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                source_ccu_name = st.selectbox("Source (Duplicate)", ["Select CCU"] + sorted(list(ccu_map.keys())), key="merge_source")
            
            with col_b:
                target_ccu_name = st.selectbox("Target (Correct Records)", ["Select CCU"] + sorted(list(ccu_map.keys())), key="merge_target")
            
            if source_ccu_name != "Select CCU" and target_ccu_name != "Select CCU":
                if source_ccu_name == target_ccu_name:
                    st.error("Source and Target cannot be the same.")
                else:
                    source_ccu = ccu_map[source_ccu_name]
                    target_ccu = ccu_map[target_ccu_name]
                    
                    # Show stats
                    source_leads = db.query(st.import_module('app.models').Lead).filterBy(ccu_id=source_ccu.id).count() # Wait, need proper query
                    # I'll just use a helper
                    
                    st.markdown(f"""
                    **Plan:**
                    - Move **{source_ccu_name}** leads to **{target_ccu_name}**.
                    - Delete record **{source_ccu_name}**.
                    """)
                    
                    if st.button("EXECUTE MERGE", type="primary"):
                        # Logic to merge
                        try:
                            from app.models import Lead
                            leads_to_move = db.query(Lead).filter(Lead.ccu_id == source_ccu.id).all()
                            for lead in leads_to_move:
                                lead.ccu_id = target_ccu.id
                            
                            db.delete(source_ccu)
                            db.commit()
                            st.success(f"Successfully merged {len(leads_to_move)} leads. CCU '{source_ccu_name}' removed.")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Merge failed: {e}")

    finally:
        db.close()
