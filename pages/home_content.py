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
st.title("VeritasLogic.ai Technical Accounting Solutions")
st.subheader("Generate strong first-draft memos using AI, based on authoritative guidance.")

# ---------------------------
# What's new (dismissible)
# ---------------------------
if st.session_state.show_whats_new:
    with st.container(border=True):
        c1, c2 = st.columns([0.9, 0.1])
        with c1:
            st.markdown("#### What's new")
            st.markdown(
                "- ASC 805 tool added to the home page cards.\n"
                f"- Last KB refresh: {LAST_KB_REFRESH}.\n"
                "- Faster runs with improved GPT‑5‑mini fallback."
            )
        with c2:
            st.button("Dismiss", key="dismiss_whats_new", 
                     on_click=lambda: st.session_state.update(show_whats_new=False))

st.divider()

# ---------------------------
# Start an analysis
# ---------------------------
st.subheader("Start an analysis")
st.caption("Pick a standard to begin. You'll upload your documents on the next screen.")

# Grid of standard cards (keep above the fold)
row1 = st.columns(3)
row2 = st.columns(2)

# ASC 606
with row1[0]:
    with st.container(border=True):
        st.markdown("##### ASC 606 — Revenue from Contracts with Customers")
        st.write("Generate a first-draft revenue memo with paragraph-level citations.")
        st.page_link("asc606/asc606_page.py", label="Start ASC 606 Analysis", icon="➡️")

# ASC 340-40
with row1[1]:
    with st.container(border=True):
        st.markdown("##### ASC 340-40 — Costs to Obtain or Fulfill a Contract")
        st.write("Draft a policy memo on capitalization and amortization of contract costs.")
        st.page_link("asc340/asc340_page.py", label="Start ASC 340-40 Analysis", icon="➡️")

# ASC 842
with row1[2]:
    with st.container(border=True):
        st.markdown("##### ASC 842 — Leases (Lessee)")
        st.write("Classify leases and generate a lessee accounting memo with citations.")
        st.page_link("asc842/asc842_page.py", label="Start ASC 842 Analysis", icon="➡️")

# ASC 718
with row2[0]:
    with st.container(border=True):
        st.markdown("##### ASC 718 — Compensation—Stock Compensation")
        st.write("Analyze equity awards and produce a stock compensation memo.")
        st.page_link("asc718/asc718_page.py", label="Start ASC 718 Analysis", icon="➡️")

# ASC 805
with row2[1]:
    with st.container(border=True):
        st.markdown("##### ASC 805 — Business Combinations")
        st.write("Assess a transaction and draft a business combinations memo.")
        st.page_link("asc805/asc805_page.py", label="Start ASC 805 Analysis", icon="➡️")

st.divider()

# ---------------------------
# Reminders (trust panel)
# ---------------------------
st.subheader("Reminders")
with st.container(border=True):
    st.markdown(
        "- **Hybrid RAG**: Uses your contract text plus the FASB Codification. See the FAQ for details.\n"
        "- **First-draft only**: Always review for completeness and accuracy before use.\n"
        "- **Scope**: Each standard page explains what's covered and what's out-of-scope.\n"
        "- **Privacy**: Your files remain in your Streamlit session. We don't store them in a database. "
        "Content sent to OpenAI via API is not used to train OpenAI models. See FAQ."
    )

st.divider()

# ---------------------------
# How it works
# ---------------------------
st.subheader("How it works")
c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown("###### 1) Select a standard")
        st.write("Choose the relevant ASC module.")
with c2:
    with st.container(border=True):
        st.markdown("###### 2) Upload your document(s)")
        st.write("Multiple PDFs are supported; we combine them for analysis.")
with c3:
    with st.container(border=True):
        st.markdown("###### 3) Analyze & generate")
        st.write("Create a first-draft memo with paragraph-level citations.")

st.divider()

# ---------------------------
# Platform snapshot (metrics — show once)
# ---------------------------
st.subheader("Platform snapshot")
mcols = st.columns(4)
mcols[0].metric("Standards available", "5")
mcols[1].metric("Last KB refresh", LAST_KB_REFRESH)
mcols[2].metric("Avg analysis time", "~30–60s per 10 pages")
mcols[3].metric("Citation level", "ASC paragraph IDs")

st.divider()
st.caption("© 2025 Controller.cpa. All Rights Reserved.")