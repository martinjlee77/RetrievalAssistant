"""
ASC 606 Contract Analysis Page
"""

import streamlit as st
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from shared.ui_components import SharedUIComponents
from shared.auth_utils import require_authentication, show_credits_warning, auth_manager
from shared.billing_manager import billing_manager
from shared.preflight_pricing import preflight_pricing
from shared.wallet_manager import wallet_manager
from shared.analysis_manager import analysis_manager
from shared.job_manager import job_manager
# CleanMemoGenerator import moved to initialization section
import tempfile
import os
from asc606.step_analyzer import ASC606StepAnalyzer
from asc606.knowledge_search import ASC606KnowledgeSearch
from utils.document_extractor import DocumentExtractor

logger = logging.getLogger(__name__)

def create_file_hash(uploaded_files):
    """Create a hash of uploaded files to detect changes."""
    if not uploaded_files:
        return None
    file_info = [(f.name, f.size) for f in uploaded_files]
    return hash(tuple(file_info))

def fetch_and_load_analysis(analysis_id: int, source: str = 'url'):
    """
    Fetch analysis from backend and load into session state.
    
    Args:
        analysis_id: Database analysis_id to fetch
        source: 'url' for URL parameter, 'recent' for auto-load
    
    Returns:
        Tuple of (success: bool, message: str, timestamp: str or None)
    """
    import requests
    from datetime import datetime
    
    try:
        # Get auth token
        token = st.session_state.get('auth_token')
        if not token:
            return False, "Authentication required", None
        
        # Fetch analysis from backend
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:3000')
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(
            f'{backend_url}/api/analysis/status/{analysis_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 404:
            return False, "Analysis not found", None
        elif response.status_code != 200:
            return False, f"Failed to fetch analysis: {response.status_code}", None
        
        data = response.json()
        
        # Verify it's completed
        if data.get('status') != 'completed':
            return False, f"Analysis is {data.get('status')}", None
        
        memo_content = data.get('memo_content')
        if not memo_content:
            return False, "No memo content found", None
        
        # Load into session state
        session_id = st.session_state.get('user_session_id', '')
        analysis_key = f'asc606_analysis_complete_{session_id}'
        memo_key = f'asc606_memo_data_{session_id}'
        
        # Store memo data with metadata
        st.session_state[analysis_key] = True
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'analysis_id': analysis_id,
            'loaded_from': source,
            'completed_at': data.get('completed_at')
        }
        
        # Clear URL parameter after loading
        if source == 'url' and 'analysis_id' in st.query_params:
            st.query_params.clear()
        
        timestamp = data.get('completed_at')
        return True, "Analysis loaded successfully", timestamp
        
    except Exception as e:
        logger.error(f"Failed to fetch analysis {analysis_id}: {str(e)}")
        return False, f"Error loading analysis: {str(e)}", None

def check_for_analysis_to_load():
    """
    Check for analysis to auto-load on page load.
    Priority: 1) URL parameter, 2) Recent analysis (within 24 hours)
    
    Returns:
        Tuple of (loaded: bool, source: str, timestamp: str or None)
    """
    import requests
    
    # Skip if already have memo in session
    session_id = st.session_state.get('user_session_id', '')
    memo_key = f'asc606_memo_data_{session_id}'
    if st.session_state.get(memo_key):
        return False, None, None
    
    # Priority 1: Check URL parameter ?analysis_id=X
    query_params = st.query_params
    if 'analysis_id' in query_params:
        try:
            analysis_id = int(query_params['analysis_id'])
            success, message, timestamp = fetch_and_load_analysis(analysis_id, source='url')
            if success:
                return True, 'url', timestamp
            else:
                st.warning(f"Could not load analysis from URL: {message}")
        except ValueError:
            st.warning("Invalid analysis_id in URL")
        return False, None, None
    
    # Priority 2: Check for recent completed analysis (within 24 hours)
    try:
        token = st.session_state.get('auth_token')
        if not token:
            return False, None, None
        
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:3000')
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(
            f'{backend_url}/api/analysis/recent/asc606',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            analysis_id = data.get('analysis_id')
            
            # Guard: Only load if analysis_id is present
            if not analysis_id:
                logger.warning("Recent analysis response missing analysis_id")
                return False, None, None
            
            # Load this analysis into session state
            success, message, timestamp = fetch_and_load_analysis(analysis_id, source='recent')
            if success:
                return True, 'recent', timestamp
        elif response.status_code != 404:
            logger.warning(f"Failed to check for recent analysis: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error checking for recent analysis: {str(e)}")
    
    return False, None, None

def render_asc606_page():
    """Render the ASC 606 analysis page."""
    
    # Authentication check - must be logged in to access
    if not require_authentication():
        return  # User will see login page
    
    # Initialize user session ID for memo persistence
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
        logger.info(f"Created new user session: {st.session_state.user_session_id[:8]}...")
    
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
    
    # Check for analysis to auto-load (URL parameter or recent analysis)
    loaded, source, timestamp = check_for_analysis_to_load()
    if loaded:
        # Display notice about loaded analysis
        if source == 'recent':
            from datetime import datetime
            try:
                completed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if timestamp else None
                if completed_time:
                    time_diff = datetime.now(completed_time.tzinfo) - completed_time
                    hours = int(time_diff.total_seconds() // 3600)
                    minutes = int((time_diff.total_seconds() % 3600) // 60)
                    
                    if hours == 0:
                        time_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
                    elif hours < 24:
                        time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
                    else:
                        time_str = "earlier today"
                    
                    st.info(f"📋 Your analysis from {time_str} is ready below. To view older analyses, visit your **History** tab.")
                else:
                    st.info("📋 Your recent analysis is ready below. To view older analyses, visit your **History** tab.")
            except Exception as e:
                logger.warning(f"Failed to parse timestamp: {e}")
                st.info("📋 Your recent analysis is ready below. To view older analyses, visit your **History** tab.")
        # No notice for URL-loaded analyses (user clicked from History intentionally)
    
    # Check for existing completed analysis in session state (restore persistence)
    session_id = st.session_state.get('user_session_id', '')
    logger.info(f"🔍 Page load - session_id: {session_id}, session keys: {list(st.session_state.keys())}")
    
    # Always construct the keys (works with empty session_id too)
    analysis_key = f'asc606_analysis_complete_{session_id}'
    memo_key = f'asc606_memo_data_{session_id}'
    
    logger.info(f"🔍 Checking for memo: analysis_key={analysis_key}, has_analysis_key={st.session_state.get(analysis_key, False)}, has_memo_key={bool(st.session_state.get(memo_key))}")
    
    # If analysis is complete and memo exists, show results instead of file upload
    if st.session_state.get(analysis_key, False) and st.session_state.get(memo_key):
            # Force scroll to top when memo is displayed
            st.markdown(
                """
                <script>
                    window.parent.document.querySelector('section.main').scrollTo(0, 0);
                </script>
                """,
                unsafe_allow_html=True
            )
            
            st.success("✅ **Analysis Complete!** This AI-generated analysis requires review by qualified accounting professionals and should be approved by management before use.")
            st.markdown("""📄 **Your ASC 606 memo is ready below.** To save the results, you can either:

- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
- **Download:** Download the memo as a Word (.docx), Markdown, or PDF file for later use.
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
            st.info("📋 Each analysis comes with one complimentary re-run within 14 days for input modifications or extractable text adjustments. If you'd like to request one, please contact support at support@veritaslogic.ai.")
            
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

    # Process files when uploaded - extract, de-identify, and price
    pricing_result = None
    processing_container = st.empty()
    pricing_container = st.empty()
    
    if uploaded_files:
        # Step 1: Extract and de-identify for Document Processing section
        file_hash = create_file_hash(uploaded_files)
        privacy_hash_key = f'asc606_privacy_hash_{session_id}'
        cached_text_key = f'asc606_cached_text_{session_id}'
        cached_deidentify_key = f'asc606_cached_deidentify_{session_id}'
        cached_word_count_key = f'asc606_cached_word_count_{session_id}'
        
        # Check if we need to re-process (files changed)
        if st.session_state.get(privacy_hash_key) != file_hash:
            if cached_text_key in st.session_state:
                del st.session_state[cached_text_key]
            if cached_deidentify_key in st.session_state:
                del st.session_state[cached_deidentify_key]
            if cached_word_count_key in st.session_state:
                del st.session_state[cached_word_count_key]
            st.session_state[privacy_hash_key] = file_hash
        
        # Extract and de-identify if not cached
        if cached_text_key not in st.session_state:
            with st.spinner("📄 Extracting and processing contract text..."):
                try:
                    extractor = DocumentExtractor()
                    all_texts = []
                    failed_files = []
                    
                    for uploaded_file in uploaded_files:
                        uploaded_file.seek(0)
                        result = extractor.extract_text(uploaded_file)
                        # Check if extraction succeeded (no error and has text)
                        if result and isinstance(result, dict) and not result.get('error') and result.get('text'):
                            all_texts.append(result['text'])
                        else:
                            failed_files.append(uploaded_file.name)
                    
                    # Check if we have any successfully extracted text
                    if not all_texts:
                        st.error(
                            f"❌ **File extraction failed**\n\n"
                            f"Could not extract text from any uploaded files. "
                            f"Please ensure your files are text-based (not scanned images) and try again."
                        )
                        return
                    
                    combined_text = "\n\n---\n\n".join(all_texts)
                    
                    # Calculate word count for pricing
                    word_count = len(combined_text.split())
                    
                    # Extract party names and de-identify
                    analyzer = ASC606StepAnalyzer()
                    party_names = analyzer.extract_party_names_llm(combined_text)
                    vendor_name = party_names.get('vendor')
                    customer_name = party_names.get('customer')
                    
                    deidentify_result = analyzer.deidentify_contract_text(
                        combined_text,
                        vendor_name,
                        customer_name
                    )
                    
                    # Cache results
                    st.session_state[cached_text_key] = combined_text
                    st.session_state[cached_deidentify_key] = deidentify_result
                    st.session_state[cached_word_count_key] = word_count
                    st.session_state[f'asc606_failed_files_{session_id}'] = failed_files
                    
                except Exception as e:
                    logger.error(f"Error in document processing: {str(e)}")
                    st.error(f"❌ Error processing contract: {str(e)}")
        
        # Show Document Processing section
        if cached_deidentify_key in st.session_state:
            deidentify_result = st.session_state[cached_deidentify_key]
            failed_files = st.session_state.get(f'asc606_failed_files_{session_id}', [])
            
            with processing_container.container():
                st.markdown("### :primary[Document Processing]")
                
                # Show extraction warnings if any
                if failed_files:
                    st.warning(
                        f"⚠️ **File extraction issues:** {len(failed_files)} file(s) could not be processed: "
                        f"{', '.join(failed_files)}. The analysis will proceed with the remaining files only."
                    )
                
                if deidentify_result['success']:
                    st.success("✓ Privacy protection applied successfully. Please contact support@veritaslogic.ai if you need any assistance.")
                    
                    with st.container(border=True):
                        st.markdown("**Party names replaced:**")
                        if deidentify_result['vendor_name']:
                            st.markdown(f"• Vendor: **\"{deidentify_result['vendor_name']}\"** → **\"the Company\"**")
                        if deidentify_result['customer_name']:
                            st.markdown(f"• Customer: **\"{deidentify_result['customer_name']}\"** → **\"the Customer\"**")
                    
                    # Show 4000-char preview
                    preview_text = deidentify_result['text'][:4000]
                    st.markdown("**Preview of text to be analyzed (first 4,000 characters):**")
                    st.text_area(
                        label="De-identified contract text",
                        value=preview_text,
                        height=300,
                        disabled=True,
                        label_visibility="collapsed",
                        key="deidentified_preview"
                    )
                else:
                    st.warning("⚠️ " + deidentify_result['error'])
                    st.info(
                        "**Your choice:** The system was unable to automatically detect and replace party names. "
                        "The analysis will proceed using the original text."
                    )
                    
                    # Show original text preview
                    preview_text = st.session_state[cached_text_key][:4000]
                    st.markdown("**Preview of text to be analyzed (first 4,000 characters):**")
                    st.text_area(
                        label="Original contract text",
                        value=preview_text,
                        height=300,
                        disabled=True,
                        label_visibility="collapsed",
                        key="original_preview"
                    )
        
        # Step 2: Calculate pricing from cached word count (no re-extraction)
        if cached_word_count_key in st.session_state:
            word_count = st.session_state[cached_word_count_key]
            pricing_result = preflight_pricing.calculate_pricing_from_word_count(word_count, len(uploaded_files))

            if pricing_result['success']:
                with pricing_container.container():
                    st.markdown("### :primary[Analysis Pricing]")
                    st.info(pricing_result['billing_summary'])
            else:
                st.error(f"❌ **Pricing Calculation Failed**\n\n{pricing_result['error']}")

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
            warning_placeholder = st.empty()
            warning_placeholder.info(
                "⚠️ **IMPORTANT:** Analysis takes up to **3-20 minutes**. Please don't close this tab until complete"
            )
            
            if st.button("3️⃣ Confirm & Analyze",
                       type="primary",
                       use_container_width=True,
                       key="asc606_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()
                processing_container.empty()
                pricing_container.empty()
                credit_container.empty()
                upload_form_container.empty()
                
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                
                # Get cached de-identified text
                cached_text_key = f'asc606_cached_text_{session_id}'
                cached_deidentify_key = f'asc606_cached_deidentify_{session_id}'
                
                if cached_deidentify_key in st.session_state:
                    deidentify_result = st.session_state[cached_deidentify_key]
                    cached_text = deidentify_result['text']
                else:
                    cached_text = None
                
                # Ensure we have cached text
                if not cached_text:
                    st.error("❌ Contract text not found. Please re-upload your documents.")
                    return
                
                # Submit analysis to background job queue
                uploaded_filenames = [f.name for f in uploaded_files] if uploaded_files else []
                
                # Import job runner
                from asc606.job_analysis_runner import submit_and_monitor_asc606_job
                
                # Submit job and monitor progress
                submit_and_monitor_asc606_job(
                    pricing_result=pricing_result,
                    additional_context=additional_context,
                    user_token=user_token,
                    cached_combined_text=cached_text,
                    uploaded_filenames=uploaded_filenames,
                    session_id=session_id
                )
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


# For direct execution/testing
if __name__ == "__main__":
    render_asc606_page()
