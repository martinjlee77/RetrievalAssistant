"""
Shared UI Helper Functions for Multi-Standard Platform
"""

import streamlit as st
import json
from typing import Dict, Any, List

def load_custom_css():
    """Load optimized CSS for the RAG-enabled multi-standard platform"""
    css = """
    /* Import Google Fonts for professional branding */
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

    /* Clean navigation styling - removed icon fixes as they're UI-specific */

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
    
    # Removed JavaScript fixes - focused on core platform functionality

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

def render_analysis_metrics(analysis_results: Any):
    """Render analysis metrics in a consistent format for RAG-enhanced results"""
    st.subheader("Analysis Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Updated to show actual source quality from RAG system
        source_quality = getattr(analysis_results, 'source_quality', 'Hybrid RAG')
        st.metric("Source Quality", source_quality, "RAG-Enhanced")
    
    with col2:
        citations = getattr(analysis_results, 'citations', [])
        citations_count = len(citations) if citations else 0
        st.metric("Citations", citations_count, "Authoritative Sources")
    
    with col3:
        guidance = getattr(analysis_results, 'implementation_guidance', [])
        guidance_count = len(guidance) if guidance else 0
        st.metric("Guidance Items", guidance_count, "Implementation Notes")
    
    with col4:
        memo = getattr(analysis_results, 'professional_memo', '')
        memo_length = len(memo) if memo else 0
        st.metric("Memo Length", f"{memo_length:,}", "Characters")

def render_step_analysis(step_name: str, step_data: Dict[str, Any]):
    """Render individual step analysis in a card format using new structured JSON data"""
    with st.container():
        st.markdown(f"""
        <div class="step-card">
            <h3 style="margin-bottom: 1rem; color: #0A2B4C;">{step_name}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if isinstance(step_data, dict):
            # Extract executive conclusion (updated from 'conclusion')
            conclusion = step_data.get('executive_conclusion', 'No conclusion provided')
            st.write(f"**Conclusion:** {conclusion}")
            
            # Extract structured data specific to each step
            if 'contract_criteria_assessment' in step_data:
                with st.expander("Contract Criteria Assessment"):
                    for criterion in step_data['contract_criteria_assessment']:
                        status = criterion.get('status', 'Unknown')
                        criterion_name = criterion.get('criterion', 'Unknown Criterion')
                        st.write(f"• **{criterion_name}:** {status}")
            
            if 'performance_obligations' in step_data:
                with st.expander("Performance Obligations"):
                    for po in step_data['performance_obligations']:
                        po_desc = po.get('po_description', 'Unknown PO')
                        is_distinct = po.get('is_distinct', 'Unknown')
                        st.write(f"• **{po_desc}:** {'✅ Distinct' if is_distinct == 'Yes' else '❌ Not Distinct'}")
            
            if 'transaction_price_components' in step_data:
                with st.expander("Transaction Price Components"):
                    price_data = step_data['transaction_price_components']
                    st.write(f"• **Total Price:** {price_data.get('total_transaction_price', 'Not specified')}")
                    st.write(f"• **Fixed Consideration:** {price_data.get('fixed_consideration', 'Not specified')}")
                    if price_data.get('variable_consideration'):
                        st.write("• **Variable Consideration:** Present")
            
            if 'allocation_details' in step_data:
                with st.expander("Allocation Details"):
                    allocation_data = step_data['allocation_details']
                    if allocation_data.get('allocations'):
                        for allocation in allocation_data['allocations']:
                            po_name = allocation.get('performance_obligation', 'Unknown PO')
                            amount = allocation.get('allocated_amount', 'Unknown amount')
                            st.write(f"• **{po_name}:** {amount}")
            
            if 'revenue_recognition_plan' in step_data:
                with st.expander("Revenue Recognition Plan"):
                    for plan in step_data['revenue_recognition_plan']:
                        po_name = plan.get('performance_obligation', 'Unknown PO')
                        method = plan.get('recognition_method', 'Unknown method')
                        st.write(f"• **{po_name}:** {method}")
            
            # Extract analysis points (updated from 'rationale')
            analysis_points = step_data.get('analysis_points', [])
            if analysis_points:
                with st.expander("Detailed Analysis"):
                    for i, point in enumerate(analysis_points, 1):
                        topic_title = point.get('topic_title', f'Analysis Point {i}')
                        analysis_text = point.get('analysis_text', 'No analysis provided')
                        evidence_quotes = point.get('evidence_quotes', [])
                        
                        st.write(f"**{i}. {topic_title}**")
                        st.write(analysis_text)
                        
                        # Display evidence quotes (updated from 'supporting_evidence')
                        if evidence_quotes and isinstance(evidence_quotes, list):
                            st.write("*Supporting Evidence:*")
                            for quote in evidence_quotes:
                                if isinstance(quote, str):
                                    st.write(f"> {quote}")
                        elif isinstance(evidence_quotes, str):
                            st.write("*Supporting Evidence:*")
                            st.write(f"> {evidence_quotes}")
                        
                        if i < len(analysis_points):  # Add separator between points
                            st.write("---")
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

def render_rag_knowledge_base_status(kb_stats: Dict[str, Any]):
    """Render knowledge base status for RAG system debugging"""
    with st.expander("🔍 Knowledge Base Status", expanded=False):
        if kb_stats.get('rag_enabled', False):
            st.success(f"✅ RAG System Active")
            st.write(f"**Collection:** {kb_stats.get('collection_name', 'Unknown')}")
            st.write(f"**Total Chunks:** {kb_stats.get('total_chunks', 0):,}")
            st.write(f"**Status:** {kb_stats.get('status', 'Unknown')}")
            if 'manager_type' in kb_stats:
                st.write(f"**Manager:** {kb_stats['manager_type']}")
        else:
            st.warning("⚠️ RAG System Not Available")
            if 'error' in kb_stats:
                st.error(f"Error: {kb_stats['error']}")

def format_dict_as_markdown(data_dict: Dict[str, Any], indent_level: int = 0) -> str:
    """Convert dictionary to formatted markdown for better readability"""
    result = []
    indent = "  " * indent_level
    
    for key, value in data_dict.items():
        formatted_key = key.replace('_', ' ').title()
        
        if isinstance(value, dict):
            result.append(f"{indent}**{formatted_key}:**")
            result.append(format_dict_as_markdown(value, indent_level + 1))
        elif isinstance(value, list):
            result.append(f"{indent}**{formatted_key}:**")
            for item in value:
                if isinstance(item, str):
                    result.append(f"{indent}  • {item}")
                else:
                    result.append(f"{indent}  • {str(item)}")
        else:
            result.append(f"{indent}**{formatted_key}:** {value}")
    
    return "\n".join(result)