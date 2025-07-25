"""
ASC 606 Revenue Recognition Analysis Page
"""
import streamlit as st
import time
from datetime import date
from typing import Optional, List
from pydantic import ValidationError

# Import core components
try:
    from core.models import ContractData, ASC606Analysis
    from utils.asc606_analyzer import ASC606Analyzer
    from utils.document_extractor import DocumentExtractor
    from utils.llm import create_debug_sidebar
except ImportError:
    # Handle missing imports gracefully
    st.error("Core components not found. Please ensure all required modules are available.")
    st.stop()

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'contract_data' not in st.session_state:
    st.session_state.contract_data = None
if 'selected_standard' not in st.session_state:
    st.session_state.selected_standard = 'ASC 606'

# Initialize analyzer and extractor
@st.cache_resource
def get_cached_analyzer():
    return ASC606Analyzer()

analyzer = get_cached_analyzer()
extractor = DocumentExtractor()

# Standard header
st.title("ASC 606: Revenue Contract Analysis")
st.write(
    "**Powered by Authoritative FASB Codification & Industry Interpretive Guidance.**\n\n"
    "An intelligent platform to generate comprehensive ASC 606 memos. Follow the numbered tabs to input contract details, provide context, and configure your analysis."
)

debug_config = create_debug_sidebar()

# Main application logic
if st.session_state.analysis_results is None:

    tab1, tab2, tab3 = st.tabs([
        "**① Contract & Documents**",
        "**② Key Considerations**",
        "**③ Configure & Run**"
    ])

    with tab1:
        col1, col2 = st.columns(2, gap="small")
        with col1:
            analysis_title = st.text_input(
                "Analysis Title *",
                placeholder="e.g., Q4 Project Phoenix SOW",
                help="A unique name to identify this analysis")
        with col2:
            customer_name = st.text_input("Customer Name *",
                                          placeholder="e.g., ABC Corporation",
                                          help="The legal entity name of the customer as it appears on the contract.")
        col3, col4 = st.columns(2, gap="small")
        with col3:
            contract_types = st.multiselect(
                "Contract Document Types Included *", [
                    "Master Agreement", "Master Services Agreement (MSA)", "Statement of Work (SOW)",
                    "Software as a Service (SaaS) Agreement", "Software License Agreement",
                    "Professional Services Agreement", "Sales Order / Order Form", "Purchase Order (PO)",
                    "Contract Amendment / Addendum", "Change Order", "Reseller / Partner Agreement", "Invoice", "Other"
                ],
                help="Select all document types that are part of this analysis."
            )
        with col4:
            currency = st.selectbox("Currency *", ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "Other"],
                                     help="Primary currency for the contract")
        col5, col6 = st.columns(2, gap="small")
        with col5:
            contract_start = st.date_input("Contract Start Date *",
                                           help="The effective start date of the contractual period being analyzed.")
        with col6:
            contract_end = st.date_input("Contract End Date *",
                                         help="The effective end date of the contractual period being analyzed.")
        arrangement_description = st.text_area(
            "Overall Arrangement Summary (Optional)",
            placeholder='e.g., "New 3-year SaaS license with one-time setup fee."',
            height=100,
            help="Provide a one-sentence summary of the deal. This gives the AI crucial high-level context before it analyzes the details."
        )
        st.subheader("📄 Document Upload")
        uploaded_files = st.file_uploader(
            "Upload All Related Contract Documents *", type=['pdf', 'docx', 'txt'], accept_multiple_files=True,
            help="Crucial: Upload the complete set of related documents for this arrangement."
        )
        st.markdown("---")
        with st.container(border=True):
            st.info(
                "Once the fields above are complete, continue to the **② Key Considerations** tab.",
                icon="➡️")

    # Tab 2: Analysis Questions (New Compact Design with Expanders)
    with tab2:
        st.write("Your answers address key areas of judgment and provide crucial context for the AI.")

        # Initialize all optional detail variables to None to prevent errors
        original_contract_uploaded = None
        principal_agent_details = None
        variable_consideration_details = None
        financing_component_details = None
        noncash_consideration_details = None
        consideration_payable_details = None

        with st.expander("**Step 1: Identify the Contract (required)**", expanded=True):
            col1, col2 = st.columns(2, gap="medium")
            with col1:
                collectibility = st.toggle("Collectibility is probable *", value=True, help="A contract does not exist under ASC 606 if collection is not probable.")
                is_modification = st.toggle("This is a contract modification *", value=False,
                                            help="Select if this is an amendment, addendum, or change order that modifies an existing contract.")
            with col2:
                is_combined_contract = st.toggle("Evaluate docs as one contract? *", value=True,
                                                 help="Per ASC 606-10-25-9, contracts entered into at or near the same time with the same customer should be combined if certain criteria are met. Select if these documents should be treated as a single accounting contract.")
                original_contract_uploaded = st.toggle("Is the original contract uploaded? *", value=False, disabled=not is_modification)

        with st.expander("**Step 2: Identify Performance Obligations (optional)**"):
            st.info("The AI will analyze the contract(s) to identify distinct goods or services.", icon="🤖")
            principal_agent_involved = st.toggle("Is a third party involved in providing goods or services?",
                                                  help="Select if another party is involved in providing the goods or services to your end customer (e.g., you are reselling another company's product).")
            if principal_agent_involved:
                principal_agent_details = st.text_area("Describe the arrangement and specify who controls the good/service:", placeholder="e.g., We are an agent for Party X's software...", label_visibility="collapsed")

        with st.expander("**Step 3: Determine the Transaction Price (optional)**"):
            col3, col4 = st.columns(2, gap="medium")
            with col3:
                variable_consideration_involved = st.toggle("Includes variable consideration?")
                noncash_consideration_involved = st.toggle("Includes noncash consideration?")
            with col4:
                financing_component_involved = st.toggle("Includes significant financing?")
                consideration_payable_involved = st.toggle("Includes consideration payable?")

            if variable_consideration_involved:
                variable_consideration_details = st.text_area("Details on variable consideration:", placeholder="e.g., A $10,000 bonus is 90% probable.", label_visibility="collapsed")
            if financing_component_involved:
                financing_component_details = st.text_area("Details on financing component:", placeholder="e.g., Customer pays upfront for a 3-year service.", label_visibility="collapsed")
            if noncash_consideration_involved:
                noncash_consideration_details = st.text_area("Details on noncash consideration:", placeholder="e.g., Customer provides equipment valued at $50K.", label_visibility="collapsed")
            if consideration_payable_involved:
                consideration_payable_details = st.text_area("Details on consideration payable:", placeholder="e.g., Customer receives a $5,000 credit for marketing.", label_visibility="collapsed")

        with st.expander("**Step 4: Allocate the Transaction Price**"):
            ssp_represents_contract_price = st.toggle("Do contract prices represent Standalone Selling Price (SSP)?", value=True, help="SSP is the price at which you would sell a good or service separately.")

        with st.expander("**Step 5: Recognize Revenue**"):
            revenue_recognition_timing_details = st.text_area("Describe when control transfers for each major performance obligation:", placeholder="e.g., Software license delivered upfront; support services provided evenly over 12 months.")

        st.markdown("---")
        st.info("Continue to the **③ Configure & Run** tab.", icon="➡️")

    # Tab 3: Analysis Configuration and Execution
    with tab3:
        # Define the detailed help text as a constant for clarity
        AUDIENCE_HELP_TEXT = """
        Select the primary audience for the final memo. This adjusts the tone, focus, and level of technical detail. The underlying five-step analysis remains comprehensive for all options.

        • **Technical Accounting Team / Audit File (Default):**
          - **Focus:** Deep technical compliance and audit readiness.
          - **Content:** Assumes expert knowledge. Includes detailed step-by-step reasoning, direct quotations from ASC 606, and precise citations (e.g., ASC 606-10-55-34). This is the most detailed and formal output, suitable for internal accounting records and external auditors.

        • **Management Review:**
          - **Focus:** Key judgments, financial impact, and business implications.
          - **Content:** Summarizes critical conclusions upfront. Uses less technical jargon and focuses on the "so what" for decision-makers like the CFO or Controller. It answers questions like, "How does this contract affect our revenue forecast?"

        • **Deal Desk / Sales Team:**
          - **Focus:** Explaining the revenue recognition impact of specific contract terms.
          - **Content:** Translates complex accounting rules into practical guidance for teams structuring deals. It helps them understand how different clauses (e.g., acceptance terms, payment timing) can accelerate or defer revenue, enabling them to negotiate more effectively.
        """

        st.subheader("⚙️ Configure & Run Analysis")
        st.write(
            "Finalize your analysis by providing optional focus areas and audience preferences before generating the memo."
        )

        # Key Focus Areas - The most important steering input
        key_focus_areas = st.text_area(
            "Key Focus Areas / Specific Questions (Optional)",
            placeholder=(
                "Example: 'The main uncertainty is whether the implementation services are distinct from the "
                "SaaS license. Please analyze this thoroughly, referencing the criteria in ASC 606-10-25-21.'"
            ),
            height=100,
            help="Direct the AI to analyze specific clauses, risks, or uncertainties you have identified. This is the most effective way to improve the analysis."
        )

        col7, col8 = st.columns(2, gap="small")
        with col7:
            memo_audience = st.selectbox(
                "Tailor Memo for Audience (Optional)",
                ["Technical Accounting Team / Audit File", "Management Review", "Deal Desk / Sales Team"],
                index=0,  # Default to the most comprehensive option
                help=AUDIENCE_HELP_TEXT
            )
            
        with col8:
            # Materiality Threshold for financial significance
            materiality_threshold = st.number_input(
                "Materiality Threshold (Optional)",
                min_value=0,
                value=1000,
                step=1000,
                help="The AI will use this to assess the financial significance of contract elements like bonuses, penalties, or discounts, and focus its commentary accordingly."
            )

        def validate_form():
            """Validate required fields from Tab 1"""
            errors = []
            if not analysis_title: errors.append("Analysis Title is required (Tab 1).")
            if not customer_name: errors.append("Customer Name is required (Tab 1).")
            # arrangement_description is now optional
            if not contract_types: errors.append("At least one Document Type must be selected (Tab 1).")
            if not uploaded_files: errors.append("At least one document must be uploaded (Tab 1).")
            return errors

        st.markdown("---")
        if st.button("🔍 Analyze Contract", use_container_width=True, type="primary"):
            validation_errors = validate_form()
            if validation_errors:
                st.error("Please fix the following issues before submitting:")
                [st.warning(f"• {e}") for e in validation_errors]
                st.stop()

            with st.status("🔍 Analyzing contract...", expanded=True) as status:
                try:
                    # Text extraction logic
                    st.write("📄 Extracting text from documents...")
                    all_extracted_text = [extractor.extract_text(f)['text'] for f in uploaded_files if extractor.extract_text(f).get('text')]
                    if not all_extracted_text: 
                        st.error("No text could be extracted.")
                        st.stop()
                    combined_text = "\n\n--- END OF DOCUMENT ---\n\n".join(all_extracted_text)

                    st.write("🧠 Processing your answers and guidance...")

                    # Create the ContractData object with the new steering fields
                    contract_data = ContractData(
                        analysis_title=analysis_title, customer_name=customer_name, arrangement_description=arrangement_description, contract_start=contract_start,
                        contract_end=contract_end, currency=currency, uploaded_file_name=", ".join([f.name for f in uploaded_files]), contract_types=contract_types,
                        # New steering fields from Tab 3
                        key_focus_areas=key_focus_areas,
                        memo_audience=memo_audience,
                        materiality_threshold=materiality_threshold,
                        # All data from Tab 2
                        collectibility=collectibility, is_combined_contract=is_combined_contract, is_modification=is_modification, original_contract_uploaded=original_contract_uploaded,
                        principal_agent_involved=principal_agent_involved, principal_agent_details=principal_agent_details,
                        variable_consideration_involved=variable_consideration_involved, variable_consideration_details=variable_consideration_details,
                        financing_component_involved=financing_component_involved, financing_component_details=financing_component_details,
                        noncash_consideration_involved=noncash_consideration_involved, noncash_consideration_details=noncash_consideration_details,
                        consideration_payable_involved=consideration_payable_involved, consideration_payable_details=consideration_payable_details,
                        ssp_represents_contract_price=ssp_represents_contract_price, revenue_recognition_timing_details=revenue_recognition_timing_details
                    )

                    st.write("⚡ Running AI analysis...")
                    analysis_results = analyzer.analyze_contract(combined_text, contract_data, debug_config=debug_config)
                    st.session_state.analysis_results = analysis_results
                    st.session_state.contract_data = contract_data
                    status.update(label="✅ Analysis complete!", state="complete")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"An unexpected error occurred during analysis: {str(e)}")
                    st.exception(e)
                    st.stop()

else:
    # Display results
    analysis_results = st.session_state.analysis_results
    contract_data = st.session_state.contract_data

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📊 Analysis Results: {contract_data.analysis_title}")
    with col2:
        if st.button("🔄 New Analysis", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Analysis metrics
    with st.container(border=True):
        st.markdown("**📊 Analysis Overview**")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("Source Quality", getattr(analysis_results, 'source_quality', 'N/A'))
        with metrics_col2:
            st.metric("Audience", contract_data.memo_audience.split(' / ')[0])
        with metrics_col3:
            st.metric("Currency", contract_data.currency)

    # Five-step analysis summary
    st.markdown("---")
    st.subheader("📋 ASC 606 Five-Step Analysis Summary")
    
    steps = [
        ("Contract Identification", getattr(analysis_results, 'step1_contract_identification', 'N/A')),
        ("Performance Obligations", getattr(analysis_results, 'step2_performance_obligations', 'N/A')),
        ("Transaction Price", getattr(analysis_results, 'step3_transaction_price', 'N/A')),
        ("Price Allocation", getattr(analysis_results, 'step4_price_allocation', 'N/A')),
        ("Revenue Recognition", getattr(analysis_results, 'step5_revenue_recognition', 'N/A'))
    ]
    
    for i, (step_name, step_data) in enumerate(steps, 1):
        with st.expander(f"**Step {i}: {step_name}**", expanded=(i==1)):
            if isinstance(step_data, dict):
                st.json(step_data)
            else:
                st.markdown(str(step_data))

    # Professional memo
    st.markdown("---")
    st.subheader("📋 Professional Accounting Memo")
    memo = getattr(analysis_results, 'professional_memo', None)
    if memo:
        with st.container(border=True):
            st.markdown(memo)
            st.download_button(
                label="📄 Download Memo",
                data=memo.encode('utf-8'),
                file_name=f"{contract_data.analysis_title.replace(' ', '_')}_ASC606_Memo.txt",
                mime="text/plain"
            )
    else:
        st.info("No memo generated for this analysis.")

    # Additional sections for comprehensive results
    if debug_config.get("show_raw_response", False):
        st.markdown("---")
        st.subheader("🔧 Debug Information")
        st.json(analysis_results.__dict__ if hasattr(analysis_results, '__dict__') else str(analysis_results))

    # Citations and guidance
    if hasattr(analysis_results, 'citations') and analysis_results.citations:
        st.markdown("---")
        st.subheader("📚 Citations")
        for citation in analysis_results.citations:
            st.write(f"• {citation}")

    if hasattr(analysis_results, 'implementation_guidance') and analysis_results.implementation_guidance:
        st.markdown("---")
        st.subheader("💡 Implementation Guidance")
        for guidance in analysis_results.implementation_guidance:
            st.write(f"• {guidance}")

    if hasattr(analysis_results, 'not_applicable_items') and analysis_results.not_applicable_items:
        st.markdown("---")
        st.subheader("❌ Not Applicable Items")
        for item in analysis_results.not_applicable_items:
            st.write(f"• {item}")