"""
ASC 340-40 Contract Costs Analysis - Single Page Design V2
Generates comprehensive accounting policy memorandums for contract costs under ASC 340-40.
"""

import streamlit as st
import asyncio
import json
import time
from datetime import date
from typing import Optional, List
from pydantic import ValidationError

# Add root directory to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import ContractCostsData, ASC340Analysis
from core.analyzers import get_analyzer
from utils.document_extractor import DocumentExtractor
from utils.llm import create_docx_from_text
from utils.html_export import convert_memo_to_html

def render_single_page_form():
    """Render the complete single-page ASC 340-40 form"""
    st.title("ASC 340-40 Contract Costs Policy Analysis")
    st.markdown("Generate an accounting policy memorandum for contract costs under ASC 340-40.")
    
    # Section 1: Policy Information
    st.subheader(":material/contract: Background Information")
    
    col1, col2 = st.columns(2, gap="small")
    with col1:
        analysis_title = st.text_input(
            "Analysis Title *",
            placeholder='e.g., "Contract Costs Policy - Sales Commissions and Setup Costs"',
            help="Descriptive title for this contract costs accounting policy.")
        
        arrangement_description = st.text_area(
            "Contract Cost Summary (Optional)",
            placeholder='e.g., "This policy will govern sales commissions for new enterprise contracts and standard setup costs for customer onboarding."',
            height=80,
            help="Brief description of the business context and scope of this policy.")
    
    with col2:
        company_name = st.text_input(
            "Company Name *",
            placeholder='e.g., "TechCorp Solutions"',
            help="The legal entity name for this accounting policy.")
            
        policy_effective_date = st.date_input(
            "Policy Effective Date (Optional)",
            value=None,
            help="The date when this accounting policy becomes effective. If left blank, will default to generation date.")
    
    # Section 2: Document Upload (Now Required)
    st.subheader(":material/upload_file: Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload Contract Cost Documents for Analysis (Required) *",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="Upload the primary source document that governs the costs, such as a Sales Commission Plan or a standard SOW for fulfillment.")
    
    # Validation for required file upload
    file_uploaded = uploaded_files is not None and len(uploaded_files) > 0
    
    # Section 3: Cost Analysis Parameters
    st.subheader(":material/settings: Cost Analysis Parameters")
    
    # Primary Cost Categories (Required)
    col1, col2 = st.columns(2, gap="small")
    with col1:
        primary_cost_categories = st.multiselect(
            "Primary Cost Categories in Scope *",
            [
                "Sales Commissions (External)",
                "Sales Commissions (Internal Employee)",
                "Sales Bonuses & Incentives",
                "Contract Setup & Onboarding Costs",
                "Customer Migration & Data Conversion Costs",
                "Fulfillment-Related Third-Party Fees",
                "Other (please specify in description)"
            ],
            help="Select the primary categories of contract costs this policy will address.")

    with col2:
        standard_amortization_period = st.number_input(
            "Standard Amortization Period (months) *",
            min_value=1,
            max_value=120,
            value=36,
            help="Default amortization period for capitalized contract costs.")
    
    recovery_probable = st.toggle(
        "Is recovery of costs probable? *",
        value=True,
        help="Assessment of whether contract costs are expected to be recoverable.")
        
    practical_expedient = st.toggle(
        "Apply Practical Expedient (≤1 yr) *",
        value=False,
        help="Whether to apply the one-year practical expedient for immediate expensing.")
    
    # Validation logic
    required_fields_complete = (
        analysis_title and 
        company_name and 
        file_uploaded and 
        primary_cost_categories and 
        recovery_probable is not None and 
        standard_amortization_period and 
        practical_expedient is not None
    )
    
    st.divider()
    
    # Generate Memo Button
    generate_button = st.button(
        "📝 Generate Policy Memo",
        type="primary",
        use_container_width=True,
        disabled=not required_fields_complete
    )
    
    if not required_fields_complete and not file_uploaded:
        st.error("Please upload a policy document and complete all required fields (*) before generating the memo.")
    elif not required_fields_complete:
        st.error("Please complete all required fields (*) before generating the memo.")
    
    return {
        "analysis_title": analysis_title,
        "company_name": company_name,
        "policy_effective_date": policy_effective_date or date.today(),  # Default to today if None
        "primary_cost_categories": primary_cost_categories,
        "arrangement_description": arrangement_description,
        "uploaded_files": uploaded_files,
        "recovery_probable": recovery_probable,
        "standard_amortization_period": standard_amortization_period,
        "practical_expedient": practical_expedient,
        "generate_button": generate_button,
        "required_fields_complete": required_fields_complete
    }

def process_analysis(form_data: dict):
    """Process the ASC 340-40 analysis with form data"""
    
    # Show analysis summary
    st.subheader("📊 Analysis Summary")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Policy Title:** {form_data['analysis_title']}")
            st.write(f"**Company:** {form_data['company_name']}")
            st.write(f"**Effective Date:** {form_data['policy_effective_date']}")
        with col2:
            st.write(f"**Cost Categories:** {', '.join(form_data['primary_cost_categories'][:2])}{'...' if len(form_data['primary_cost_categories']) > 2 else ''}")
            st.write(f"**Amortization Period:** {form_data['standard_amortization_period']} months")
            st.write(f"**Recovery Probable:** {'Yes' if form_data['recovery_probable'] else 'No'}")
            st.write(f"**Practical Expedient:** {'Yes' if form_data['practical_expedient'] else 'No'}")
    
    # Process documents
    documents = []
    if form_data.get("uploaded_files"):
        doc_extractor = DocumentExtractor()
        for uploaded_file in form_data["uploaded_files"]:
            try:
                doc_result = doc_extractor.extract_text(uploaded_file)
                documents.append({
                    'filename': uploaded_file.name,
                    'text': doc_result.get('text', '') if isinstance(doc_result, dict) else str(doc_result)
                })
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                return
    
    # Create contract data object
    try:
        contract_data = ContractCostsData(
            analysis_title=form_data["analysis_title"],
            company_name=form_data["company_name"],
            policy_effective_date=form_data["policy_effective_date"],
            contract_types_in_scope=form_data["primary_cost_categories"],  # Using cost categories as scope
            cost_timing="All Periods",  # Fixed since removed from UI
            arrangement_description=form_data.get("arrangement_description"),
            cost_type="Incremental Cost of Obtaining",  # Default since simplified
            recovery_probable=form_data["recovery_probable"],
            standard_amortization_period=form_data["standard_amortization_period"],
            practical_expedient=form_data["practical_expedient"],
            contract_type_scope=form_data["primary_cost_categories"],
            memo_audience="Technical Accounting Team",  # Hard-coded as requested
            documents=documents,
            document_names=[doc['filename'] for doc in documents]
        )
    except ValidationError as e:
        st.error(f"Data validation error: {e}")
        return
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Run analysis
    with st.spinner("🔍 Analyzing contract costs policy..."):
        try:
            # Get analyzer
            analyzer = get_analyzer("ASC340")
            
            # Update progress
            status_text.text("Initializing ASC 340-40 analysis...")
            progress_bar.progress(20)
            
            # Run analysis
            result = asyncio.run(analyzer.analyze_contract_costs_policy(contract_data))
            
            progress_bar.progress(100)
            status_text.text("Analysis completed successfully!")
            
            time.sleep(1)  # Brief pause for user experience
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
            progress_bar.empty()
            status_text.empty()
            return
    
    # Display results
    if result and hasattr(result, 'professional_memo'):
        # Debug memo content
        memo_content = result.professional_memo
        if not memo_content or not memo_content.strip():
            st.error("Analysis completed but the generated memo is empty. Please check the documents and try again.")
            st.info("Debug info: Result object exists but professional_memo field is empty or None")
            return
            
        st.subheader("📝 Generated Policy Memorandum")
        
        # Display memo
        with st.container(border=True):
            st.markdown(memo_content)
        
        # Export options
        st.subheader("📥 Export Options")
        col1, col2 = st.columns(2)
        
        with col1:
            # HTML Export - only if memo has content
            try:
                html_content = convert_memo_to_html(memo_content)
                st.download_button(
                    label="📄 Download HTML",
                    data=html_content,
                    file_name=f"ASC340_Policy_{form_data['company_name'].replace(' ', '_')}.html",
                    mime="text/html"
                )
            except ValueError as e:
                st.error(f"HTML export failed: {str(e)}")
                st.info(f"Memo content length: {len(memo_content) if memo_content else 0} characters")
        
        with col2:
            # DOCX Export
            try:
                docx_content = create_docx_from_text(
                    result.professional_memo,
                    form_data["analysis_title"]
                )
                st.download_button(
                    label="📄 Download DOCX",
                    data=docx_content,
                    file_name=f"ASC340_Policy_{form_data['company_name'].replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"DOCX generation error: {str(e)}")
        
        # Analysis metadata
        with st.expander("📊 Analysis Details"):
            st.json({
                "Analysis Duration": f"{getattr(result, 'analysis_duration_seconds', 'N/A')} seconds",
                "Relevant Knowledge Chunks": getattr(result, 'relevant_chunks', 'N/A'),
                "Analysis Timestamp": getattr(result, 'analysis_timestamp', 'N/A'),
                "Analyzer Version": getattr(result, 'analyzer_version', 'ASC340_v1.0')
            })
    else:
        st.error("Analysis completed but no memo was generated. Please try again.")

def main():
    """Main function for ASC 340-40 Contract Costs analysis page"""
    
    # Render the form
    form_data = render_single_page_form()
    
    # Process analysis if button clicked
    if form_data["generate_button"] and form_data["required_fields_complete"]:
        st.markdown("---")
        process_analysis(form_data)

if __name__ == "__main__":
    main()