"""
ASC 718 Stock Compensation Analysis Page
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
from shared.analysis_manager import analysis_manager
# CleanMemoGenerator import moved to initialization section
import tempfile
import os
from utils.document_extractor import DocumentExtractor
from asc718.step_analyzer import ASC718StepAnalyzer
from asc718.knowledge_search import ASC718KnowledgeSearch
from asc718.job_analysis_runner import submit_and_monitor_asc718_job

logger = logging.getLogger(__name__)

def create_file_hash(uploaded_files):
    """Create a hash of uploaded files to detect changes."""
    if not uploaded_files:
        return None
    file_info = [(f.name, f.size) for f in uploaded_files]
    return hash(tuple(file_info))

def fetch_and_load_analysis(analysis_id: int, source: str = 'url'):
    """Fetch analysis from backend and load into session state."""
    import requests
    from datetime import datetime
    
    try:
        token = st.session_state.get('auth_token')
        if not token:
            return False, "Authentication required", None
        
        website_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(
            f'{website_url}/api/analysis/status/{analysis_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 404:
            return False, "Analysis not found", None
        elif response.status_code != 200:
            return False, f"Failed to fetch analysis: {response.status_code}", None
        
        data = response.json()
        
        if data.get('status') != 'completed':
            return False, f"Analysis is {data.get('status')}", None
        
        memo_content = data.get('memo_content')
        if not memo_content:
            return False, "No memo content found", None
        
        session_id = st.session_state.get('user_session_id', '')
        analysis_key = f'asc718_analysis_complete_{session_id}'
        memo_key = f'asc718_memo_data_{session_id}'
        
        st.session_state[analysis_key] = True
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'analysis_id': analysis_id,
            'loaded_from': source,
            'completed_at': data.get('completed_at')
        }
        
        if 'skip_auto_load' in st.session_state:
            del st.session_state['skip_auto_load']
        
        if source == 'url' and 'analysis_id' in st.query_params:
            st.query_params.clear()
        
        timestamp = data.get('completed_at')
        return True, "Analysis loaded successfully", timestamp
        
    except Exception as e:
        logger.error(f"Failed to fetch analysis {analysis_id}: {str(e)}")
        return False, f"Error loading analysis: {str(e)}", None

def check_for_analysis_to_load():
    """Check for analysis to auto-load on page load."""
    import requests
    
    if st.session_state.get('skip_auto_load', False):
        return False, None, None
    
    session_id = st.session_state.get('user_session_id', '')
    memo_key = f'asc718_memo_data_{session_id}'
    if st.session_state.get(memo_key):
        return False, None, None
    
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
    
    try:
        token = st.session_state.get('auth_token')
        if not token:
            return False, None, None
        
        website_url = os.getenv('WEBSITE_URL', 'https://www.veritaslogic.ai')
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(
            f'{website_url}/api/analysis/recent/asc718',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            analysis_id = data.get('analysis_id')
            
            if not analysis_id:
                logger.warning("Recent analysis response missing analysis_id")
                return False, None, None
            
            success, message, timestamp = fetch_and_load_analysis(analysis_id, source='recent')
            if success:
                return True, 'recent', timestamp
        elif response.status_code != 404:
            logger.warning(f"Failed to check for recent analysis: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error checking for recent analysis: {str(e)}")
    
    return False, None, None

def render_asc718_page():
    """Render the ASC 718 analysis page."""
    
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
    
    # Check for analysis to auto-load (URL parameter or recent analysis)
    loaded, source, timestamp = check_for_analysis_to_load()
    if loaded:
        logger.info(f"📥 Auto-loaded analysis from {source}: timestamp={timestamp}")

    # Page header
    st.title(":primary[ASC 718: Stock Compensation]")
    with st.container(border=True):
        st.markdown(":primary[**Purpose:**] Automatically analyze stock compensation arrangements and generate a first draft of professional ASC 718 memo. Simply upload your documents to begin.")
    
    # Check for active analysis first
    if analysis_manager.show_active_analysis_warning():
        return  # User has active analysis, show warning and exit
    
    # Check for existing completed analysis in session state (restore persistence)
    session_id = st.session_state.get('user_session_id', '')
    if session_id:
        analysis_key = f'asc718_analysis_complete_{session_id}'
        memo_key = f'asc718_memo_data_{session_id}'
        
        # If analysis is complete and memo exists, show results instead of file upload
        if st.session_state.get(analysis_key, False) and st.session_state.get(memo_key):
            # Show auto-load banner if this was loaded from recent analysis
            memo_data = st.session_state.get(memo_key, {})
            if memo_data.get('loaded_from') == 'recent':
                from datetime import datetime
                timestamp = memo_data.get('completed_at')
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
            
            st.success("✅ **Analysis Complete!** This AI-generated analysis requires review by qualified accounting professionals and should be approved by management before use.")
            st.markdown("""📄 **Your ASC 718 memo is ready below.** To save the results, you can either:

- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
- **Download:** Download the memo as a Markdown, PDF, or Word (.docx) file for later use.
                        """)
            
            # Quick action buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<a href="#save-your-memo" style="text-decoration: none;"><button style="width: 100%; padding: 0.5rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer;">⬇️ Jump to Downloads</button></a>', unsafe_allow_html=True)
            with col2:
                if st.button("🔄 Start New Analysis", type="secondary", use_container_width=True, key="top_new_analysis_existing"):
                    keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc718' in k.lower()]
                    for key in keys_to_clear:
                        del st.session_state[key]
                    st.session_state['skip_auto_load'] = True
                    st.rerun()
            
            st.markdown("---")
            
            # Display the existing memo with enhanced downloads
            from asc718.clean_memo_generator import CleanMemoGenerator
            memo_generator = CleanMemoGenerator()
            memo_data = st.session_state[memo_key]
            # Extract memo content from stored dictionary
            memo_content = memo_data['memo_content'] if isinstance(memo_data, dict) else memo_data
            # Extract parameters for memo display
            analysis_id = memo_data.get('analysis_id') if isinstance(memo_data, dict) else f"memo_{session_id}"
            filename = memo_data.get('filename') if isinstance(memo_data, dict) else None
            customer_name = memo_data.get('customer_name') if isinstance(memo_data, dict) else None
            memo_generator.display_clean_memo(memo_content, analysis_id, filename, customer_name)
            
            # Re-run policy note and "Analyze Another" button
            st.markdown("---")
            st.info("📋 Each analysis comes with one complimentary re-run within 14 days for input modifications or extractable text adjustments. If you'd like to request one, please contact support at support@veritaslogic.ai.")
            
            if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True, key="bottom_new_analysis_existing"):
                # Clear session state for new analysis
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc718' in k.lower()]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.session_state['skip_auto_load'] = True
                st.rerun()
            
            return  # Exit early, don't show file upload interface
    
    # Get user inputs with progressive disclosure - wrap in container to allow clearing
    upload_form_container = st.empty()
    with upload_form_container.container():
        uploaded_files, additional_context, is_ready = get_asc718_inputs_new()

    # Process files when uploaded - extract, de-identify, and price
    pricing_result = None
    processing_container = st.empty()
    pricing_container = st.empty()
    
    if uploaded_files:
        # Step 1: Extract and de-identify for Document Processing section
        cached_text_key = f'asc718_cached_text_{session_id}'
        cached_deidentify_key = f'asc718_cached_deidentify_{session_id}'
        cached_word_count_key = f'asc718_cached_word_count_{session_id}'
        
        # Extract and de-identify if not cached
        if cached_text_key not in st.session_state:
            with st.spinner("📄 Extracting and processing stock compensation documents..."):
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
                    analyzer = ASC718StepAnalyzer()
                    party_names = analyzer.extract_party_names_llm(combined_text)
                    granting_company = party_names.get('granting_company')
                    recipient = party_names.get('recipient')
                    
                    deidentify_result = analyzer.deidentify_contract_text(
                        combined_text,
                        granting_company,
                        recipient
                    )
                    
                    # Cache results
                    st.session_state[cached_text_key] = combined_text
                    st.session_state[cached_deidentify_key] = deidentify_result
                    st.session_state[cached_word_count_key] = word_count
                    st.session_state[f'asc718_failed_files_{session_id}'] = failed_files
                    
                except Exception as e:
                    logger.error(f"Error in document processing: {str(e)}")
                    st.error(f"❌ Error processing stock compensation documents: {str(e)}")
        
        # Show Document Processing section
        if cached_deidentify_key in st.session_state:
            deidentify_result = st.session_state[cached_deidentify_key]
            failed_files = st.session_state.get(f'asc718_failed_files_{session_id}', [])
            
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
                        if deidentify_result['granting_company_name']:
                            st.markdown(f"• Granting Company: **\"{deidentify_result['granting_company_name']}\"** → **\"the Company\"**")
                        if deidentify_result['recipient_name']:
                            st.markdown(f"• Recipient: **\"{deidentify_result['recipient_name']}\"** → **\"the Employee\"**")
                    
                    # Show 4000-char preview
                    preview_text = deidentify_result['text'][:4000]
                    st.markdown("**Preview of text to be analyzed (first 4,000 characters):**")
                    st.text_area(
                        label="De-identified stock compensation text",
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
                        label="Original stock compensation text",
                        value=preview_text,
                        height=300,
                        disabled=True,
                        label_visibility="collapsed",
                        key="original_preview"
                    )
        
        # Step 2: Check subscription allowance from cached word count (no re-extraction)
        if cached_word_count_key in st.session_state:
            word_count = st.session_state[cached_word_count_key]
            user_token = auth_manager.get_auth_token()
            if not user_token:
                st.error("❌ Authentication required. Please refresh the page and log in again.")
                return
            
            # Check subscription word allowance
            allowance_result = preflight_pricing.check_subscription_allowance(
                user_token=user_token,
                total_words=word_count
            )
            
            # Store as pricing_result for backwards compatibility
            pricing_result = allowance_result

            if allowance_result['can_proceed']:
                # Show allowance status with inline warning if needed
                if allowance_result['show_warning']:
                    with pricing_container.container():
                        # Show inline warning card
                        msg_parts = []
                        if allowance_result['segment'] == 'trial':
                            msg_parts.append(f"🎉 **Trial Analysis** ({allowance_result['total_words']:,} words)")
                            msg_parts.append(f"• Remaining after this analysis: **{allowance_result['words_remaining_after']:,} words**")
                            msg_parts.append(f"• Trial resets: **{allowance_result['renewal_date']}**")
                        elif allowance_result['segment'] == 'paid':
                            msg_parts.append(f"📊 **Analysis** ({allowance_result['total_words']:,} words)")
                            msg_parts.append(f"• Remaining after: **{allowance_result['words_remaining_after']:,} words**")
                            msg_parts.append(f"• Allowance resets: **{allowance_result['renewal_date']}**")
                        elif allowance_result['segment'] == 'past_due':
                            msg_parts.append("⚠️ **Subscription Past Due**")
                            msg_parts.append(f"Analysis will use rollover words ({allowance_result['total_words']:,} words)")
                        
                        if allowance_result.get('upgrade_link'):
                            msg_parts.append(f"\n[View Dashboard →]({allowance_result['upgrade_link']})")
                        
                        st.info("\n".join(msg_parts))
            else:
                # Cannot proceed - show error and upgrade link
                st.error(f"❌ {allowance_result['error_message']}")
                if allowance_result.get('upgrade_link'):
                    st.markdown(f"[View Dashboard to Upgrade →]({allowance_result['upgrade_link']})")

    # Subscription allowance flow (only proceed if allowance check passed)
    if is_ready and pricing_result and pricing_result.get('can_proceed'):
        # Subscription system - no credit checks needed
        user_token = auth_manager.get_auth_token()
        if not user_token:
            st.error("❌ Authentication required. Please refresh the page and log in again.")
            return
        
        # Analysis section (allowance already verified)
        can_proceed = True
        if can_proceed:
            warning_placeholder = st.empty()
            warning_placeholder.info(
                "⚠️ **IMPORTANT:** Analysis takes up to **3-20 minutes**. Please don't close this tab until complete"
            )
            
            if st.button("3️⃣ Confirm & Analyze",
                       type="primary",
                       use_container_width=True,
                       key="asc718_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()
                processing_container.empty()
                pricing_container.empty()
                upload_form_container.empty()
                
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                
                # Get cached de-identified text
                cached_text_key = f'asc718_cached_text_{session_id}'
                cached_deidentify_key = f'asc718_cached_deidentify_{session_id}'
                
                if cached_deidentify_key in st.session_state:
                    deidentify_result = st.session_state[cached_deidentify_key]
                    cached_text = deidentify_result['text']
                else:
                    cached_text = None
                
                # Run analysis with cached text and pass uploaded filenames
                uploaded_filenames = [f.name for f in uploaded_files] if uploaded_files else []
                perform_asc718_analysis(pricing_result, additional_context, user_token, cached_combined_text=cached_text, uploaded_filenames=uploaded_filenames)
        else:
            st.button("3️⃣ Insufficient Credits", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc718_analyze_disabled")
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Confirm & Analyze", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc718_analyze_disabled")


def get_asc718_inputs_new():
    """Get ASC 718 specific inputs using modern direct file upload pattern."""
    
    # File uploader key initialization 
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
        
    uploaded_files = st.file_uploader(
        "1️⃣ Upload stock compensation agreements and related documents - PDF or DOCX files (required)",
        type=['pdf', 'docx'],
        accept_multiple_files=True,
        help="Upload stock compensation agreements, equity awards, or related documents for ASC 718 analysis",
        key=f"asc718_uploader_{st.session_state.get('file_uploader_key', 0)}"
    )

    # Additional info (optional)
    additional_context = st.text_area(
        "2️⃣ Additional information or concerns (optional)",
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents (e.g., verbal agreements, specific concerns about vesting conditions, performance metrics, or areas requiring focused analysis).",
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


def perform_asc718_analysis(pricing_result, additional_context: str = "", user_token: str = "", 
                           cached_combined_text: Optional[str] = None, uploaded_filenames: Optional[List[str]] = None):
    """Perform the complete ASC 718 analysis and display results with session isolation."""
    
    # Validate pricing result and user token
    if not pricing_result or not pricing_result.get('success'):
        st.error("❌ Invalid pricing information.")
        return
    
    if not user_token:
        st.error("❌ Authentication required.")
        return
    
    # Use cached text if provided (from privacy screen), otherwise extract from pricing result
    if cached_combined_text:
        contract_text = cached_combined_text
        filename_string = ", ".join(uploaded_filenames) if uploaded_filenames else "Uploaded Documents"
    else:
        # Reconstruct combined text from file details (same pattern as ASC 606)
        combined_text = ""
        filename_list = []
        
        for file_detail in pricing_result['file_details']:
            if 'text_content' in file_detail and file_detail['text_content'].strip():
                combined_text += f"\n\n=== {file_detail['filename']} ===\n\n{file_detail['text_content']}"
                filename_list.append(file_detail['filename'])
            else:
                # Fallback if text_content is missing
                combined_text += f"\n\n=== {file_detail['filename']} ===\n\n[File content extraction failed]"
                filename_list.append(file_detail['filename'])
        
        filename_string = ", ".join(filename_list) if filename_list else "Uploaded Documents"
        
        # Check if we have valid content
        if not combined_text.strip() or "[File content extraction failed]" in combined_text:
            st.error("❌ No readable content found in uploaded files.")
            return
            
        contract_text = combined_text.strip()
    
    # Session isolation - create unique session ID for this user
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
        logger.info(f"Created new user session: {st.session_state.user_session_id[:8]}...")
    
    session_id = st.session_state.user_session_id
    
    # Initialize analysis complete status with session isolation
    analysis_key = f'asc718_analysis_complete_{session_id}'
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = False
    
    # Submit background job for analysis
    user_token = st.session_state.get('auth_token', '')
    submit_and_monitor_asc718_job(
        pricing_result=pricing_result,
        additional_context=additional_context,
        user_token=user_token,
        cached_combined_text=contract_text,
        uploaded_filenames=uploaded_filenames,
        session_id=session_id
    )


# Configure logging
logging.basicConfig(level=logging.INFO)


# Main function for Streamlit navigation
def main():
    """Main function called by Streamlit navigation."""
    render_asc718_page()


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
    return f"ASC805_Analysis_{datetime.now().strftime('%m%d_%H%M%S')}"


# For direct execution/testing
if __name__ == "__main__":
    render_asc718_page()