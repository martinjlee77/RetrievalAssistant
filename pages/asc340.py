"""
ASC 340-40 Contract Costs Analysis Page
Following the proven ASC 606 interface pattern for consistency
"""
import asyncio
import streamlit as st
import time
from datetime import date
from typing import Optional, List
from pydantic import ValidationError
# Add root directory to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import ContractCostsData, ASC340Analysis
from utils.asc340_analyzer import ASC340Analyzer
from utils.document_extractor import DocumentExtractor
from utils.llm import create_debug_sidebar, create_docx_from_text


def format_dict_as_markdown(data: dict) -> str:
    """Converts a dictionary to a readable Markdown bulleted list."""
    markdown_str = ""
    for key, value in data.items():
        # Format the key (e.g., 'is_enforceable' -> 'Is Enforceable')
        formatted_key = key.replace('_', ' ').replace('-', ' ').title()
        markdown_str += f"- **{formatted_key}:** {value}\n"
    return markdown_str


def render_tab1_basic_information() -> dict:
    """Render Tab 1: Basic policy information and document upload"""
    st.subheader(":material/policy: Enter Policy Development Details")
    
    col1, col2 = st.columns(2, gap="small")
    with col1:
        analysis_title = st.text_input(
            "Policy Analysis Title *",
            placeholder="e.g., ASC 340-40 Implementation Policy",
            help="A unique name to identify this contract costs policy analysis.")
    with col2:
        company_name = st.text_input(
            "Company Name *",
            placeholder="e.g., XYZ Corporation",
            help="The name of the entity implementing the ASC 340-40 contract costs policy.")
    
    col3, col4 = st.columns(2, gap="small")
    with col3:
        contract_types_in_scope = st.multiselect(
            "Contract Types in Scope *", [
                "Software as a Service (SaaS) Agreements",
                "Software License Agreements", 
                "Professional Services Agreements",
                "Master Services Agreements (MSAs)",
                "Consulting Agreements",
                "Implementation Services",
                "Support and Maintenance Agreements",
                "Sales Commissions on Customer Contracts",
                "Other Contract-Related Costs"
            ],
            help="Select the types of customer contracts that will be subject to ASC 340-40 contract costs analysis.")
    with col4:
        cost_timing = st.selectbox(
            "Cost Timing Focus *",
            ["All Periods", "Current Period Only", "Future Periods Only"],
            help="Specify the temporal scope of costs to be addressed in the policy.")
    
    policy_effective_date = st.date_input(
        "Policy Effective Date *",
        help="The date when this ASC 340-40 contract costs policy becomes effective.")
    
    arrangement_description = st.text_area(
        "Policy Context Summary (Optional)",
        placeholder='e.g., "Implementation of ASC 340-40 policy for technology company with significant sales commissions and customer onboarding costs."',
        height=100,
        help="Provide context about the business and the types of contract costs that are typical for the organization.")
    
    st.subheader(":material/upload_file: Upload Reference Documents")
    uploaded_files = st.file_uploader(
        "Upload Sample Contracts or Cost Documentation (Optional)",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="Upload sample contracts, cost analysis, or other documents to provide context for policy development. These are used as reference examples, not for specific transaction analysis.")
    
    st.markdown("---")
    with st.container(border=True):
        st.info("Once the fields above are complete, continue to the **2️⃣ Analysis Context** tab.")
    
    return {
        "analysis_title": analysis_title,
        "company_name": company_name,
        "contract_types_in_scope": contract_types_in_scope,
        "cost_timing": cost_timing,
        "policy_effective_date": policy_effective_date,
        "arrangement_description": arrangement_description,
        "uploaded_files": uploaded_files
    }


def render_tab2_analysis_context() -> dict:
    """Render Tab 2: Analysis context and focus areas"""
    st.subheader(":material/tune: Policy Analysis Parameters")
    
    # Required fields section
    st.markdown("### Required Parameters")
    
    col1, col2 = st.columns(2, gap="small")
    with col1:
        cost_type = st.selectbox(
            "Cost Type *",
            ["Incremental Cost of Obtaining", "Cost to Fulfill a Contract", "Both Types"],
            index=0,
            help="Primary type of contract costs this policy will address.")
        
        recovery_probable = st.toggle(
            "Is recovery of costs probable? *",
            value=True,
            help="Assessment of whether contract costs are expected to be recoverable.")
    
    with col2:
        standard_amortization_period = st.number_input(
            "Standard Amortization Period (months) *",
            min_value=1,
            max_value=120,
            value=36,
            help="Default amortization period for capitalized contract costs.")
        
        practical_expedient = st.toggle(
            "Apply Practical Expedient (≤1 yr) *",
            value=False,
            help="Whether to apply the one-year practical expedient for immediate expensing.")
    
    # Optional fields section
    st.markdown("### Optional Parameters")
    
    col3, col4 = st.columns(2, gap="small")
    with col3:
        contract_type_scope = st.multiselect(
            "Contract Type Scope (Optional)",
            ["Software as a Service (SaaS)", "Professional Services", "Product Sales", "Maintenance & Support", "Implementation Services"],
            help="Specific contract types to focus on in the policy analysis.")
        
        memo_audience = st.selectbox(
            "Primary Memo Audience",
            ["Technical Accounting Team", "Audit File Documentation", "Management Review", "Board Presentation"],
            help="Select the primary audience for the accounting policy memorandum.")
    
    with col4:
        cost_timing_focus = st.selectbox(
            "Cost Timing Focus (Optional)",
            [None, "Pre-contract Costs", "Contract Execution Costs", "Post-delivery Costs"],
            format_func=lambda x: "All Periods" if x is None else x,
            help="Temporal focus for the cost analysis.")
        
        materiality_threshold = st.number_input(
            "Materiality Threshold (Optional)",
            min_value=0,
            value=None,
            format="%d",
            help="Enter materiality threshold in USD for policy application (leave blank if not applicable).")
    
    st.markdown("---")
    with st.container(border=True):
        st.info("Complete the required fields above, then continue to **3️⃣ Generate Analysis** to create your ASC 340-40 policy memorandum.")
    
    return {
        "cost_type": cost_type,
        "recovery_probable": recovery_probable,
        "standard_amortization_period": standard_amortization_period,
        "practical_expedient": practical_expedient,
        "contract_type_scope": contract_type_scope,
        "cost_timing_focus": cost_timing_focus,
        "memo_audience": memo_audience,
        "materiality_threshold": materiality_threshold
    }


def render_tab3_generate_analysis(tab1_data: dict, tab2_data: dict):
    """Render Tab 3: Generate ASC 340-40 policy analysis"""
    st.subheader(":material/analytics: Generate ASC 340-40 Contract Costs Policy")
    
    # Validation
    required_fields_tab1 = ["analysis_title", "company_name", "contract_types_in_scope", "cost_timing", "policy_effective_date"]
    required_fields_tab2 = ["cost_type", "recovery_probable", "standard_amortization_period", "practical_expedient"]
    
    missing_fields = []
    missing_fields.extend([field for field in required_fields_tab1 if not tab1_data.get(field)])
    missing_fields.extend([field for field in required_fields_tab2 if tab2_data.get(field) is None])
    
    if missing_fields:
        st.error(f"Please complete the following required fields in previous tabs: {', '.join(missing_fields)}")
        return
    
    # Display summary
    with st.expander("📋 Analysis Summary", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Policy Title:** {tab1_data['analysis_title']}")
            st.write(f"**Company:** {tab1_data['company_name']}")
            st.write(f"**Effective Date:** {tab1_data['policy_effective_date']}")
        with col2:
            st.write(f"**Cost Type:** {tab2_data['cost_type']}")
            st.write(f"**Amortization Period:** {tab2_data['standard_amortization_period']} months")
            st.write(f"**Recovery Probable:** {'Yes' if tab2_data['recovery_probable'] else 'No'}")
            st.write(f"**Practical Expedient:** {'Yes' if tab2_data['practical_expedient'] else 'No'}")
    
    # Analysis button
    if st.button("🚀 Generate ASC 340-40 Policy Analysis", type="primary", use_container_width=True):
        generate_asc340_analysis(tab1_data, tab2_data)


def generate_asc340_analysis(tab1_data: dict, tab2_data: dict):
    """Generate the ASC 340-40 contract costs policy analysis"""
    
    # Show progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Create contract costs data object
        status_text.text("🔧 Preparing analysis data...")
        progress_bar.progress(10)
        
        # Extract document text if uploaded
        documents = []
        if tab1_data.get("uploaded_files"):
            doc_extractor = DocumentExtractor()
            for uploaded_file in tab1_data["uploaded_files"]:
                try:
                    doc_result = doc_extractor.extract_text(uploaded_file)
                    documents.append({
                        'filename': uploaded_file.name,
                        'text': doc_result.get('text', '') if isinstance(doc_result, dict) else str(doc_result)
                    })
                except Exception as e:
                    st.warning(f"Could not extract text from {uploaded_file.name}: {str(e)}")
        
        # Create ContractCostsData object
        contract_costs_data = ContractCostsData(
            analysis_title=tab1_data["analysis_title"],
            company_name=tab1_data["company_name"],
            policy_effective_date=tab1_data["policy_effective_date"],
            contract_types_in_scope=tab1_data["contract_types_in_scope"],
            cost_timing=tab1_data["cost_timing"],
            arrangement_description=tab1_data.get("arrangement_description"),
            cost_type=tab2_data["cost_type"],
            recovery_probable=tab2_data["recovery_probable"],
            standard_amortization_period=tab2_data["standard_amortization_period"],
            practical_expedient=tab2_data["practical_expedient"],
            contract_type_scope=tab2_data.get("contract_type_scope"),
            cost_timing_focus=tab2_data.get("cost_timing_focus"),
            memo_audience=tab2_data["memo_audience"],
            materiality_threshold=tab2_data.get("materiality_threshold"),
            documents=documents,
            document_names=[f.name for f in tab1_data.get("uploaded_files", [])]
        )
        
        # Initialize analyzer
        status_text.text("🤖 Initializing ASC 340-40 analyzer...")
        progress_bar.progress(20)
        
        analyzer = ASC340Analyzer()
        
        # Run analysis
        status_text.text("📊 Analyzing contract costs policy (4 steps)...")
        progress_bar.progress(30)
        
        start_time = time.time()
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            analysis_result = loop.run_until_complete(
                analyzer.analyze_contract_costs_policy(contract_costs_data)
            )
        finally:
            loop.close()
        
        analysis_duration = int(time.time() - start_time)
        
        # Generate memo
        status_text.text("📝 Generating policy memorandum...")
        progress_bar.progress(80)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            professional_memo = loop.run_until_complete(
                analyzer.generate_full_memo(analysis_result)
            )
            analysis_result.professional_memo = professional_memo
        finally:
            loop.close()
        
        # Complete
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        # Store in session state
        st.session_state['asc340_analysis'] = analysis_result
        st.session_state['asc340_analysis_duration'] = analysis_duration
        
        time.sleep(1)  # Brief pause to show completion
        progress_bar.empty()
        status_text.empty()
        
        # Display results
        display_analysis_results(analysis_result, analysis_duration)
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Analysis failed: {str(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            st.error(f"Debug info: {traceback.format_exc()}")


def display_analysis_results(analysis: ASC340Analysis, duration: int):
    """Display the analysis results"""
    
    st.success(f"🎉 ASC 340-40 Contract Costs Policy Analysis Complete! (Analysis took {duration} seconds)")
    
    # Get analysis summary
    analyzer = ASC340Analyzer()
    summary = analyzer.get_analysis_summary(analysis)
    
    # Display summary
    with st.expander("📈 Analysis Summary", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Steps Completed", f"{summary['total_steps_completed']}/4")
            st.write(f"**Scope Determination:** {summary['scope_determination']}")
        with col2:
            st.write(f"**Policy Framework:** {summary['policy_framework']}")
            st.write(f"**Cost Categories:** {', '.join(summary['cost_categories'])}")
    
    # Display professional memo
    st.subheader("📋 ASC 340-40 Accounting Policy Memorandum")
    
    # Create tabs for different views
    memo_tab1, memo_tab2, memo_tab3 = st.tabs(["📖 Full Memorandum", "🔍 Step Details", "⬇️ Export Options"])
    
    with memo_tab1:
        if analysis.professional_memo:
            st.markdown(analysis.professional_memo)
        else:
            st.warning("Professional memorandum generation failed or is empty.")
    
    with memo_tab2:
        display_step_details(analysis)
    
    with memo_tab3:
        display_export_options(analysis)


def display_step_details(analysis: ASC340Analysis):
    """Display detailed step-by-step analysis results"""
    
    steps_data = [
        ("Step 1: Scope Assessment", analysis.step1_scope_assessment),
        ("Step 2: Cost Classification", analysis.step2_cost_classification),
        ("Step 3: Measurement & Amortization Policy", analysis.step3_measurement_policy),
        ("Step 4: Illustrative Financial Impact", analysis.step4_illustrative_impact)
    ]
    
    for step_name, step_data in steps_data:
        with st.expander(f"📋 {step_name}", expanded=False):
            if step_data and not step_data.get("error"):
                if isinstance(step_data, dict):
                    # Display formatted analysis data
                    st.json(step_data)
                else:
                    st.write(str(step_data))
            else:
                st.error(f"{step_name} analysis failed: {step_data.get('error', 'Unknown error')}")


def display_export_options(analysis: ASC340Analysis):
    """Display export options for the analysis"""
    
    st.subheader("Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export as DOCX", use_container_width=True):
            if analysis.professional_memo:
                try:
                    docx_file = create_docx_from_text(
                        analysis.professional_memo,
                        title=f"ASC_340-40_Policy_{analysis.contract_data.company_name}_{analysis.contract_data.analysis_title}"
                    )
                    
                    with open(docx_file, "rb") as file:
                        st.download_button(
                            label="⬇️ Download DOCX File",
                            data=file.read(),
                            file_name=f"ASC_340-40_Policy_{analysis.contract_data.company_name}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"DOCX export failed: {str(e)}")
            else:
                st.warning("No memo content available for export.")
    
    with col2:
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            if analysis.professional_memo:
                st.text_area("Copy the text below:", analysis.professional_memo, height=200)
            else:
                st.warning("No memo content available to copy.")


def main():
    """Main ASC 340-40 analysis page"""
    
    st.title("🏢 ASC 340-40 Contract Costs")
    st.markdown("Generate comprehensive accounting policy memorandums for contract costs under ASC 340-40")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "1️⃣ Basic Information", 
        "2️⃣ Analysis Context", 
        "3️⃣ Generate Analysis"
    ])
    
    with tab1:
        tab1_data = render_tab1_basic_information()
    
    with tab2:
        tab2_data = render_tab2_analysis_context()
    
    with tab3:
        render_tab3_generate_analysis(tab1_data, tab2_data)
    
    # Debug sidebar (only in development)
    create_debug_sidebar()


if __name__ == "__main__":
    main()