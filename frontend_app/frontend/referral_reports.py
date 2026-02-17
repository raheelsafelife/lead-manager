"""
Referral Reports Page

Generate a comprehensive **Professional Word Report** of all referrals from the AWS database.
    
    ### Report Features:
    
    The report is designed for **maximum readability**:
    
    1. **Landscape Orientation** - Optimized for wide data visibility
    2. **Grouped Information** - Columns like Contact Info, Address, and CCU details are intelligently grouped to save space
    3. **Three Sections** - Sent, Confirmed, and Rejected referrals in color-coded sections
    4. **All 40 Data Points Included** - All CCU and client details are preserved
"""

import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import streamlit as st
import requests
from datetime import datetime
from app.db import SessionLocal


def referral_reports():
    """Referral Reports page - Generate and download comprehensive referral reports"""
    
    st.markdown('<div class="main-header">📊 Referral Reports</div>', unsafe_allow_html=True)
    
    st.markdown("""
    Generate a comprehensive **Professional Word Report** of all referrals from the AWS database.
    
    ### Report Contents:
    
    1. **Summary** - Detailed overview with statistics
    2. **Referrals Sent** - Blue themed section
    3. **Referrals Confirmed** - Green themed section
    4. **Referrals Rejected** - Red themed section
    
    ### Data Included (40 Columns):
    
    - **Client Information**: Name, Phone, Email, DOB, Age, SSN, Medicaid Number
    - **Address**: Street, City, State, Zip Code
    - **Emergency Contact**: Name, Relation, Phone
    - **Referral Details**: Staff Name, Source, Type, Status, Priority
    - **Authorization**: Authorization Status, Care Status, SOC Date
    - **Payor Information**: Name, Address, Phone, Fax, Email
    - **CCU Details**: Name, Street, City, State, Zip, Phone, Fax, Email, Coordinator
    - **Metadata**: Created At, Created By, Latest Comment
    
    ---
    """)
    
    # Get statistics from database
    db = SessionLocal()
    
    try:
        from app.services.referral_report import get_report_statistics
        
        stats = get_report_statistics(db)
        
        # Display statistics in columns
        st.markdown("### 📈 Current Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Referrals Sent", stats['sent'], help="Referrals sent but not yet authorized")
        
        with col2:
            st.metric("Referrals Confirmed", stats['confirmed'], help="Referrals with authorization received")
        
        with col3:
            st.metric("Referrals Rejected", stats['rejected'], help="Referrals marked as Not Approved")
        
        with col4:
            st.metric("Total Records", stats['total'], help="Total referrals in report")
        
        st.divider()
        
        # Generate Report Section
        st.markdown("### 📥 Generate Report")
        
        st.info("""
        **Note:** The report includes all historical referral data. Deleted referrals are excluded.
        The **Word Document (.docx)** is formatted in **Landscape mode** with **grouped columns** for high readability.
        Open with Microsoft Word, Google Docs, or any Word processor.
        """)
        
        # Generate button
        if st.button("🔄 Generate Referral Report", type="primary", use_container_width=True):
            with st.spinner("Generating report from AWS database..."):
                try:
                    # Call the backend API endpoint
                    # Use localhost for local development, update for production
                    api_url = "http://localhost:8000/api/reports/referrals/export"
                    
                    response = requests.get(api_url, timeout=60)
                    
                    if response.status_code == 200:
                        # Get filename from headers or create one
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"referral_report_{timestamp}.docx"
                        
                        # Provide download button
                        st.success("✅ Report generated successfully!")
                        
                        st.download_button(
                            label="⬇️ Download Professional Word Report",
                            data=response.content,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary",
                            use_container_width=True
                        )
                        
                        st.markdown(f"""
                        **Report Details:**
                        - Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        - Total records: {stats['total']}
                        - Filename: `{filename}`
                        """)
                        
                    else:
                        st.error(f"❌ Error generating report: {response.status_code}")
                        st.error(response.text)
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to API server. Please ensure the backend server is running on port 8000.")
                    st.info("Run the backend with: `python backend/api_server.py`")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        st.divider()
        
        # Additional Information
        with st.expander("ℹ️ Report Information"):
            st.markdown("""
            ### How to Use the Report
            
            1. Click "Generate Referral Report" to create the Word document
            2. Download the file to your computer
            3. Open with Microsoft Word, Google Docs, or any Word processor
            
            ### Report Structure
            
            The Word document contains:
            
            - **Landscape Layout**: Ensures all columns fit and are readable
            - **Merged Columns**: Logical grouping of First/Last Name, Addresses, and CCU Contacts
            - **Color-Coded Headers**: Blue (Sent), Green (Confirmed), Red (Rejected)
            - **Summary Table**: Statistics included at the end of the document
            
            The document has:
            - Color-coded headers (Blue for Sent, Green for Confirmed, Red for Rejected)
            - Optimized column widths for readability
            - Frozen header row for easy scrolling
            - Professional formatting
            
            Each section includes a summary count at the end.
            
            ### Data Source
            
            All data is extracted directly from the AWS database in real-time.
            The report reflects the current state of all referrals at the time of generation.
            
            ### Privacy & Security
            
            - Reports contain sensitive client information (SSN, Medicaid numbers)
            - Handle downloaded files securely
            - Do not share reports via unsecured channels
            - Delete old reports when no longer needed
            """)
    
    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")
    
    finally:
        db.close()


if __name__ == "__main__":
    # For testing
    referral_reports()
