"""
ASC 842 Leases - Classification, Measurement, and Journal Entry Suite
Lessee Accounting Only - Module 1 Implementation
"""

import streamlit as st
from datetime import datetime
from typing import Optional

from core.ui_helpers import load_custom_css
from core.models import ASC842Analysis
from core.analyzers import get_analyzer
from utils.document_extractor import DocumentExtractor
from utils.html_export import convert_memo_to_html
from utils.llm import generate_docx_memo

def show_asc842_page():
    """ASC 842 Lease Accounting - Module 1: Classification Tool"""
    
    # Load styling 
    load_custom_css()
    
    # Page header
    st.title("🏢 ASC 842 Lease Classification Tool")
    st.markdown("### Professional Lease Analysis - Operating vs Finance")
    
    # Scope notice
    st.info("""
    **📋 Classification Analysis Scope**
    
    This tool analyzes lease contracts under ASC 842 to determine classification:
    - **Operating Lease** vs **Finance Lease**
    - Applies all 5 classification tests systematically
    - Generates professional memorandums with ASC 842 citations
    - Lessee accounting only
    """)
    
    # Main interface
    st.markdown("---")
    
    # File upload section
    st.markdown("### 📄 Upload Lease Contract")
    uploaded_file = st.file_uploader(
        "Upload your lease agreement for analysis",
        type=['pdf', 'docx', 'txt'],
        help="Supported formats: PDF, DOCX, TXT"
    )
    
    contract_text = ""
    if uploaded_file:
        try:
            extractor = DocumentExtractor()
            extraction_result = extractor.extract_text(uploaded_file)
            contract_text = extraction_result.get('text', '') if extraction_result else ''
            
            if contract_text.strip():
                st.success(f"✅ Contract extracted: {len(contract_text):,} characters")
                with st.expander("📋 Preview Contract Text"):
                    st.text(contract_text[:2000] + "..." if len(contract_text) > 2000 else contract_text)
            else:
                st.error("❌ No text could be extracted from the file")
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
    
    # Lease data input section
    st.markdown("### 📊 Lease Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        asset_type = st.text_input(
            "Asset Type",
            placeholder="e.g., Office Building, Equipment, Vehicles",
            help="Describe the underlying asset being leased"
        )
        
        lease_term_months = st.number_input(
            "Lease Term (months)",
            min_value=1,
            max_value=1200,
            value=36,
            help="Total noncancellable lease term including renewal options reasonably certain to exercise"
        )
        
        annual_lease_payment = st.number_input(
            "Annual Lease Payment ($)",
            min_value=0.01,
            value=120000.00,
            format="%.2f",
            help="Annual fixed lease payments (exclude variable payments)"
        )
        
        discount_rate = st.number_input(
            "Discount Rate (%)",
            min_value=0.01,
            max_value=50.0,
            value=6.0,
            format="%.2f",
            help="Rate implicit in lease or incremental borrowing rate"
        )
    
    with col2:
        asset_fair_value = st.number_input(
            "Asset Fair Value ($)",
            min_value=0.01,
            value=500000.00,
            format="%.2f",
            help="Fair value of underlying asset at commencement (if known)"
        )
        
        asset_economic_life_years = st.number_input(
            "Asset Economic Life (years)",
            min_value=1,
            max_value=100,
            value=10,
            help="Total economic life of the underlying asset"
        )
        
        purchase_option_exists = st.selectbox(
            "Purchase Option",
            ["No", "Yes - Reasonably Certain to Exercise", "Yes - Not Reasonably Certain"],
            help="Does lease include purchase option lessee is reasonably certain to exercise?"
        )
        
        ownership_transfer = st.selectbox(
            "Ownership Transfer",
            ["No", "Yes"],
            help="Does lease transfer ownership to lessee by end of lease term?"
        )
    
    # Advanced options
    with st.expander("🔧 Advanced Options"):
        alternative_use_limitation = st.selectbox(
            "Alternative Use Limitation",
            ["Unknown/Not Applicable", "No Alternative Use", "Has Alternative Use"],
            help="Is the asset so specialized it has no alternative use to lessor?"
        )
        
        variable_payments = st.number_input(
            "Variable Payments (Annual)",
            min_value=0.0,
            value=0.0,
            format="%.2f",
            help="Estimated annual variable payments (optional)"
        )
    
    # Analysis button
    st.markdown("---")
    
    if st.button("🚀 Analyze Lease Classification", type="primary", disabled=not (contract_text.strip() and asset_type.strip())):
        if not contract_text.strip():
            st.error("Please upload a lease contract first")
        elif not asset_type.strip():
            st.error("Please specify the asset type")
        else:
            # Perform analysis
            with st.spinner("Analyzing lease classification using ASC 842 guidance..."):
                try:
                    # Create lease data dictionary for now
                    lease_data = {
                        "asset_type": asset_type,
                        "lease_term_months": lease_term_months,
                        "annual_lease_payment": annual_lease_payment,
                        "discount_rate": discount_rate,
                        "asset_fair_value": asset_fair_value,
                        "asset_economic_life_years": asset_economic_life_years,
                        "purchase_option_exists": purchase_option_exists == "Yes - Reasonably Certain to Exercise",
                        "ownership_transfer": ownership_transfer == "Yes"
                    }
                    
                    # Get ASC 842 analyzer
                    analyzer = get_analyzer("ASC 842")
                    
                    # Perform classification analysis
                    analysis = analyzer.analyze_lease_classification(
                        contract_text=contract_text,
                        lease_data=lease_data
                    )
                    
                    # Store in session state
                    st.session_state.asc842_analysis = analysis
                    st.session_state.asc842_lease_data = lease_data
                    st.session_state.asc842_contract_text = contract_text
                    
                    st.success("✅ Classification analysis completed!")
                    
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
                    st.exception(e)
    
    # Display results if available
    if hasattr(st.session_state, 'asc842_analysis'):
        st.markdown("---")
        st.markdown("### 📋 Classification Analysis Results")
        
        analysis = st.session_state.asc842_analysis
        lease_data = st.session_state.asc842_lease_data
        
        # Show classification result
        classification_text = analysis.lease_classification
        
        # Display analysis
        st.markdown("#### 🎯 Classification Analysis")
        st.markdown(classification_text)
        
        # Generate memo section
        st.markdown("---")
        st.markdown("### 📝 Professional Memorandum")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate Memorandum", type="secondary"):
                with st.spinner("Generating professional memorandum..."):
                    try:
                        analyzer = get_analyzer("ASC 842")
                        memo = analyzer.generate_classification_memo(analysis, lease_data)
                        st.session_state.asc842_memo = memo
                        st.success("✅ Memorandum generated!")
                    except Exception as e:
                        st.error(f"❌ Memo generation failed: {str(e)}")
        
        with col2:
            if hasattr(st.session_state, 'asc842_memo'):
                # Download buttons
                memo = st.session_state.asc842_memo
                
                # HTML download
                html_content = convert_memo_to_html(memo)
                st.download_button(
                    label="📄 Download HTML",
                    data=html_content,
                    file_name=f"ASC842_Classification_Memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html"
                )
                
                # DOCX download
                try:
                    docx_buffer = generate_docx_memo(memo)
                    st.download_button(
                        label="📄 Download DOCX",
                        data=docx_buffer.getvalue(),
                        file_name=f"ASC842_Classification_Memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"DOCX generation error: {str(e)}")
        
        # Display memo if available
        if hasattr(st.session_state, 'asc842_memo'):
            st.markdown("#### 📋 Memorandum Preview")
            memo = st.session_state.asc842_memo
            
            # Convert to HTML for better display
            try:
                html_preview = convert_memo_to_html(memo)
                st.components.v1.html(html_preview, height=800, scrolling=True)
            except:
                # Fallback to markdown
                st.markdown(memo)
    
    # Module 2: Calculator Section
    if hasattr(st.session_state, 'asc842_analysis'):
        st.markdown("---")
        st.markdown("### 🧮 Module 2: Measurement Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Calculate Lease Measurement", type="secondary"):
                with st.spinner("Calculating initial and subsequent measurement..."):
                    try:
                        analyzer = get_analyzer("ASC 842")
                        classification_result = st.session_state.asc842_analysis.lease_classification
                        measurement_results = analyzer.calculate_lease_measurement(
                            lease_data=st.session_state.asc842_lease_data,
                            classification_result=classification_result
                        )
                        st.session_state.asc842_measurement = measurement_results
                        st.success("✅ Measurement calculations completed!")
                    except Exception as e:
                        st.error(f"❌ Calculation failed: {str(e)}")
        
        # Display measurement results
        if hasattr(st.session_state, 'asc842_measurement'):
            with st.expander("📊 View Measurement Calculations"):
                st.markdown(st.session_state.asc842_measurement)
    
    # Module 3: Journal Generator Section  
    if hasattr(st.session_state, 'asc842_measurement'):
        st.markdown("---")
        st.markdown("### 📝 Module 3: Journal Entry Generator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate Journal Entries", type="secondary"):
                with st.spinner("Generating accounting journal entries..."):
                    try:
                        analyzer = get_analyzer("ASC 842")
                        journal_entries = analyzer.generate_journal_entries(
                            measurement_results=st.session_state.asc842_measurement,
                            lease_data=st.session_state.asc842_lease_data
                        )
                        st.session_state.asc842_journals = journal_entries
                        st.success("✅ Journal entries generated!")
                    except Exception as e:
                        st.error(f"❌ Journal generation failed: {str(e)}")
        
        with col2:
            if hasattr(st.session_state, 'asc842_journals'):
                # Download journal entries
                journals = st.session_state.asc842_journals
                
                st.download_button(
                    label="📄 Download Journal Entries",
                    data=journals,
                    file_name=f"ASC842_Journal_Entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        
        # Display journal entries
        if hasattr(st.session_state, 'asc842_journals'):
            with st.expander("📋 View Journal Entries"):
                st.markdown(st.session_state.asc842_journals)
    
    # Workflow Summary
    if hasattr(st.session_state, 'asc842_analysis'):
        st.markdown("---")
        st.markdown("### 📋 Complete ASC 842 Analysis Summary")
        
        progress_items = []
        if hasattr(st.session_state, 'asc842_analysis'):
            progress_items.append("✅ Module 1: Lease Classification Complete")
        if hasattr(st.session_state, 'asc842_measurement'):
            progress_items.append("✅ Module 2: Measurement Calculations Complete")
        if hasattr(st.session_state, 'asc842_journals'):
            progress_items.append("✅ Module 3: Journal Entries Complete")
        
        if len(progress_items) == 3:
            st.success("🎉 **Complete ASC 842 Lease Accounting Analysis Ready!**")
            st.markdown("All three modules completed - ready for controller review and ERP integration.")
        
        for item in progress_items:
            st.markdown(item)
    
    # Information section
    st.markdown("---")
    st.markdown("### ℹ️ ASC 842 Three-Module Workflow")
    
    with st.expander("📚 Understanding the Complete Process"):
        st.markdown("""
        **Module 1: Classification (Operating vs Finance)**
        - Upload lease contract for analysis
        - Apply 5 ASC 842 classification tests systematically
        - Generate professional classification memorandum
        
        **Module 2: Measurement Calculator**
        - Calculate initial lease liability (present value)
        - Determine right-of-use asset value  
        - Generate period-by-period amortization schedule
        
        **Module 3: Journal Entry Generator**
        - Convert calculations to accounting journal entries
        - Support initial recognition and periodic entries
        - Export in multiple formats for ERP systems
        
        **Sequential Workflow:** Module 1 → Module 2 → Module 3
        **Independent Usage:** Each module can be used standalone
        """)
    
    # Footer - use standard Streamlit footer
    st.markdown("---")
    st.markdown("*ASC 842 Lease Accounting Analysis - Professional Implementation*")

if __name__ == "__main__":
    show_asc842_page()