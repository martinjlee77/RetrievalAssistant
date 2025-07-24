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

    ## Set up the tabs
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

    # Tab 2: Preliminary Assessment
    with tab2:

        st.write(
            "Provide your initial analysis - the AI will verify against the contract text."
        )
        # Create our two main columns for organization
        col1, col2 = st.columns(2, gap="large")

        # --- Column 1: Judgment & Flags Panel ---
        with col1:
            st.markdown("##### Key Contract Judgments")
            collectibility_assessment = st.radio(
                "Collectibility Assessment *",
                ["Probable", "Not Probable", "Uncertain"],
                index=0,
                horizontal=True,
                help=
                "Management's assessment of whether it is probable that the entity will collect substantially all of the consideration."
            )
            is_combined_contract = st.checkbox(
                "Evaluate as a single combined contract?",
                help=
                "Check if the uploaded documents were entered into at or near the same time and should be accounted for as a single arrangement per ASC 606-10-25-9."
            )
            is_modification = st.checkbox(
                "Is this a contract modification or amendment?",
                value=st.session_state.get('is_modification', False),
                help=
                "Check if this contract modifies or amends an existing agreement.",
                key="is_modification")
            st.divider()
            st.markdown("##### Additional Elements Check")
            financing_component = st.checkbox(
                "Significant Financing Component?",
                value=st.session_state.get('financing_component', False),
                key="financing_component")
            material_rights = st.checkbox("Material Rights for future items?",
                                          value=st.session_state.get(
                                              'material_rights', False),
                                          key="material_rights")
            customer_options = st.checkbox(
                "Other Customer Options for additional goods/services?",
                value=st.session_state.get('customer_options', False),
                key="customer_options")

        # --- Column 2: Interactive Details Panel ---
        with col2:
            st.markdown("##### Performance Obligations")
            if 'performance_obligations' not in st.session_state:
                st.session_state.performance_obligations = []

            with st.expander("Add a Performance Obligation"):
                po_col1, po_col2 = st.columns(2)
                new_po_name = po_col1.text_input(
                    "PO Name", placeholder="e.g., Software License")
                new_po_type = po_col2.selectbox(
                    "Type", ["Good", "Service", "License", "Other"],
                    key="po_type")

                po_col3, po_col4 = st.columns(2)
                new_po_timing = po_col3.selectbox(
                    "Timing", ["Point in Time", "Over Time"], key="po_timing")
                new_po_ssp = po_col4.number_input(
                    "Standalone Selling Price (SSP)",
                    min_value=0.0,
                    format="%.2f",
                    key="po_ssp")

                if st.button("Add PO"):
                    if new_po_name and new_po_ssp > 0:
                        st.session_state.performance_obligations.append({
                            'name':
                            new_po_name,
                            'type':
                            new_po_type,
                            'timing':
                            new_po_timing,
                            'ssp':
                            new_po_ssp
                        })
                        st.success(f"Added: {new_po_name}")
                        st.rerun()

            if st.session_state.performance_obligations:
                st.write("**Current Performance Obligations:**")
                for i, po in enumerate(
                        st.session_state.performance_obligations):
                    po_display_col1, po_display_col2 = st.columns([4, 1])
                    po_display_col1.write(
                        f"**{i+1}. {po['name']}** ({po['type']}) - {po['ssp']:,.2f}"
                    )
                    if po_display_col2.button("✖️",
                                              key=f"remove_po_{i}",
                                              help="Remove this PO"):
                        st.session_state.performance_obligations.pop(i)
                        st.rerun()
            st.divider()
            st.markdown("##### Transaction Price")
            fixed_consideration = st.number_input(
                "Fixed Consideration *",
                value=st.session_state.get('fixed_consideration', 0.0),
                min_value=0.0,
                format="%.2f",
                help="The guaranteed, fixed amount in the contract.",
                key="fixed_consideration")
            has_variable = st.checkbox("Includes Variable Consideration?",
                                       value=st.session_state.get(
                                           'has_variable_consideration',
                                           False),
                                       key="has_variable_consideration")
            if has_variable:
                var_col1, var_col2 = st.columns(2)
                variable_type = var_col1.selectbox(
                    "Variable Consideration Type",
                    ["Performance Bonus", "Penalty", "Usage-based", "Other"],
                    key="variable_type")
                variable_amount = var_col2.number_input(
                    "Estimated Variable Amount",
                    value=st.session_state.get('variable_amount', 0.0),
                    min_value=0.0,
                    format="%.2f",
                    key="variable_amount")
            has_consideration_payable = st.checkbox(
                "Includes Consideration Payable to Customer?",
                help=
                "Check if the contract includes payments to the customer (e.g., rebates, coupons)."
            )
            if has_consideration_payable:
                consideration_payable_amount = st.number_input(
                    "Total Consideration Payable to Customer",
                    min_value=0.0,
                    format="%.2f",
                    key="consideration_payable_amount")

        # Guidance for Tab 2
        st.markdown("---")
        with st.container(border=True):
            st.info(
                "After completing your assessment, proceed to the **⚙️ Step 3: Analysis & Submission** tab to run the analysis.",
                icon="➡️"
            )
            
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
                        performance_obligations=performance_obligations_data,
                        fixed_consideration=fixed_consideration,
                        variable_consideration=variable_consideration_data,
                        financing_component=financing_component,
                        material_rights=material_rights,
                        customer_options=customer_options,
                        collectibility_assessment=collectibility_assessment,
                        has_consideration_payable=has_consideration_payable,
                        consideration_payable_amount=
                        consideration_payable_amount)
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
            # Format memo with proper markdown
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
        kb_stats = analyzer.get_knowledge_base_stats()
        st.json(kb_stats)
