"""
ASC 805 Business Combination Analysis Page
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
from asc805.step_analyzer import ASC805StepAnalyzer
from asc805.knowledge_search import ASC805KnowledgeSearch
from utils.document_extractor import DocumentExtractor
from asc805.job_analysis_runner import submit_and_monitor_asc805_job

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
        analysis_key = f'asc805_analysis_complete_{session_id}'
        memo_key = f'asc805_memo_data_{session_id}'
        
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
    memo_key = f'asc805_memo_data_{session_id}'
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
            f'{website_url}/api/analysis/recent/asc805',
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

def render_asc805_page():
    """Render the ASC 805 analysis page."""
    
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
    st.title(":primary[ASC 805: Business Combinations]")
    with st.container(border=True):
        st.markdown(":primary[**Purpose:**] Automatically analyze business combination transactions and generate a first draft of professional ASC 805 memo. Simply upload your documents to begin.")
    
    # Check for active analysis first
    if analysis_manager.show_active_analysis_warning():
        return  # User has active analysis, show warning and exit
    
    # Check for existing completed analysis in session state (restore persistence)
    session_id = st.session_state.get('user_session_id', '')
    if session_id:
        analysis_key = f'asc805_analysis_complete_{session_id}'
        memo_key = f'asc805_memo_data_{session_id}'
        
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
            st.markdown("""📄 **Your ASC 805 memo is ready below.**  To save the results, you can either:

- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
- **Download:** Download the memo as a Markdown, PDF, or Word (.docx) file for later use.
                        """)
            
            # Quick action buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<a href="#save-your-memo" style="text-decoration: none;"><button style="width: 100%; padding: 0.5rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer;">⬇️ Jump to Downloads</button></a>', unsafe_allow_html=True)
            with col2:
                if st.button("🔄 Start New Analysis", type="secondary", use_container_width=True, key="top_new_analysis_existing"):
                    keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc805' in k.lower()]
                    for key in keys_to_clear:
                        del st.session_state[key]
                    st.session_state['skip_auto_load'] = True
                    st.rerun()
            
            st.markdown("---")
            
            # Display the existing memo with enhanced downloads
            from asc805.clean_memo_generator import CleanMemoGenerator
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
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc805' in k.lower()]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.session_state['skip_auto_load'] = True
                st.rerun()
            
            return  # Exit early, don't show file upload interface
    
    # Get user inputs with progressive disclosure - wrap in container to allow clearing
    upload_form_container = st.empty()
    with upload_form_container.container():
        uploaded_files, additional_context, is_ready = get_asc805_inputs_new()

    # Process files when uploaded - extract, de-identify, and price
    pricing_result = None
    processing_container = st.empty()
    pricing_container = st.empty()
    
    if uploaded_files:
        # Step 1: Extract and de-identify for Document Processing section
        cached_text_key = f'asc805_cached_text_{session_id}'
        cached_deidentify_key = f'asc805_cached_deidentify_{session_id}'
        cached_word_count_key = f'asc805_cached_word_count_{session_id}'
        
        # Extract and de-identify if not cached
        if cached_text_key not in st.session_state:
            with st.spinner("📄 Extracting and processing transaction documents..."):
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
                    analyzer = ASC805StepAnalyzer()
                    party_names = analyzer.extract_party_names_llm(combined_text)
                    acquirer_name = party_names.get('acquirer')
                    target_name = party_names.get('target')
                    
                    deidentify_result = analyzer.deidentify_contract_text(
                        combined_text,
                        acquirer_name,
                        target_name
                    )
                    
                    # Cache results
                    st.session_state[cached_text_key] = combined_text
                    st.session_state[cached_deidentify_key] = deidentify_result
                    st.session_state[cached_word_count_key] = word_count
                    st.session_state[f'asc805_failed_files_{session_id}'] = failed_files
                    
                except Exception as e:
                    logger.error(f"Error in document processing: {str(e)}")
                    st.error(f"❌ Error processing transaction documents: {str(e)}")
        
        # Show Document Processing section
        if cached_deidentify_key in st.session_state:
            deidentify_result = st.session_state[cached_deidentify_key]
            failed_files = st.session_state.get(f'asc805_failed_files_{session_id}', [])
            
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
                        if deidentify_result['acquirer_name']:
                            st.markdown(f"• Acquirer: **\"{deidentify_result['acquirer_name']}\"** → **\"the Company\"**")
                        if deidentify_result['target_name']:
                            st.markdown(f"• Target: **\"{deidentify_result['target_name']}\"** → **\"the Target\"**")
                    
                    # Show 4000-char preview
                    preview_text = deidentify_result['text'][:4000]
                    st.markdown("**Preview of text to be analyzed (first 4,000 characters):**")
                    st.text_area(
                        label="De-identified transaction text",
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
                        label="Original transaction text",
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

            # Always show allowance information (not just when there's a warning)
            with pricing_container.container():
                if allowance_result['can_proceed']:
                    # Show allowance status
                    msg_parts = []
                    if allowance_result['segment'] == 'trial':
                        msg_parts.append(f"🎉 **Trial Analysis** ({allowance_result['total_words']:,} words)")
                        msg_parts.append(f"• Words available: **{allowance_result['words_available']:,}**")
                        msg_parts.append(f"• Remaining after this analysis: **{allowance_result['words_remaining_after']:,} words**")
                        msg_parts.append(f"• Trial resets: **{allowance_result['renewal_date']}**")
                    elif allowance_result['segment'] == 'paid':
                        msg_parts.append(f"📊 **Subscription Analysis** ({allowance_result['total_words']:,} words)")
                        msg_parts.append(f"• Words available: **{allowance_result['words_available']:,}**")
                        msg_parts.append(f"• Remaining after: **{allowance_result['words_remaining_after']:,} words**")
                        msg_parts.append(f"• Allowance resets: **{allowance_result['renewal_date']}**")
                    
                    if allowance_result.get('upgrade_link'):
                        msg_parts.append(f"\n[View Dashboard →]({allowance_result['upgrade_link']})")
                    
                    # Use warning styling if low on words, otherwise info
                    if allowance_result.get('show_warning'):
                        st.warning("\n".join(msg_parts))
                    else:
                        st.info("\n".join(msg_parts))
                else:
                    # Cannot proceed - past_due, insufficient allowance, or no subscription
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
                "⚠️ **IMPORTANT:** ** Please confirm that the documents uploaded above are complete. Also, note that analysis takes up to **3-20 minutes**."
            )
            
            if st.button("3️⃣ Confirm & Analyze",
                       type="primary",
                       use_container_width=True,
                       key="asc805_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()
                processing_container.empty()
                pricing_container.empty()
                upload_form_container.empty()
                
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                
                # Get cached de-identified text
                cached_text_key = f'asc805_cached_text_{session_id}'
                cached_deidentify_key = f'asc805_cached_deidentify_{session_id}'
                
                if cached_deidentify_key in st.session_state:
                    deidentify_result = st.session_state[cached_deidentify_key]
                    cached_text = deidentify_result['text']
                else:
                    cached_text = None
                
                # Run analysis with cached text and pass uploaded filenames
                uploaded_filenames = [f.name for f in uploaded_files] if uploaded_files else []
                perform_asc805_analysis_new(pricing_result, additional_context, user_token, cached_combined_text=cached_text, uploaded_filenames=uploaded_filenames)
        else:
            st.button("3️⃣ Insufficient Credits", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc805_analyze_disabled")
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Confirm & Analyze", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc805_analyze_disabled")


def get_asc805_inputs_new():
    """Get ASC 805 specific inputs with new preflight system."""
    
    # Document upload section       
    uploaded_files = st.file_uploader(
        "1️⃣ Upload business combination documents - PDF or DOCX files (required)",
        type=['pdf', 'docx'],
        accept_multiple_files=True,
        help="Upload purchase agreements, merger documents, LOI, due diligence reports for ASC 805 analysis",
        key=f"asc805_uploader_{st.session_state.get('file_uploader_key', 0)}"
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

def perform_asc805_analysis_new(pricing_result: Dict[str, Any], additional_context: str, user_token: str, cached_combined_text: Optional[str] = None, uploaded_filenames: Optional[List[str]] = None):
    """Perform ASC 805 analysis with new billing system integration."""
    
    # Session isolation - create unique session ID for this user
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
        logger.info(f"Created new user session: {st.session_state.user_session_id[:8]}...")
    
    session_id = st.session_state.user_session_id
    
    # Create session-specific keys
    analysis_key = f'asc805_analysis_complete_{session_id}'
    memo_key = f'asc805_memo_data_{session_id}'
    
    analysis_id = None
    
    try:
        # Step 1: Start analysis tracking
        analysis_details = {
            'asc_standard': 'ASC 805',
            'total_words': pricing_result['total_words'],
            'file_count': pricing_result['file_count'],
            'tier_info': pricing_result['tier_info'],
            'cost_charged': pricing_result['tier_info']['price']
        }
        
        # Get contract text from cached text or pricing result
        contract_text = cached_combined_text if cached_combined_text else pricing_result.get('combined_text', '')
        
        # Submit background job for analysis
        user_token = st.session_state.get('auth_token', '')
        
        # Get user's org_id for word deduction
        user_data = st.session_state.get('user_data', {})
        org_id = user_data.get('org_id')
        
        # Add file_count to pricing_result (needed by job submission)
        pricing_result['file_count'] = len(uploaded_filenames) if uploaded_filenames else 0
        
        submit_and_monitor_asc805_job(
            allowance_result=pricing_result,
            additional_context=additional_context,
            user_token=user_token,
            cached_combined_text=contract_text,
            uploaded_filenames=uploaded_filenames,
            session_id=session_id,
            org_id=org_id,
            total_words=pricing_result['total_words']
        )
        
    except Exception as e:
        logger.error(f"ASC 805 analysis error for session {session_id[:8]}: {str(e)}")
        st.error("❌ Analysis failed. Please try again. Contact support if this issue persists.")


def _upload_and_process_asc805():
    """Handle file upload and processing specifically for ASC 805 analysis."""
    # Use session state to control file uploader key for clearing
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
        
    uploaded_files = st.file_uploader(
        "1️⃣ Upload a **complete purchase agreement and related documents**, e.g., executed purchase agreement, asset purchase agreement, merger agreement, LOI, due diligence reports (required)",
        type=['pdf', 'docx'],
        help="Upload up to 5 relevant transaction documents (PDF or DOCX) for ASC 805 business combinations analysis. Include the main purchase agreement and any amendments, letters of intent, due diligence reports, or related documentation. Incomplete documentation may lead to inaccurate acquisition accounting analysis.",
        accept_multiple_files=True,
        key=f"contract_files_{st.session_state.file_uploader_key}"
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

def _extract_customer_name(contract_text: str) -> str:
    """Extract entity name from business combination documents."""
    try:
        import re
        
        if not contract_text:
            return "Entity"

        # Normalize quotes and whitespace
        sample = contract_text[:6000].replace(""", '"').replace(""", '"').replace("'", "'")
        sample = re.sub(r'[ \t]+', ' ', sample)

        def clean_name(name: str) -> str:
            n = name.strip().strip(' "').strip()
            n = re.sub(r'\s+', ' ', n)
            n = re.sub(r'[\s\.,;:)\]]+$', '', n)
            if len(n) < 3 or len(n) > 120:
                return ""
            return n

        def plausible_company(name: str) -> bool:
            if not name:
                return False
            addr_tokens = {"street", "st.", "road", "rd.", "avenue", "ave.", "suite", "ste.", "floor", "fl.", "drive", "dr.", "blvd", "boulevard", "lane", "ln.", "way", "p.o.", "po box", "box"}
            lname = name.lower()
            if any(t in lname for t in addr_tokens):
                return False
            if not re.search(r'[A-Za-z]', name):
                return False
            return True

        # Look for acquiring/target company patterns
        target_patterns = [
            r'\b(?:target|acquired|acquisition)\s+(?:company|entity|corporation|corp|inc|llc)[\s:]*([A-Za-z0-9\.\,&\-\s]{3,120})',
            r'\b([A-Za-z0-9\.\,&\-\s]{3,120})\s+\((?:the\s+)?["\']?(?:target|acquired|acquisition)["\']?\s*\)',
            r'\bbetween\s+([^,\n;]+?)\s+and\s+([^,\n;]+)',
        ]
        
        for pattern in target_patterns:
            matches = re.finditer(pattern, sample, re.IGNORECASE)
            for match in matches:
                for group in match.groups():
                    name = clean_name(group)
                    if name and plausible_company(name):
                        return name

        # Company suffix fallback
        company_suffix = re.compile(
            r'([A-Z][A-Za-z0-9&\.\- ]{2,80}?\s(?:Inc\.?|Incorporated|LLC|L\.L\.C\.|Ltd\.?|Limited|Corp\.?|Corporation|PLC|LP|LLP|GmbH|S\.?A\.?R\.?L\.?|S\.?A\.?|SAS|BV|NV|Pty\.?\s?Ltd\.?|Co\.?))\b'
        )
        matches = company_suffix.findall(sample)
        if matches:
            for name in matches:
                if plausible_company(clean_name(name)):
                    return clean_name(name)

        return "Entity"

    except Exception as e:
        if 'logger' in globals():
            logger.error(f"Error extracting entity name: {str(e)}")
        return "Entity"


def _generate_analysis_title() -> str:
    """Generate analysis title with timestamp."""
    return f"ASC805_Analysis_{datetime.now().strftime('%m%d_%H%M%S')}"


# Configure logging
logging.basicConfig(level=logging.INFO)


# Main function for Streamlit navigation
def main():
    """Main function called by Streamlit navigation."""
    render_asc805_page()


# Legacy system components removed - Using modern direct approach


# Configure logging
logging.basicConfig(level=logging.INFO)


# Main function for Streamlit navigation
def main():
    """Main function called by Streamlit navigation."""
    render_asc805_page()


# For direct execution/testing
if __name__ == "__main__":
    render_asc805_page()