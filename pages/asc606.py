"""
ASC 606 Revenue Recognition Analysis Page
"""

import streamlit as st
import time
import json
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ValidationError

# Import core components
from core.analyzers import get_analyzer
from core.models import ContractData, ASC606Analysis
from core.ui_helpers import (render_analysis_metrics, render_step_analysis,
                             render_professional_memo)
from utils.document_extractor import DocumentExtractor
from utils.llm import create_debug_sidebar
# Navigation is handled by main Home.py file

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
    """Get cached analyzer instance"""
    return get_analyzer("ASC 606")


analyzer = get_cached_analyzer()
extractor = DocumentExtractor()

# Standard header
st.title("Contract Review Using Hybrid RAG (ChatGPT-4o)")
st.write(
    "Contract analysis using authoritative FASB guidance and industry leading interpretations. Complete the **required fields(*)** then click Analyze Contract."
)

# Add debugging controls in sidebar
debug_config = create_debug_sidebar()

# Main application logic
if st.session_state.analysis_results is None:

    ## MODIFICATION 1: Use Markdown in tab labels for a bolder look.
    tab1, tab2, tab3 = st.tabs([
        "**📋 Step 1: Contract Details & Upload**",
        "**📝 Step 2: Preliminary Assessment**",
        "**⚙️ Step 3: Analysis & Submission**"
    ])

    # Tab 1: Contract Details & Upload
    with tab1:
        # ... (all the existing content of tab1 remains here) ...
        # Contract details section
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
                    "Master Agreement", "Master Services Agreement (MSA)",
                    "Statement of Work (SOW)",
                    "Software as a Service (SaaS) Agreement",
                    "Software License Agreement",
                    "Professional Services Agreement",
                    "Sales Order / Order Form", "Purchase Order (PO)",
                    "Contract Amendment / Addendum", "Change Order",
                    "Reseller / Partner Agreement", "Invoice", "Other"
                ],
                help=
                "Select all document types that are part of this analysis. This helps the AI understand the relationship between the uploaded files."
            )

        with col4:
            currency = st.selectbox(
                "Currency *",
                ["USD", "EUR", "GBP", "CAD", "AUD", "KWR", "JPY", "Other"],
                help="Primary currency for the contract")

        col5, col6 = st.columns(2, gap="small")
        with col5:
            contract_start = st.date_input("Contract Start Date *")
        with col6:
            contract_end = st.date_input("Contract End Date *")

        arrangement_description = st.text_area(
            "Arrangement Description *",
            placeholder=
            "e.g., Three-year SaaS subscription with implementation services",
            height=100,
            help=
            "Description of the contractual arrangement - more detail is better to provide context for the AI"
        )

        # File upload
        st.subheader("📄 Document Upload")
        uploaded_files = st.file_uploader(
            "Upload All Related Contract Documents *",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help=
            "Crucial: Upload the complete set of related documents for this arrangement (e.g., the MSA, all SOWs, and any amendments)."
        )

        # Guidance for Tab 1
        st.markdown("---")
        with st.container(border=True):
            st.info(
                "Once the fields above are complete, continue to the **📝 Step 2: Preliminary Assessment** tab.",
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

    with tab3:
        st.subheader("⚙️ Analysis Configuration")
        # ... (all the existing content of tab3 remains here) ...
        analysis_depth = st.selectbox(
            "Analysis Depth", [
                "Standard Analysis", "Detailed Analysis",
                "Comprehensive Analysis"
            ],
            help="Choose the level of detail for your analysis")
        output_format = st.selectbox(
            "Output Format",
            ["Professional Memo", "Executive Summary", "Technical Analysis"],
            help="Select the format for your analysis results")
        include_citations = st.checkbox(
            "Include Citations",
            value=True,
            help="Include authoritative source citations in the analysis")
        include_examples = st.checkbox(
            "Include Examples",
            value=False,
            help="Include practical examples and illustrations")
        additional_notes = st.text_area(
            "Additional Notes",
            placeholder=
            "Any specific requirements or context for this analysis...",
            height=100,
            help="Optional notes to guide the analysis")

        # Validation function
        def validate_form(data):
            """Gathers all validation errors into a list."""
            errors = []
            if not data['analysis_title']:
                errors.append("Analysis Title is required (Step 1).")
            if not data['customer_name']:
                errors.append("Customer Name is required (Step 1).")
            if not data['arrangement_description']:
                errors.append("Arrangement Description is required (Step 1).")
            if not data['contract_types']:
                errors.append(
                    "At least one Contract Document Type must be selected (Step 1)."
                )
            if not data['uploaded_files']:
                errors.append(
                    "At least one document must be uploaded (Step 1).")
            if data['uploaded_files'] and len(data['uploaded_files']) > 5:
                errors.append("Please upload a maximum of 5 files (Step 1).")
            if data['fixed_consideration'] is None:
                errors.append("Fixed Consideration is required (Step 2).")
            if not data['performance_obligations']:
                errors.append(
                    "At least one Performance Obligation must be added (Step 2)."
                )
            if not data['collectibility_assessment']:
                errors.append(
                    "Collectibility Assessment is required (Step 2).")
            return errors

        ## MODIFICATION 4: Move the entire analysis button and logic block INSIDE Tab 3.
        st.markdown("---")
        st.write(
            "Click the button below to begin the AI analysis. This may take a few moments."
        )
        if st.button("🔍 Analyze Contract",
                     use_container_width=True,
                     type="primary"):
            form_data = {
                "analysis_title": analysis_title,
                "customer_name": customer_name,
                "arrangement_description": arrangement_description,
                "contract_types": contract_types,
                "uploaded_files": uploaded_files,
                "fixed_consideration": fixed_consideration,
                "performance_obligations":
                st.session_state.performance_obligations,
                "collectibility_assessment": collectibility_assessment,
                "has_consideration_payable": has_consideration_payable,
                "is_combined_contract": is_combined_contract
            }

            validation_errors = validate_form(form_data)

            if validation_errors:
                st.error("Please fix the following issues before submitting:")
                for error in validation_errors:
                    st.warning(
                        f"• {error}")  # Using warning for better visibility
                st.stop()

            # Process the analysis
            with st.status("🔍 Analyzing contract...", expanded=True) as status:
                try:
                    # ... (the entire try/except block for analysis remains here) ...
                    st.write("📄 Extracting text from uploaded documents...")
                    all_extracted_text = []
                    all_metadata = []
                    for uploaded_file in uploaded_files:
                        extraction_result = extractor.extract_text(
                            uploaded_file)
                        if extraction_result.get('text'):
                            all_extracted_text.append(
                                extraction_result['text'])
                            all_metadata.append({
                                'file_name':
                                uploaded_file.name,
                                'method':
                                extraction_result.get('method', 'unknown'),
                                'word_count':
                                extraction_result.get('word_count', 0),
                                'char_count':
                                len(extraction_result.get('text', ''))
                            })
                    if not all_extracted_text:
                        st.error(
                            "No text could be extracted from the uploaded documents"
                        )
                        st.stop()
                    combined_text = "\n".join(all_extracted_text)
                    st.write(
                        "🧠 Processing contract data and preliminary assessment..."
                    )
                    time.sleep(0.5)
                    performance_obligations_data = []
                    for po in st.session_state.performance_obligations:
                        performance_obligations_data.append({
                            'name':
                            po['name'],
                            'type':
                            po['type'],
                            'timing':
                            po['timing'],
                            'ssp':
                            po['ssp']
                        })
                    variable_consideration_data = None
                    if has_variable:
                        variable_consideration_data = {
                            'type': variable_type,
                            'estimated_amount': variable_amount
                        }
                    consideration_payable_amount = 0.0
                    if has_consideration_payable:
                        consideration_payable_amount = st.session_state.get(
                            'consideration_payable_amount', 0.0
                        ) if 'consideration_payable_amount' in st.session_state else 0.0
                    contract_data = ContractData(
                        analysis_title=analysis_title,
                        customer_name=customer_name,
                        arrangement_description=arrangement_description,
                        contract_start=contract_start,
                        contract_end=contract_end,
                        currency=currency,
                        uploaded_file_name=", ".join(
                            [f.name for f in uploaded_files]),
                        contract_types=contract_types,
                        analysis_depth=analysis_depth,
                        output_format=output_format,
                        include_citations=include_citations,
                        include_examples=include_examples,
                        additional_notes=additional_notes,
                        is_modification=is_modification,
                        is_combined_contract=is_combined_contract,
                        performance_obligations=[],  # Let AI analyze from contract
                        fixed_consideration=0.0,  # Let AI extract from contract
                        variable_consideration=None,
                        financing_component=(financing_component == "Yes"),
                        material_rights=False,  # Let AI analyze
                        customer_options=False,  # Let AI analyze
                        collectibility_assessment=collectibility_assessment,
                        has_consideration_payable=(has_consideration_payable == "Yes"),
                        consideration_payable_amount=0.0,  # Let AI extract from contract
                        # Enhanced ASC 606 Assessment Fields
                        original_contract_uploaded=original_contract_uploaded,
                        principal_agent_involved=(principal_agent_involved == "Yes"),
                        principal_agent_details=principal_agent_details,
                        noncash_consideration_involved=(noncash_consideration_involved == "Yes"),
                        noncash_consideration_details=noncash_consideration_details,
                        ssp_represents_contract_price=(ssp_represents_contract_price == "Yes"),
                        revenue_recognition_timing_details=revenue_recognition_timing_details)
                    st.write("⚡ Running AI analysis with hybrid RAG system...")
                    analysis_results = analyzer.analyze_contract(
                        combined_text,
                        contract_data,
                        debug_config=debug_config)
                    st.session_state.analysis_results = analysis_results
                    st.session_state.contract_data = contract_data
                    status.update(label="✅ Analysis complete!",
                                  state="complete")
                    st.success("Analysis completed successfully!")
                    if debug_config.get("show_raw_response") and hasattr(
                            analysis_results, 'raw_response'):
                        with st.expander("🔧 Raw AI Response (Debug)",
                                         expanded=False):
                            st.text(analysis_results.raw_response)
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.stop()

else:
    # Render analysis results
    analysis_results = st.session_state.analysis_results
    contract_data = st.session_state.contract_data

    # Header with restart option
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📊 Analysis Results: {contract_data.analysis_title}")
    with col2:
        if st.button("🔄 New Analysis", use_container_width=True):
            st.session_state.analysis_results = None
            st.session_state.contract_data = None
            st.rerun()

    # Render analysis metrics with better formatting
    with st.container(border=True):
        st.markdown("**📊 Analysis Overview**")

        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

        with metrics_col1:
            st.metric("Source Quality", analysis_results.source_quality
                      or "Hybrid RAG")
        with metrics_col2:
            st.metric("Analysis Depth", contract_data.analysis_depth.title())
        with metrics_col3:
            st.metric("Currency", contract_data.currency)
        with metrics_col4:
            citations_count = len(analysis_results.citations
                                  ) if analysis_results.citations else 0
            st.metric("Citations", citations_count)

    st.markdown("---")

    # ASC 606 Five-Step Analysis Summary
    st.subheader("📋 ASC 606 Five-Step Analysis Summary")

    steps = [("Contract Identification",
              analysis_results.step1_contract_identification),
             ("Performance Obligations",
              analysis_results.step2_performance_obligations),
             ("Transaction Price", analysis_results.step3_transaction_price),
             ("Price Allocation", analysis_results.step4_price_allocation),
             ("Revenue Recognition",
              analysis_results.step5_revenue_recognition)]

    # Enhanced step analysis display
    for i, (step_name, step_data) in enumerate(steps, 1):
        with st.expander(f"**Step {i}: {step_name}**", expanded=False):
            if isinstance(step_data, dict):
                # Pretty print JSON data
                st.json(step_data)
            else:
                # Display text data with markdown
                st.markdown(step_data)

    # Professional Memo with improved formatting
    st.markdown("---")
    st.subheader("📋 Professional Accounting Memo")

    if analysis_results.professional_memo:
        with st.container(border=True):
            # Format memo with proper styling
            st.markdown(analysis_results.professional_memo)

            # Download button for memo
            memo_bytes = analysis_results.professional_memo.encode('utf-8')
            st.download_button(
                label="📄 Download Memo",
                data=memo_bytes,
                file_name=
                f"{contract_data.analysis_title.replace(' ', '_')}_ASC606_Memo.txt",
                mime="text/plain")
    else:
        st.info("No memo generated for this analysis.")

    # Additional Analysis Details
    st.markdown("---")
    st.subheader("📚 Additional Analysis Details")

    # Implementation Guidance
    if analysis_results.implementation_guidance:
        with st.expander("Implementation Guidance"):
            for guidance in analysis_results.implementation_guidance:
                st.write(f"• {guidance}")

    # Citations
    if analysis_results.citations:
        with st.expander("Source Citations"):
            for citation in analysis_results.citations:
                st.write(f"• {citation}")

    # Not Applicable Items
    if analysis_results.not_applicable_items:
        with st.expander("Not Applicable Items"):
            for item in analysis_results.not_applicable_items:
                st.write(f"• {item}")

    # Analysis Statistics
    with st.expander("Analysis Statistics"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(
                f"**Total Characters**: {len(analysis_results.professional_memo) if analysis_results.professional_memo else 0:,}"
            )
            st.write(f"**Analysis Depth**: {contract_data.analysis_depth}")
        with col2:
            st.write(f"**Output Format**: {contract_data.output_format}")
            st.write(
                f"**Include Citations**: {'Yes' if contract_data.include_citations else 'No'}"
            )
