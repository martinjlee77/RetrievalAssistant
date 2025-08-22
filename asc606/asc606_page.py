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
from shared.clean_memo_generator import CleanMemoGenerator
from shared.document_processor import SharedDocumentProcessor
from asc606.step_analyzer import ASC606StepAnalyzer
from asc606.knowledge_search import ASC606KnowledgeSearch

logger = logging.getLogger(__name__)


def render_asc606_page():
    """Render the ASC 606 analysis page."""

    # Page header
    st.title("📃 ASC 606 Contract Review")
    st.markdown(
        "AI-generated comprehensive 5-step revenue recognition memo. Enter the required information below to begin."
    )

    # Get user inputs
    contract_text, filename, customer_name, analysis_title, additional_context, validation_errors = get_asc606_inputs(
    )

    # Show analysis buttons if inputs are valid
    if not validation_errors and contract_text:
        # Check for cached analysis
        cache_key = _generate_cache_key(contract_text, customer_name, additional_context)
        cached_analysis = _get_cached_analysis(cache_key)
        
        if cached_analysis:
            st.success("🎯 Found previous analysis for this contract!")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("⚡ Generate Memo from Cache",
                           type="primary",
                           use_container_width=True,
                           key="asc606_from_cache"):
                    _generate_memo_from_cache(cached_analysis, customer_name, analysis_title)
            
            with col2:
                if st.button("🔄 Regenerate Analysis",
                           type="secondary",
                           use_container_width=True,
                           key="asc606_regenerate"):
                    _clear_cache(cache_key)
                    perform_asc606_analysis(contract_text, customer_name,
                                          analysis_title, additional_context, cache_key)
        else:
            if st.button("➡️ Analyze Contract",
                       type="primary",
                       use_container_width=True,
                       key="asc606_analyze"):
                perform_asc606_analysis(contract_text, customer_name,
                                      analysis_title, additional_context, cache_key)


def get_asc606_inputs():
    """Get ASC 606 specific inputs and validate them."""
    st.subheader("Required Information")

    # ASC 606 specific inputs
    col1, col2 = st.columns(2)

    with col1:
        customer_name = st.text_input(
            "Customer name",
            placeholder="ABC Corp.",
            # help="Name of the customer for the revenue contract"
        )

    with col2:
        analysis_title = st.text_input(
            "Analysis title",
            placeholder="Contract_123",
            # help="Title for this analysis (will appear in the memo)"
        )

    # Additional context input (optional)
    additional_context = st.text_area(
        "Additional Context or Specific Questions (Optional)",
        placeholder="e.g., Focus on warranty provisions, consider prior verbal agreements, analyze specific performance obligations...",
        help="Provide any additional context, specific questions, or areas of focus for the analysis",
        height=100)

    # Document upload
    processor = SharedDocumentProcessor()
    contract_text, filename = processor.upload_and_process(
        "**Upload all** relevant contract documents in PDF or DOCX format")

    # Display document info if processed
    if contract_text and filename:
        processor.display_document_info(contract_text, filename)

    # Validate inputs
    validation_errors = validate_asc606_inputs(customer_name, analysis_title,
                                               contract_text)

    # Display validation errors if any
    if validation_errors:
        ui = SharedUIComponents()
        ui.validation_errors(validation_errors)

    return contract_text, filename, customer_name, analysis_title, additional_context, validation_errors


def validate_asc606_inputs(customer_name, analysis_title, contract_text):
    """Validate ASC 606 specific inputs."""
    errors = []

    if not customer_name or not customer_name.strip():
        errors.append("Please enter a customer name")

    if not analysis_title or not analysis_title.strip():
        errors.append("Please enter an analysis title")

    if not contract_text:
        errors.append("Please upload a contract document")

    # ASC 606 specific validation - check to see if there are less than 100 characters in the contract text
    if contract_text:
        processor = SharedDocumentProcessor()
        if len(contract_text.strip()) < 100:
            errors.append(
                "Document appears to be incomplete or not a valid contract")
        else:
            # Check for revenue-related terms
            revenue_terms = [
                'payment', 'payments', 'fees', 'fee', 'price', 'consideration', 
                'revenue', 'sale', 'sales', 'service', 'services', 'invoice', 
                'invoices', 'billing', 'transaction', 'purchase', 'license', 
                'subscription', 'agreement', 'agreements', 'arrangement', 
                'termination', 'project', 'deliverable', 'deliverables', 
                'performance', 'support', 'term', 'acceptance', 'agree', 
                'cancellation', 'refund', 'account', 'warranties', 'warranty', 
                'liability', 'arbitration', 'governing law', 'software', 
                'maintenance', 'entity', 'entities', 'business', 'businessnes', 
                'privacy', 'data', 'membership', 'taxes', 'tax', 
                'indemnification', 'indemnify', 'insurance', 'audit rights', 
                'audit', 'force majeure', 'ship', 'deliver', 'shipment', 
                'delivery', 'statement'
            ]
            contract_lower = contract_text.lower()
            found_revenue_terms = sum(1 for term in revenue_terms
                                      if term in contract_lower)

            if found_revenue_terms < 2:
                errors.append(
                    "Document may not be suitable for revenue recognition analysis - consider if this contains revenue-generating activities"
                )

    return errors


def perform_asc606_analysis(contract_text: str, customer_name: str,
                            analysis_title: str, additional_context: str = "", cache_key: str = None):
    """Perform the complete ASC 606 analysis and display results."""

    try:
        # Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC606StepAnalyzer()
                knowledge_search = ASC606KnowledgeSearch()
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
            "Starting", "Step 1", "Step 2", "Step 3", "Step 4",
            "Step 5", "Memo Generation"
        ]
        progress_placeholder = st.empty()

        # Complete analysis using analyzer's analyze_contract method
        with st.spinner("Performing complete ASC 606 analysis..."):
            # Get consolidated authoritative context
            authoritative_context = knowledge_search.search_for_step(1, contract_text)
            
            # Use the complete analyze_contract method which includes additional sections
            analysis_results = analyzer.analyze_contract(
                contract_text=contract_text,
                authoritative_context=authoritative_context,
                customer_name=customer_name,
                analysis_title=analysis_title,
                additional_context=additional_context
            )
            
            # Cache analysis results if successful
            if cache_key:
                _cache_analysis_results(cache_key, {
                    'analysis_results': analysis_results,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Generate memo directly from complete analysis results
            memo_content = memo_generator.combine_clean_steps(analysis_results)

        # Display final memo
        progress_placeholder.empty()
        st.success("✅ Work is completed successfully!")

        memo_generator.display_clean_memo(memo_content)

        # Display knowledge base info if available
        if knowledge_search.is_available():
            kb_info = knowledge_search.get_user_kb_info()
            ui.display_knowledge_base_stats(kb_info)

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
        return None
    return st.session_state.memo_cache.get(cache_key)

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
        
        memo_generator = CleanMemoGenerator()
        
        # Use cached memo data directly
        memo_data = cached_data.get('memo_data', {})
        
        memo_content = memo_generator.combine_clean_steps(cached_data.get('analysis_results', {}))
        
        st.success("✅ Memo generated from cache instantly!")
        memo_generator.display_clean_memo(memo_content)
        
        # Show cache info
        cache_time = cached_data.get('timestamp', 'Unknown')
        st.info(f"📅 This analysis was cached on: {cache_time}")
        
    except Exception as e:
        st.error(f"❌ Error generating memo from cache: {str(e)}")
        logger.error(f"Cache memo generation error: {str(e)}")

# For direct execution/testing
if __name__ == "__main__":
    render_asc606_page()
