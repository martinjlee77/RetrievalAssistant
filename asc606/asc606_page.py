"""
ASC 606 Contract Analysis Page
"""

import streamlit as st
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List

from shared.ui_components import SharedUIComponents
from shared.auth_utils import require_authentication, show_credits_warning, auth_manager
from shared.billing_manager import billing_manager
from shared.preflight_pricing import preflight_pricing
from shared.wallet_manager import wallet_manager
from shared.analysis_manager import analysis_manager
# CleanMemoGenerator import moved to initialization section
import tempfile
import os
from asc606.step_analyzer import ASC606StepAnalyzer
from asc606.knowledge_search import ASC606KnowledgeSearch
from utils.document_extractor import DocumentExtractor

logger = logging.getLogger(__name__)

def render_asc606_page():
    """Render the ASC 606 analysis page."""
    
    # Authentication check - must be logged in to access
    if not require_authentication():
        return  # User will see login page
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Page header
    st.title(":primary[ASC 606: Revenue Recognition]")
    with st.container(border=True):
        st.markdown(":primary[**Purpose:**] Automatically analyze revenue contracts and generate a first draft of professional ASC 606 memo. Simply upload your documents to begin.")
    
    # Check for active analysis first
    if analysis_manager.show_active_analysis_warning():
        return  # User has active analysis, show warning and exit
    
    # Check for existing completed analysis in session state (restore persistence)
    session_id = st.session_state.get('user_session_id', '')
    if session_id:
        analysis_key = f'asc606_analysis_complete_{session_id}'
        memo_key = f'asc606_memo_data_{session_id}'
        
        # If analysis is complete and memo exists, show results instead of file upload
        if st.session_state.get(analysis_key, False) and st.session_state.get(memo_key):
            st.success("✅ **Analysis Complete!** This AI-generated analysis requires review by qualified accounting professionals and should be approved by management before use.")
            st.markdown("""📄 **Your ASC 606 memo is ready below.** To save the results, you can either:

- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
- **Download:** Download the memo as a Markdown, PDF, or Word (.docx) file for later use.
                        """)
            
            # Quick action buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<a href="#save-your-memo" style="text-decoration: none;"><button style="width: 100%; padding: 0.5rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer;">⬇️ Jump to Downloads</button></a>', unsafe_allow_html=True)
            with col2:
                if st.button("🔄 Start New Analysis", type="secondary", use_container_width=True, key="top_new_analysis_existing"):
                    # Clear session state for new analysis
                    keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc606' in k.lower()]
                    for key in keys_to_clear:
                        del st.session_state[key]
                    st.rerun()
            
            st.markdown("---")
            
            # Display the existing memo with enhanced downloads
            from asc606.clean_memo_generator import CleanMemoGenerator
            memo_generator = CleanMemoGenerator()
            memo_data = st.session_state[memo_key]
            # Extract memo content from stored dictionary
            memo_content = memo_data['memo_content'] if isinstance(memo_data, dict) else memo_data
            # Get analysis_id from memo_data or generate fallback
            analysis_id = memo_data.get('analysis_id') if isinstance(memo_data, dict) else f"memo_{session_id}"
            memo_generator.display_clean_memo(memo_content, analysis_id)
            
            # Re-run policy note and "Analyze Another" button
            st.markdown("---")
            st.info("📋 **Need changes to this memo?** Due to resource costs, re-runs require pre-approval. Contact Support to request a re-run.")
            
            if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True, key="bottom_new_analysis_existing"):
                # Clear session state for new analysis
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc606' in k.lower()]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
            
            return  # Exit early, don't show file upload interface
    
    # Get user inputs with progressive disclosure - wrap in container to allow clearing
    upload_form_container = st.empty()
    with upload_form_container.container():
        uploaded_files, additional_context, is_ready = get_asc606_inputs_new()

    # Show pricing information immediately when files are uploaded (regardless of is_ready)
    pricing_result = None
    pricing_container = st.empty()  # Create clearable container FIRST (before if block)
    if uploaded_files:
        # Process files for pricing - dynamic cost updating with progress indicator
        with st.spinner("📄 Analyzing document content and calculating costs. Please be patient for large files."):
            pricing_result = preflight_pricing.process_files_for_pricing(uploaded_files)

        if pricing_result['success']:
            with pricing_container.container():  # Put EVERYTHING inside
                st.markdown("### :primary[Analysis Pricing]")
                st.info(pricing_result['billing_summary'])

                # Show file processing details
                if pricing_result.get('processing_errors'):
                    st.warning(f"⚠️ **Some files had issues:** {'; '.join(pricing_result['processing_errors'])}")

                # Display document quality feedback
                if pricing_result.get('file_details'):
                    SharedUIComponents.display_document_quality_feedback(pricing_result['file_details'])  
        
        else:
            # Handle different error types
            if pricing_result.get('error') == 'scanned_pdf_detected':
                st.error(pricing_result.get('user_message', 'Scanned PDF detected'))
                
                # Add helpful expandable section
                with st.expander("💡 Detailed Instructions"):
                    st.markdown("""
                    **Using ChatGPT-4 Vision:**
                    1. Go to ChatGPT-4 with Vision
                    2. Upload your scanned PDF
                    3. Ask: "Please convert this document to clean, searchable text"
                    4. Copy the text and create a new Word/PDF document
                    5. Upload the new text-based document here
                    
                    **Alternative Tools:**
                    - Adobe Acrobat (OCR feature)
                    - Google Docs (automatically OCRs uploaded PDFs)
                    - Microsoft Word (Insert > Object > Text from File)
                    """)
            else:
                st.error(f"❌ **File Processing Failed**\n\n{pricing_result['error']}")

    # Preflight pricing and payment flow (only proceed if ready AND pricing successful)
    if is_ready and pricing_result and pricing_result['success']:
        
        # Get required price and check wallet balance
        required_price = pricing_result['tier_info']['price']
        user_token = auth_manager.get_auth_token()
        
        # Get wallet balance
        if not user_token:
            st.error("❌ Authentication required. Please refresh the page and log in again.")
            return
        wallet_info = wallet_manager.get_user_balance(user_token)
        current_balance = wallet_info.get('balance', 0.0)
        
        # Check if user has sufficient credits
        credit_check = preflight_pricing.check_sufficient_credits(required_price, current_balance)
        
        # Credit balance display - store in variable so we can clear it
        credit_container = st.empty()       
        if credit_check['can_proceed']:
            msg = (
                f"{credit_check['message']}\n"
                f"After this analysis, you will have \\${credit_check['credits_remaining']:.0f} remaining."
            )
            credit_container.info(msg)
            can_proceed = True
        else:
            credit_container.error(credit_check['message'])
            
            # Show wallet top-up options
            selected_amount = wallet_manager.show_wallet_top_up_options(current_balance, required_price)
            
            if selected_amount:
                # Process credit purchase
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                purchase_result = wallet_manager.process_credit_purchase(user_token, selected_amount)
                
                if purchase_result['success']:
                    st.success(purchase_result['message'])
                    st.rerun()  # Refresh to update balance
                else:
                    st.error(purchase_result['message'])
            
            can_proceed = False
        
        # Analysis section
        if can_proceed:
            warning_placeholder = st.empty()  # Create a placeholder for the warning
            warning_placeholder.info(
                "⚠️ **IMPORTANT:** Analysis takes up to **3-20 minutes**. Please don't close this tab until complete"
            )
            
            if st.button("3️⃣ Confirm & Analyze",
                       type="primary",
                       use_container_width=True,
                       key="asc606_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()  # Clear the warning 
                pricing_container.empty()    # Clear pricing information
                credit_container.empty()     # Clear credit balance info
                upload_form_container.empty()  # Clear the upload form
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                perform_asc606_analysis_new(pricing_result, additional_context, user_token)
        else:
            st.button("3️⃣ Insufficient Credits", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc606_analyze_disabled")
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Confirm & Analyze", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc606_analyze_disabled")


def get_asc606_inputs_new():
    """Get ASC 606 specific inputs with new preflight system."""
    
    # Document upload section       
    uploaded_files = st.file_uploader(
        "1️⃣ Upload revenue contract documents - PDF or DOCX files (required) - NOTE: completeness and document quality will drive the quality of the memo.",
        type=['pdf', 'docx'],
        accept_multiple_files=True,
        help="Upload complete revenue contracts, agreements, or amendments for ASC 606 analysis. Incomplete information or poor quality documents provided will result in incomplete or low quality analysis. For PDFs, if available, always use the original text-based version.",
        key=f"asc606_uploader_{st.session_state.get('file_uploader_key', 0)}"
    )

    # Additional info (optional)
    additional_context = st.text_area(
        "2️⃣ Additional information or concerns (optional)",
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents (e.g., verbal agreement) or specify your areas of focus or concerns.",
        height=100)
    
    # Determine if ready to proceed with word count enforcement
    if uploaded_files:
        # Check total word count across all files
        try:
            from utils.document_extractor import DocumentExtractor
            extractor = DocumentExtractor()
            total_words = 0
            
            for file in uploaded_files:
                file_text = extractor.extract_text(file)['text']
                total_words += len(file_text.split())
            
            if total_words > 60000:
                st.error(f"""
                📄 **Document too large ({total_words:,} words)**
                
                Contracts over 60,000 words require custom handling and consultation. 
                
                Please contact our support team at **support@veritaslogic.ai** for:
                - Large contract analysis (60k+ words)
                - Complex multi-document arrangements  
                - Custom enterprise solutions
                
                We'll provide dedicated assistance for your large-scale analysis needs.
                """)
                is_ready = False
            else:
                is_ready = True
        except Exception as e:
            # If word count check fails, allow to proceed but log the issue
            logger.warning(f"Word count check failed: {str(e)}")
            is_ready = True
    else:
        is_ready = False
    
    return uploaded_files, additional_context, is_ready

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




def _extract_customer_name(contract_text: str) -> str:
    """Extract the customer/recipient party name from typical contract preambles or headings."""
    try:
        import re
        
        if not contract_text:
            return "Customer"

        # Preprocess: examine the first part of the document (preamble/definitions often appear early)
        sample = contract_text[:6000]

        # Normalize quotes and whitespace
        sample = sample.replace(""", '"').replace(""", '"').replace("'", "'")
        sample = re.sub(r'[ \t]+', ' ', sample)

        # Role vocabularies (lowercase)
        customer_roles = {
            "customer", "client", "buyer", "purchaser", "licensee", "lessee",
            "subscriber", "tenant", "end user", "end-user", "grantee",
            # PO/invoice style labels treated as customer indicators:
            "bill to", "sold to", "ship to"
        }
        vendor_roles = {
            "vendor", "supplier", "seller", "licensor", "lessor",
            "service provider", "provider", "contractor", "consultant", "reseller"
        }

        def clean_name(name: str) -> str:
            # Trim, remove enclosing quotes/parentheses, compress spaces, strip trailing punctuation
            n = name.strip().strip(' "').strip()
            n = re.sub(r'\s+', ' ', n)
            # Remove common trailing descriptors like .,;:)
            n = re.sub(r'[\s\.,;:)\]]+$', '', n)
            # Avoid obvious non-names
            if len(n) < 3 or len(n) > 120:
                return ""
            return n

        def plausible_company(name: str) -> bool:
            if not name:
                return False
            # Avoid address-like strings
            addr_tokens = {"street", "st.", "road", "rd.", "avenue", "ave.", "suite", "ste.", "floor", "fl.", "drive", "dr.", "blvd", "boulevard", "lane", "ln.", "way", "p.o.", "po box", "box"}
            lname = name.lower()
            if any(t in lname for t in addr_tokens):
                return False
            # Contains at least one letter and not mostly numbers
            if not re.search(r'[A-Za-z]', name):
                return False
            # Reasonable length already checked in clean_name
            return True

        # PRIORITY 1: Preamble with both parties defined by role, e.g.:
        # "between Acme, Inc. ("Supplier") and Beta LLC ("Customer")"
        preamble_pair = re.compile(
            r'\bbetween\s+(?P<p1>[^,\n;]+?)\s*\(\s*(?:the\s+)?["\']?(?P<r1>[^"\')]+)["\']?\s*\)\s*(?:,|and)?\s*and\s+(?P<p2>[^,\n;]+?)\s*\(\s*(?:the\s+)?["\']?(?P<r2>[^"\')]+)["\']?\s*\)',
            re.IGNORECASE | re.DOTALL
        )
        for m in preamble_pair.finditer(sample):
            p1, r1, p2, r2 = m.group('p1', 'r1', 'p2', 'r2')
            name_role_pairs = [
                (clean_name(p1), r1.strip().lower()),
                (clean_name(p2), r2.strip().lower())
            ]
            for name, role in name_role_pairs:
                if name and any(cr == role or role in cr for cr in customer_roles):
                    return name
            # If one is clearly vendor and the other not, pick the non-vendor
            roles = [r1.strip().lower(), r2.strip().lower()]
            names = [clean_name(p1), clean_name(p2)]
            if any(rv in vendor_roles for rv in roles):
                # choose the one whose role is not vendor-like
                for name, role in zip(names, roles):
                    if name and (role not in vendor_roles):
                        return name
            # If ambiguous, try r2 if it looks like a customer role
            if clean_name(p2) and plausible_company(clean_name(p2)):
                # Heuristic: often the second party is the customer
                return clean_name(p2)

        # PRIORITY 2: Single party labeled as customer-like in the preamble or headings:
        # e.g., 'and Global Dynamics Corp. ("Customer")'
        labeled_single = re.compile(
            r'\b(?:and\s+)?(?P<name>[^,\n;]+?)\s*\(\s*(?:the\s+)?["\']?(?P<role>Customer|Client|Buyer|Purchaser|Licensee|Lessee|Subscriber|Tenant|End[-\s]?User)["\']?\s*\)',
            re.IGNORECASE
        )
        for m in labeled_single.finditer(sample):
            name = clean_name(m.group('name'))
            if name and plausible_company(name):
                return name

        # PRIORITY 3: Header fields like "Customer: Acme, Inc." or "Licensee: Orion LLC" or "Bill To: ..."
        labeled_field = re.compile(
            r'\b(?P<label>Customer|Client|Buyer|Purchaser|Licensee|Lessee|Subscriber|Tenant|End[-\s]?User|Bill\s*To|Sold\s*To|Ship\s*To)\s*[:\-]\s*(?P<name>[A-Za-z0-9\.\,&\-\s]{3,120})',
            re.IGNORECASE
        )
        for m in labeled_field.finditer(sample):
            name = clean_name(m.group('name'))
            if name and plausible_company(name):
                return name

        # PRIORITY 4: If there is a preamble "between X and Y" without roles, try to pick the second party
        between_two = re.compile(
            r'\bbetween\s+(?P<p1>[^,\n;]+?)\s+and\s+(?P<p2>[^,\n;]+)',
            re.IGNORECASE
        )
        m = between_two.search(sample)
        if m:
            p2 = clean_name(m.group('p2'))
            if p2 and plausible_company(p2):
                return p2

        # LAST RESORT: Any plausible company name with common corporate suffixes
        company_suffix = re.compile(
            r'([A-Z][A-Za-z0-9&\.\- ]{2,80}?\s(?:Inc\.?|Incorporated|LLC|L\.L\.C\.|Ltd\.?|Limited|Corp\.?|Corporation|PLC|LP|LLP|GmbH|S\.?A\.?R\.?L\.?|S\.?A\.?|SAS|BV|NV|Pty\.?\s?Ltd\.?|Co\.?))\b'
        )
        matches = company_suffix.findall(sample)
        if matches:
            # Prefer a name that is near customer-like labels elsewhere
            for name in matches:
                if plausible_company(clean_name(name)):
                    return clean_name(name)

        return "Customer"

    except Exception as e:
        # Keep existing logging if present
        if 'logger' in globals():
            logger.error(f"Error extracting customer name: {str(e)}")
        return "Customer"


def _generate_analysis_title() -> str:
    """Generate analysis title with timestamp."""
    return f"ASC606_Analysis_{datetime.now().strftime('%m%d_%H%M%S')}"

def perform_asc606_analysis_new(pricing_result: Dict[str, Any], additional_context: str, user_token: str):
    """Perform ASC 606 analysis with new billing system integration."""
    
    analysis_id = None
    
    try:
        # Step 1: Start analysis tracking
        analysis_details = {
            'asc_standard': 'ASC 606',
            'total_words': pricing_result['total_words'],
            'file_count': pricing_result['file_count'],
            'tier_info': pricing_result['tier_info'],
            'cost_charged': pricing_result['tier_info']['price']
        }
        
        analysis_id = analysis_manager.start_analysis(analysis_details)
        
        # Step 2: Payment will be processed when analysis completes (no upfront charging)
        
        # Step 3: Reconstruct combined text from file details
        combined_text = ""
        filename_list = []
        
        for file_detail in pricing_result['file_details']:
            if 'text_content' in file_detail and file_detail['text_content'].strip():
                combined_text += f"\\n\\n=== {file_detail['filename']} ===\\n\\n{file_detail['text_content']}"
                filename_list.append(file_detail['filename'])
            else:
                # Fallback if text_content is missing
                combined_text += f"\\n\\n=== {file_detail['filename']} ===\\n\\n[File content extraction failed]"
                filename_list.append(file_detail['filename'])
        
        filename = ", ".join(filename_list)
        
        # Check if we have valid content
        if not combined_text.strip() or "[File content extraction failed]" in combined_text:
            st.error("❌ **Technical Implementation Note**: Full file content reconstruction not yet implemented.")
            st.info("🔄 **Temporary Workaround**: This integration is in progress. The preflight pricing system is working, but the analysis part needs the file content to be properly passed through.")
            
            # Mark analysis as failed (no refund needed since payment happens on completion)
            if analysis_id:
                analysis_manager.complete_analysis(analysis_id, success=False, error_message="File content reconstruction not implemented")
            
            st.info("ℹ️ **No Charge Applied**: Since the analysis could not be completed, you were not charged.")
            return
        
        # Step 4: Reset API cost tracking for new analysis
        from shared.api_cost_tracker import reset_cost_tracking
        reset_cost_tracking()
        
        # Step 5: Show analysis warning and proceed with full workflow
        # Add the important warning box that users should not leave the page
        progress_message_placeholder = st.empty()
        progress_message_placeholder.error(
            "🚨 **ANALYSIS IN PROGRESS - DO NOT CLOSE THIS TAB!**\n\n"
            "Your analysis is running and will take up to 3-20 minutes. "
            "Closing this browser will stop the analysis and forfeit your progress."
        )
        
        # Step 5: Now proceed with the full ASC 606 analysis workflow
        # Initialize analyzer and perform the complete analysis with progress UI
        
        try:
            # Initialize the ASC 606 analyzer and memo generator
            from asc606.step_analyzer import ASC606StepAnalyzer
            from asc606.knowledge_search import ASC606KnowledgeSearch
            from asc606.clean_memo_generator import CleanMemoGenerator
            
            # Create analyzer with knowledge base
            analyzer = ASC606StepAnalyzer()
            knowledge_search = ASC606KnowledgeSearch()
            memo_generator = CleanMemoGenerator(template_path="asc606/templates/memo_template.md")
            
            # Initialize UI components
            from shared.ui_components import SharedUIComponents
            ui = SharedUIComponents()
            
            # Extract party names and de-identify contract text for privacy
            with st.spinner("🔒 Extracting party names and de-identifying contract..."):
                try:
                    # Extract both vendor and customer names
                    party_names = analyzer.extract_party_names_llm(combined_text)
                    vendor_name = party_names.get('vendor')
                    customer_name_extracted = party_names.get('customer')
                    
                    # De-identify contract text by replacing party names
                    if vendor_name or customer_name_extracted:
                        try:
                            combined_text = analyzer.deidentify_contract_text(
                                combined_text, 
                                vendor_name, 
                                customer_name_extracted
                            )
                            logger.info("✓ Contract text de-identified for privacy")
                        except ValueError as ve:
                            # De-identification failed - hard stop to prevent privacy leakage
                            logger.error(f"De-identification failed: {str(ve)}")
                            st.error(
                                "❌ **Privacy Protection Error**\n\n"
                                "We were unable to de-identify the party names in your contract before analysis. "
                                "This is a safety feature to protect your data privacy.\n\n"
                                "**What happened:** The system extracted party names but couldn't find them in the "
                                "contract text to replace them with generic terms.\n\n"
                                "**What to do:** Please try uploading the contract again. If the issue persists, "
                                "contact support@veritaslogic.ai."
                            )
                            # Mark analysis as failed (no charge)
                            if analysis_id:
                                analysis_manager.complete_analysis(
                                    analysis_id, 
                                    success=False, 
                                    error_message="De-identification failure - privacy protection"
                                )
                            st.info("ℹ️ **No Charge Applied**: Since the analysis could not be completed safely, you were not charged.")
                            return
                    else:
                        logger.warning("No party names extracted, proceeding without de-identification")
                    
                    # Use generic "Customer" for memo since we've de-identified
                    customer_name = "the Customer"
                    
                except Exception as e:
                    logger.error(f"Party extraction failed: {str(e)}")
                    # If extraction itself fails, proceed without de-identification
                    # (extraction is best-effort, de-identification has hard stop)
                    customer_name = "the Customer"
                    
            # Setup progress tracking
            steps = [
                "Processing", "Step 1", "Step 2", "Step 3", "Step 4", 
                "Step 5", "Memo Generation"
            ]
            progress_placeholder = st.empty()
            progress_indicator_placeholder = st.empty()
            
            # Run 5 ASC 606 steps with progress indicators
            analysis_results = {}
            
            for step_num in range(1, 6):
                # Show progress
                ui.analysis_progress(steps, step_num, progress_indicator_placeholder)
                
                with st.spinner(f"🔄 Running Step {step_num}..."):
                    try:
                        # Get relevant knowledge for this step
                        authoritative_context = knowledge_search.search_for_step(step_num, combined_text)
                        
                        # Analyze the step with knowledge base context
                        step_result = analyzer._analyze_step(
                            step_num=step_num,
                            contract_text=combined_text,
                            authoritative_context=authoritative_context,
                            customer_name=customer_name,
                            additional_context=additional_context
                        )
                        
                        analysis_results[f'step_{step_num}'] = step_result
                        logger.info(f"Completed ASC 606 Step {step_num}")
                    except Exception as e:
                        logger.error(f"Error in Step {step_num}: {str(e)}")
                        # Continue with other steps
                        analysis_results[f'step_{step_num}'] = {
                            'markdown_content': f"Error in Step {step_num}: {str(e)}",
                            'title': f"Step {step_num}: Error",
                            'step_num': str(step_num)
                        }
            
            # Show memo generation progress
            ui.analysis_progress(steps, 6, progress_indicator_placeholder)
            
            # Generate memo
            with st.spinner("📄 Generating professional memo..."):
                try:
                    # Extract conclusions and generate additional sections
                    conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results)
                    executive_summary = analyzer.generate_executive_summary(conclusions_text, customer_name)
                    background = analyzer.generate_background_section(conclusions_text, customer_name) 
                    conclusion = analyzer.generate_final_conclusion(analysis_results)
                    
                    # Prepare analysis_results dict with all components for CleanMemoGenerator
                    memo_analysis_results = {
                        **analysis_results,  # Include all step results
                        'customer_name': customer_name,
                        'filename': filename,
                        'executive_summary': executive_summary,
                        'background': background,
                        'conclusion': conclusion,
                        'additional_context': additional_context
                    }
                    
                    # Generate clean memo using the memo generator with analysis_id
                    memo_result = memo_generator.combine_clean_steps(memo_analysis_results, analysis_id)
                    
                    # Mark analysis as successful
                    analysis_manager.complete_analysis(analysis_id, success=True)
                    
                    # Clear progress and warning message, show results
                    progress_indicator_placeholder.empty()
                    progress_message_placeholder.empty()  # Remove the warning
                    
                    # Display results
                    st.success("✅ **Analysis Complete! This AI-generated analysis requires review by qualified accounting professionals and should be approved by management before use.**")
                    st.markdown("""📄 **Your ASC 606 memo is ready below.** To save the results, you can either:

- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
- **Download:** Download the memo as a Markdown, PDF, or Word (.docx) file for later use.
                        """)
                    
                    # Quick action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown('<a href="#save-your-memo" style="text-decoration: none;"><button style="width: 100%; padding: 0.5rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer;">⬇️ Jump to Downloads</button></a>', unsafe_allow_html=True)
                    with col2:
                        if st.button("🔄 Start New Analysis", type="secondary", use_container_width=True, key="top_new_analysis"):
                            # Clear session state for new analysis
                            keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc606' in k.lower()]
                            for key in keys_to_clear:
                                del st.session_state[key]
                            st.rerun()
                    
                    st.markdown("---")
                    
                    # memo_result is a string (markdown content), not a dict
                    if memo_result:
                        
                        # Store memo in session state for persistence
                        if 'user_session_id' not in st.session_state:
                            st.session_state.user_session_id = str(uuid.uuid4())
                        
                        session_id = st.session_state.user_session_id
                        memo_key = f'asc606_memo_data_{session_id}'
                        analysis_key = f'asc606_analysis_complete_{session_id}'
                        
                        # Store memo data and completion state with analysis ID
                        st.session_state[memo_key] = {
                            'memo_content': memo_result,
                            'analysis_id': analysis_id,
                            'completion_timestamp': datetime.now().isoformat()
                        }
                        st.session_state[analysis_key] = True
                        
                        # Use the CleanMemoGenerator's display method with analysis_id
                        memo_generator.display_clean_memo(memo_result, analysis_id, filename, customer_name)
                        
                        # Re-run policy note and "Analyze Another" button
                        st.markdown("---")
                        st.info("📋 **Need changes to this memo?** Due to resource costs, re-runs require pre-approval. Contact Support to request a re-run.")
                        
                        if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True):
                            # Clear session state for new analysis
                            keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc606' in k.lower()]
                            for key in keys_to_clear:
                                del st.session_state[key]
                            st.rerun()
                        
                    else:
                        st.error("❌ Memo generation produced empty content")
                    
                except Exception as e:
                    logger.error(f"Memo generation failed: {str(e)}")
                    analysis_manager.complete_analysis(analysis_id, success=False, error_message=f"Memo generation failed: {str(e)}")
                    st.error(f"❌ **Memo Generation Failed**: {str(e)}")
                    return
                    
        except Exception as e:
            logger.error(f"Analysis workflow error: {str(e)}")
            analysis_manager.complete_analysis(analysis_id, success=False, error_message=str(e))
            st.error(f"❌ **Analysis Error**: {str(e)}")
            return
        
    except Exception as e:
        logger.error(f"Critical error in new ASC 606 analysis: {str(e)}")
        
        # Auto-credit user for failed analysis
        if analysis_id:
            billing_manager.auto_credit_on_failure(user_token, pricing_result['tier_info']['price'], analysis_id)
            analysis_manager.complete_analysis(analysis_id, success=False, error_message=str(e))
        
        st.error(f"❌ **Analysis Failed**: {str(e)}")
        st.info("💰 **Refund Processed**: The full amount has been credited back to your wallet.")


# For direct execution/testing
if __name__ == "__main__":
    render_asc606_page()
