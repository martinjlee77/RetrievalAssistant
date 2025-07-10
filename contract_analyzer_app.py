import streamlit as st
import time
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ValidationError

# --- CHANGE 4: Use Pydantic for robust data modeling ---
# This class defines the data structure for our contract inputs.
# It provides automatic validation and makes the code self-documenting.
class ContractData(BaseModel):
    analysis_title: str
    customer_name: str
    arrangement_description: str
    contract_start: date
    contract_end: date
    transaction_price: float
    currency: str
    analysis_depth: str
    output_format: str
    include_citations: bool
    include_examples: bool
    additional_notes: Optional[str] = ""
    uploaded_file_name: str

# --- Main Application Class ---
class ContractAnalyzerApp:
    # --- CHANGE 5: Centralize app configuration ---
    APP_CONFIG = {
        'version': "1.1.0",
        'last_updated': "July 2025",
    }
    AVAILABLE_STANDARDS = {
        'ASC 606': {
            'name': 'Revenue from Contracts with Customers',
            'description': 'Analyze revenue recognition under the 5-step model.',
            'status': 'available'
        },
        'ASC 842': {
            'name': 'Leases',
            'description': 'Analyze lease classification and measurement.',
            'status': 'coming_soon'
        },
        'ASC 815': {
            'name': 'Derivatives and Hedging',
            'description': 'Analyze derivative instruments and hedging activities.',
            'status': 'coming_soon'
        },
        'ASC 326': {
            'name': 'Credit Losses',
            'description': 'Analyze current expected credit losses.',
            'status': 'coming_soon'
        }
    }

    def __init__(self):
        # Configure page settings
        st.set_page_config(
            page_title="Technical Accounting Analyzer",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        # Initialize session state safely
        self.initialize_session_state()

    def initialize_session_state(self):
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = None
        if 'contract_data' not in st.session_state:
            st.session_state.contract_data = None
        if 'selected_standard' not in st.session_state:
            st.session_state.selected_standard = 'ASC 606'

    def run(self):
        self.render_sidebar()

        st.title(f"📊 {st.session_state.selected_standard} - Revenue Contract Analyzer")

        if st.session_state.analysis_results is None:
            self.render_upload_interface()
        else:
            self.render_analysis_results()

    def render_sidebar(self):
        with st.sidebar:
            st.header("📋 Accounting Standards")

            # Display currently selected standard
            current_standard = st.session_state.selected_standard
            current_info = self.AVAILABLE_STANDARDS[current_standard]
            st.success(f"✅ **{current_standard}**")
            st.write(f"*{current_info['description']}*")
            st.divider()

            # Selection for other standards
            st.subheader("Select Standard")
            for code, info in self.AVAILABLE_STANDARDS.items():
                if info['status'] == 'available':
                    if st.button(f"{code}: {info['name']}", key=f"select_{code}", disabled=(code == current_standard), use_container_width=True):
                        st.session_state.selected_standard = code
                        st.rerun()
                else:
                    # --- CHANGE 5: Cleaner display for "Coming Soon" ---
                    st.info(f"**{code}**\n\n*{info['name']}*\n\n(Coming Soon)", icon="⏳")

            st.divider()
            st.subheader("ℹ️ System Information")
            st.caption(f"Version: {self.APP_CONFIG['version']}\n\nLast Updated: {self.APP_CONFIG['last_updated']}")

    def render_upload_interface(self):
        # --- CHANGE 2: Use a form for all inputs ---
        # This prevents the app from re-running on every widget interaction.
        with st.form(key="contract_form"):

            # --- CHANGE 3: Organize inputs into clear tabs ---
            tab1, tab2, tab3 = st.tabs(["1. Contract Details", "2. Upload Document", "3. Analysis Options"])

            with tab1:
                st.subheader("Key Contract Information")
                col1, col2 = st.columns(2)
                analysis_title = col1.text_input(
                    "Analysis Title / Contract ID *", 
                    placeholder="e.g., Q4 Project Phoenix SOW",
                    help="A unique, user-friendly name for this specific analysis. This allows you and the system to easily track and reference this specific contract memo."
                )
                customer_name = col2.text_input(
                    "Customer Name *", 
                    placeholder="e.g., ABC Corporation",
                    help="The legal name of the customer. This is the most basic identifier for the counterparty and will be used throughout the memo."
                )

                col3, col4 = st.columns(2)
                contract_start = col3.date_input(
                    "Contract Start Date *",
                    help="The beginning of the period over which goods or services are expected to be delivered. This directly informs the revenue recognition period, especially for services recognized 'over time.'"
                )
                contract_end = col4.date_input(
                    "Contract End Date *",
                    help="The end of the period over which goods or services are expected to be delivered. This directly informs the revenue recognition period, especially for services recognized 'over time.'"
                )

                col5, col6 = st.columns(2)
                transaction_price = col5.number_input(
                    "Total Transaction Price *", 
                    min_value=0.0, 
                    format="%.2f",
                    help="The total fixed value of the contract. Leave as 0 if the price is entirely variable. This gives the LLM a key financial data point to anchor its analysis for Steps 3 (Determine Price) and 4 (Allocate Price)."
                )
                currency = col6.selectbox(
                    "Currency *", 
                    ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "Other"],
                    help="The currency of the contract. This is critical context for the transaction price and any financial figures mentioned in the memo."
                )

                arrangement_description = st.text_area(
                    "Brief Description of the Arrangement *",
                    placeholder="e.g., A three-year SaaS subscription with one-time implementation services.",
                    height=100,
                    help="A one- or two-sentence, plain-English summary of the deal. This is a powerful input that gives the LLM immediate, high-level context of the business purpose, helping it better interpret the legal language and structure of the contract."
                )

            with tab2:
                st.subheader("Contract Document")
                uploaded_file = st.file_uploader(
                    "Upload your contract in PDF or Word format *",
                    type=['pdf', 'docx', 'doc']
                )

            with tab3:
                st.subheader("Analysis Configuration")
                col7, col8 = st.columns(2)
                analysis_depth = col7.selectbox("Analysis Depth", ["Standard Analysis", "Detailed Analysis"])
                output_format = col8.selectbox("Output Format", ["Professional Memo", "Executive Summary"])

                col7.markdown("<br>", unsafe_allow_html=True) # Spacer
                include_citations = col7.checkbox("Include Citations", value=True)
                include_examples = col8.checkbox("Include Examples", value=False)

                additional_notes = st.text_area(
                    "Additional Instructions (Optional)",
                    placeholder="e.g., Focus specifically on variable consideration and the series guidance.",
                    height=100
                )

            # The submit button for the form
            submitted = st.form_submit_button("🔍 Analyze Contract", type="primary", use_container_width=True)

        if submitted:
            # --- CHANGE 4: Validate inputs using Pydantic model ---
            try:
                if not uploaded_file:
                    st.error("Please upload a contract document.")
                    return

                # Create an instance of our Pydantic model
                contract_data = ContractData(
                    analysis_title=analysis_title,
                    customer_name=customer_name,
                    contract_start=contract_start,
                    contract_end=contract_end,
                    transaction_price=transaction_price,
                    currency=currency,
                    arrangement_description=arrangement_description,
                    uploaded_file_name=uploaded_file.name,
                    analysis_depth=analysis_depth,
                    output_format=output_format,
                    include_citations=include_citations,
                    include_examples=include_examples,
                    additional_notes=additional_notes
                )
                # Store the validated data model in session state
                st.session_state.contract_data = contract_data
                self.process_contract(uploaded_file)

            except ValidationError as e:
                # Pydantic raises an error if fields are missing or types are wrong
                st.error("Please fill in all required fields marked with *")
                # For debugging, you can print the detailed error:
                # st.error(e)

            # --- CHANGE 1: BUG FIX ---
            # The original code had a NameError because `effective_date` wasn't defined.
            # This is now prevented by using the Pydantic model, which only includes defined fields.


    def process_contract(self, uploaded_file):
        with st.spinner("Analyzing contract... This may take a moment."):
            # In a real app, this is where you would:
            # 1. Read the file bytes: `file_content = uploaded_file.read()`
            # 2. Extract text from the PDF/DOCX
            # 3. Call your backend/LLM API with the text and contract_data
            time.sleep(3)  # Simulate processing time

            # Mock results
            st.session_state.analysis_results = {
                'processing_time': 3.2,
                'sections_analyzed': 5,
                'issues_identified': 3,
            }
        st.success("✅ Contract analysis completed!")
        st.rerun()

    def render_analysis_results(self):
        st.header("📊 Analysis Results")

        contract: ContractData = st.session_state.contract_data
        results = st.session_state.analysis_results

        # Display key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Analysis Type", st.session_state.selected_standard)
        col2.metric("Processing Time", f"{results['processing_time']:.1f}s")
        col3.metric("Key Issues Found", results['issues_identified'])

        # Display a summary of the inputs
        with st.expander("Show Original Contract Details", expanded=False):
            st.write(f"**Analysis Title:** {contract.analysis_title}")
            st.write(f"**Customer:** {contract.customer_name}")
            st.write(f"**Contract Period:** {contract.contract_start.strftime('%b %d, %Y')} to {contract.contract_end.strftime('%b %d, %Y')}")
            st.write(f"**Transaction Price:** {contract.currency} {contract.transaction_price:,.2f}")
            st.write(f"**File:** {contract.uploaded_file_name}")

        # Placeholder for the actual analysis output, now using tabs
        st.subheader("ASC 606 - 5 Step Analysis")
        step1, step2, step3, step4, step5 = st.tabs([
            "Step 1: Contract", 
            "Step 2: Perf. Obligations", 
            "Step 3: Price", 
            "Step 4: Allocate", 
            "Step 5: Recognize"
        ])
        with step1:
            st.info("Analysis of Step 1 (Identify the Contract) will appear here.")
        with step2:
            st.info("Analysis of Step 2 (Identify Performance Obligations) will appear here.")
        with step3:
            st.info("Analysis of Step 3 (Determine Transaction Price) will appear here.")
        with step4:
            st.info("Analysis of Step 4 (Allocate Transaction Price) will appear here.")
        with step5:
            st.info("Analysis of Step 5 (Recognize Revenue) will appear here.")

        st.divider()
        if st.button("🔄 Analyze Another Contract", use_container_width=True):
            st.session_state.analysis_results = None
            st.session_state.contract_data = None
            st.rerun()


if __name__ == "__main__":
    app = ContractAnalyzerApp()
    app.run()