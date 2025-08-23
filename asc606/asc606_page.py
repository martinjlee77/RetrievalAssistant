"""
ASC 606 Contract Analysis Page
"""

import streamlit as st
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List

from shared.ui_components import SharedUIComponents
# CleanMemoGenerator import moved to initialization section
from shared.document_processor import SharedDocumentProcessor
from asc606.step_analyzer import ASC606StepAnalyzer
from asc606.knowledge_search import ASC606KnowledgeSearch

logger = logging.getLogger(__name__)


def render_asc606_page():
    """Render the ASC 606 analysis page."""

    # Page header
    st.title("ASC 606 Revenue Recognition Analyzer")
    st.markdown(
        "Automatically analyze revenue contracts under ASC 606. This tool performs the five-step revenue recognition analysis, generating a comprehensive review memo that details the findings. Enter your contract details below to proceed."
    )

    st.warning("**Important:** Upload complete contract documents for accurate analysis.  Incomplete documents may lead to inaccurate results.")

    
    # Get user inputs with progressive disclosure
    contract_text, filename, customer_name, analysis_title, additional_context, is_ready = get_asc606_inputs()

    # Show analysis buttons with smart states
    if is_ready:
        # Check for cached analysis
        cache_key = _generate_cache_key(contract_text, customer_name, additional_context)
        cached_analysis = _get_cached_analysis(cache_key)
        
        if cached_analysis and cached_analysis.get('analysis_results'):
            # Subtle indication of cached analysis instead of big success box
            st.info("💾 Previous analysis available")
            col1, col2 = st.columns(2)
            
            # Track if memo should be generated from cache
            generate_from_cache = False
            regenerate_analysis = False
            
            with col1:
                if st.button("⚡ Generate Memo from Cache",
                           type="primary",
                           use_container_width=True,
                           key="asc606_from_cache"):
                    generate_from_cache = True
            
            with col2:
                if st.button("🔄 Regenerate Analysis",
                           type="secondary",
                           use_container_width=True,
                           key="asc606_regenerate"):
                    regenerate_analysis = True
            
            # Generate memo outside of columns for full width display
            if generate_from_cache:
                _generate_memo_from_cache(cached_analysis, customer_name, analysis_title)
            elif regenerate_analysis:
                _clear_cache(cache_key)
                perform_asc606_analysis(contract_text, customer_name,
                                      analysis_title, additional_context, cache_key)
        else:
            if st.button("Analyze Contract & Generate Memo",
                       type="primary",
                       use_container_width=True,
                       key="asc606_analyze"):
                perform_asc606_analysis(contract_text, customer_name,
                                      analysis_title, additional_context, cache_key)
    else:
        # Show disabled button with helpful message when not ready
        missing_items = []
        if not customer_name or not customer_name.strip():
            missing_items.append("customer name")
        if not analysis_title or not analysis_title.strip():
            missing_items.append("analysis title")
        if not contract_text:
            missing_items.append("contract document")
        
        if missing_items:
            st.button("Analyze Contract & Generate Memo", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc606_analyze_disabled_missing",
                     help=f"The analysis cannot begin until the required fields above are completed. Please fill in the missing {', '.join(missing_items)}.")
        else:
            st.button("Analyze Contract & Generate Memo", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc606_analyze_disabled_ready")


def get_asc606_inputs():
    """Get ASC 606 specific inputs with progressive disclosure."""
    st.subheader("Contract Details")

    # ASC 606 specific inputs with clear required indicators
    col1, col2 = st.columns(2)

    with col1:
        customer_name = st.text_input(
            "Customer name (required)",
            placeholder="ABC Corp.",
        )

    with col2:
        analysis_title = st.text_input(
            "Analysis title (required)",
            placeholder="Contract_123", 
            help="Unique identifier for this analysis; used to track the memo and results.  This title will appear on the generated memo."
        )

    # Document upload with clear required indicator
    processor = SharedDocumentProcessor()
    contract_text, filename = processor.upload_and_process(
        "Upload contract and related documents (required)")

    # Additional context input (clearly marked as optional)
    additional_context = st.text_area(
        "Additional context (optional)",
        placeholder="Provide specific guidance to the AI (e.g., highlight focus areas or key clauses or mention a verbal agreement.",
        height=100)

    # Check completion status for smart button enablement
    is_ready = bool(customer_name and customer_name.strip() and 
                   analysis_title and analysis_title.strip() and 
                   contract_text)

    return contract_text, filename, customer_name, analysis_title, additional_context, is_ready


# Old validation function removed - using progressive disclosure approach instead


def perform_asc606_analysis(contract_text: str, customer_name: str,
                            analysis_title: str, additional_context: str = "", cache_key: str = None):
    """Perform the complete ASC 606 analysis and display results."""

    try:
        # Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC606StepAnalyzer()
                knowledge_search = ASC606KnowledgeSearch()
                from asc606.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator(
                    template_path="asc606/templates/memo_template.md")
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 606 knowledge base is not available. Try again and contact support if this persists.")
                st.stop()
                return

        # Display progress
        steps = [
            "Processing", "Step 1", "Step 2", "Step 3", "Step 4",
            "Step 5", "Memo Generation"
        ]
        progress_placeholder = st.empty()

        # Step-by-step analysis with progress indicators
        analysis_results = {}
        
        # Run 5 ASC 606 steps with progress
        for step_num in range(1, 6):
            with progress_placeholder:
                st.subheader(f"🔄 Analyzing Step {step_num}")
                ui.analysis_progress(steps, step_num)

            with st.spinner(f"Analyzing Step {step_num}..."):
                # Get relevant guidance from knowledge base
                authoritative_context = knowledge_search.search_for_step(
                    step_num, contract_text)

                # Analyze the step with additional context
                step_result = analyzer._analyze_step(
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name,
                    additional_context=additional_context)

                analysis_results[f'step_{step_num}'] = step_result
                logger.info(f"DEBUG: Completed step {step_num}")

        # Generate additional sections (Executive Summary, Background, Conclusion)
        with progress_placeholder:
            st.subheader("📋 Generating additional sections...")
            ui.analysis_progress(steps, 6)

        with st.spinner("Generating Executive Summary, Background, and Conclusion..."):
            # Extract conclusions from the 5 steps
            conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results)
            
            # Generate the three additional sections
            executive_summary = analyzer.generate_executive_summary(conclusions_text, customer_name)
            background = analyzer.generate_background_section(conclusions_text, customer_name)
            conclusion = analyzer.generate_conclusion_section(conclusions_text)
            
            # Combine into the expected structure for memo generator
            final_results = {
                'customer_name': customer_name,
                'analysis_title': analysis_title,
                'analysis_date': datetime.now().strftime("%B %d, %Y"),
                'steps': analysis_results,
                'executive_summary': executive_summary,
                'background': background,
                'conclusion': conclusion
            }
            
            # Cache analysis results if successful
            if cache_key:
                _cache_analysis_results(cache_key, {
                    'analysis_results': final_results,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Generate memo directly from complete analysis results
            memo_content = memo_generator.combine_clean_steps(final_results)

        # Store memo data in session state and navigate to memo page
        progress_placeholder.empty()
        st.success("✅ Analysis completed successfully! Redirecting to memo...")
        
        # Store memo data for the memo page
        st.session_state.asc606_memo_data = {
            'memo_content': memo_content,
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
        
        # Display knowledge base info if available (briefly before redirect)
        if knowledge_search.is_available():
            kb_info = knowledge_search.get_user_kb_info()
            ui.display_knowledge_base_stats(kb_info)
        
        # Navigate to memo page
        st.switch_page("asc606/memo_page.py")

    except Exception as e:
        st.error("❌ Analysis failed. Please try again. Contact support if this issue persists.")
        logger.error(f"ASC 606 analysis error: {str(e)}")

# OLD PARSING SYSTEM REMOVED - Using direct markdown approach only


# Executive summary generation moved to ASC606StepAnalyzer class


# Final conclusion generation moved to ASC606StepAnalyzer class


# Issues collection removed - issues are already included in individual step analyses


# Configure logging
logging.basicConfig(level=logging.INFO)


# Main function for Streamlit navigation
def main():
    """Main function called by Streamlit navigation."""
    render_asc606_page()


# ===== CACHE HELPER FUNCTIONS =====
# These are for development convenience and can be removed before deployment

def _generate_cache_key(contract_text: str, customer_name: str, additional_context: str) -> str:
    """Generate a cache key based on input parameters."""
    content = f"{contract_text[:1000]}{customer_name}{additional_context}"  # Use first 1000 chars
    return hashlib.md5(content.encode()).hexdigest()

def _get_cached_analysis(cache_key: str) -> Dict[str, Any]:
    """Get cached analysis results if they exist."""
    if 'memo_cache' not in st.session_state:
        return {}
    return st.session_state.memo_cache.get(cache_key, {})

def _cache_analysis_results(cache_key: str, data: Dict[str, Any]) -> None:
    """Cache analysis results for later use."""
    if 'memo_cache' not in st.session_state:
        st.session_state.memo_cache = {}
    st.session_state.memo_cache[cache_key] = data

def _clear_cache(cache_key: str = None) -> None:
    """Clear specific cache entry or all cache."""
    if 'memo_cache' not in st.session_state:
        return
    if cache_key:
        st.session_state.memo_cache.pop(cache_key, None)
    else:
        st.session_state.memo_cache.clear()

def _generate_memo_from_cache(cached_data: Dict[str, Any], customer_name: str, analysis_title: str) -> None:
    """Generate memo from cached analysis results."""
    try:
        st.info("⚡ Generating memo from cached analysis...")
        
        from asc606.clean_memo_generator import CleanMemoGenerator
        memo_generator = CleanMemoGenerator()
        
        # Use cached memo data directly
        memo_data = cached_data.get('memo_data', {})
        
        memo_content = memo_generator.combine_clean_steps(cached_data.get('analysis_results', {}))
        
        st.success("✅ Memo generated from cache instantly! Redirecting to memo...")
        
        # Store memo data for the memo page
        st.session_state.asc606_memo_data = {
            'memo_content': memo_content,
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
        
        # Show cache info briefly before redirect
        cache_time = cached_data.get('timestamp', 'Unknown')
        st.info(f"📅 This analysis was cached on: {cache_time}")
        
        # Navigate to memo page
        st.switch_page("asc606/memo_page.py")
        
    except Exception as e:
        st.error(f"❌ Error generating memo from cache: {str(e)}")
        logger.error(f"Cache memo generation error: {str(e)}")

# For direct execution/testing
if __name__ == "__main__":
    render_asc606_page()
