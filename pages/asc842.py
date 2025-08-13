"""
ASC 842 Leases - Classification, Measurement, and Journal Entry Suite
Lessee Accounting Only - Module 1 Implementation
"""

import streamlit as st
from datetime import datetime
from typing import Optional

from core.ui_helpers import render_header, render_footer
from core.models import LeaseClassificationData, ASC842Analysis
from core.analyzers import get_analyzer
from utils.document_extractor import extract_text_from_file
from utils.html_export import convert_memo_to_html
from utils.llm import generate_docx_memo

def show_asc842_page():
    """ASC 842 Lease Accounting - Module 1: Classification Tool"""
    
    # Page header
    render_header()
    
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
            contract_text = extract_text_from_file(uploaded_file)
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
                    # Create lease data object
                    lease_data = LeaseClassificationData(
                        asset_type=asset_type,
                        lease_term_months=lease_term_months,
                        annual_lease_payment=annual_lease_payment,
                        discount_rate=discount_rate,
                        asset_fair_value=asset_fair_value,
                        asset_economic_life_years=asset_economic_life_years,
                        purchase_option_exists=purchase_option_exists == "Yes - Reasonably Certain to Exercise",
                        ownership_transfer=ownership_transfer == "Yes"
                    )
                    
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
    
    # Information section
    st.markdown("---")
    st.markdown("### ℹ️ ASC 842 Classification Tests")
    
    with st.expander("📚 Learn About the 5 Classification Tests"):
        st.markdown("""
        A lease is classified as a **Finance Lease** if it meets ANY ONE of these criteria:
        
        **1. Ownership Transfer**
        - Lease transfers ownership to lessee by end of term
        
        **2. Purchase Option**
        - Contains purchase option reasonably certain to be exercised
        
        **3. Lease Term**
        - Term covers major part (≥75%) of asset's economic life
        - Exception: Near end of asset life
        
        **4. Present Value**
        - PV of payments ≥ substantially all (≥90%) of asset fair value
        
        **5. Alternative Use**
        - Asset so specialized it has no alternative use to lessor
        
        If **no tests are met** → **Operating Lease**
        """)
    
    # Footer
    render_footer()

if __name__ == "__main__":
    show_asc842_page()