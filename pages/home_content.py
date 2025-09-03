import streamlit as st
from datetime import datetime

# ---------------------------
# Session helpers
# ---------------------------
if "show_whats_new" not in st.session_state:
    st.session_state.show_whats_new = True

LAST_KB_REFRESH = "September 3, 2025"

# ---------------------------
# Header
# ---------------------------
st.title("🎯 VeritasLogic.ai Technical Accounting Solutions")
st.subheader("Generate **strong first-draft memos** using AI, based on authoritative guidance.")

# ---------------------------
# What's new (dismissible banner)
# ---------------------------
if st.session_state.show_whats_new:
    st.success("🆕 **What's new** • ASC 805 tool launched • KB refresh: " + LAST_KB_REFRESH + " • Faster GPT-5-mini fallback")
    if st.button("✖ Dismiss", key="dismiss_whats_new", type="secondary"):
        st.session_state.show_whats_new = False
        st.rerun()

st.divider()

# ---------------------------
# Start an analysis
# ---------------------------
st.markdown("### 🚀 Start an Analysis")
st.caption("Pick a standard to begin. You'll upload your documents on the next screen.")

# Grid of standard cards with fixed heights and consistent styling
row1 = st.columns(3, gap="medium")
row2 = st.columns([1, 1, 1], gap="medium")  # Equal spacing for bottom row

# ASC 606
with row1[0]:
    with st.container(border=True, height=180):
        st.markdown("#### 💰 ASC 606")
        st.markdown("**Revenue from Contracts**")
        st.write("First-draft revenue memo with paragraph citations.")
        st.page_link("asc606/asc606_page.py", label="🚀 Start ASC 606 Analysis", icon="💰", use_container_width=True)

# ASC 340-40
with row1[1]:
    with st.container(border=True, height=180):
        st.markdown("#### 📄 ASC 340-40")
        st.markdown("**Contract Costs**")
        st.write("Policy memo on cost capitalization and amortization.")
        st.page_link("asc340/asc340_page.py", label="🚀 Start ASC 340-40 Analysis", icon="📄", use_container_width=True)

# ASC 842
with row1[2]:
    with st.container(border=True, height=180):
        st.markdown("#### 🏢 ASC 842")
        st.markdown("**Leases (Lessee)**")
        st.write("Lease classification and lessee accounting memo.")
        st.page_link("asc842/asc842_page.py", label="🚀 Start ASC 842 Analysis", icon="🏢", use_container_width=True)

# Center the bottom row
col_spacer, row2_col1, row2_col2, col_spacer2 = st.columns([0.5, 1, 1, 0.5])

# ASC 718
with row2_col1:
    with st.container(border=True, height=180):
        st.markdown("#### 📈 ASC 718")
        st.markdown("**Stock Compensation**")
        st.write("Equity awards analysis and compensation memo.")
        st.page_link("asc718/asc718_page.py", label="🚀 Start ASC 718 Analysis", icon="📈", use_container_width=True)

# ASC 805
with row2_col2:
    with st.container(border=True, height=180):
        st.markdown("#### 🤝 ASC 805")
        st.markdown("**Business Combinations**")
        st.write("Transaction assessment and M&A accounting memo.")
        st.page_link("asc805/asc805_page.py", label="🚀 Start ASC 805 Analysis", icon="🤝", use_container_width=True)

st.divider()

# ---------------------------
# Reminders (trust panel)
# ---------------------------
st.markdown("### ⚠️ Key Reminders")
st.info("""
🔗 **Hybrid RAG**: Contract text + FASB Codification ([FAQ](pages/faq.py) for details)  
📝 **First-draft only**: Always review for completeness and accuracy  
🎯 **Scope**: Each standard page explains coverage and limitations  
🔒 **Privacy**: Files stay in your session. OpenAI API content not used for training
""")

st.divider()

# ---------------------------
# How it works (with visual flow)
# ---------------------------
st.markdown("### 🛠️ How It Works")

c1, arrow1, c2, arrow2, c3 = st.columns([1, 0.1, 1, 0.1, 1])

with c1:
    with st.container(border=True, height=140):
        st.markdown("#### 1️⃣ Select Standard")
        st.write("Choose the relevant ASC module for your analysis.")

with arrow1:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ➡️")

with c2:
    with st.container(border=True, height=140):
        st.markdown("#### 2️⃣ Upload Documents")
        st.write("Multiple PDFs supported; we combine them for analysis.")

with arrow2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ➡️")

with c3:
    with st.container(border=True, height=140):
        st.markdown("#### 3️⃣ Generate Memo")
        st.write("Create first-draft memo with paragraph-level citations.")

st.divider()

# ---------------------------
# Platform snapshot (improved metrics)
# ---------------------------
st.markdown("### 📊 Platform Snapshot")

# Use 2x2 grid for better text visibility
metric_row1 = st.columns(2, gap="large")
metric_row2 = st.columns(2, gap="large")

with metric_row1[0]:
    st.metric(
        label="📋 Standards Available",
        value="5",
        help="ASC 606, 340-40, 842, 718, 805"
    )

with metric_row1[1]:
    st.metric(
        label="🔄 Last KB Refresh",
        value=LAST_KB_REFRESH,
        help="Knowledge base last updated"
    )

with metric_row2[0]:
    st.metric(
        label="⚡ Analysis Speed",
        value="~30-60s",
        delta="per 10 pages",
        help="Average processing time"
    )

with metric_row2[1]:
    st.metric(
        label="🎯 Citation Level",
        value="ASC ¶ IDs",
        help="Paragraph-level FASB citations"
    )

st.divider()

# ---------------------------
# Footer with help links
# ---------------------------
st.markdown("### 💡 Help & Resources")
help_cols = st.columns(4)

with help_cols[0]:
    st.page_link("pages/faq.py", label="❓ FAQ", use_container_width=True)

with help_cols[1]:
    st.page_link("pages/gethelp.py", label="🆘 Get Help", use_container_width=True)

with help_cols[2]:
    st.markdown("[📚 Scope Guide](#)", help="What's covered per standard")

with help_cols[3]:
    st.page_link("pages/research_assistant.py", label="🔍 Research Assistant", use_container_width=True)

st.divider()
st.caption("© 2025 Controller.cpa. All Rights Reserved.")