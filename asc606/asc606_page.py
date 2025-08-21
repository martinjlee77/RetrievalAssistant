"""
ASC 606 Contract Analysis Page
"""

import streamlit as st
import logging
from typing import Dict, Any, List

from shared.ui_components import SharedUIComponents
from shared.memo_generator import SharedMemoGenerator
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
    contract_text, filename, customer_name, analysis_title, validation_errors = get_asc606_inputs(
    )

    # Show analysis button if inputs are valid
    if not validation_errors and contract_text:
        if st.button("➡️ Analyze Contract",
                     type="primary",
                     use_container_width=True,
                     key="asc606_analyze"):
            perform_asc606_analysis(contract_text, customer_name,
                                    analysis_title)


def get_asc606_inputs():
    """Get ASC 606 specific inputs and validate them."""
    st.subheader("ℹ️ Required Information")

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

    # Document upload
    processor = SharedDocumentProcessor()
    contract_text, filename = processor.upload_and_process(
        "**Upload all** relevant contract documents in PDF or DOCX format")

    # Display document info if processed
    if contract_text and filename:
        processor.display_document_info(contract_text, filename)

    # Validate inputs
    validation_errors = validate_asc606_inputs(customer_name, analysis_title, contract_text)

    # Display validation errors if any
    if validation_errors:
        ui = SharedUIComponents()
        ui.validation_errors(validation_errors)

    return customer_name, analysis_title, contract_text, filename, validation_errors


def validate_asc606_inputs(analysis_title, contract_text, customer_name):
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
            'payment', 'payments', 'fees', 'fee', 'price', 'consideration', 'revenue', 'sale', 'sales', 'service', 'services', 'invoice', 'invoices', 'billing', 'transaction', 'purchase', 'license', 'subscription', 'agreement', 'agreements', 'arrangement', 'termination', 'project', 'deliverable', 'deliverables', 'performance', 'support', 'term', 'acceptance', 'agree', 'cancellation', 'refund', 'account', 'warranties', 'warranty', 'liability', 'arbitration', 'governing law', 'software', 'maintenance', 'entity', 'entities', 'business', 'businessnes', 'privacy', 'data', 'membership', 'account', 'taxes', 'tax', 'indemnification', 'indemnify', 'insurance', 'audit rights', 'audit', 'force majeure', 'ship', 'deliver', 'shipment', 'delivery', 'statement'
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
                            analysis_title: str):
    """Perform the complete ASC 606 analysis and display results."""

    try:
        # Initialize components
        with st.spinner("Initializing analysis components..."):
            analyzer = ASC606StepAnalyzer()
            knowledge_search = ASC606KnowledgeSearch()
            memo_generator = SharedMemoGenerator(
                template_path="asc606/templates/memo_template.md")
            from shared.ui_components import SharedUIComponents
            ui = SharedUIComponents()

        # Display progress
        steps = [
            "Contract Review", "Step 1", "Step 2", "Step 3", "Step 4",
            "Step 5", "Memo Generation"
        ]
        progress_placeholder = st.empty()

        # Step-by-step analysis with knowledge base integration
        analysis_results = {}

        for step_num in range(1, 6):
            with progress_placeholder:
                st.subheader(f"🔄 Analyzing Step {step_num}")
                ui.analysis_progress(steps, step_num)

            with st.spinner(f"Analyzing Step {step_num}..."):
                # Get relevant guidance
                if knowledge_search.is_available():
                    authoritative_context = knowledge_search.search_for_step(
                        step_num, contract_text)
                else:
                    authoritative_context = "Knowledge base not available. Analysis will proceed with general ASC 606 knowledge."

                # Analyze the step
                step_result = analyzer._analyze_step(
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name)

                analysis_results[f'step_{step_num}'] = step_result

                # Display step results immediately
                display_step_results(step_num, step_result)

        # Generate final memo
        with progress_placeholder:
            st.subheader("📋 Generating Professional Memo")
            ui.analysis_progress(steps, 6)

        with st.spinner("Generating memo..."):
            memo_data = prepare_memo_data(analysis_results, customer_name,
                                          analysis_title)
            memo_content = memo_generator.generate_memo(
                memo_data=memo_data,
                customer_name=customer_name,
                analysis_title=analysis_title,
                standard_name="ASC 606")

        # Display final memo
        progress_placeholder.empty()
        st.success("✅ Analysis completed successfully!")

        memo_generator.display_memo(memo_content)

        # Display knowledge base stats if available
        if knowledge_search.is_available():
            kb_stats = knowledge_search.get_knowledge_base_stats()
            ui.display_knowledge_base_stats(kb_stats)

    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        logger.error(f"ASC 606 analysis error: {str(e)}")


def display_step_results(step_num: int, step_result: Dict[str, str]):
    """Display results for a single step analysis."""

    step_title = step_result.get('title', f'Step {step_num}')

    with st.expander(f"📋 {step_title}", expanded=True):

        # Analysis section
        if step_result.get('analysis'):
            st.markdown("**Analysis:**")
            st.markdown(step_result['analysis'])
            st.markdown("---")

        # Conclusion section
        if step_result.get('conclusion'):
            st.markdown("**Conclusion:**")
            st.markdown(step_result['conclusion'])

        # Issues section
        if step_result.get('issues') and step_result['issues'].strip():
            if 'none' not in step_result['issues'].lower(
            ) and 'not applicable' not in step_result['issues'].lower():
                st.markdown("---")
                st.markdown("**Issues/Uncertainties:**")
                st.markdown(step_result['issues'])


def prepare_memo_data(analysis_results: Dict[str, Any], customer_name: str,
                      analysis_title: str) -> Dict[str, Any]:
    """Prepare analysis results for memo generation."""

    # Build analysis section with all steps
    analysis_content = []

    for step_num in range(1, 6):
        step_key = f'step_{step_num}'
        if step_key in analysis_results:
            step_data = analysis_results[step_key]
            step_title = step_data.get('title', f'Step {step_num}')

            step_content = f"### {step_title}\n\n"

            if step_data.get('analysis'):
                step_content += f"{step_data['analysis']}\n\n"

            if step_data.get('conclusion'):
                step_content += f"**Conclusion:** {step_data['conclusion']}\n\n"

            analysis_content.append(step_content)

    # Prepare memo data
    memo_data = {
        'analysis_content':
        "\n".join(analysis_content),
        'executive_summary':
        generate_executive_summary(analysis_results, customer_name),
        'conclusion':
        generate_final_conclusion(analysis_results),
        'issues_for_investigation':
        collect_all_issues(analysis_results)
    }

    return memo_data


def generate_executive_summary(analysis_results: Dict[str, Any],
                               customer_name: str) -> str:
    """Generate executive summary from analysis results."""

    summary = f"We have completed a comprehensive ASC 606 revenue recognition analysis for {customer_name}. "
    summary += "The analysis follows the five-step ASC 606 methodology and addresses contract identification, "
    summary += "performance obligation determination, transaction price establishment, price allocation, "
    summary += "and revenue recognition timing. "
    summary += "The proposed accounting treatment is consistent with ASC 606 requirements."

    return summary


def generate_final_conclusion(analysis_results: Dict[str, Any]) -> str:
    """Generate final conclusion from step results."""

    conclusion = "Based on our comprehensive analysis under ASC 606, the proposed revenue recognition "
    conclusion += "treatment is appropriate and complies with the authoritative guidance. "

    # Count successful steps
    successful_steps = len(
        [k for k, v in analysis_results.items() if v.get('conclusion')])

    if successful_steps >= 4:
        conclusion += "All key ASC 606 requirements have been addressed in this analysis."
    else:
        conclusion += "The analysis addresses the primary ASC 606 considerations for this contract."

    return conclusion


def collect_all_issues(analysis_results: Dict[str, Any]) -> List[str]:
    """Collect all issues from step analyses."""

    all_issues = []

    for step_key, step_data in analysis_results.items():
        if isinstance(step_data, dict) and step_data.get('issues'):
            issues_text = step_data['issues'].strip()
            if issues_text and 'none' not in issues_text.lower(
            ) and 'not applicable' not in issues_text.lower():
                step_num = step_key.split('_')[1]
                all_issues.append(f"Step {step_num}: {issues_text}")

    # Add standard issues if none found
    if not all_issues:
        all_issues = [
            "Validate completeness of contract documentation and any amendments",
            "Confirm implementation timeline and system capability requirements",
            "Review final accounting treatment with external auditors prior to implementation"
        ]

    return all_issues


# Configure logging
logging.basicConfig(level=logging.INFO)


# Main function for Streamlit navigation
def main():
    """Main function called by Streamlit navigation."""
    render_asc606_page()


# For direct execution/testing
if __name__ == "__main__":
    render_asc606_page()
