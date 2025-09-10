"""
ASC 842 Lease Accounting Analysis Page
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
from utils.document_extractor import DocumentExtractor
from asc842.step_analyzer import ASC842StepAnalyzer
from asc842.knowledge_search import ASC842KnowledgeSearch

logger = logging.getLogger(__name__)

def render_asc842_page():
    """Render the ASC 842 analysis page."""
    
    # Authentication check - must be logged in to access
    if not require_authentication():
        return  # User will see login page
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Page header
    st.title(":primary[ASC 842 Analyzer & Memo Generator]")
    with st.container(border=True):
        st.markdown(":primary[**Purpose:**] Automatically analyze lease contracts and generate a professional ASC 842 memo. Simply upload your lease documents to begin.")
    
    # Check for active analysis first
    if analysis_manager.show_active_analysis_warning():
        return  # User has active analysis, show warning and exit
    
    # Check for existing completed analysis in session state (restore persistence)
    session_id = st.session_state.get('user_session_id', '')
    if session_id:
        analysis_key = f'asc842_analysis_complete_{session_id}'
        memo_key = f'asc842_memo_data_{session_id}'
        
        if analysis_key in st.session_state and st.session_state[analysis_key]:
            # Show completed analysis and download options
            st.success("✅ **Analysis Complete!** Your ASC 842 lease accounting memo is ready.")
            
            if memo_key in st.session_state:
                # Display the existing memo with enhanced downloads
                from asc842.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator()
                memo_data = st.session_state[memo_key]
                # Extract memo content from stored dictionary
                memo_content = memo_data['memo_content'] if isinstance(memo_data, dict) else memo_data
                memo_generator.display_clean_memo(memo_content)
                
                # Option to clear and start new analysis
                st.divider()
                if st.button("🔄 Clear Results & Start New Analysis", 
                           type="secondary", 
                           use_container_width=True):
                    # Clear session state
                    if analysis_key in st.session_state:
                        del st.session_state[analysis_key]
                    if memo_key in st.session_state:
                        del st.session_state[memo_key]
                    st.rerun()
                return
    
    # Get user inputs with progressive disclosure
    contract_text, filename, additional_context, is_ready = get_asc842_inputs()

    # Preflight pricing and payment flow
    if is_ready:
        # Mock pricing result for single contract text (similar to ASC 340-40 pattern)
        pricing_result = {
            'success': True,
            'billing_summary': '💰 **Estimated Cost:** This analysis will consume approximately 15-25 credits',
            'tier_info': {'price': 20},  # Estimated price
            'processing_errors': []
        }
        
        # Display pricing information
        pricing_container = st.empty()
        with pricing_container:
            st.markdown("### :primary[Analysis Pricing]")
            st.info(pricing_result['billing_summary'])
        
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
        
        # Credit balance display
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
                "⚠️ **IMPORTANT:** Keep this browser tab active during analysis!\n\n"
                "- Analysis takes **3-5 minutes**\n"
                "- Switching tabs or closing the browser will stop the analysis\n"
                "- Stay on this tab until analysis is complete\n"
                "- You'll see a completion message when it's done"
            )
            
            if st.button("3️⃣ Confirm, Start Analysis & Generate Memo",
                       type="primary",
                       use_container_width=True,
                       key="asc842_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()  # Clear the warning 
                pricing_container.empty()    # Clear pricing information
                credit_container.empty()     # Clear credit balance info
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                if contract_text:  # Type guard to ensure contract_text is not None
                    perform_asc842_analysis(contract_text, additional_context, filename or "lease_contract.txt")
        else:
            st.button("3️⃣ Insufficient Credits", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc842_analyze_disabled")
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Analyze Lease Contract & Generate Memo", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc842_analyze_disabled")


def get_asc842_inputs():
    """Get ASC 842 specific inputs."""

    # Document upload with ASC 842 specific help text
    contract_text, filename = _upload_and_process_asc842()

    # Additional info (optional)
    additional_context = st.text_area(
        "2️⃣ Additional information or concerns (optional)",
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents or specify your areas of focus or concerns.",
        height=100)

    # Check completion status - only contract text required
    is_ready = bool(contract_text)

    return contract_text, filename, additional_context, is_ready


def _upload_and_process_asc842():
    """Handle file upload and processing specifically for ASC 842 analysis."""
    # Use session state to control file uploader key for clearing
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
        
    uploaded_files = st.file_uploader(
        "1️⃣ Upload **lease agreement and related documents**, e.g., executed lease, amendments, schedules, addenda (required)",
        type=['pdf', 'docx'],
        help="Upload up to 5 relevant lease documents (PDF or DOCX) for ASC 842 lease accounting analysis. Include the main lease agreement and any amendments, schedules, addenda, or related documentation. Incomplete documentation may lead to inaccurate lease accounting analysis.",
        accept_multiple_files=True,
        key=f"lease_files_{st.session_state.file_uploader_key}"
    )
    
    if not uploaded_files:
        return None, None
        
    # Limit to 5 files for practical processing
    if len(uploaded_files) > 5:
        st.warning("⚠️ Maximum 5 files allowed. Using first 5 files only.")
        uploaded_files = uploaded_files[:5]
        
    try:
        combined_text = ""
        processed_filenames = []
        extractor = DocumentExtractor()
        
        # Show processing status to users
        with st.spinner(f"Processing {len(uploaded_files)} document(s)..."):
            for uploaded_file in uploaded_files:
                # Extract text using existing extractor
                extraction_result = extractor.extract_text(uploaded_file)
                
                # Check for extraction errors
                if extraction_result.get('error'):
                    st.error(f"❌ Document extraction failed for {uploaded_file.name}: {extraction_result['error']}")
                    continue
                
                # Get the text from the extraction result
                extracted_text = extraction_result.get('text', '')
                if extracted_text and extracted_text.strip():
                    combined_text += f"\\n\\n=== {uploaded_file.name} ===\\n\\n{extracted_text}"
                    processed_filenames.append(uploaded_file.name)
                    # st.success(f"✅ Successfully processed {uploaded_file.name} ({len(extracted_text):,} characters)")
                else:
                    st.warning(f"⚠️ No readable content extracted from {uploaded_file.name}")
        
        if not combined_text.strip():
            st.error("❌ No readable content found in any uploaded files. Please check your documents and try again.")
            return None, None
        
        # Create comma-separated filename string
        filename_string = ", ".join(processed_filenames)
        
        # st.success(f"🎉 Successfully processed {len(processed_filenames)} document(s): {filename_string}")
        # st.info(f"📄 Total extracted content: {len(combined_text):,} characters")
        
        return combined_text.strip(), filename_string
            
    except Exception as e:
        logger.error(f"Error processing uploaded files: {str(e)}")
        st.error(f"❌ Error processing files: {str(e)}")
        return None, None


def perform_asc842_analysis(contract_text: str, additional_context: str = "", filename: str = None):
    """Perform the complete ASC 842 analysis and display results with session isolation."""
    
    # Session isolation - create unique session ID for this user
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
        logger.info(f"Created new user session: {st.session_state.user_session_id[:8]}...")
    
    session_id = st.session_state.user_session_id
    
    # Create placeholder for the in-progress message
    progress_message_placeholder = st.empty()
    progress_message_placeholder.error(
        "🚨 **ANALYSIS IN PROGRESS - DO NOT CLOSE OR SWITCH TABS!**\n\n"
        "Your analysis is running and will take up to 3-5 minutes. "
        "Switching to another tab or closing this browser will stop the analysis and forfeit your progress."
    )
    
    # Initialize analysis complete status with session isolation
    analysis_key = f'asc842_analysis_complete_{session_id}'
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = False
    
    # Generate analysis title
    analysis_title = _generate_analysis_title()

    try:
        # Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC842StepAnalyzer()
                knowledge_search = ASC842KnowledgeSearch()
                from asc842.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator(
                    template_path="asc842/templates/memo_template.md")
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 842 knowledge base is not available. Try again and contact support if this persists.")
                st.stop()
                return

        # Extract entity name using LLM (with regex fallback)
        with st.spinner("🏢 Extracting entity name..."):
            try:
                entity_name = analyzer.extract_entity_name_llm(contract_text)
                logger.info(f"LLM extracted entity name: {entity_name}")
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {str(e)}, falling back to regex")
                entity_name = _extract_entity_name(contract_text)
                logger.info(f"Regex fallback entity name: {entity_name}")

        # Display progress
        steps = [
            "Processing", "Step 1", "Step 2", "Step 3", "Step 4",
            "Step 5", "Memo Generation"
        ]
        progress_placeholder = st.empty()

        # Step-by-step analysis with progress indicators
        analysis_results = {}
        
        # Create a separate placeholder for progress indicators that can be cleared
        progress_indicator_placeholder = st.empty()
        
        # Run 5 ASC 842 steps with progress
        for step_num in range(1, 6):
            # Show progress indicators in clearable placeholder
            ui.analysis_progress(steps, step_num, progress_indicator_placeholder)

            with st.spinner(f"Analyzing Step {step_num}..."):
                # Get relevant guidance from knowledge base
                authoritative_context = knowledge_search.search_for_step(
                    step_num, contract_text)

                # Analyze the step with additional context
                step_result = analyzer._analyze_step(
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    entity_name=entity_name,
                    additional_context=additional_context)

                analysis_results[f'step_{step_num}'] = step_result
                logger.info(f"DEBUG: Completed step {step_num}")

        # Generate additional sections (Executive Summary, Background, Conclusion)
        # Show final progress indicators in clearable placeholder
        ui.analysis_progress(steps, 6, progress_indicator_placeholder)

        with st.spinner("Generating Executive Summary, Background, and Conclusion..."):
            # Extract conclusions from the 5 steps
            conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results)
            
            # Generate the three additional sections
            executive_summary = analyzer.generate_executive_summary(conclusions_text, entity_name)
            background = analyzer.generate_background_section(conclusions_text, entity_name)
            conclusion = analyzer.generate_conclusion_section(conclusions_text)
            
            # Combine into the expected structure for memo generator
            final_results = {
                'entity_name': entity_name,
                'analysis_title': analysis_title,
                'analysis_date': datetime.now().strftime("%B %d, %Y"),
                'filename': filename,
                'steps': analysis_results,
                'executive_summary': executive_summary,
                'background': background,
                'conclusion': conclusion
            }
            
            
            # Generate memo directly from complete analysis results
            memo_content = memo_generator.combine_clean_steps(final_results)

        # Store memo data in session state and clear progress messages
        progress_message_placeholder.empty()  # Clears the in-progress message
        progress_placeholder.empty()  # Clears the step headers
        progress_indicator_placeholder.empty()  # Clears the persistent success boxes
        
        # Create clearable completion message
        completion_message_placeholder = st.empty()
        completion_message_placeholder.success(
            f"✅ **ANALYSIS COMPLETE!** Your professional ASC 842 memo is ready. Scroll down to view the results."
        )
        
        # Signal completion with session isolation
        st.session_state[analysis_key] = True
        
        # Store memo data with session isolation
        memo_key = f'asc842_memo_data_{session_id}'
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'entity_name': entity_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
             
        # Display memo inline instead of switching pages
        st.markdown("---")

        with st.container(border=True):
            st.markdown("""Your ASC 842 memo is displayed below. To save the results, you can either:
            
- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).
- **Download as Markdown:**  Download the memo as a Markdown file for later use (download link below).
                """)
        
        # Display the memo using CleanMemoGenerator
        memo_generator_display = CleanMemoGenerator()
        memo_generator_display.display_clean_memo(memo_content)
        
        # Clear completion message immediately after memo displays
        completion_message_placeholder.empty()
        
        if st.button("🔄 Analyze Another Contract", type="primary", use_container_width=True):
            # Clear analysis state for fresh start with session isolation
            st.session_state.file_uploader_key = st.session_state.get('file_uploader_key', 0) + 1
            st.cache_data.clear()  # Clear Streamlit cache to reset file uploader
            
            # Clean up session-specific data
            memo_key = f'asc842_memo_data_{session_id}'
            if memo_key in st.session_state:
                del st.session_state[memo_key]
            if analysis_key in st.session_state:
                del st.session_state[analysis_key]
            
            logger.info(f"Cleaned up session data for user: {session_id[:8]}...")
            st.rerun()

    except Exception as e:
        # Clear the progress message even on error
        progress_message_placeholder.empty()
        st.error("❌ Analysis failed. Please try again. Contact support if this issue persists.")
        logger.error(f"ASC 842 analysis error for session {session_id[:8]}...: {str(e)}")
        st.session_state[analysis_key] = True  # Signal completion (even on error)


# OLD PARSING SYSTEM REMOVED - Using direct markdown approach only


# Executive summary generation moved to ASC842StepAnalyzer class


# Final conclusion generation moved to ASC842StepAnalyzer class


# Issues collection removed - issues are already included in individual step analyses


# Configure logging
logging.basicConfig(level=logging.INFO)


# Main function for Streamlit navigation
def main():
    """Main function called by Streamlit navigation."""
    render_asc842_page()



def _extract_entity_name(contract_text: str) -> str:
    """Extract the lessee/tenant entity name from typical lease contract preambles or headings."""
    try:
        import re
        
        if not contract_text:
            return "Entity"

        # Preprocess: examine the first part of the document (preamble/definitions often appear early)
        sample = contract_text[:6000]

        # Normalize quotes and whitespace
        sample = sample.replace(""", '"').replace(""", '"').replace("'", "'")
        sample = re.sub(r'[ \t]+', ' ', sample)

        # Role vocabularies (lowercase) - adapted for lease contexts
        lessee_roles = {
            "lessee", "tenant", "renter", "occupant", "subtenant", "sublessee",
            "licensee", "grantee", "user", "end user", "end-user"
        }
        lessor_roles = {
            "lessor", "landlord", "owner", "licensor", "grantor", "property owner",
            "building owner", "landlord entity", "property manager"
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
        # "between Acme Properties, LLC (\"Lessor\") and Beta Corp (\"Lessee\")"
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
                if name and any(lr == role or role in lr for lr in lessee_roles):
                    return name
            # If one is clearly lessor and the other not, pick the non-lessor
            roles = [r1.strip().lower(), r2.strip().lower()]
            names = [clean_name(p1), clean_name(p2)]
            if any(rv in lessor_roles for rv in roles):
                # choose the one whose role is not lessor-like
                for name, role in zip(names, roles):
                    if name and (role not in lessor_roles):
                        return name
            # If ambiguous, try r2 if it looks like a lessee role
            if clean_name(p2) and plausible_company(clean_name(p2)):
                # Heuristic: often the second party is the lessee
                return clean_name(p2)

        # PRIORITY 2: Single party labeled as lessee-like in the preamble or headings:
        # e.g., 'and Global Dynamics Corp. ("Lessee")'
        labeled_single = re.compile(
            r'\b(?:and\s+)?(?P<name>[^,\n;]+?)\s*\(\s*(?:the\s+)?["\']?(?P<role>Lessee|Tenant|Renter|Occupant|Subtenant|Sublessee|Licensee)["\']?\s*\)',
            re.IGNORECASE
        )
        for m in labeled_single.finditer(sample):
            name = clean_name(m.group('name'))
            if name and plausible_company(name):
                return name

        # PRIORITY 3: Header fields like "Lessee: Acme, Inc." or "Tenant: Orion LLC"
        labeled_field = re.compile(
            r'\b(?P<label>Lessee|Tenant|Renter|Occupant|Subtenant|Sublessee|Licensee)\s*[:\-]\s*(?P<name>[A-Za-z0-9\.\,&\-\s]{3,120})',
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
            # Prefer a name that is near lessee-like labels elsewhere
            for name in matches:
                if plausible_company(clean_name(name)):
                    return clean_name(name)

        return "Entity"

    except Exception as e:
        # Keep existing logging if present
        if 'logger' in globals():
            logger.error(f"Error extracting entity name: {str(e)}")
        return "Entity"



def _generate_analysis_title() -> str:
    """Generate analysis title with timestamp."""
    return f"ASC842_Analysis_{datetime.now().strftime('%m%d_%H%M%S')}"


# For direct execution/testing
if __name__ == "__main__":
    render_asc842_page()