"""
ASC 606 Revenue Recognition Analysis - Simple Approach

This page demonstrates the raw LLM output approach with direct markdown rendering.
"""

import streamlit as st
import time
import tempfile
import os
from asc606.simple_analyzer import SimpleASC606Analyzer
from shared.document_processor import SharedDocumentProcessor
from shared.ui_components import SharedUIComponents

def show_asc606_simple_page():
    """Display the simplified ASC 606 analysis page."""
    
    st.title("🎯 ASC 606 Revenue Recognition (Simple)")
    st.markdown("**Raw LLM output approach - single call, direct markdown display**")
    
    # Initialize components
    if 'simple_analyzer' not in st.session_state:
        st.session_state.simple_analyzer = SimpleASC606Analyzer()
    
    if 'doc_processor' not in st.session_state:
        st.session_state.doc_processor = SharedDocumentProcessor()
    
    if 'ui_components' not in st.session_state:
        st.session_state.ui_components = SharedUIComponents()
    
    # Input section
    with st.container():
        st.markdown("### 📄 Contract Analysis Setup")
        
        # Document upload
        uploaded_file = st.file_uploader(
            "Upload Contract Document",
            type=['pdf', 'docx', 'txt'],
            help="Upload the contract document for ASC 606 analysis"
        )
        
        # Basic inputs
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input(
                "Customer Name",
                value="Global Dynamics",
                help="Name of the customer/client"
            )
        
        with col2:
            analysis_title = st.text_input(
                "Analysis Title", 
                value="contract01",
                help="Short title for this analysis"
            )
        
        # Additional context
        additional_context = st.text_area(
            "Additional Context (Optional)",
            placeholder="Any additional information or specific focus areas for the analysis...",
            height=100
        )
    
    # Analysis button
    if st.button("🚀 Generate ASC 606 Analysis", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("Please upload a contract document first.")
            return
        
        if not customer_name.strip():
            st.error("Please enter a customer name.")
            return
        
        try:
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Process document
            status_text.text("📄 Processing contract document...")
            progress_bar.progress(20)
            
            # Process the uploaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                contract_text = st.session_state.doc_processor.extractor.extract_text(tmp_file_path)
            finally:
                os.unlink(tmp_file_path)
            
            if not contract_text or len(contract_text.strip()) < 100:
                st.error("Could not extract sufficient text from the document. Please check the file format.")
                return
            
            # Step 2: Generate analysis
            status_text.text("🤖 Generating ASC 606 analysis...")
            progress_bar.progress(60)
            
            # For this demo, use basic authoritative context
            authoritative_context = """
            ASC 606 establishes a five-step model for revenue recognition:
            1. Identify the contract with a customer
            2. Identify performance obligations in the contract  
            3. Determine the transaction price
            4. Allocate the transaction price to performance obligations
            5. Recognize revenue when performance obligations are satisfied
            
            Key principles include control transfer, standalone selling prices, and proper timing of recognition.
            """
            
            result = st.session_state.simple_analyzer.analyze_contract(
                contract_text=contract_text,
                authoritative_context=authoritative_context,
                customer_name=customer_name,
                analysis_title=analysis_title,
                additional_context=additional_context
            )
            
            # Step 3: Display results
            status_text.text("✅ Analysis complete!")
            progress_bar.progress(100)
            time.sleep(0.5)
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Display the memo using raw markdown
            st.markdown("---")
            st.markdown("## 📋 Generated Memo")
            
            # Display memo content directly as markdown
            st.markdown(result['memo_content'])
            
            # Download button
            st.download_button(
                label="📥 Download Memo (Markdown)",
                data=result['memo_content'],
                file_name=f"asc606_memo_{customer_name.replace(' ', '_')}_{result['analysis_date'].replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    show_asc606_simple_page()