import streamlit as st
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Technical Accounting Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'contract_data' not in st.session_state:
    st.session_state.contract_data = None

class ContractAnalyzerApp:
    def __init__(self):
        self.available_standards = {
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
    
    def run(self):
        st.title("📊 Technical Accounting Analyzer")
        st.markdown("**Professional contract analysis under US GAAP accounting standards**")
        
        # Sidebar for standard selection
        self.render_sidebar()
        
        # Main content area
        if st.session_state.analysis_results is None:
            self.render_upload_interface()
        else:
            self.render_analysis_results()
    
    def render_sidebar(self):
        st.sidebar.header("📋 Available Standards")
        
        for standard_code, standard_info in self.available_standards.items():
            with st.sidebar.expander(f"{standard_code}: {standard_info['name']}", expanded=(standard_code == 'ASC 606')):
                st.write(f"**Description:** {standard_info['description']}")
                
                if standard_info['status'] == 'available':
                    st.success("✅ Available")
                else:
                    st.info("🔄 Coming Soon")
        
        st.sidebar.divider()
        
        # System info
        st.sidebar.subheader("ℹ️ System Information")
        st.sidebar.write("**Version:** 1.0.0")
        st.sidebar.write("**Last Updated:** July 2025")
        st.sidebar.write("**Standards Supported:** 1 of 4")
    
    def render_upload_interface(self):
        st.header("📄 Contract Upload & Analysis Setup")
        
        # Standard selection
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("1. Select Accounting Standard")
            
            # Filter available standards
            available_options = {k: v for k, v in self.available_standards.items() if v['status'] == 'available'}
            
            selected_standard = st.selectbox(
                "Choose standard for analysis:",
                options=list(available_options.keys()),
                format_func=lambda x: f"{x}: {available_options[x]['name']}",
                help="Select the accounting standard applicable to your contract"
            )
            
            if selected_standard:
                st.info(f"**Selected:** {available_options[selected_standard]['description']}")
        
        with col2:
            st.subheader("2. Contract Information")
            
            # Required contract details
            analysis_title = st.text_input(
                "Analysis Title / Contract ID *",
                placeholder="e.g., Q4 Project Phoenix SOW, ABC Corp Master Agreement",
                help="A unique, user-friendly name for this specific analysis. This allows you and the system to easily track and reference this specific contract memo."
            )
            
            customer_name = st.text_input(
                "Customer Name *",
                placeholder="e.g., ABC Corporation",
                help="The legal name of the customer. This is the most basic identifier for the counterparty and will be used throughout the memo."
            )
            
            effective_date = st.date_input(
                "Effective Date *",
                help="The date the contract is legally in effect. This establishes the 'contract inception' date for the analysis, which is the anchor point for all ASC 606 assessments."
            )
            
            col2a, col2b = st.columns(2)
            
            with col2a:
                contract_start = st.date_input(
                    "Contract Start Date *",
                    help="The beginning of the period over which goods or services are expected to be delivered. This directly informs the revenue recognition period, especially for services recognized 'over time.'"
                )
            
            with col2b:
                contract_end = st.date_input(
                    "Contract End Date *",
                    help="The end of the period over which goods or services are expected to be delivered. This directly informs the revenue recognition period, especially for services recognized 'over time.'"
                )
            
            col2c, col2d = st.columns(2)
            
            with col2c:
                transaction_price = st.number_input(
                    "Total Transaction Price *",
                    min_value=0.0,
                    format="%.2f",
                    help="The total fixed value of the contract. Leave as 0 if the price is entirely variable. This gives the LLM a key financial data point to anchor its analysis for Steps 3 (Determine Price) and 4 (Allocate Price)."
                )
            
            with col2d:
                currency = st.selectbox(
                    "Currency *",
                    options=["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "Other"],
                    help="The currency of the contract. This is critical context for the transaction price and any financial figures mentioned in the memo."
                )
            
            arrangement_description = st.text_area(
                "Brief Description of the Arrangement *",
                placeholder="e.g., A three-year subscription to our SaaS platform with one-time professional services for implementation.",
                height=100,
                help="A one- or two-sentence, plain-English summary of the deal. This is a powerful input that gives the LLM immediate, high-level context of the business purpose, helping it better interpret the legal language and structure of the contract."
            )
        
        # Contract upload section
        st.subheader("3. Upload Contract Document")
        
        uploaded_file = st.file_uploader(
            "Choose contract file",
            type=['pdf', 'docx', 'doc'],
            help="Upload your contract in PDF or Word format"
        )
        
        if uploaded_file is not None:
            # File details
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.write(f"**File size:** {uploaded_file.size:,} bytes")
            st.write(f"**File type:** {uploaded_file.type}")
        
        # Analysis options
        st.subheader("4. Analysis Options")
        
        col3, col4 = st.columns(2)
        
        with col3:
            analysis_depth = st.selectbox(
                "Analysis Depth",
                options=["Standard Analysis", "Detailed Analysis", "Comprehensive Analysis"],
                help="Select the level of detail for the analysis"
            )
            
            include_citations = st.checkbox(
                "Include Citations",
                value=True,
                help="Include references to specific accounting guidance"
            )
        
        with col4:
            output_format = st.selectbox(
                "Output Format",
                options=["Professional Memo", "Technical Analysis", "Executive Summary"],
                help="Choose the format for the analysis output"
            )
            
            include_examples = st.checkbox(
                "Include Examples",
                value=True,
                help="Include relevant examples from accounting guidance"
            )
        
        # Additional notes
        st.subheader("5. Additional Instructions (Optional)")
        
        additional_notes = st.text_area(
            "Special considerations or focus areas",
            placeholder="e.g., Focus on performance obligation identification, complex variable consideration terms, etc.",
            height=100,
            help="Enter any specific areas you want the analysis to focus on"
        )
        
        # Analysis button
        st.divider()
        
        if st.button("🔍 Analyze Contract", type="primary", use_container_width=True):
            # Validate inputs
            if not uploaded_file:
                st.error("Please upload a contract document")
                return
            
            if not analysis_title.strip():
                st.error("Please enter an analysis title/contract ID")
                return
            
            if not customer_name.strip():
                st.error("Please enter the customer name")
                return
            
            if not arrangement_description.strip():
                st.error("Please enter a brief description of the arrangement")
                return
            
            # Store contract data
            st.session_state.contract_data = {
                'standard': selected_standard,
                'analysis_title': analysis_title,
                'customer_name': customer_name,
                'effective_date': effective_date.isoformat(),
                'contract_start': contract_start.isoformat(),
                'contract_end': contract_end.isoformat(),
                'transaction_price': transaction_price,
                'currency': currency,
                'arrangement_description': arrangement_description,
                'analysis_depth': analysis_depth,
                'include_citations': include_citations,
                'output_format': output_format,
                'include_examples': include_examples,
                'additional_notes': additional_notes,
                'uploaded_file': uploaded_file.name,
                'timestamp': datetime.now().isoformat()
            }
            
            # Process the contract
            self.process_contract(uploaded_file)
    
    def process_contract(self, uploaded_file):
        """Process the uploaded contract"""
        with st.spinner("Processing contract..."):
            # Placeholder for contract processing
            # This will integrate with the actual analysis engine
            
            # Simulate processing
            import time
            time.sleep(2)
            
            # Mock analysis results
            st.session_state.analysis_results = {
                'success': True,
                'analysis_type': st.session_state.contract_data['standard'],
                'processing_time': 2.5,
                'sections_analyzed': 5,
                'issues_identified': 3,
                'recommendations': 7
            }
            
            st.success("✅ Contract analysis completed!")
            st.rerun()
    
    def render_analysis_results(self):
        """Display analysis results"""
        st.header("📊 Analysis Results")
        
        contract_data = st.session_state.contract_data
        results = st.session_state.analysis_results
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Analysis Type", contract_data['standard'])
        
        with col2:
            st.metric("Processing Time", f"{results['processing_time']:.1f}s")
        
        with col3:
            st.metric("Sections Analyzed", results['sections_analyzed'])
        
        with col4:
            st.metric("Issues Found", results['issues_identified'])
        
        # Contract details
        st.subheader("Contract Information")
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write(f"**Analysis Title:** {contract_data['analysis_title']}")
            st.write(f"**Customer:** {contract_data['customer_name']}")
            st.write(f"**Effective Date:** {contract_data['effective_date']}")
            st.write(f"**Contract Period:** {contract_data['contract_start']} to {contract_data['contract_end']}")
        
        with info_col2:
            st.write(f"**Transaction Price:** {contract_data['currency']} {contract_data['transaction_price']:,.2f}")
            st.write(f"**Description:** {contract_data['arrangement_description']}")
            st.write(f"**File:** {contract_data['uploaded_file']}")
        
        # Placeholder for actual analysis content
        st.subheader("Analysis Output")
        st.info("🔄 Analysis engine integration coming soon...")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Generate Report", use_container_width=True):
                st.info("Report generation feature coming soon")
        
        with col2:
            if st.button("💾 Save Analysis", use_container_width=True):
                st.info("Save functionality coming soon")
        
        with col3:
            if st.button("🔄 Analyze Another Contract", use_container_width=True):
                st.session_state.analysis_results = None
                st.session_state.contract_data = None
                st.rerun()

if __name__ == "__main__":
    app = ContractAnalyzerApp()
    app.run()