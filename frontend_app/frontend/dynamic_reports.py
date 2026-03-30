"""
Dynamic Dimension Reports Page
==============================
Shows the Top 3 or Top 5 entities (CCU, Source, Status, Staff, MCO) 
by referral count with a leaderboard and full data download (Excel or Word).
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import streamlit as st
import requests
import os
from datetime import datetime
from app.db import SessionLocal


def dynamic_reports():
    """Dynamic Reports page — Top N leaderboard for any dimension"""

    st.markdown('<div class="main-header">📊 Dynamic Dimension Reports</div>', unsafe_allow_html=True)

    st.markdown("""
    Analyze your lead data by different dimensions. Pick a category (like CCU, Source, or Staff) 
     to see the Top 3 or 5 performers and download a complete data breakdown.
    """)

    # ── Settings row ─────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 1, 2])

    with c1:
        st.markdown("**Report Category:**")
        dim_map = {
            "Community Care Unit (CCU)": "ccu",
            "Lead Source": "source",
            "Contact Status": "status",
            "Staff Member": "staff",
            "MCO / Provider": "mco",
            "Payor": "payor"
        }
        dim_choice_label = st.selectbox(
            "Category",
            options=list(dim_map.keys()),
            index=0,
            label_visibility="collapsed",
            key="dyn_report_dim"
        )
        dim_param = dim_map[dim_choice_label]

    with c2:
        st.markdown("**Show Top:**")
        n_choice = st.radio(
            "Show Top",
            options=[3, 5],
            index=1,          # default: 5
            horizontal=True,
            label_visibility="collapsed",
            key="dyn_report_n",
        )

    with c3:
        st.markdown("**Download Format:**")
        fmt_choice = st.radio(
            "Download Format",
            options=["Excel (.xlsx)", "Word (.docx)"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key="dyn_report_fmt",
        )
    fmt_param = "excel" if "Excel" in fmt_choice else "word"

    st.divider()

    # ── Live stats from DB ────────────────────────────────────────────────────
    db = SessionLocal()
    try:
        from app.services.generic_report import get_dimension_report_stats
        stats = get_dimension_report_stats(db, dimension=dim_param, limit=n_choice)
    except Exception as e:
        st.error(f"❌ Error loading report stats: {e}")
        db.close()
        return
    finally:
        db.close()

    leaderboard = stats.get("leaderboard", [])
    total = stats.get("total_referrals_in_top", 0)

    if not leaderboard:
        st.warning(f"⚠️ No referral data found for category: **{dim_choice_label}**.")
        return

    # ── Summary KPI row ───────────────────────────────────────────────────────
    st.markdown(f"### 🏆 Top {n_choice} {dim_choice_label} Leaderboard")
    kpi_cols = st.columns(min(len(leaderboard), 5))
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    for i, entry in enumerate(leaderboard):
        if i < len(kpi_cols):
            with kpi_cols[i]:
                st.metric(
                    label=f"{medals[i]} {entry['name']}",
                    value=f"{entry['referral_count']} leads",
                    delta=f"{entry['percentage']}% of top {n_choice}",
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Detailed leaderboard table ────────────────────────────────────────────
    import pandas as pd

    table_data = []
    for e in leaderboard:
        row = {
            "Rank": f"#{e['rank']}",
            "Name": e["name"],
            "Referrals": e["referral_count"],
            "Share %": f"{e['percentage']}%",
        }
        # Add extra details if available (for CCU/Payor)
        details = e.get("details", {})
        if "Phone" in details: row["Phone"] = details["Phone"]
        if "Email" in details: row["Email"] = details["Email"]
        if "Coordinator" in details: row["Coordinator"] = details["Coordinator"]
        
        table_data.append(row)

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Download section ──────────────────────────────────────────────────────
    st.markdown("### 📥 Generate Full Data Report")

    ext = "xlsx" if fmt_param == "excel" else "docx"
    st.info(f"""
    **What's included in the report:**  
    - Grouped by: **{dim_choice_label}** (Top {n_choice})  
    - One section/sheet per {dim_choice_label}  
    - Every lead row including: Call Status, Auth Status, SOC Date, Priority, Staff, Payor, Comments...  
    - Format: **{fmt_choice}**
    """)

    if st.button(
        f"🔄 Generate Top {n_choice} {dim_choice_label} Report ({fmt_choice})",
        type="primary",
        use_container_width=True,
        key="dyn_report_generate_btn",
    ):
        with st.spinner("Generating report..."):
            try:
                backend_api_url = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
                api_url = f"{backend_api_url}/api/reports/top/export"

                response = requests.get(
                    api_url,
                    params={"dimension": dim_param, "limit": n_choice, "format": fmt_param},
                    timeout=120,
                )

                if response.status_code == 200:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"top_{n_choice}_{dim_param}_report_{timestamp}.{ext}"

                    mime = (
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        if fmt_param == "excel"
                        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                    st.success("✅ Report generated successfully!")
                    st.download_button(
                        label=f"⬇️ Download {fmt_choice} Report",
                        data=response.content,
                        file_name=filename,
                        mime=mime,
                        type="primary",
                        use_container_width=True,
                        key="dyn_report_download_btn",
                    )

                else:
                    st.error(f"❌ Error generating report: HTTP {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API server on port 8000.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    st.divider()

    # ── How to use expander ───────────────────────────────────────────────────
    with st.expander("ℹ️ Report Information"):
        st.markdown(f"""
        ### How to Use

        1. Choose a **Category** (e.g. CCU, Source, Staff).
        2. Pick **Top 3** or **Top 5**.
        3. Select **Excel** or **Word**.
        4. Click **Generate** and then **Download**.

        ### Data Highlights in Report

        The report includes all 20+ columns for every lead assigned to the top performers, including:
        - **Identity**: Full Name, DOB, Age
        - **Status**: Call Status, Authorization Status, Care Status
        - **Timeline**: Created At, SOC Date
        - **Tracking**: Staff Name, Source, Payor/MCO, CCU
        - **Notes**: Latest Comment from lead history
        """)


if __name__ == "__main__":
    dynamic_reports()
