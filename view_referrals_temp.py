def view_referrals():
    """View and manage referrals only"""
    st.markdown('<div class="main-header">🎯 Referrals</div>', unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Initialize status filter in session state
    if 'referral_status_filter' not in st.session_state:
        st.session_state.referral_status_filter = "All"
    
    # Initialize my referrals filter
    if 'show_only_my_referrals' not in st.session_state:
        st.session_state.show_only_my_referrals = True  # Default to showing only user's referrals
    
    # Toggle buttons for regular users to switch between My Referrals and All Referrals
    if st.session_state.user_role != "admin":
        st.subheader("View Mode")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "📋 My Referrals",
                use_container_width=True,
                type="primary" if st.session_state.show_only_my_referrals else "secondary"
            ):
                st.session_state.show_only_my_referrals = True
                st.rerun()
        
        with col2:
            if st.button(
                "🌐 All Referrals",
                use_container_width=True,
                type="primary" if not st.session_state.show_only_my_referrals else "secondary"
            ):
                st.session_state.show_only_my_referrals = False
                st.rerun()
        
        st.divider()
    
    # Contact Status Filter Buttons
    st.subheader("Filter by Contact Status")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📞 Intro Call", use_container_width=True, 
                    type="primary" if st.session_state.referral_status_filter == "Intro Call" else "secondary"):
            st.session_state.referral_status_filter = "Intro Call"
            st.rerun()
    
    with col2:
        if st.button("🔄 Follow Up", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "Follow Up" else "secondary"):
            st.session_state.referral_status_filter = "Follow Up"
            st.rerun()
    
    with col3:
        if st.button("❌ No Response", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "No Response" else "secondary"):
            st.session_state.referral_status_filter = "No Response"
            st.rerun()
    
    with col4:
        if st.button("⏳ Intake Call", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "Intake Call" else "secondary"):
            st.session_state.referral_status_filter = "Intake Call"
            st.rerun()
    
    with col5:
        if st.button("📋 All", use_container_width=True,
                    type="primary" if st.session_state.referral_status_filter == "All" else "secondary"):
            st.session_state.referral_status_filter = "All"
            st.rerun()
    
    st.divider()
    
    # Search and filter
    col1, col2, col3 = st.columns(3)
    with col1:
        search_name = st.text_input("🔍 Search by name")
    with col2:
        filter_staff = st.text_input("👤 Filter by staff")
    with col3:
        filter_source = st.text_input("📍 Filter by source")
    
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
    
    # Show count with filter info
    filter_info = f"Status: {st.session_state.referral_status_filter}"
    if st.session_state.user_role != "admin" and st.session_state.show_only_my_referrals:
        filter_info += f" | Showing: My Referrals Only"
    st.write(f"**Showing {len(leads)} referrals** ({filter_info})")
    
    # Display referrals
    if leads:
        for lead in leads:
            with st.expander(f"🎯 {lead.first_name} {lead.last_name} - {lead.staff_name}"):
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
                    st.success("**Referral:** ✅ Yes")
                    st.write(f"**Created:** {lead.created_at.strftime('%Y-%m-%d')}")
                    st.write(f"**Updated:** {lead.updated_at.strftime('%Y-%m-%d')}")
                    if lead.comments:
                        st.write(f"**Comments:** {lead.comments}")
                
                # Permission check for edit/delete
                can_modify = (st.session_state.user_role == "admin" or 
                             lead.staff_name == st.session_state.username)
                
                if not can_modify:
                    st.warning("⚠️ You can only edit/delete your own referrals")
                
                col1, col2, col3, col4 = st.columns([1, 1, 1.5, 2])
                with col1:
                    if can_modify and st.button("✏️ Edit", key=f"edit_ref_{lead.id}"):
                        st.session_state[f'editing_{lead.id}'] = True
                        st.rerun()
                with col2:
                    if can_modify and st.button("🗑️ Delete", key=f"delete_ref_{lead.id}"):
                        crud_leads.delete_lead(db, lead.id)
                        st.success("✅ Referral deleted")
                        st.rerun()
                with col3:
                    # Unmark Referral button (always shows unmark since we're in referrals view)
                    if can_modify:
                        if st.button("✅ Unmark Referral", key=f"unmark_ref_{lead.id}", type="primary"):
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
                            crud_leads.update_lead(db, lead.id, update_data)
                            st.success(f"✅ Lead unmarked as Referral!")
                            st.rerun()

                
                # Edit form (shown when Edit button is clicked)
                if st.session_state.get(f'editing_{lead.id}', False):
                    st.divider()
                    st.subheader("✏️ Edit Referral")
                    
                    with st.form(f"edit_ref_form_{lead.id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_staff_name = st.text_input("Staff Name *", value=lead.staff_name)
                            edit_first_name = st.text_input("First Name *", value=lead.first_name)
                            edit_last_name = st.text_input("Last Name *", value=lead.last_name)
                            edit_source = st.selectbox("Source *", 
                                                      ["HHN", "Web", "Referral", "Event", "Other"],
                                                      index=["HHN", "Web", "Referral", "Event", "Other"].index(lead.source) if lead.source in ["HHN", "Web", "Referral", "Event", "Other"] else 0)
                            edit_phone = st.text_input("Phone *", value=lead.phone)
                            edit_city = st.text_input("City", value=lead.city or "")
                            edit_zip_code = st.text_input("Zip Code", value=lead.zip_code or "")
                        
                        
                        with col2:
                            edit_status = st.selectbox("Contact Status", 
                                                      ["Intro Call", "Follow Up", "No Response", "Intake Call"],
                                                      index=["Intro Call", "Follow Up", "No Response", "Intake Call"].index(lead.last_contact_status) if lead.last_contact_status in ["Intro Call", "Follow Up", "No Response", "Intake Call"] else 0)
                            edit_dob = st.date_input("Date of Birth", value=lead.dob)
                            edit_medicaid_no = st.text_input("Medicaid Number", value=lead.medicaid_no or "")
                            edit_e_contact_name = st.text_input("Emergency Contact Name", value=lead.e_contact_name or "")
                            edit_e_contact_phone = st.text_input("Emergency Contact Phone", value=lead.e_contact_phone or "")
                            edit_comments = st.text_area("Comments", value=lead.comments or "")
                        
                        st.divider()
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            save = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
                        with col2:
                            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)
                        
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
                                e_contact_phone=edit_e_contact_phone or None,
                                comments=edit_comments or None
                            )
                            crud_leads.update_lead(db, lead.id, update_data)
                            st.session_state[f'editing_{lead.id}'] = False
                            st.success("✅ Referral updated successfully!")
                            st.rerun()
                        
                        if cancel:
                            st.session_state[f'editing_{lead.id}'] = False
                            st.rerun()
    else:
        st.info("No referrals found")
    
    db.close()

