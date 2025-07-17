"""
Shared UI Helper Functions for Multi-Standard Platform
"""

import streamlit as st
import json
from typing import Dict, Any, List

def load_custom_css():
    """Load custom CSS for brand consistency across all pages"""
    css = """
    /* --- THE FIX: Load icon font FIRST --- */
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
    
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@400;700&family=Poppins:wght@600;700&display=swap');

    /* Brand Color Variables */
    :root {
        --primary-color: #0A2B4C;
        --secondary-color: #C5A565;
        --bg-color: #F8F9FA;
        --text-color: #212529;
        --heading-font: 'Poppins', sans-serif;
        --body-font: 'Lato', sans-serif;
        --border-color: #e0e0e0;
    }

    /* Global Styling - Light Background */
    html, body, [class*="st-"] {
        font-family: var(--body-font);
        color: var(--text-color);
        background-color: white !important;
    }
    
    .stApp {
        background-color: white !important;
    }

    /* Comprehensive fix for keyboard_double_arrow_right text */
    /* Hide any element containing this text */
    body *:contains("keyboard_double_arrow_right") {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Hide Streamlit's internal sidebar controls that cause the keyboard issue */
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    [data-testid="stSidebarNavItems"] {
        display: none !important;
    }
    
    /* Hide header elements that might contain the text */
    button[kind="header"] {
        display: none !important;
    }
    
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Target specific text content */
    div:contains("keyboard_double_arrow_right"),
    span:contains("keyboard_double_arrow_right"),
    p:contains("keyboard_double_arrow_right"),
    button:contains("keyboard_double_arrow_right") {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
    }
    
    /* Hide navigation menu hover tooltips */
    [data-testid="stSidebar"] .stButton button:hover:after,
    [data-testid="stSidebar"] .stButton button:hover:before,
    [data-testid="stSidebar"] .stButton button[title*="keyboard"] {
        display: none !important;
    }
    
    /* Hide any tooltip or title attribute containing keyboard text */
    [title*="keyboard_double_arrow_right"] {
        display: none !important;
    }
    
    /* --- THE "FORCE IT" FIX --- */
    /* This rule is extremely specific and uses !important to override any other styles. */
    /* It targets the span inside the sidebar's collapse button. */
    button[data-testid="stSidebarNavCollapseButton"] > span {
        font-family: 'Material Symbols Outlined' !important;
        font-size: 0 !important;
        color: transparent !important;
        visibility: hidden !important;
        display: none !important;
    }
    
    /* Hide any sidebar collapse button entirely */
    button[data-testid="stSidebarNavCollapseButton"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Force hide any element containing keyboard text */
    *:contains("keyboard_double_arrow_right") {
        display: none !important;
        visibility: hidden !important;
        font-size: 0 !important;
        color: transparent !important;
    }

    /* Enhanced button hover effects */
    .stButton>button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(197, 165, 101, 0.4) !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--heading-font);
        color: var(--primary-color);
        font-weight: 700;
    }

    /* Main Container */
    .main .block-container {
        padding: 2rem;
        max-width: 1200px;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: var(--bg-color);
        border-right: 1px solid var(--border-color);
    }

    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 700;
        font-family: var(--body-font);
        padding: 0.75rem 1.5rem;
        border: 2px solid var(--secondary-color);
        background-color: var(--secondary-color);
        color: #fff;
        transition: all 0.3s;
    }

    .stButton>button:hover {
        background-color: #af8f4d;
        border-color: #af8f4d;
        color: #fff;
    }

    /* Input Field Styling */
    .stTextInput>div>div>input {
        border: 2px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-family: var(--body-font) !important;
        background-color: white !important;
        color: var(--text-color) !important;
    }

    .stTextInput>div>div>input:focus {
        border-color: var(--secondary-color) !important;
        box-shadow: 0 0 0 3px rgba(197, 165, 101, 0.1) !important;
    }

    .stTextArea>div>div>textarea {
        border: 2px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-family: var(--body-font) !important;
        background-color: white !important;
        color: var(--text-color) !important;
    }

    .stTextArea>div>div>textarea:focus {
        border-color: var(--secondary-color) !important;
        box-shadow: 0 0 0 3px rgba(197, 165, 101, 0.1) !important;
    }

    .stSelectbox>div>div>div {
        border: 2px solid var(--border-color) !important;
        border-radius: 8px !important;
        background-color: white !important;
    }

    .stDateInput>div>div>input {
        border: 2px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        background-color: white !important;
        color: var(--text-color) !important;
    }

    /* Primary Analysis Button */
    .analyze-button {
        background: linear-gradient(135deg, var(--secondary-color), #af8f4d);
        color: white;
        border: none;
        padding: 1rem 2rem;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: 700;
        width: 100%;
        margin: 1rem 0;
        cursor: pointer;
        transition: all 0.3s;
    }

    .analyze-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(197, 165, 101, 0.3);
    }

    /* Card Styling */
    .analysis-card {
        background: white;
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .step-card {
        background: var(--bg-color);
        border-left: 4px solid var(--secondary-color);
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }

    /* Metric Styling */
    [data-testid="stMetric"] {
        background-color: var(--bg-color);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
    }

    /* Input Styling */
    .stTextInput>div>div>input, .stTextArea>div>textarea, .stDateInput>div>div>input {
        border: 1px solid #ccc;
        border-radius: 5px;
        background-color: #fff;
        font-family: var(--body-font);
    }

    /* Expander Styling */
    [data-testid="stExpander"] {
        background: var(--bg-color);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        margin: 0.5rem 0;
    }

    /* Tab Styling */
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: transparent;
        border-bottom: 3px solid var(--secondary-color);
        color: var(--primary-color);
        font-weight: 700;
    }

    /* Success/Error Messages */
    .stSuccess {
        background-color: #d4edda;
        color: #155724;
        border-color: #c3e6cb;
    }

    .stError {
        background-color: #f8d7da;
        color: #721c24;
        border-color: #f5c6cb;
    }

    /* Progress Bar */
    .stProgress > div > div {
        background-color: var(--secondary-color);
    }
    """
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    
    # JavaScript solution to remove keyboard_double_arrow_right text
    st.markdown("""
    <script>
    function removeKeyboardArrowText() {
        // Find all text nodes containing the problematic text
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const textNodes = [];
        let node;
        
        while (node = walker.nextNode()) {
            if (node.nodeValue && node.nodeValue.includes('keyboard_double_arrow_right')) {
                textNodes.push(node);
            }
        }
        
        // Remove or hide the text nodes
        textNodes.forEach(textNode => {
            textNode.parentNode.style.display = 'none';
        });
        
        // Also check for any elements with this text content
        const allElements = document.querySelectorAll('*');
        allElements.forEach(element => {
            if (element.textContent && element.textContent.includes('keyboard_double_arrow_right')) {
                element.style.display = 'none';
            }
            
            // Remove title attributes that contain the problematic text
            if (element.getAttribute && element.getAttribute('title') && 
                element.getAttribute('title').includes('keyboard_double_arrow_right')) {
                element.removeAttribute('title');
            }
        });
        
        // Special handling for navigation tooltips
        const navButtons = document.querySelectorAll('[data-testid="stSidebar"] button');
        navButtons.forEach(button => {
            if (button.title && button.title.includes('keyboard_double_arrow_right')) {
                button.title = '';
            }
        });
    }
    
    // Run immediately and on DOM changes
    removeKeyboardArrowText();
    
    // Observer for dynamic content
    const observer = new MutationObserver(function(mutations) {
        removeKeyboardArrowText();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Run again after delays to catch late-loading content
    setTimeout(removeKeyboardArrowText, 100);
    setTimeout(removeKeyboardArrowText, 500);
    setTimeout(removeKeyboardArrowText, 1000);
    
    // Special handling for hover states and navigation
    document.addEventListener('mouseover', function(event) {
        setTimeout(removeKeyboardArrowText, 10);
    });
    
    document.addEventListener('mouseout', function(event) {
        setTimeout(removeKeyboardArrowText, 10);
    });
    </script>
    """, unsafe_allow_html=True)

def render_branded_header(title: str, subtitle: str = None):
    """Render branded header for all pages"""
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-family: Poppins, sans-serif; font-size: 2.5rem; color: #0A2B4C; margin-bottom: 0.5rem;">
            Controller.cpa
        </h1>
        <h2 style="font-size: 1.8rem; color: #0A2B4C; margin-bottom: 1rem;">
            {title}
        </h2>
        {f'<p style="font-size: 1.1rem; color: #666; margin-bottom: 2rem;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def render_standard_sidebar(current_standard: str, available_standards: Dict[str, Dict]):
    """Render sidebar for standard selection"""
    with st.sidebar:
        st.header("Controller.cpa")
        st.subheader("Active Standard")
        
        current_info = available_standards[current_standard]
        st.success(f"✅ **{current_standard}**")
        st.write(f"*{current_info['description']}*")
        st.divider()
        
        st.subheader("Switch Standard")
        for code, info in available_standards.items():
            if info['status'] == 'available':
                if st.button(f"{code}: {info['name']}", 
                           key=f"select_{code}", 
                           disabled=(code == current_standard), 
                           use_container_width=True):
                    st.session_state.selected_standard = code
                    st.rerun()
            else:
                st.info(f"**{code}**\n\n*{info['name']}*\n\n(Coming Soon)", icon="⏳")

def render_analysis_metrics(analysis_results: Dict[str, Any]):
    """Render analysis metrics in a consistent format"""
    st.subheader("Analysis Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Source Quality", "Hybrid RAG", "Authoritative + AI")
    
    with col2:
        citations_count = len(analysis_results.get('citations', []))
        st.metric("Citations", citations_count, "Source References")
    
    with col3:
        guidance_count = len(analysis_results.get('implementation_guidance', []))
        st.metric("Guidance Items", guidance_count, "Implementation Notes")
    
    with col4:
        memo_length = len(analysis_results.get('professional_memo', ''))
        st.metric("Memo Length", f"{memo_length:,}", "Characters")

def render_step_analysis(step_name: str, step_data: Dict[str, Any]):
    """Render individual step analysis in a card format"""
    with st.container():
        st.markdown(f"""
        <div class="step-card">
            <h3 style="margin-bottom: 1rem; color: #0A2B4C;">{step_name}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if isinstance(step_data, dict):
            # Extract conclusion
            conclusion = step_data.get('conclusion', 'No conclusion provided')
            st.write(f"**Conclusion:** {conclusion}")
            
            # Extract key findings
            if 'key_findings' in step_data:
                with st.expander("Key Findings"):
                    for finding in step_data['key_findings']:
                        st.write(f"• {finding}")
            
            # Extract rationale
            if 'rationale' in step_data:
                with st.expander("Rationale"):
                    st.write(step_data['rationale'])
            
            # Extract supporting evidence
            if 'supporting_evidence' in step_data:
                with st.expander("Supporting Evidence"):
                    for evidence in step_data['supporting_evidence']:
                        st.write(f"• {evidence}")
        else:
            st.write(str(step_data))

def render_professional_memo(memo_content: str):
    """Render professional memo with proper formatting"""
    st.subheader("Professional Accounting Memo")
    
    # Create download button
    st.download_button(
        label="📄 Download Professional Memo",
        data=memo_content,
        file_name="accounting_analysis_memo.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    # Display memo content
    st.markdown("""
    <div class="analysis-card">
        <div style="font-family: 'Courier New', monospace; font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap;">
    """ + memo_content + """
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_upload_interface_two_column(standard: str):
    """Render two-column upload interface"""
    st.header(f"Start New {standard} Analysis")
    st.write("Complete the required fields and upload your document, then click Analyze.")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.subheader("📋 Required Information")
        
        analysis_title = st.text_input(
            "Analysis Title / Document ID *",
            placeholder="e.g., Q4 Project Phoenix Contract",
            help="A unique name to identify this analysis"
        )
        
        if standard == "ASC 606":
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
        
        elif standard == "ASC 842":
            lessor_name = st.text_input(
                "Lessor Name *",
                placeholder="e.g., Property Management Co."
            )
            
            lessee_name = st.text_input(
                "Lessee Name *",
                placeholder="e.g., Your Company Name"
            )
            
            asset_description = st.text_area(
                "Asset Description *",
                placeholder="e.g., Office space at 123 Main Street, 5,000 sq ft",
                height=100,
                help="Description of the leased asset"
            )
        
        # File upload
        st.subheader("📄 Document Upload")
        uploaded_files = st.file_uploader(
            "Upload Documents",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Upload contracts, amendments, invoices, or related documents"
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
    
    if st.button("🔍 Analyze Document", use_container_width=True, type="primary"):
        # Validation logic would go here
        if not analysis_title:
            st.error("Please provide an analysis title")
            return None
        
        if not uploaded_files:
            st.error("Please upload at least one document")
            return None
        
        # Return collected data
        return {
            'analysis_title': analysis_title,
            'uploaded_files': uploaded_files,
            'analysis_depth': analysis_depth,
            'output_format': output_format,
            'include_citations': include_citations,
            'include_examples': include_examples,
            'additional_notes': additional_notes
        }
    
    return None