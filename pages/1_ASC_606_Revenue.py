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
from core.ui_helpers import (
    load_custom_css, 
    render_branded_header, 
    render_standard_sidebar,
    render_analysis_metrics,
    render_step_analysis,
    render_professional_memo
)
from document_extractor import DocumentExtractor

# Page configuration
st.set_page_config(
    page_title="ASC 606 Revenue Analysis | Controller.cpa",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom styling
load_custom_css()

# Simple navigation with sidebar
with st.sidebar:
    st.markdown("### Navigation")
    
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("Home.py")
    
    if st.button("📈 ASC 606 Revenue", use_container_width=True, type="primary"):
        pass  # Already on this page
    
    if st.button("🏢 ASC 842 Leases", use_container_width=True):
        st.switch_page("pages/2_ASC_842_Leases.py")

# Material Icons font is now loaded in load_custom_css()

# Available standards configuration
AVAILABLE_STANDARDS = {
    'ASC 606': {
        'name': 'Revenue from Contracts with Customers',
        'description': 'Analyze revenue recognition under the 5-step model',
        'status': 'available'
    },
    'ASC 842': {
        'name': 'Leases',
        'description': 'Analyze lease classification and measurement',
        'status': 'coming_soon'
    },
    'ASC 815': {
        'name': 'Derivatives and Hedging',
        'description': 'Analyze derivative instruments and hedging activities',
        'status': 'coming_soon'
    },
    'ASC 326': {
        'name': 'Credit Losses',
        'description': 'Analyze current expected credit losses',
        'status': 'coming_soon'
    }
}

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

# Clean header (matching your design preference)
st.markdown("""
<div style="text-align: center; padding: 2rem 0 1rem 0;">
    <h1 style="font-size: 2.2rem; color: #0A2B4C; margin-bottom: 0.5rem; font-family: 'Poppins', sans-serif;">ASC 606 Revenue Recognition Analysis</h1>
    <p style="font-size: 1rem; color: #666; margin-bottom: 1rem; font-weight: 400;">AI-powered contract analysis using authoritative FASB guidance and Big 4 interpretations</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Main application logic
if st.session_state.analysis_results is None:
    # Render upload interface
    st.header("Start New ASC 606 Analysis")
    st.write("Complete the required fields and upload your document, then click Analyze.")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.subheader("📋 Required Information")
        
        analysis_title = st.text_input(
            "Analysis Title / Contract ID *",
            placeholder="e.g., Q4 Project Phoenix SOW",
            help="A unique name to identify this analysis"
        )
        
        customer_name = st.text_input(
            "Customer Name *",
            placeholder="e.g., ABC Corporation"
        )
        
        arrangement_description = st.text_area(
            "Arrangement Description *",
            placeholder="e.g., Three-year SaaS subscription with implementation services",
            height=100,
            help="Brief description of the contractual arrangement"
        )
        
        # Date inputs
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            contract_start = st.date_input("Contract Start Date *")
        with sub_col2:
            contract_end = st.date_input("Contract End Date *")
        
        currency = st.selectbox(
            "Currency *",
            ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"],
            help="Primary currency for the contract"
        )
        
        # File upload
        st.subheader("📄 Document Upload")
        uploaded_files = st.file_uploader(
            "Upload Documents",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Upload contracts, amendments, invoices, or related documents (max 5 files)"
        )
    
    with col2:
        st.subheader("⚙️ Analysis Configuration")
        
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
        
        # Add preliminary assessment section
        st.subheader("📋 Preliminary Assessment")
        st.write("Provide your initial analysis - the AI will verify against the contract text")
        
        # Contract modification section
        st.markdown("**Contract Nature**")
        is_modification = st.checkbox(
            "Is this a contract modification or amendment?",
            value=st.session_state.get('is_modification', False),
            help="Check if this contract modifies or amends an existing agreement",
            key="is_modification"
        )
        
        # Performance obligations section
        st.markdown("**Performance Obligations**")
        st.write("Identify the distinct performance obligations in this contract:")
        
        # Initialize performance obligations in session state if not exists
        if 'performance_obligations' not in st.session_state:
            st.session_state.performance_obligations = []
        
        # Add new performance obligation
        with st.expander("Add Performance Obligation"):
            po_col1, po_col2 = st.columns(2)
            new_po_name = po_col1.text_input("Performance Obligation Name", placeholder="e.g., Software License")
            new_po_type = po_col2.selectbox("Type", ["License", "Service", "Good", "Other"])
            
            po_col3, po_col4 = st.columns(2)
            new_po_timing = po_col3.selectbox("Recognition Timing", ["Point in Time", "Over Time"])
            new_po_ssp = po_col4.number_input("Standalone Selling Price", min_value=0.0, format="%.2f")
            
            if st.button("Add Performance Obligation"):
                if new_po_name and new_po_ssp > 0:
                    st.session_state.performance_obligations.append({
                        'name': new_po_name,
                        'type': new_po_type,
                        'timing': new_po_timing,
                        'ssp': new_po_ssp
                    })
                    st.success(f"Added: {new_po_name}")
                    st.rerun()
        
        # Display current performance obligations
        if st.session_state.performance_obligations:
            st.write("**Current Performance Obligations:**")
            for i, po in enumerate(st.session_state.performance_obligations):
                po_display_col1, po_display_col2 = st.columns([4, 1])
                po_display_col1.write(f"**{po['name']}** ({po['type']}) - {po['timing']} - {currency} {po['ssp']:,.2f}")
                if po_display_col2.button("Remove", key=f"remove_po_{i}"):
                    st.session_state.performance_obligations.pop(i)
                    st.rerun()
        
        # Transaction price section
        st.markdown("**Transaction Price**")
        price_col1, price_col2 = st.columns(2)
        
        fixed_consideration = price_col1.number_input(
            "Fixed Consideration",
            value=st.session_state.get('fixed_consideration', 0.0),
            min_value=0.0,
            format="%.2f",
            help="The guaranteed, fixed amount in the contract",
            key="fixed_consideration"
        )
        
        has_variable = price_col2.checkbox(
            "Has Variable Consideration?",
            value=st.session_state.get('has_variable_consideration', False),
            key="has_variable_consideration"
        )
        
        if has_variable:
            var_col1, var_col2 = st.columns(2)
            variable_type = var_col1.selectbox(
                "Variable Consideration Type",
                ["Performance Bonus", "Penalty", "Usage-based", "Other"],
                key="variable_type"
            )
            variable_amount = var_col2.number_input(
                "Estimated Variable Amount",
                value=st.session_state.get('variable_amount', 0.0),
                min_value=0.0,
                format="%.2f",
                key="variable_amount"
            )
        
        # Additional elements
        st.markdown("**Additional Elements**")
        add_col1, add_col2 = st.columns(2)
        
        financing_component = add_col1.checkbox(
            "Significant Financing Component?",
            value=st.session_state.get('financing_component', False),
            key="financing_component"
        )
        
        material_rights = add_col2.checkbox(
            "Material Rights Present?",
            value=st.session_state.get('material_rights', False),
            key="material_rights"
        )
        
        customer_options = add_col1.checkbox(
            "Customer Options for Additional Goods/Services?",
            value=st.session_state.get('customer_options', False),
            key="customer_options"
        )
    
    # Full-width analyze button
    st.markdown("---")
    
    if st.button("🔍 Analyze Contract", use_container_width=True, type="primary"):
        # Validation
        if not analysis_title:
            st.error("Please provide an analysis title")
            st.stop()
        
        if not customer_name:
            st.error("Please provide a customer name")
            st.stop()
        
        if not arrangement_description:
            st.error("Please provide an arrangement description")
            st.stop()
        
        if not uploaded_files:
            st.error("Please upload at least one document")
            st.stop()
        
        if len(uploaded_files) > 5:
            st.error("Please upload a maximum of 5 files")
            st.stop()
        
        # Process the analysis
        with st.spinner("🔍 Analyzing contract..."):
            try:
                # Extract text from uploaded files
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
                
                # Combine all extracted text
                combined_text = "\n".join(all_extracted_text)
                
                # Process performance obligations
                performance_obligations_data = []
                for po in st.session_state.performance_obligations:
                    performance_obligations_data.append({
                        'name': po['name'],
                        'type': po['type'],
                        'timing': po['timing'],
                        'ssp': po['ssp']
                    })
                
                # Process variable consideration
                variable_consideration_data = None
                if has_variable:
                    variable_consideration_data = {
                        'type': variable_type,
                        'estimated_amount': variable_amount
                    }
                
                # Create contract data with preliminary assessment
                contract_data = ContractData(
                    analysis_title=analysis_title,
                    customer_name=customer_name,
                    arrangement_description=arrangement_description,
                    contract_start=contract_start,
                    contract_end=contract_end,
                    currency=currency,
                    uploaded_file_name=", ".join([f.name for f in uploaded_files]),
                    analysis_depth=analysis_depth,
                    output_format=output_format,
                    include_citations=include_citations,
                    include_examples=include_examples,
                    additional_notes=additional_notes,
                    # Preliminary assessment fields
                    is_modification=is_modification,
                    performance_obligations=performance_obligations_data,
                    fixed_consideration=fixed_consideration,
                    variable_consideration=variable_consideration_data,
                    financing_component=financing_component,
                    material_rights=material_rights,
                    customer_options=customer_options
                )
                
                # Perform analysis
                analysis_results = analyzer.analyze_contract(combined_text, contract_data)
                
                # Store results in session state
                st.session_state.analysis_results = analysis_results
                st.session_state.contract_data = contract_data
                
                st.success("✅ Analysis complete!")
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
    
    # Render analysis metrics
    render_analysis_metrics(analysis_results.__dict__)
    
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
    
    for step_name, step_data in steps:
        render_step_analysis(step_name, step_data)
    
    # Professional Memo
    st.markdown("---")
    render_professional_memo(analysis_results.professional_memo)
    
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