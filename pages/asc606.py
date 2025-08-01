"""
ASC 606 Revenue Recognition Analysis Page
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

try:
    from core.models import ContractData, ASC606Analysis
except ImportError:
    # Fallback import handling
    sys.path.append('.')
    from core.models import ContractData, ASC606Analysis
from utils.asc606_analyzer import ASC606Analyzer
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


def render_tab1_contract_details() -> dict:
    """Render Tab 1: Contract details and document upload"""
    st.subheader(":material/contract: Enter Key Contract Details")
    
    col1, col2 = st.columns(2, gap="small")
    with col1:
        analysis_title = st.text_input(
            "Analysis Title *",
            placeholder="e.g., Q4 Project Phoenix SOW",
            help="A unique name to identify this contract analysis.")
    with col2:
        customer_name = st.text_input(
            "Customer Name *",
            placeholder="e.g., ABC Corporation",
            help="The name of the customer or end user of the goods or services provided.")
    
    col3, col4 = st.columns(2, gap="small")
    with col3:
        contract_types = st.multiselect(
            "Contract Document Types Included *", [
                "Online Terms and Conditions",
                "Master Services Agreement (MSA)",
                "Statement of Work (SOW)",
                "Software as a Service (SaaS) Agreement",
                "Software License Agreement",
                "Professional Services Agreement",
                "Sales Order / Order Form", "Purchase Order (PO)",
                "Contract Amendment / Addendum", "Change Order",
                "Reseller / Partner Agreement", "Invoice", "Other"
            ],
            help="Select all applicable document types. This helps the AI understand the relationship between the files (e.g., that an SOW is governed by an MSA).")
    with col4:
        currency = st.selectbox(
            "Currency *",
            ["USD", "EUR", "GBP", "CAD", "AUD", "KRW", "JPY", "Other"],
            help="Select the contract's primary currency. This provides context for the AI and is used in relation to the Materiality Threshold set in Tab 3.")
    
    col5, col6 = st.columns(2, gap="small")
    with col5:
        contract_start = st.date_input(
            "Contract Start Date *",
            help="The effective start date of the contractual period being analyzed.")
    with col6:
        contract_end = st.date_input(
            "Contract End Date *",
            help="The effective end date of the contractual period being analyzed.")
    
    arrangement_description = st.text_area(
        "Overall Arrangement Summary (Optional)",
        placeholder='e.g., "New 3-year SaaS license with one-time setup fee."',
        height=100,
        help="Provide a one-sentence summary of the deal. This gives the AI crucial high-level context before it analyzes the details.")
    
    st.subheader(":material/upload_file: Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload All Related Contract Documents *",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="Crucial: Upload the complete set of related documents for this arrangement. Missing documents can lead to incomplete or inaccurate results.")
    
    st.markdown("---")
    with st.container(border=True):
        st.info("Once the fields above are complete, continue to the **2️⃣ Provide Context** tab.")
    
    return {
        "analysis_title": analysis_title,
        "customer_name": customer_name,
        "contract_types": contract_types,
        "currency": currency,
        "contract_start": contract_start,
        "contract_end": contract_end,
        "arrangement_description": arrangement_description,
        "uploaded_files": uploaded_files
    }


def render_tab2_asc606_assessment() -> dict:
    """Render Tab 2: ASC 606 specific assessment questions"""
    st.subheader(":material/question_answer: Provide Key Considerations for 5-Step Model")

    # Initialize all optional detail variables to None to prevent errors
    original_contract_uploaded = None
    principal_agent_details = None
    variable_consideration_details = None
    financing_component_details = None
    noncash_consideration_details = None
    consideration_payable_details = None

    with st.expander("**Step 1: Identify the Contract (required)**", expanded=True):
        col1, col2 = st.columns(2, gap="medium")
        with col1:
            collectibility = st.toggle(
                "Collectibility is probable *",
                value=True,
                help="A contract does not exist under ASC 606 if collection is not probable.")
            is_modification = st.toggle(
                "This is a contract modification *",
                value=False,
                help="Select if this modifies an existing contract. This tells the AI to apply specific modification accounting rules (ASC 606-10-25-10 to 13) instead of treating it as a new contract.")
        with col2:
            is_combined_contract = st.toggle(
                "Evaluate docs as one contract? *",
                value=True,
                help="Per ASC 606-10-25-9, contracts entered into at or near the same time with the same customer should be combined if certain criteria are met. Select if these documents should be treated as a single accounting contract.")
            original_contract_uploaded = st.toggle(
                "Is the original contract uploaded? *",
                value=False,
                disabled=not is_modification)

    with st.expander("**Step 2: Identify Performance Obligations (optional)**"):
        st.info("The AI will analyze the contract(s) to identify distinct goods or services.", icon="🤖")
        principal_agent_involved = st.toggle(
            "Is a third party involved in providing goods or services?",
            help="Select if a third party is involved. This directs the AI to perform a principal vs. agent analysis (ASC 606-10-55-36) to determine if revenue should be recognized gross or net.")
        if principal_agent_involved:
            principal_agent_details = st.text_area(
                "Describe the arrangement and specify who controls the good/service:",
                placeholder="e.g., We are an agent for Party X's software...",
                label_visibility="collapsed")

    with st.expander("**Step 3: Determine the Transaction Price (optional)**"):
        col3, col4 = st.columns(2, gap="medium")
        with col3:
            variable_consideration_involved = st.toggle(
                "Is there variable consideration?",
                help="Select if the price includes items like bonuses, penalties, discounts, rebates, refunds, credits, incentives, performance bonuses, or other similar items. This prompts the AI to assess whether the variable amount should be estimated and included in the transaction price.")
            financing_component_involved = st.toggle(
                "Is there a significant financing component?",
                help="This occurs when the timing of payments provides the customer or the entity with a significant benefit of financing.")
        with col4:
            noncash_consideration_involved = st.toggle(
                "Is there noncash consideration?",
                help="Noncash consideration includes goods, services, or other noncash items that a customer contributes.")
            consideration_payable_involved = st.toggle(
                "Is consideration payable to customer?",
                help="This includes payments to the customer (or parties that purchase from the customer) such as coupons, vouchers, or credits.")

        # Conditional text areas for Step 3
        if variable_consideration_involved:
            variable_consideration_details = st.text_area(
                "Details on variable consideration:",
                placeholder="e.g., 20% performance bonus if project completed early.",
                label_visibility="collapsed")
        if financing_component_involved:
            financing_component_details = st.text_area(
                "Details on financing component:",
                placeholder="e.g., Customer pays upfront for a 3-year service.",
                label_visibility="collapsed")
        if noncash_consideration_involved:
            noncash_consideration_details = st.text_area(
                "Details on noncash consideration:",
                placeholder="e.g., Customer provides equipment valued at $50K.",
                label_visibility="collapsed")
        if consideration_payable_involved:
            consideration_payable_details = st.text_area(
                "Details on consideration payable:",
                placeholder="e.g., Customer receives a $5,000 credit for marketing.",
                label_visibility="collapsed")

    with st.expander("**Step 4: Allocate the Transaction Price**"):
        ssp_represents_contract_price = st.toggle(
            "Do contract prices represent Standalone Selling Price (SSP)?",
            value=True,
            help="SSP is the price at which you would sell a good or service separately.")

    with st.expander("**Step 5: Recognize Revenue**"):
        revenue_recognition_timing_details = st.text_area(
            "Describe when control transfers for each major performance obligation:",
            placeholder="e.g., Software license delivered upfront; support services provided evenly over 12 months.")

    st.markdown("---")
    st.info("Continue to the **3️⃣ Generate the Memo** tab.")

    return {
        "collectibility": collectibility,
        "is_combined_contract": is_combined_contract,
        "is_modification": is_modification,
        "original_contract_uploaded": original_contract_uploaded,
        "principal_agent_involved": principal_agent_involved,
        "principal_agent_details": principal_agent_details,
        "variable_consideration_involved": variable_consideration_involved,
        "variable_consideration_details": variable_consideration_details,
        "financing_component_involved": financing_component_involved,
        "financing_component_details": financing_component_details,
        "noncash_consideration_involved": noncash_consideration_involved,
        "noncash_consideration_details": noncash_consideration_details,
        "consideration_payable_involved": consideration_payable_involved,
        "consideration_payable_details": consideration_payable_details,
        "ssp_represents_contract_price": ssp_represents_contract_price,
        "revenue_recognition_timing_details": revenue_recognition_timing_details
    }


def render_tab3_analysis_config() -> dict:
    """Render Tab 3: Analysis focus and audience configuration"""
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
    
    # Key Focus Areas - The most important steering input
    key_focus_areas = st.text_area(
        "Key Focus Areas / Specific Questions (Optional)",
        placeholder=("Example: 'The main uncertainty is whether the implementation services are distinct from the "
                     "SaaS license. Please analyze this thoroughly, referencing the criteria in ASC 606-10-25-21.'"),
        height=100,
        help="Direct the AI to analyze specific clauses, risks, or uncertainties you have identified. This is the most effective way to improve the analysis.")

    col1, col2 = st.columns(2, gap="small")
    with col1:
        memo_audience = st.selectbox(
            "Tailor Memo for Audience (Optional)",
            ["Technical Accounting Team / Audit File", "Management Review", "Deal Desk / Sales Team"],
            index=0,  # Default to the most comprehensive option
            help=AUDIENCE_HELP_TEXT)

    with col2:
        # Materiality Threshold for financial significance
        materiality_threshold = st.number_input(
            "Materiality Threshold (Optional)",
            min_value=0,
            value=1000,
            step=1000,
            help="The AI will use this to assess the financial significance of contract elements like bonuses, penalties, or discounts, and focus its commentary accordingly.")

    return {
        "key_focus_areas": key_focus_areas,
        "memo_audience": memo_audience,
        "materiality_threshold": materiality_threshold
    }


def validate_form_data(tab1_data: dict, tab2_data: dict) -> list:
    """Validate required fields from all tabs"""
    errors = []
    
    # Tab 1 validations
    if not tab1_data["analysis_title"]:
        errors.append("Analysis Title is required (Tab 1).")
    if not tab1_data["customer_name"]:
        errors.append("Customer Name is required (Tab 1).")
    if not tab1_data["contract_types"]:
        errors.append("At least one Document Type must be selected (Tab 1).")
    if not tab1_data["currency"]:
        errors.append("Currency is required (Tab 1).")
    if not tab1_data["contract_start"]:
        errors.append("Contract Start Date is required (Tab 1).")
    if not tab1_data["contract_end"]:
        errors.append("Contract End Date is required (Tab 1).")
    
    # This check can remain, but it should be separate
    if tab1_data["contract_start"] and tab1_data["contract_end"]:
        if tab1_data["contract_end"] < tab1_data["contract_start"]:
            errors.append("Contract End Date cannot be before the Contract Start Date (Tab 1).")
    if not tab1_data["uploaded_files"]:
        errors.append("At least one document must be uploaded (Tab 1).")

    # Tab 2 validations
    if tab2_data["is_modification"] and tab2_data["original_contract_uploaded"] is None:
        errors.append("When 'This is a contract modification' is on, you must also specify if the original contract is uploaded (Tab 2).")

    return errors


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
st.title("ASC 606: Contract Review Memo Generator")
st.info(
    """
    This tool analyzes your contract documents to generate a comprehensive, professional ASC 606 memo.
    
    **For the best results:**
    - **Upload Complete Documents:** Include all related contracts, SOWs, and amendments.
    - **Add Crucial Context:** Use the tabs below to guide the AI on key terms, judgments, and focus areas.

    The more context you provide, the more tailored and accurate your final memo will be.
    """,
    icon="💡")

debug_config = create_debug_sidebar()

# Main application logic - refactored with dedicated tab functions
if st.session_state.analysis_results is None:

    tab1, tab2, tab3 = st.tabs([
        "**1️⃣ Define the Contract**", "**2️⃣ Provide Context**",
        "**3️⃣ Generate the Memo**"
    ])

    # Render each tab using dedicated functions for cleaner architecture
    with tab1:
        tab1_data = render_tab1_contract_details()

    with tab2:
        tab2_data = render_tab2_asc606_assessment()

    with tab3:
        tab3_data = render_tab3_analysis_config()

        # Validate form data using the new validation function
        validation_errors = validate_form_data(tab1_data, tab2_data)
        
        st.markdown("---")

        if st.button("📝 Generate the Memo", use_container_width=True, type="primary"):
            if validation_errors:
                st.error("Please fix the following issues before submitting:")
                [st.warning(f"• {e}") for e in validation_errors]
                st.stop()

            # Continue with analysis workflow (this would connect to the existing analysis logic)
            # Use a generic, static label for the status box itself. This will be small.
            with st.status("Analysis in progress, please be patient...", expanded=True) as status:
                try:
                    # Merge all form data for processing  
                    all_form_data = {**tab1_data, **tab2_data, **tab3_data}
                    
                    # Enhanced text extraction with fail-safe policy
                    # Use st.write for all our dynamic steps so they have a consistent, larger font.
                    st.write("➡️ **Verifying documents and extracting texts...**")
                    all_extracted_text_with_sources = []
                    failed_files = []

                    for f in all_form_data["uploaded_files"]:
                        try:
                            extraction_result = extractor.extract_text(f)
                            if extraction_result and extraction_result.get('text'):
                                # Prepend the document name as a clear header for source identification
                                document_header = f"--- START OF DOCUMENT: {f.name} ---\n\n"
                                full_text = document_header + extraction_result['text']
                                all_extracted_text_with_sources.append(full_text)
                            else:
                                failed_files.append(f.name)
                        except Exception:
                            failed_files.append(f.name)

                    # Check for failures and decide whether to continue or stop
                    if failed_files:
                        successful_files = len(all_form_data["uploaded_files"]) - len(failed_files)
                        if successful_files == 0:
                            error_message = (
                                f"**Text extraction failed for all uploaded file(s):**\n"
                                f"- `{'`, `'.join(failed_files)}`\n\n"
                                "**Please check the file(s) and try again. Common reasons for failure include:**\n"
                                "- The file is password-protected.\n"
                                "- The PDF is an image-only scan with no machine-readable text.\n"
                                "- The file is corrupted or in an unsupported format."
                            )
                            st.error(error_message, icon="🚨")
                            st.stop()
                        else:
                            warning_message = (
                                f"⚠️ **Warning:** Text extraction failed for {len(failed_files)} file(s): `{'`, `'.join(failed_files)}`\n\n"
                                f"**Continuing analysis with {successful_files} successful file(s).** "
                                "The failed files may be corrupted, password-protected, or image-only scans."
                            )
                            st.warning(warning_message, icon="⚠️")

                    # The new combined_text now contains source information for each document
                    combined_text = "\n\n--- END OF DOCUMENT ---\n\n".join(all_extracted_text_with_sources)

                    # Create ContractData object from all form data
                    contract_data = ContractData(
                        analysis_title=all_form_data.get("analysis_title", ""),
                        customer_name=all_form_data.get("customer_name", ""),
                        arrangement_description=all_form_data.get("arrangement_description", ""),
                        contract_start=all_form_data.get("contract_start"),
                        contract_end=all_form_data.get("contract_end"),
                        currency=all_form_data.get("currency", "USD"),
                        uploaded_file_name=", ".join([f.name for f in all_form_data["uploaded_files"]]),
                        document_names=[f.name for f in all_form_data["uploaded_files"]],  # Individual filenames for memo
                        contract_types=all_form_data.get("contract_types", []),
                        # New steering fields from Tab 3
                        key_focus_areas=all_form_data.get("key_focus_areas", ""),
                        memo_audience=all_form_data.get("memo_audience", "Technical Accounting Team / Audit File"),
                        materiality_threshold=all_form_data.get("materiality_threshold", 1000),
                        # All data from Tab 2
                        collectibility=all_form_data.get("collectibility", True),
                        is_combined_contract=all_form_data.get("is_combined_contract", True),
                        is_modification=all_form_data.get("is_modification", False),
                        original_contract_uploaded=all_form_data.get("original_contract_uploaded"),
                        principal_agent_involved=all_form_data.get("principal_agent_involved", False),
                        principal_agent_details=all_form_data.get("principal_agent_details"),
                        variable_consideration_involved=all_form_data.get("variable_consideration_involved", False),
                        variable_consideration_details=all_form_data.get("variable_consideration_details"),
                        financing_component_involved=all_form_data.get("financing_component_involved", False),
                        financing_component_details=all_form_data.get("financing_component_details"),
                        noncash_consideration_involved=all_form_data.get("noncash_consideration_involved", False),
                        noncash_consideration_details=all_form_data.get("noncash_consideration_details"),
                        consideration_payable_involved=all_form_data.get("consideration_payable_involved", False),
                        consideration_payable_details=all_form_data.get("consideration_payable_details"),
                        ssp_represents_contract_price=all_form_data.get("ssp_represents_contract_price", True),
                        revenue_recognition_timing_details=all_form_data.get("revenue_recognition_timing_details", "")
                    )

                    st.write("➡️ **Processing your inputs...**")
                    # Contract data object creation happens here (already done above)
                    
                    st.write("➡️ **Running AI analysis...**")
                    # Use asyncio.run to execute the async analyzer method
                    analysis_results = asyncio.run(analyzer.analyze_contract(combined_text, contract_data, debug_config=debug_config))
                    st.session_state.analysis_results = analysis_results
                    st.session_state.contract_data = contract_data
                    
                    # The label here updates the small text at the top of the box.
                    status.update(label="✅ Analysis complete!", state="complete")
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error("An unexpected error occurred during the analysis. Please try again. "
                            "If the problem persists, please contact support.")
                    # Only show the full technical error if debug mode is on
                    if debug_config.get("show_raw_response", False):
                        st.subheader("🔧 Technical Error Details")
                        st.exception(e)
                    st.stop()

else:
    # Display results (existing results display code would go here)
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

    # Analysis status - metrics disabled
    with st.container(border=True):
        st.markdown("**✅ Analysis Complete**")
        st.write("Professional ASC 606 memo generated using hybrid RAG system with authoritative sources.")

    st.subheader("📋 ASC 606 Accounting Memo")
    
    memo = getattr(analysis_results, 'professional_memo', None)
    
    if memo:
        # --- 1. MEMO ACTIONS (Buttons First) ---
        with st.container(border=True):
            st.markdown("**Memo Actions**")
            st.write("Your analysis is complete. Choose an option below to view or download the memo.")

            # Generate the HTML content once to be used for both the link and the preview
            from utils.html_export import convert_memo_to_html, render_view_in_browser_button
            from utils.llm import create_docx_from_text
            
            html_content = convert_memo_to_html(memo, contract_data)
            analysis_title = contract_data.analysis_title if contract_data and contract_data.analysis_title else "ASC606_Analysis"

            # Keep the download buttons in columns for alignment
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                try:
                    docx_content = create_docx_from_text(memo, contract_data)
                    st.download_button(
                        label="📄 Download DOCX",
                        data=docx_content,
                        file_name=f"{analysis_title.replace(' ', '_')}_ASC606_Memo.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        help="Download the memo as an editable Word document."
                    )
                except Exception as e:
                    st.error(f"Error generating DOCX: {str(e)}")

            # The other column can remain empty or contain another download link if needed.
            with dl_col2:
                # We can put a placeholder or another button here if we want.
                # For now, leaving it empty is fine.
                pass

            # **CRITICAL FIX:** Render the custom JavaScript button OUTSIDE the columns.
            # This gives it its own container and isolates it from other widget interactions.
            st.write("") # Adds a little vertical space
            render_view_in_browser_button(html_content)

        # --- 2. OPTIONAL MEMO PREVIEW (Below the buttons) ---
        st.markdown("---")  # Visual separator
        with st.expander("📄 Show Memo Preview", expanded=False):
            import streamlit.components.v1 as components

            # Display the styled HTML in a scrollable container
            components.html(html_content, height=800, scrolling=True)

    else:
        st.info("No memo was generated for this analysis.")
