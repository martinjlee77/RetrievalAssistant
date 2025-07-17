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

# Fix Material Icons font loading issue
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    </style>
""", unsafe_allow_html=True)

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
                
                # Create contract data
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
                    additional_notes=additional_notes
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