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

    # Tab 2: ASC 606 Analysis Questions (Gemini's Clean Layout)
    with tab2:
        st.write(
            "This section helps our AI understand key details about the contract that may not be explicitly stated in the documents. Your answers will guide the analysis."
        )
        st.markdown("---")

        collectibility_assessment = st.selectbox(
            "Is it probable that the entity will collect the consideration?",
            options=["Probable", "Not Probable"],  # Removed "Uncertain" per Gemini
            index=0,
            help="If collection of the full contract price is not probable, a contract may still exist for a lesser amount that is probable of collection."
        )
        
        is_combined_contract_dropdown = st.selectbox(
            "Should all uploaded documents be evaluated together as a single deal?",
            options=["Yes", "No"], 
            index=0,
            help="Multiple documents may need to be combined per ASC 606-10-25-9"
        )
        is_combined_contract = is_combined_contract_dropdown == "Yes"
        
        is_modification_dropdown = st.selectbox(
            "Is this a modification to an existing contract?",
            options=["Yes", "No"], 
            index=1,
            help="Contract modifications require special accounting per ASC 606-10-25-10"
        )
        is_modification = is_modification_dropdown == "Yes"
        
        original_contract_uploaded = None
        if is_modification:
            original_contract_uploaded = st.selectbox(
                "Have you also uploaded the original contract documents?",
                options=["Yes", "No"], 
                index=1
            )
        st.markdown("---")

        st.info("The AI will analyze the contract(s) to identify distinct goods or services (performance obligations), including any customer options that may represent a **material right**.", icon="🤖")
        
        principal_agent_involved = st.selectbox(
            "Is a third party involved in providing any goods or services to the end customer?",
            options=["No", "Yes"], 
            index=0,
            help="This helps determine if you should recognize revenue gross or net"
        )
        
        principal_agent_details = None
        if principal_agent_involved == "Yes":
            principal_agent_details = st.text_area(
                "Please describe the arrangement. Specify which party controls the good or service before transfer:",
                placeholder="e.g., We are an agent for Party X's software, and they handle fulfillment and support."
            )
        st.markdown("---")

        has_variable_consideration = st.selectbox(
            "Does the contract include any variable consideration?",
            options=["No", "Yes"], 
            index=0,
            help="Variable consideration includes volume discounts, performance bonuses, penalties, etc."
        )
        
        variable_consideration_details = None
        if has_variable_consideration == "Yes":
            variable_consideration_details = st.text_area(
                "Please provide details on the variable consideration and your estimate:",
                placeholder="e.g., A $10,000 performance bonus is included, which we estimate is 90% probable based on past performance."
            )
            
        financing_component = st.selectbox(
            "Does the contract include a significant financing component?",
            options=["No", "Yes"], 
            index=0,
            help="This applies when payment timing provides significant financing benefit"
        )
        
        financing_component_details = None
        if financing_component == "Yes":
            financing_component_details = st.text_area(
                "Please provide details on the financing component:",
                placeholder="e.g., Customer pays $120K upfront for 3-year service valued at $150K, creating a 10% discount rate."
            )
            
        noncash_consideration_involved = st.selectbox(
            "Does the contract include any noncash consideration?",
            options=["No", "Yes"], 
            index=0,
            help="Such as equity, customer-provided materials, etc."
        )
        
        noncash_consideration_details = None
        if noncash_consideration_involved == "Yes":
            noncash_consideration_details = st.text_area(
                "Please describe the noncash consideration and provide its estimated fair value:",
                placeholder="e.g., Customer provides equipment valued at $50K as partial payment."
            )
            
        has_consideration_payable = st.selectbox(
            "Does the contract include consideration payable to the customer?",
            options=["No", "Yes"], 
            index=0,
            help="Such as rebates, coupons, or other payments to the customer"
        )
        
        consideration_payable_details = None
        if has_consideration_payable == "Yes":
            # Corrected to be a text area as requested per Gemini feedback
            consideration_payable_details = st.text_area(
                "Please describe the consideration and provide its amount. Note: This typically reduces the transaction price.",
                placeholder="e.g., Customer receives a $5,000 upfront credit for marketing activities."
            )
        st.markdown("---")

        ssp_represents_contract_price = st.selectbox(
            "Do the prices in the contract represent their Standalone Selling Price (SSP)?",
            options=["Yes", "No"],  # Removed "Uncertain" per Gemini feedback
            index=0,
            help="SSP is the price at which you would sell a good or service separately. If contract prices are reasonable estimates, select 'Yes'."
        )
        st.markdown("---")

        revenue_recognition_timing_details = st.text_area(
            "Please describe when control transfers for each major performance obligation:",
            placeholder="e.g., Software license is delivered upfront, Support services are provided evenly over 12 months.",
            help="This helps the AI understand your specific timing considerations"
        )
        st.markdown("---")
        
        with st.container(border=True):
            st.info("After completing your assessment, proceed to the **⚙️ Step 3: Analyze** tab to run the analysis.", icon="➡️")

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
            """Validate required fields"""
            errors = []
            if not analysis_title:
                errors.append("Analysis Title is required")
            if not customer_name:
                errors.append("Customer Name is required")
            if not arrangement_description:
                errors.append("Arrangement Description is required")
            if not contract_types:
                errors.append("At least one Contract Document Type must be selected")
            if not uploaded_files:
                errors.append("At least one document must be uploaded")
            return errors

        st.markdown("---")
        st.write("Click the button below to begin the AI analysis. This may take a few moments.")
        
        if st.button("🔍 Analyze Contract", use_container_width=True, type="primary"):
            validation_errors = validate_form()
            
            if validation_errors:
                st.error("Please fix the following issues before submitting:")
                for error in validation_errors:
                    st.warning(f"• {error}")
                st.stop()

            with st.status("🔍 Analyzing contract...", expanded=True) as status:
                try:
                    st.write("📄 Extracting text from uploaded documents...")
                    all_extracted_text = []
                    for file in uploaded_files:
                        result = extractor.extract_text(file)
                        if result.get('text'):
                            all_extracted_text.append(result['text'])
                    
                    if not all_extracted_text:
                        st.error("No text could be extracted from the uploaded documents")
                        st.stop()
                    
                    combined_text = "\n\n--- END OF DOCUMENT ---\n\n".join(all_extracted_text)
                    st.write("🧠 Processing contract data and your answers...")

                    # Create contract data object
                    try:
                        contract_data = ContractData(
                            analysis_title=analysis_title,
                            customer_name=customer_name,
                            arrangement_description=arrangement_description,
                            contract_start=contract_start,
                            contract_end=contract_end,
                            currency=currency,
                            uploaded_file_name=", ".join([f.name for f in uploaded_files]),
                            contract_types=contract_types,
                            analysis_depth=analysis_depth,
                            output_format=output_format,
                            include_citations=include_citations,
                            include_examples=include_examples,
                            additional_notes=additional_notes,
                            # Preliminary Assessment Data
                            collectibility=collectibility_assessment == "Probable",
                            is_combined_contract=is_combined_contract,
                            is_modification=is_modification,
                            original_contract_uploaded=original_contract_uploaded == "Yes" if original_contract_uploaded else None,
                            # Enhanced fields
                            financing_component=financing_component == "Yes",
                            financing_component_details=financing_component_details,
                            variable_consideration=has_variable_consideration == "Yes",
                            variable_consideration_details=variable_consideration_details,
                            material_rights=False,  # Let AI analyze
                            customer_options=False,  # Let AI analyze
                            collectibility_assessment=collectibility_assessment,
                            has_consideration_payable=(has_consideration_payable == "Yes"),
                            consideration_payable_amount=0.0,  # Let AI extract from contract
                            # Enhanced ASC 606 Assessment Fields
                            principal_agent_involved=(principal_agent_involved == "Yes"),
                            principal_agent_details=principal_agent_details,
                            noncash_consideration_involved=(noncash_consideration_involved == "Yes"),
                            noncash_consideration_details=noncash_consideration_details,
                            ssp_represents_contract_price=(ssp_represents_contract_price == "Yes"),
                            revenue_recognition_timing_details=revenue_recognition_timing_details
                        )
                    except ValidationError as e:
                        st.error(f"Data validation error: {e}")
                        st.stop()

                    st.write("⚡ Running AI analysis...")
                    analysis_results = analyzer.analyze_contract(combined_text, contract_data, debug_config=debug_config)
                    
                    st.session_state.analysis_results = analysis_results
                    st.session_state.contract_data = contract_data
                    status.update(label="✅ Analysis complete!", state="complete")
                    st.success("Analysis completed successfully!")
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