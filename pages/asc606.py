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
st.title("ASC 606 Contract Analysis")
st.write(
    "Contract analysis using authoritative FASB guidance and industry leading interpretations. Complete the **required fields(*)** then click Analyze Contract."
)

debug_config = create_debug_sidebar()

# Main application logic
if st.session_state.analysis_results is None:

    tab1, tab2, tab3 = st.tabs([
        "**📋 Step 1: Upload Contract**",
        "**📝 Step 2: Analysis Questions**",
        "**⚙️ Step 3: Analyze**"
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
                                          placeholder="e.g., ABC Corporation")
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
            contract_start = st.date_input("Contract Start Date *")
        with col6:
            contract_end = st.date_input("Contract End Date *")
        arrangement_description = st.text_area(
            "Arrangement Description *",
            placeholder="e.g., Three-year SaaS subscription with implementation services",
            height=100,
            help="Description of the contractual arrangement - more detail is better to provide context for the AI"
        )
        st.subheader("📄 Document Upload")
        uploaded_files = st.file_uploader(
            "Upload All Related Contract Documents *", type=['pdf', 'docx', 'txt'], accept_multiple_files=True,
            help="Crucial: Upload the complete set of related documents for this arrangement."
        )
        st.markdown("---")
        with st.container(border=True):
            st.info(
                "Once the fields above are complete, continue to the **📝 Step 2: Analysis Questions** tab.",
                icon="➡️")

    # Tab 2: Analysis Questions (New Compact Design with Expanders)
    with tab2:
        st.write("Your answers provide crucial context for the AI analysis. **Required fields are marked with an asterisk (*).**")

        # Initialize all optional detail variables to None to prevent errors
        original_contract_uploaded = None
        principal_agent_details = None
        variable_consideration_details = None
        financing_component_details = None
        noncash_consideration_details = None
        consideration_payable_details = None

        with st.expander("**Step 1: Identify the Contract**", expanded=True):
            col1, col2 = st.columns(2, gap="medium")
            with col1:
                collectibility = st.toggle("Collectibility is probable *", value=True, help="A contract does not exist under ASC 606 if collection is not probable.")
                is_modification = st.toggle("This is a contract modification *", value=False)
            with col2:
                is_combined_contract = st.toggle("Evaluate docs as one contract? *", value=True)
                if is_modification:
                    original_contract_uploaded = st.toggle("Is the original contract uploaded?", value=False)

        with st.expander("**Step 2: Identify Performance Obligations**"):
            st.info("The AI will analyze the contract(s) to identify distinct goods or services.", icon="🤖")
            principal_agent_involved = st.toggle("Is a third party involved in providing goods or services?")
            if principal_agent_involved:
                principal_agent_details = st.text_area("Describe the arrangement and specify who controls the good/service:", placeholder="e.g., We are an agent for Party X's software...", label_visibility="collapsed")

        with st.expander("**Step 3: Determine the Transaction Price**"):
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
        st.info("Continue to the **⚙️ 3. Analyze** tab.", icon="➡️")

    # Tab 3: Analysis Configuration and Execution
    with tab3:
        st.subheader("⚙️ Analysis Configuration")
        col1, col2 = st.columns(2, gap="small")
        with col1:
            analysis_depth = st.selectbox(
                "Analysis Depth",
                ["Standard Analysis", "Detailed Analysis", "Comprehensive Analysis"],
                help="Choose the level of detail for your analysis"
            )
            include_citations = st.checkbox("Include Citations", value=True,
                                           help="Include ASC 606 citations in the analysis")
        with col2:
            output_format = st.selectbox(
                "Output Format",
                ["Professional Memo", "Executive Summary", "Technical Analysis"],
                help="Choose the format for your analysis output"
            )
            include_examples = st.checkbox("Include Examples", value=False,
                                          help="Include illustrative examples in the analysis")

        additional_notes = st.text_area(
            "Additional Notes (Optional)",
            placeholder="Any specific requirements or context for this analysis...",
            height=100,
            help="Provide any additional context or specific requirements"
        )

        def validate_form():
            """Validate required fields from Tab 1"""
            errors = []
            if not analysis_title: errors.append("Analysis Title is required (Tab 1).")
            if not customer_name: errors.append("Customer Name is required (Tab 1).")
            if not arrangement_description: errors.append("Arrangement Description is required (Tab 1).")
            if not contract_types: errors.append("At least one Document Type must be selected (Tab 1).")
            if not uploaded_files: errors.append("At least one document must be uploaded (Tab 1).")
            return errors

        st.markdown("---")
        if st.button("🔍 Analyze Contract", use_container_width=True, type="primary"):
            validation_errors = validate_form() # Call the corrected function
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

                    st.write("🧠 Processing your answers...")

                    # Corrected ContractData creation logic
                    contract_data = ContractData(
                        analysis_title=analysis_title, customer_name=customer_name, arrangement_description=arrangement_description, contract_start=contract_start,
                        contract_end=contract_end, currency=currency, uploaded_file_name=", ".join([f.name for f in uploaded_files]), contract_types=contract_types,
                        analysis_depth=analysis_depth, output_format=output_format, additional_notes=additional_notes,
                        # All data from Tab 2 is now correctly passed from the new UI
                        collectibility=collectibility, is_combined_contract=is_combined_contract, is_modification=is_modification, original_contract_uploaded=original_contract_uploaded,
                        principal_agent_involved=principal_agent_involved, principal_agent_details=principal_agent_details,
                        variable_consideration_involved=variable_consideration_involved, variable_consideration_details=variable_consideration_details,
                        financing_component_involved=financing_component_involved, financing_component_details=financing_component_details,
                        noncash_consideration_involved=noncash_consideration_involved, noncash_consideration_details=noncash_consideration_details,
                        consideration_payable_involved=consideration_payable_involved, consideration_payable_details=consideration_payable_details,
                        ssp_represents_contract_price=ssp_represents_contract_price, revenue_recognition_timing_details=revenue_recognition_timing_details
                    )

                    st.write("⚡ Running AI analysis...")
                    # Rest of the analysis execution
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
            st.metric("Analysis Depth", contract_data.analysis_depth.title())
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