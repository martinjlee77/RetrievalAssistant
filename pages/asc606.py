"""
ASC 606 Revenue Recognition Analysis Page
"""

import streamlit as st
import time
from typing import Dict, List, Any
from utils.document_extractor import DocumentExtractor
from utils.asc606_analyzer import ASC606Analyzer
from core.models import ContractData

st.title("ASC 606 Revenue Recognition Analyzer")

# Initialize session state for performance obligations
if 'performance_obligations' not in st.session_state:
    st.session_state.performance_obligations = []

# Check if we have analysis results to display
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'contract_data' not in st.session_state:
    st.session_state.contract_data = None

# Display analysis results if available
if st.session_state.analysis_results is None:
    # Create tabbed interface
    tab1, tab2, tab3 = st.tabs([
        "📝 Step 1: Contract Details", 
        "📊 Step 2: Preliminary Assessment", 
        "⚙️ Step 3: Analysis & Submission"
    ])
    
    with tab1:
        st.subheader("📄 Contract Information")
        
        # Analysis title and basic details
        analysis_title = st.text_input(
            "Analysis Title", 
            placeholder="e.g., XYZ Corp Software License Agreement",
            help="Provide a descriptive title for this analysis"
        )
        
        customer_name = st.text_input(
            "Customer Name",
            placeholder="e.g., ABC Company",
            help="Name of the customer/counterparty"
        )
        
        arrangement_description = st.text_area(
            "Arrangement Description",
            placeholder="Brief description of the goods/services being provided...",
            height=100,
            help="Describe what your company is providing under this contract"
        )
        
        # Contract document types
        st.markdown("**Contract Document Types**")
        contract_types = st.multiselect(
            "Select all document types included:",
            [
                "Master Service Agreement (MSA)",
                "Statement of Work (SOW)", 
                "Purchase Order",
                "Contract Amendment",
                "Service Level Agreement (SLA)",
                "Other"
            ],
            help="Select all types of documents that make up this contract"
        )
        
        # File upload
        st.markdown("**Upload Contract Documents**")
        uploaded_files = st.file_uploader(
            "Choose files (PDF, Word, or Text)",
            type=['pdf', 'docx', 'doc', 'txt'],
            accept_multiple_files=True,
            help="Upload all relevant contract documents"
        )
        
        # Currency selection
        currency = st.selectbox(
            "Contract Currency",
            ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "Other"],
            help="Primary currency for the contract amounts"
        )
        
        # Guidance for Tab 1
        st.markdown("---")
        with st.container(border=True):
            st.info(
                "After providing contract details, proceed to the **📊 Step 2: Preliminary Assessment** tab to add performance obligations and pricing details.",
                icon="➡️"
            )

    with tab2:
        st.subheader("📊 Preliminary Assessment")
        
        # Contract nature section
        st.markdown("**Contract Nature**")
        col1, col2 = st.columns(2)
        
        with col1:
            is_modification = st.checkbox(
                "Contract Modification/Amendment?",
                help="Check if this is a modification to an existing contract"
            )
        
        with col2:
            is_combined_contract = st.checkbox(
                "Combined Contract Analysis?",
                help="Check if multiple documents should be evaluated as one combined contract"
            )
        
        # Performance obligations section
        st.markdown("**Performance Obligations**")
        
        def add_performance_obligation():
            new_po = {
                'name': f"Performance Obligation {len(st.session_state.performance_obligations) + 1}",
                'type': "Good",
                'timing': "Point in time"
            }
            st.session_state.performance_obligations.append(new_po)
        
        def remove_performance_obligation(index):
            if 0 <= index < len(st.session_state.performance_obligations):
                st.session_state.performance_obligations.pop(index)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("➕ Add Performance Obligation", use_container_width=True):
                add_performance_obligation()
        
        # Display existing performance obligations
        for i, po in enumerate(st.session_state.performance_obligations):
            with st.container(border=True):
                po_col1, po_col2, po_col3, po_col4 = st.columns([2, 1, 1, 1])
                
                with po_col1:
                    po['name'] = st.text_input(
                        "Description",
                        value=po['name'],
                        key=f"po_name_{i}"
                    )
                
                with po_col2:
                    po['type'] = st.selectbox(
                        "Type",
                        ["Good", "Service", "License", "Other"],
                        index=["Good", "Service", "License", "Other"].index(po.get('type', 'Good')),
                        key=f"po_type_{i}"
                    )
                
                with po_col3:
                    po['timing'] = st.selectbox(
                        "Recognition",
                        ["Point in time", "Over time"],
                        index=["Point in time", "Over time"].index(po.get('timing', 'Point in time')),
                        key=f"po_timing_{i}"
                    )
                
                with po_col4:
                    if st.button("🗑️", key=f"remove_po_{i}", help="Remove this performance obligation"):
                        remove_performance_obligation(i)
                        st.rerun()
        
        if not st.session_state.performance_obligations:
            st.info("Add at least one performance obligation to continue.")
        
        # Transaction price section
        st.markdown("**Transaction Price**")
        
        col1, col2 = st.columns(2)
        with col1:
            fixed_consideration = st.number_input(
                "Fixed Consideration Amount",
                min_value=0.0,
                format="%.2f",
                help="Total fixed consideration amount"
            )
        
        with col2:
            has_variable_consideration = st.checkbox(
                "Includes Variable Consideration?",
                help="Check if contract includes variable pricing elements"
            )
        
        if has_variable_consideration:
            var_col1, var_col2 = st.columns(2)
            with var_col1:
                variable_type = st.selectbox(
                    "Variable Consideration Type",
                    ["Volume discounts", "Performance bonuses", "Penalties", "Other"],
                    key="variable_type"
                )
            with var_col2:
                variable_amount = st.number_input(
                    "Estimated Variable Amount",
                    value=st.session_state.get('variable_amount', 0.0),
                    min_value=0.0,
                    format="%.2f",
                    key="variable_amount"
                )
        
        # Collectibility assessment
        st.markdown("**Collectibility Assessment**")
        collectibility_assessment = st.selectbox(
            "Management's Assessment of Collection Probability",
            ["Probable", "Not Probable", "Uncertain"],
            help="Management's assessment per ASC 606-10-25-1(e)"
        )
        
        # Additional elements
        st.markdown("**Additional Elements**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            financing_component = st.checkbox(
                "Significant Financing Component?",
                help="Check if contract includes significant financing"
            )
        
        with col2:
            material_rights = st.checkbox(
                "Material Rights?",
                help="Check if contract provides material rights to customer"
            )
        
        with col3:
            customer_options = st.checkbox(
                "Customer Options?",
                help="Check if contract includes customer options for additional goods/services"
            )
        
        # Consideration payable to customer
        has_consideration_payable = st.checkbox(
            "Includes Consideration Payable to Customer?",
            help="Check if the contract includes payments to the customer (e.g., rebates, coupons)."
        )
        
        if has_consideration_payable:
            consideration_payable_amount = st.number_input(
                "Total Consideration Payable to Customer",
                min_value=0.0,
                format="%.2f",
                key="consideration_payable_amount"
            )
        else:
            consideration_payable_amount = 0.0

        # Guidance for Tab 2
        st.markdown("---")
        with st.container(border=True):
            st.info(
                "After completing your assessment, proceed to the **⚙️ Step 3: Analysis & Submission** tab to run the analysis.",
                icon="➡️"
            )
            
    with tab3:
        st.subheader("⚙️ Analysis Configuration")
        
        # Analysis options
        analysis_depth = st.selectbox(
            "Analysis Depth", 
            ["Standard Analysis", "Detailed Analysis", "Comprehensive Analysis"],
            help="Choose the level of detail for your analysis"
        )
        
        output_format = st.selectbox(
            "Output Format",
            ["Professional Memo", "Executive Summary", "Technical Analysis"],
            help="Select the format for your analysis results"
        )
        
        include_citations = st.checkbox(
            "Include Citations",
            value=True,
            help="Include authoritative source citations in the analysis"
        )
        
        include_examples = st.checkbox(
            "Include Examples",
            value=False,
            help="Include practical examples and illustrations"
        )
        
        additional_notes = st.text_area(
            "Additional Notes",
            placeholder="Any specific requirements or context for this analysis...",
            height=100,
            help="Optional notes to guide the analysis"
        )

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
                errors.append("At least one Contract Document Type must be selected (Step 1).")
            if not data['uploaded_files']:
                errors.append("At least one document must be uploaded (Step 1).")
            if not data['performance_obligations']:
                errors.append("At least one Performance Obligation must be added (Step 2).")
            return errors

        # Analyze button
        st.markdown("---")
        if st.button("🔍 Analyze Contract", type="primary", use_container_width=True):
            # Collect all form data for validation
            form_data = {
                "analysis_title": analysis_title,
                "customer_name": customer_name,
                "arrangement_description": arrangement_description,
                "contract_types": contract_types,
                "uploaded_files": uploaded_files,
                "fixed_consideration": fixed_consideration,
                "performance_obligations": st.session_state.performance_obligations,
                "collectibility_assessment": collectibility_assessment,
                "has_consideration_payable": has_consideration_payable,
                "is_combined_contract": is_combined_contract
            }

            validation_errors = validate_form(form_data)

            if validation_errors:
                st.error("Please fix the following issues before submitting:")
                for error in validation_errors:
                    st.warning(f"• {error}")
                st.stop()

            # Process the analysis
            with st.status("🔍 Analyzing contract...", expanded=True) as status:
                try:
                    # Initialize document extractor and analyzer
                    extractor = DocumentExtractor()
                    analyzer = ASC606Analyzer()
                    
                    st.write("📄 Extracting text from uploaded documents...")
                    all_extracted_text = []
                    all_metadata = []
                    
                    for uploaded_file in uploaded_files:
                        extraction_result = extractor.extract_text(uploaded_file)
                        if extraction_result.get('text'):
                            all_extracted_text.append(extraction_result['text'])
                            all_metadata.append({
                                'file_name': uploaded_file.name,
                                'method': extraction_result.get('method', 'unknown'),
                                'word_count': extraction_result.get('word_count', 0),
                                'char_count': len(extraction_result.get('text', ''))
                            })
                    
                    if not all_extracted_text:
                        st.error("No text could be extracted from the uploaded documents")
                        st.stop()
                    
                    combined_text = "\n".join(all_extracted_text)
                    
                    st.write("🧠 Processing contract data and preliminary assessment...")
                    time.sleep(0.5)
                    
                    # Process performance obligations
                    performance_obligations_data = []
                    for po in st.session_state.performance_obligations:
                        performance_obligations_data.append({
                            'name': po['name'],
                            'type': po['type'],
                            'timing': po['timing'],
                        })
                    
                    # Process variable consideration
                    variable_consideration_data = None
                    if has_variable_consideration:
                        variable_consideration_data = {
                            'type': variable_type,
                            'estimated_amount': variable_amount
                        }
                    
                    # Create contract data object
                    contract_data = ContractData(
                        analysis_title=analysis_title,
                        customer_name=customer_name,
                        arrangement_description=arrangement_description,
                        contract_types=contract_types,
                        uploaded_files=[f.name for f in uploaded_files],
                        currency=currency,
                        analysis_depth=analysis_depth,
                        output_format=output_format,
                        include_citations=include_citations,
                        include_examples=include_examples,
                        additional_notes=additional_notes,
                        # Preliminary assessment fields
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
                        consideration_payable_amount=consideration_payable_amount
                    )
                    
                    st.write("🔬 Running ASC 606 analysis...")
                    
                    # Debug configuration
                    debug_config = {
                        "model": "gpt-4o",
                        "temperature": 0.3,
                        "max_tokens": 2000,
                        "show_raw_response": False
                    }
                    
                    # Run analysis
                    analysis_results = analyzer.analyze_contract(
                        contract_text=combined_text,
                        contract_data=contract_data,
                        debug_config=debug_config
                    )
                    
                    # Store results in session state
                    st.session_state.analysis_results = analysis_results
                    st.session_state.contract_data = contract_data
                    
                    status.update(label="✅ Analysis completed!", state="complete")
                    st.success("Analysis completed successfully!")
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
            st.metric("Source Quality", analysis_results.source_quality or "Hybrid RAG")
        with metrics_col2:
            st.metric("Analysis Depth", contract_data.analysis_depth.title())
        with metrics_col3:
            st.metric("Currency", contract_data.currency)
        with metrics_col4:
            citations_count = len(analysis_results.citations) if analysis_results.citations else 0
            st.metric("Citations", citations_count)

    st.markdown("---")

    # ASC 606 Five-Step Analysis Summary
    st.subheader("📋 ASC 606 Five-Step Analysis Summary")

    steps = [
        ("Contract Identification", analysis_results.step1_contract_identification),
        ("Performance Obligations", analysis_results.step2_performance_obligations),
        ("Transaction Price", analysis_results.step3_transaction_price),
        ("Price Allocation", analysis_results.step4_price_allocation),
        ("Revenue Recognition", analysis_results.step5_revenue_recognition)
    ]

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
                file_name=f"{contract_data.analysis_title.replace(' ', '_')}_ASC606_Memo.txt",
                mime="text/plain"
            )
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
            st.write(f"**Total Characters**: {len(analysis_results.professional_memo) if analysis_results.professional_memo else 0:,}")
            st.write(f"**Analysis Depth**: {contract_data.analysis_depth}")
        with col2:
            st.write(f"**Output Format**: {contract_data.output_format}")
            st.write(f"**Include Citations**: {'Yes' if contract_data.include_citations else 'No'}")