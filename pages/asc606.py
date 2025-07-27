"""
ASC 606 Revenue Recognition Analysis Page
"""
import streamlit as st
import time
from datetime import date
from typing import Optional, List
from pydantic import ValidationError

# Import core components
try:
    from core.models import ContractData, ASC606Analysis
    from utils.asc606_analyzer import ASC606Analyzer
    from utils.document_extractor import DocumentExtractor
    from utils.llm import create_debug_sidebar, create_docx_from_text, create_pdf_from_text
except ImportError:
    # Handle missing imports gracefully
    st.error(
        "Core components not found. Please ensure all required modules are available."
    )
    st.stop()


def format_dict_as_markdown(data: dict) -> str:
    """Converts a dictionary to a readable Markdown bulleted list."""
    markdown_str = ""
    for key, value in data.items():
        # Format the key (e.g., 'is_enforceable' -> 'Is Enforceable')
        formatted_key = key.replace('_', ' ').replace('-', ' ').title()
        markdown_str += f"- **{formatted_key}:** {value}\n"
    return markdown_str


# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'contract_data' not in st.session_state:
    st.session_state.contract_data = None
if 'selected_standard' not in st.session_state:
    st.session_state.selected_standard = 'ASC 606'


# Initialize analyzer and extractor
@st.cache_resource
def get_cached_analyzer():
    return ASC606Analyzer()


analyzer = get_cached_analyzer()
extractor = DocumentExtractor()

# Standard header
st.title("ASC 606: Revenue Contract Analysis")
st.write(
    "**Powered by Authoritative FASB Codification & Leading Interpretive Guidance**\n\n"
    "An intelligent platform to generate comprehensive ASC 606 memos. Follow the numbered tabs to input contract details, provide context, and configure your analysis."
)

debug_config = create_debug_sidebar()

# Main application logic
if st.session_state.analysis_results is None:

    tab1, tab2, tab3 = st.tabs([
        "**1️⃣ Define the Contract**", "**2️⃣ Provide Context**",
        "**3️⃣ Generate the Memo**"
    ])

    with tab1:
        st.subheader(":material/contract: Enter Key Contract Details")
        col1, col2 = st.columns(2, gap="small")
        with col1:
            analysis_title = st.text_input(
                "Analysis Title *",
                placeholder="e.g., Q4 Project Phoenix SOW",
                help="A unique name to identify this analysis")
        with col2:
            customer_name = st.text_input(
                "Customer Name *",
                placeholder="e.g., ABC Corporation",
                help=
                "The legal entity name of the customer as it appears on the contract."
            )
        col3, col4 = st.columns(2, gap="small")
        with col3:
            contract_types = st.multiselect(
                "Contract Document Types Included *", [
                    "Master Agreement", "Master Services Agreement (MSA)",
                    "Statement of Work (SOW)",
                    "Software as a Service (SaaS) Agreement",
                    "Software License Agreement",
                    "Professional Services Agreement",
                    "Sales Order / Order Form", "Purchase Order (PO)",
                    "Contract Amendment / Addendum", "Change Order",
                    "Reseller / Partner Agreement", "Invoice", "Other"
                ],
                help="Select all document types that are part of this analysis."
            )
        with col4:
            currency = st.selectbox(
                "Currency *",
                ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "Other"],
                help="Primary currency for the contract")
        col5, col6 = st.columns(2, gap="small")
        with col5:
            contract_start = st.date_input(
                "Contract Start Date *",
                help=
                "The effective start date of the contractual period being analyzed."
            )
        with col6:
            contract_end = st.date_input(
                "Contract End Date *",
                help=
                "The effective end date of the contractual period being analyzed."
            )
        arrangement_description = st.text_area(
            "Overall Arrangement Summary (Optional)",
            placeholder=
            'e.g., "New 3-year SaaS license with one-time setup fee."',
            height=100,
            help=
            "Provide a one-sentence summary of the deal. This gives the AI crucial high-level context before it analyzes the details."
        )
        st.subheader(":material/upload_file: Upload Documents")
        uploaded_files = st.file_uploader(
            "Upload All Related Contract Documents *",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help=
            "Crucial: Upload the complete set of related documents for this arrangement."
        )
        st.markdown("---")
        with st.container(border=True):
            st.info(
                "Once the fields above are complete, continue to the **2️⃣ Provide Context** tab."
            )

    # Tab 2: Analysis Questions (New Compact Design with Expanders)
    with tab2:
        st.subheader(
            ":material/question_answer: Provide Key Considerations for 5-Step Model"
        )
        st.write(
            "Your answers address key areas of judgment and provide crucial context for the AI."
        )

        # Initialize all optional detail variables to None to prevent errors
        original_contract_uploaded = None
        principal_agent_details = None
        variable_consideration_details = None
        financing_component_details = None
        noncash_consideration_details = None
        consideration_payable_details = None

        with st.expander("**Step 1: Identify the Contract (required)**",
                         expanded=True):
            col1, col2 = st.columns(2, gap="medium")
            with col1:
                collectibility = st.toggle(
                    "Collectibility is probable *",
                    value=True,
                    help=
                    "A contract does not exist under ASC 606 if collection is not probable."
                )
                is_modification = st.toggle(
                    "This is a contract modification *",
                    value=False,
                    help=
                    "Select if this is an amendment, addendum, or change order that modifies an existing contract."
                )
            with col2:
                is_combined_contract = st.toggle(
                    "Evaluate docs as one contract? *",
                    value=True,
                    help=
                    "Per ASC 606-10-25-9, contracts entered into at or near the same time with the same customer should be combined if certain criteria are met. Select if these documents should be treated as a single accounting contract."
                )
                original_contract_uploaded = st.toggle(
                    "Is the original contract uploaded? *",
                    value=False,
                    disabled=not is_modification)

        with st.expander(
                "**Step 2: Identify Performance Obligations (optional)**"):
            st.info(
                "The AI will analyze the contract(s) to identify distinct goods or services.",
                icon="🤖")
            principal_agent_involved = st.toggle(
                "Is a third party involved in providing goods or services?",
                help=
                "Select if another party is involved in providing the goods or services to your end customer (e.g., you are reselling another company's product)."
            )
            if principal_agent_involved:
                principal_agent_details = st.text_area(
                    "Describe the arrangement and specify who controls the good/service:",
                    placeholder=
                    "e.g., We are an agent for Party X's software...",
                    label_visibility="collapsed")

        with st.expander(
                "**Step 3: Determine the Transaction Price (optional)**"):
            col3, col4 = st.columns(2, gap="medium")
            with col3:
                variable_consideration_involved = st.toggle(
                    "Includes variable consideration?")
                noncash_consideration_involved = st.toggle(
                    "Includes noncash consideration?")
            with col4:
                financing_component_involved = st.toggle(
                    "Includes significant financing?")
                consideration_payable_involved = st.toggle(
                    "Includes consideration payable?")

            if variable_consideration_involved:
                variable_consideration_details = st.text_area(
                    "Details on variable consideration:",
                    placeholder="e.g., A $10,000 bonus is 90% probable.",
                    label_visibility="collapsed")
            if financing_component_involved:
                financing_component_details = st.text_area(
                    "Details on financing component:",
                    placeholder=
                    "e.g., Customer pays upfront for a 3-year service.",
                    label_visibility="collapsed")
            if noncash_consideration_involved:
                noncash_consideration_details = st.text_area(
                    "Details on noncash consideration:",
                    placeholder=
                    "e.g., Customer provides equipment valued at $50K.",
                    label_visibility="collapsed")
            if consideration_payable_involved:
                consideration_payable_details = st.text_area(
                    "Details on consideration payable:",
                    placeholder=
                    "e.g., Customer receives a $5,000 credit for marketing.",
                    label_visibility="collapsed")

        with st.expander("**Step 4: Allocate the Transaction Price**"):
            ssp_represents_contract_price = st.toggle(
                "Do contract prices represent Standalone Selling Price (SSP)?",
                value=True,
                help=
                "SSP is the price at which you would sell a good or service separately."
            )

        with st.expander("**Step 5: Recognize Revenue**"):
            revenue_recognition_timing_details = st.text_area(
                "Describe when control transfers for each major performance obligation:",
                placeholder=
                "e.g., Software license delivered upfront; support services provided evenly over 12 months."
            )

        st.markdown("---")
        st.info("Continue to the **3️⃣ Generate the Memo** tab.")

    # Tab 3: Analysis Configuration and Execution
    with tab3:
        # Define the detailed help text as a constant for clarity
        AUDIENCE_HELP_TEXT = """
        Select the primary audience for the final memo. This adjusts the tone, focus, and level of technical detail. The underlying five-step analysis remains comprehensive for all options.

        • **Technical Accounting Team / Audit File (Default):**
          - **Focus:** Deep technical compliance and audit readiness.
          - **Content:** Assumes expert knowledge. Includes detailed step-by-step reasoning, direct quotations from ASC 606, and precise citations (e.g., ASC 606-10-55-34). This is the most detailed and formal output, suitable for internal accounting records and external auditors.

        • **Management Review:**
          - **Focus:** Key judgments, financial impact, and business implications.
          - **Content:** Summarizes critical conclusions upfront. Uses less technical jargon and focuses on the "so what" for decision-makers like the CFO or Controller. It answers questions like, "How does this contract affect our revenue forecast?"

        • **Deal Desk / Sales Team:**
          - **Focus:** Explaining the revenue recognition impact of specific contract terms.
          - **Content:** Translates complex accounting rules into practical guidance for teams structuring deals. It helps them understand how different clauses (e.g., acceptance terms, payment timing) can accelerate or defer revenue, enabling them to negotiate more effectively.
        """

        st.subheader(":material/grading: Set Analysis Focus & Audience")
        st.write(
            "Finalize your analysis by providing optional focus areas and audience preferences before generating the memo."
        )

        # Key Focus Areas - The most important steering input
        key_focus_areas = st.text_area(
            "Key Focus Areas / Specific Questions (Optional)",
            placeholder=
            ("Example: 'The main uncertainty is whether the implementation services are distinct from the "
             "SaaS license. Please analyze this thoroughly, referencing the criteria in ASC 606-10-25-21.'"
             ),
            height=100,
            help=
            "Direct the AI to analyze specific clauses, risks, or uncertainties you have identified. This is the most effective way to improve the analysis."
        )

        col1, col2 = st.columns(2, gap="small")
        with col1:
            memo_audience = st.selectbox(
                "Tailor Memo for Audience (Optional)",
                [
                    "Technical Accounting Team / Audit File",
                    "Management Review", "Deal Desk / Sales Team"
                ],
                index=0,  # Default to the most comprehensive option
                help=AUDIENCE_HELP_TEXT)

        with col2:
            # Materiality Threshold for financial significance
            materiality_threshold = st.number_input(
                "Materiality Threshold (Optional)",
                min_value=0,
                value=1000,
                step=1000,
                help=
                "The AI will use this to assess the financial significance of contract elements like bonuses, penalties, or discounts, and focus its commentary accordingly."
            )

        def validate_form():
            """Validate required fields from Tab 1"""
            errors = []
            if not analysis_title:
                errors.append("Analysis Title is required (Tab 1).")
            if not customer_name:
                errors.append("Customer Name is required (Tab 1).")
            if not contract_types:
                errors.append(
                    "At least one Document Type must be selected (Tab 1).")
            if not currency: errors.append("Currency is required (Tab 1).")
            if not contract_start:
                errors.append("Contract Start Date is required (Tab 1).")
            if not contract_end:
                errors.append("Contract End Date is required (Tab 1).")
            if contract_start and contract_end:
                if contract_end < contract_start:
                    errors.append(
                        "Contract End Date cannot be before the Contract Start Date (Tab 1)."
                    )
            if not uploaded_files:
                errors.append(
                    "At least one document must be uploaded (Tab 1).")

            if collectibility is None:
                errors.append("Collectibility must be specified (Tab 2).")
            if is_modification is None:
                errors.append(
                    "Contract Modification status must be specified (Tab 2).")
            if is_modification and original_contract_uploaded is None:
                errors.append(
                    "When 'This is a contract modification' is on, you must also specify if the original contract is uploaded (Tab 2)."
                )
            if is_combined_contract is None:
                errors.append(
                    "Combined Contract status must be specified (Tab 2).")

            return errors

        st.markdown("---")

        if st.button("📝 Generate the Memo",
                     use_container_width=True,
                     type="primary"):
            validation_errors = validate_form()
            if validation_errors:
                st.error("Please fix the following issues before submitting:")
                [st.warning(f"• {e}") for e in validation_errors]
                st.stop()

            with st.status("🔍 Analyzing contract...", expanded=True) as status:
                try:
                    # Enhanced text extraction with fail-safe policy
                    st.write(
                        "📄 Verifying and extracting text from documents...")
                    all_extracted_text = []
                    failed_files = []

                    for f in uploaded_files:
                        try:
                            extraction_result = extractor.extract_text(f)
                            # Check if the extraction returned a valid result with actual text
                            if extraction_result and extraction_result.get(
                                    'text'):
                                all_extracted_text.append(
                                    extraction_result['text'])
                            else:
                                # The file was processed but no text was found (e.g., a scanned image PDF)
                                failed_files.append(f.name)
                        except Exception:
                            # The extractor itself threw an error (e.g., corrupted or password-protected file)
                            failed_files.append(f.name)

                    # Check for failures and stop the process if any exist
                    if failed_files:
                        # Construct a helpful, multi-line error message
                        error_message = (
                            f"**Text extraction failed for the following file(s):**\n"
                            f"- `{'`, `'.join(failed_files)}`\n\n"
                            "**Please check the file(s) and try again. Common reasons for failure include:**\n"
                            "- The file is password-protected.\n"
                            "- The PDF is an image-only scan with no machine-readable text.\n"
                            "- The file is corrupted or in an unsupported format."
                        )
                        st.error(error_message, icon="🚨")
                        st.stop()  # Immediately halt the analysis

                    # This part only runs if all files were successful
                    combined_text = "\n\n--- END OF DOCUMENT ---\n\n".join(
                        all_extracted_text)

                    st.write("🧠 Processing your answers and guidance...")

                    # Create the ContractData object with the new steering fields
                    contract_data = ContractData(
                        analysis_title=analysis_title,
                        customer_name=customer_name,
                        arrangement_description=arrangement_description,
                        contract_start=contract_start,
                        contract_end=contract_end,
                        currency=currency,
                        uploaded_file_name=", ".join(
                            [f.name for f in uploaded_files]),
                        contract_types=contract_types,
                        # New steering fields from Tab 3
                        key_focus_areas=key_focus_areas,
                        memo_audience=memo_audience,
                        materiality_threshold=materiality_threshold,
                        # All data from Tab 2
                        collectibility=collectibility,
                        is_combined_contract=is_combined_contract,
                        is_modification=is_modification,
                        original_contract_uploaded=original_contract_uploaded,
                        principal_agent_involved=principal_agent_involved,
                        principal_agent_details=principal_agent_details,
                        variable_consideration_involved=
                        variable_consideration_involved,
                        variable_consideration_details=
                        variable_consideration_details,
                        financing_component_involved=
                        financing_component_involved,
                        financing_component_details=financing_component_details,
                        noncash_consideration_involved=
                        noncash_consideration_involved,
                        noncash_consideration_details=
                        noncash_consideration_details,
                        consideration_payable_involved=
                        consideration_payable_involved,
                        consideration_payable_details=
                        consideration_payable_details,
                        ssp_represents_contract_price=
                        ssp_represents_contract_price,
                        revenue_recognition_timing_details=
                        revenue_recognition_timing_details)

                    st.write("⚡ Running AI analysis...")
                    analysis_results = analyzer.analyze_contract(
                        combined_text,
                        contract_data,
                        debug_config=debug_config)
                    st.session_state.analysis_results = analysis_results
                    st.session_state.contract_data = contract_data
                    status.update(label="✅ Analysis complete!",
                                  state="complete")
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(
                        "An unexpected error occurred during the analysis. Please try again. "
                        "If the problem persists, please contact support.")

                    # Only show the full technical error if debug mode is on
                    if debug_config.get("show_raw_response", False):
                        st.subheader("🔧 Technical Error Details")
                        st.exception(e)
                    # Always stop after an error, regardless of debug mode
                    st.stop()

else:
    # Display results
    analysis_results = st.session_state.analysis_results
    contract_data = st.session_state.contract_data

    col1, col2 = st.columns([3, 1])
    with col1:
        analysis_title = contract_data.analysis_title if contract_data else "Unknown Analysis"
        st.subheader(f"📊 Analysis Results: {analysis_title}")
    with col2:
        if st.button("🔄 Start New Analysis", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Analysis metrics
    with st.container(border=True):
        st.markdown("**📊 Analysis Overview**")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric(
                "Source Quality",
                getattr(analysis_results, 'source_quality', 'N/A'),
                help=
                "This score (out of 100) reflects the quality and authority of the sources used for the analysis. Higher scores indicate reliance on direct FASB guidance, while lower scores may indicate reliance on interpretive or general knowledge."
            )
        with metrics_col2:
            memo_audience = contract_data.memo_audience if contract_data else "Unknown"
            st.metric("Audience", memo_audience.split(' / ')[0])
        with metrics_col3:
            currency = contract_data.currency if contract_data else "USD"
            st.metric("Currency", currency)

    # Five-step analysis summary
    st.markdown("---")
    st.subheader("📋 ASC 606 Five-Step Analysis Summary")

    steps = [("Contract Identification",
              getattr(analysis_results, 'step1_contract_identification',
                      'N/A')),
             ("Performance Obligations",
              getattr(analysis_results, 'step2_performance_obligations',
                      'N/A')),
             ("Transaction Price",
              getattr(analysis_results, 'step3_transaction_price', 'N/A')),
             ("Price Allocation",
              getattr(analysis_results, 'step4_price_allocation', 'N/A')),
             ("Revenue Recognition",
              getattr(analysis_results, 'step5_revenue_recognition', 'N/A'))]

    for i, (step_name, step_data) in enumerate(steps, 1):
        with st.expander(f"**Step {i}: {step_name}**", expanded=(i == 1)):
            if isinstance(step_data, dict):
                st.markdown(format_dict_as_markdown(step_data))
            else:
                st.markdown(str(step_data))

    # Professional memo
    st.markdown("---")
    st.subheader("📋 Professional Accounting Memo")
    memo = getattr(analysis_results, 'professional_memo', None)
    if memo:
        with st.container(border=True):
            st.markdown(memo)
            # Create columns for the download buttons
            dl_col1, dl_col2 = st.columns(2)

            with dl_col1:
                analysis_title = contract_data.analysis_title if contract_data else "ASC606_Analysis"
                st.download_button(
                    label="📄 Download as .docx",
                    data=create_docx_from_text(memo),
                    file_name=
                    f"{analysis_title.replace(' ', '_')}_ASC606_Memo.docx",
                    mime=
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True)

            with dl_col2:
                analysis_title = contract_data.analysis_title if contract_data else "ASC606_Analysis"
                st.download_button(
                    label="📋 Download as .pdf",
                    data=create_pdf_from_text(
                        memo, title=analysis_title),
                    file_name=
                    f"{analysis_title.replace(' ', '_')}_ASC606_Memo.pdf",
                    mime="application/pdf",
                    use_container_width=True)
    else:
        st.info("No memo generated for this analysis.")

    # Additional sections for comprehensive results
    if debug_config.get("show_raw_response", False):
        st.markdown("---")
        st.subheader("🔧 Debug Information")
        st.json(analysis_results.__dict__ if hasattr(
            analysis_results, '__dict__') else str(analysis_results))

    # Citations and guidance
    if hasattr(analysis_results, 'citations') and analysis_results.citations:
        st.markdown("---")
        st.subheader("📚 Citations")
        for citation in analysis_results.citations:
            st.write(f"• {citation}")

    if hasattr(analysis_results, 'implementation_guidance'
               ) and analysis_results.implementation_guidance:
        st.markdown("---")
        st.subheader("💡 Implementation Guidance")
        for guidance in analysis_results.implementation_guidance:
            st.write(f"• {guidance}")

    if hasattr(
            analysis_results,
            'not_applicable_items') and analysis_results.not_applicable_items:
        st.markdown("---")
        st.subheader("❌ Not Applicable Items")
        for item in analysis_results.not_applicable_items:
            st.write(f"• {item}")
