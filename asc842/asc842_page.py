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

def create_file_hash(uploaded_files):
    """Create a hash of uploaded files to detect changes."""
    if not uploaded_files:
        return None
    file_info = [(f.name, f.size) for f in uploaded_files]
    return hash(tuple(file_info))

def show_confirmation_screen(uploaded_files, pricing_result, additional_context, user_token, session_id):
    """Show privacy protection confirmation screen with de-identified text preview."""
    
    # Cache keys
    cached_text_key = f'asc842_cached_text_{session_id}'
    cached_deidentify_key = f'asc842_cached_deidentify_{session_id}'
    preview_confirmed_key = f'asc842_preview_confirmed_{session_id}'
    
    # If not already cached, extract and de-identify text
    if cached_text_key not in st.session_state:
        with st.spinner("📄 Extracting and processing lease agreement text..."):
            try:
                # Extract text from all files
                extractor = DocumentExtractor()
                all_texts = []
                failed_files = []
                
                for uploaded_file in uploaded_files:
                    # Reset file pointer to beginning
                    uploaded_file.seek(0)
                    result = extractor.extract_text(uploaded_file)
                    if result and isinstance(result, dict) and result.get('success'):
                        all_texts.append(result['text'])
                    else:
                        logger.warning(f"Failed to extract text from {uploaded_file.name}")
                        failed_files.append(uploaded_file.name)
                
                combined_text = "\n\n---\n\n".join(all_texts)
                
                # Store failed files list for UI display
                st.session_state[f'asc842_failed_files_{session_id}'] = failed_files
                
                # Extract party names and de-identify
                analyzer = ASC842StepAnalyzer()
                party_names = analyzer.extract_party_names_llm(combined_text)
                lessor_name = party_names.get('lessor')
                lessee_name = party_names.get('lessee')
                
                # Run de-identification
                deidentify_result = analyzer.deidentify_contract_text(
                    combined_text,
                    lessor_name,
                    lessee_name
                )
                
                # Cache results
                st.session_state[cached_text_key] = combined_text
                st.session_state[cached_deidentify_key] = deidentify_result
                
            except Exception as e:
                logger.error(f"Error in privacy processing: {str(e)}")
                st.error(f"❌ Error processing lease agreement: {str(e)}")
                return
    
    # Get cached results
    combined_text = st.session_state[cached_text_key]
    deidentify_result = st.session_state[cached_deidentify_key]
    failed_files = st.session_state.get(f'asc842_failed_files_{session_id}', [])
    
    # Show confirmation UI
    st.markdown("### 🔒 Privacy Protection Review")
    
    # Show warning if some files failed to extract
    if failed_files:
        st.warning(
            f"⚠️ **File extraction issues:** {len(failed_files)} file(s) could not be processed: "
            f"{', '.join(failed_files)}. The analysis will proceed with the remaining files only."
        )
    
    if deidentify_result['success']:
        # Success case - show what was replaced
        st.success("✓ Privacy protection applied successfully. Please contact support@veritaslogic.ai if you need any assistance.")
        
        # Info box with replacements
        with st.container(border=True):
            st.markdown("**Party names replaced:**")
            lessor_name = deidentify_result['lessor_name']
            lessee_name = deidentify_result['lessee_name']
            
            if lessor_name:
                st.markdown(f"• Lessor: **\"{lessor_name}\"** → **\"the Lessor\"**")
            if lessee_name:
                st.markdown(f"• Lessee: **\"{lessee_name}\"** → **\"the Company\"**")
        
        # Show preview of de-identified text
        preview_text = deidentify_result['text'][:4000]
        st.markdown("**Preview of text to be analyzed (first 4,000 characters):**")
        st.text_area(
            label="De-identified lease text",
            value=preview_text,
            height=300,
            disabled=True,
            label_visibility="collapsed"
        )
        
    else:
        # Failure case - show warning
        st.warning("⚠️ " + deidentify_result['error'])
        st.info(
            "**Your choice:** The system was unable to automatically detect and replace party names. "
            "You can still proceed with the analysis using the original text."
        )
        
        # Show preview of original text
        preview_text = combined_text[:4000]
        st.markdown("**Preview of text to be analyzed (first 4,000 characters):**")
        st.text_area(
            label="Original lease text",
            value=preview_text,
            height=300,
            disabled=True,
            label_visibility="collapsed"
        )
    
    # Confirmation and run button
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("◀️ Go Back", use_container_width=True, key="asc842_go_back"):
            # Clear confirmation state to go back
            show_review_screen_key = f'asc842_show_review_{session_id}'
            st.session_state[show_review_screen_key] = False
            st.session_state[preview_confirmed_key] = False
            st.rerun()
    
    with col2:
        if st.button("▶️ Run Analysis", type="primary", use_container_width=True, key="asc842_run_final"):
            # Mark as confirmed and run analysis
            st.session_state[preview_confirmed_key] = True
            
            # Clear the UI and run analysis
            st.empty()
            
            # Use cached de-identified text
            final_text = deidentify_result['text']
            
            # Run the analysis with the confirmed text
            # Pass uploaded filenames for memo header
            uploaded_filenames = [f.name for f in uploaded_files] if uploaded_files else []
            perform_asc842_analysis_new(
                pricing_result, 
                additional_context, 
                user_token,
                cached_combined_text=final_text,
                uploaded_filenames=uploaded_filenames
            )

def render_asc842_page():
    """Render the ASC 842 analysis page."""
    
    # Authentication check - must be logged in to access
    if not require_authentication():
        return  # User will see login page
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Page header
    st.title(":primary[ASC 842: Leases (Lessee)]")
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
            st.success("✅ **Analysis Complete!** This AI-generated analysis requires review by qualified accounting professionals and should be approved by management before use.")
            st.markdown("""📄 **Your ASC 842 memo is ready below.**  To save the results, you can either:

- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
- **Download:** Download the memo as a Markdown, PDF, or Word (.docx) file for later use.
            """)
            
            # Quick action buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<a href="#save-your-memo" style="text-decoration: none;"><button style="width: 100%; padding: 0.5rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer;">⬇️ Jump to Downloads</button></a>', unsafe_allow_html=True)
            with col2:
                if st.button("🔄 Start New Analysis", type="secondary", use_container_width=True, key="top_new_analysis_existing"):
                    keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc842' in k.lower()]
                    for key in keys_to_clear:
                        del st.session_state[key]
                    st.rerun()
            
            st.markdown("---")
            
            if memo_key in st.session_state:
                # Display the existing memo with enhanced downloads
                from asc842.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator()
                memo_data = st.session_state[memo_key]
                # Extract memo content from stored dictionary
                memo_content = memo_data['memo_content'] if isinstance(memo_data, dict) else memo_data
                # Extract parameters for memo display - prioritize session memo UUID
                analysis_id = (memo_data.get('analysis_id') if isinstance(memo_data, dict) else None) or \
                              st.session_state.get('analysis_manager_memo_uuid') or \
                              f"memo_{session_id}"
                filename = memo_data.get('filename') if isinstance(memo_data, dict) else None
                customer_name = memo_data.get('customer_name') if isinstance(memo_data, dict) else None
                memo_generator.display_clean_memo(memo_content, analysis_id, filename, customer_name)
                
                # Re-run policy note and "Analyze Another" button
                st.markdown("---")
                st.info("📋 Each analysis comes with one complimentary re-run within 14 days for input modifications or extractable text adjustments. If you'd like to request one, please contact support at support@veritaslogic.ai.")
                
                if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True, key="bottom_new_analysis_existing"):
                    # Clear session state for new analysis
                    keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc842' in k.lower()]
                    for key in keys_to_clear:
                        del st.session_state[key]
                    st.rerun()
                
                return
    
    # Get user inputs with progressive disclosure - wrap in container to allow clearing
    upload_form_container = st.empty()
    with upload_form_container.container():
        uploaded_files, additional_context, is_ready = get_asc842_inputs_new()

    # Process files when uploaded - extract, de-identify, and price
    pricing_result = None
    processing_container = st.empty()
    pricing_container = st.empty()
    
    if uploaded_files:
        # Step 1: Extract and de-identify for Document Processing section
        file_hash = create_file_hash(uploaded_files)
        privacy_hash_key = f'asc842_privacy_hash_{session_id}'
        cached_text_key = f'asc842_cached_text_{session_id}'
        cached_deidentify_key = f'asc842_cached_deidentify_{session_id}'
        cached_word_count_key = f'asc842_cached_word_count_{session_id}'
        
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
            with st.spinner("📄 Extracting and processing lease agreement text..."):
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
                    analyzer = ASC842StepAnalyzer()
                    party_names = analyzer.extract_party_names_llm(combined_text)
                    lessor_name = party_names.get('lessor')
                    lessee_name = party_names.get('lessee')
                    
                    deidentify_result = analyzer.deidentify_contract_text(
                        combined_text,
                        lessor_name,
                        lessee_name
                    )
                    
                    # Cache results
                    st.session_state[cached_text_key] = combined_text
                    st.session_state[cached_deidentify_key] = deidentify_result
                    st.session_state[cached_word_count_key] = word_count
                    st.session_state[f'asc842_failed_files_{session_id}'] = failed_files
                    
                except Exception as e:
                    logger.error(f"Error in document processing: {str(e)}")
                    st.error(f"❌ Error processing lease agreement: {str(e)}")
        
        # Show Document Processing section
        if cached_deidentify_key in st.session_state:
            deidentify_result = st.session_state[cached_deidentify_key]
            failed_files = st.session_state.get(f'asc842_failed_files_{session_id}', [])
            
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
                        if deidentify_result['lessor_name']:
                            st.markdown(f"• Lessor: **\"{deidentify_result['lessor_name']}\"** → **\"the Lessor\"**")
                        if deidentify_result['lessee_name']:
                            st.markdown(f"• Lessee: **\"{deidentify_result['lessee_name']}\"** → **\"the Company\"**")
                    
                    # Show 4000-char preview
                    preview_text = deidentify_result['text'][:4000]
                    st.markdown("**Preview of text to be analyzed (first 4,000 characters):**")
                    st.text_area(
                        label="De-identified lease text",
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
                        label="Original lease text",
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
                "⚠️ **IMPORTANT:** Analysis takes up to **3-20 minutes**. Please don't close this tab until complete"
            )
            
            if st.button("3️⃣ Confirm & Analyze",
                       type="primary",
                       use_container_width=True,
                       key="asc842_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()  # Clear the warning 
                processing_container.empty()  # Clear document processing preview
                pricing_container.empty()    # Clear pricing information
                credit_container.empty()     # Clear credit balance info
                upload_form_container.empty()  # Clear upload form
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                
                # Use cached de-identified text if available
                cached_deidentify_key = f'asc842_cached_deidentify_{session_id}'
                if cached_deidentify_key in st.session_state:
                    deidentify_result = st.session_state[cached_deidentify_key]
                    final_text = deidentify_result['text']
                    uploaded_filenames = [f.name for f in uploaded_files] if uploaded_files else []
                    perform_asc842_analysis_new(
                        pricing_result, 
                        additional_context, 
                        user_token,
                        cached_combined_text=final_text,
                        uploaded_filenames=uploaded_filenames
                    )
                else:
                    # Fallback to original flow if no cached text
                    perform_asc842_analysis_new(pricing_result, additional_context, user_token)
        else:
            st.button("3️⃣ Insufficient Credits", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc842_analyze_disabled")
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Confirm & Analyze", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc842_analyze_disabled")


def get_asc842_inputs_new():
    """Get ASC 842 specific inputs with new preflight system."""
    
    # Document upload section       
    uploaded_files = st.file_uploader(
        "1️⃣ Upload lease agreement and related documents - PDF or DOCX files (required)",
        type=['pdf', 'docx'],
        accept_multiple_files=True,
        help="Upload lease agreements, amendments, schedules, addenda, etc. for ASC 842 analysis",
        key=f"asc842_uploader_{st.session_state.get('file_uploader_key', 0)}"
    )

    # Additional info (optional)
    additional_context = st.text_area(
        "2️⃣ Additional information or concerns (optional)",
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents or specify your areas of focus or concerns.",
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


def perform_asc842_analysis_new(pricing_result: dict, additional_context: str, user_token: str, cached_combined_text: str = None, uploaded_filenames: list = None):
    """Perform the complete ASC 842 analysis using new file processing system."""
    
    # Session isolation - create unique session ID for this user
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
        logger.info(f"Created new user session: {st.session_state.user_session_id[:8]}...")
    
    session_id = st.session_state.user_session_id
    
    # Create placeholder for the in-progress message
    progress_message_placeholder = st.empty()
    progress_message_placeholder.error(
        "🚨 **IMPORTANT: ANALYSIS IN PROGRESS - DO NOT CLOSE THIS TAB!**\n\n"
        "Your analysis is running and will take up to 3-20 minutes. "
        "Closing this browser will stop the analysis and forfeit your progress."
    )
    
    # Initialize analysis complete status with session isolation
    analysis_key = f'asc842_analysis_complete_{session_id}'
    memo_key = f'asc842_memo_data_{session_id}'
    
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = False
    
    try:
        # Process billing using wallet manager (like ASC 340-40)
        required_price = pricing_result['tier_info']['price']
        analysis_details = {
            'asc_standard': 'ASC 842',
            'total_words': pricing_result.get('total_words', 0),
            'file_count': pricing_result.get('file_count', 0),
            'tier_info': pricing_result['tier_info'],
            'cost_charged': pricing_result['tier_info']['price']
        }
        
        # Payment will be processed when analysis completes (no upfront charging)
        
        # Use cached text if available, otherwise extract from file details
        if cached_combined_text:
            combined_text = cached_combined_text
            filename_string = ", ".join(uploaded_filenames) if uploaded_filenames else "lease_contract.txt"
        else:
            # Extract combined text from file details (like ASC 340-40)
            combined_text = ""
            filename_list = []
            
            for file_detail in pricing_result.get('file_details', []):
                if 'text_content' in file_detail and file_detail['text_content'].strip():
                    combined_text += f"\n\n=== {file_detail['filename']} ===\n\n{file_detail['text_content']}"
                    filename_list.append(file_detail['filename'])
            
            filename_string = ", ".join(filename_list)
        
        if not combined_text.strip():
            st.error("❌ No readable content found in uploaded files. Please check your documents and try again.")
            return
        
        # Proceed with original analysis logic using the extracted text
        perform_asc842_analysis(combined_text, additional_context, filename_string, analysis_details)
        
        # Clear the progress message after analysis
        progress_message_placeholder.empty()
        
    except Exception as e:
        logger.error(f"ASC 842 analysis error for session {session_id[:8]}: {str(e)}")
        # Clear the progress message on error
        progress_message_placeholder.empty()
        st.error("❌ Analysis failed. Please try again. Contact support if this issue persists.")

def perform_asc842_analysis(contract_text: str, additional_context: str = "", filename: str = "lease_contract.txt", analysis_details: dict = None):
    """Perform the complete ASC 842 analysis and display results with session isolation."""
    
    # Session isolation - create unique session ID for this user
    if 'user_session_id' not in st.session_state:
        st.session_state.user_session_id = str(uuid.uuid4())
        logger.info(f"Created new user session: {st.session_state.user_session_id[:8]}...")
    
    session_id = st.session_state.user_session_id
    
    # NOTE: Progress message now managed by calling function to avoid duplication
    
    # Initialize analysis complete status with session isolation
    analysis_key = f'asc842_analysis_complete_{session_id}'
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = False
    
    # Start analysis tracking for database capture
    if analysis_details is None:
        # Fallback for legacy calls
        pricing_result = st.session_state.get('pricing_result', {})
        analysis_details = {
            'asc_standard': 'ASC 842',
            'total_words': len(contract_text.split()),
            'file_count': 1,
            'tier_info': pricing_result.get('tier_info', {}),
            'cost_charged': pricing_result.get('tier_info', {}).get('price', 0.0)
        }
    analysis_id = analysis_manager.start_analysis(analysis_details)
    
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
        with st.spinner("🔁 Starting..."):
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

                # Analyze the step with additional context (using retry wrapper)
                step_result = analyzer._analyze_step_with_retry(
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
            # Extract conclusions once from the 5 steps
            conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results)
            
            # Generate the three additional sections
            executive_summary = analyzer.generate_executive_summary(conclusions_text, entity_name)
            background = analyzer.generate_background_section(conclusions_text, entity_name)
            conclusion = analyzer.generate_final_conclusion(conclusions_text)
            
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
        # NOTE: Progress message clearing handled by calling function
        progress_placeholder.empty()  # Clears the step headers
        progress_indicator_placeholder.empty()  # Clears the persistent success boxes
        
        # Create clearable completion message
        completion_message_placeholder = st.empty()
        completion_message_placeholder.success(
            f"✅ **ANALYSIS COMPLETE!** Your professional ASC 842 memo is ready. Scroll down to view the results."
        )
        
        # Signal completion with session isolation
        st.session_state[analysis_key] = True
        
        # Complete analysis for database capture  
        memo_uuid = None
        if analysis_id:
            completion_result = analysis_manager.complete_analysis(analysis_id, success=True)
            # Extract memo_uuid from the database save response
            memo_uuid = st.session_state.get('analysis_manager_memo_uuid', analysis_id)
        
        # Store memo data with session isolation
        memo_key = f'asc842_memo_data_{session_id}'
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'entity_name': entity_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y"),
            'analysis_id': memo_uuid or analysis_id  # Use database memo_uuid if available
        }
        
        st.success("✅ **Analysis Complete!** This AI-generated analysis requires review by qualified accounting professionals and should be approved by management before use.")
        st.markdown("""📄 **Your ASC 842 memo is ready below.** To save the results, you can either:

- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
- **Download:** Download the memo as a Markdown, PDF, or Word (.docx) file for later use.

        """)
        
        # Quick action buttons
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<a href="#save-your-memo" style="text-decoration: none;"><button style="width: 100%; padding: 0.5rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer;">⬇️ Jump to Downloads</button></a>', unsafe_allow_html=True)
        with col2:
            if st.button("🔄 Start New Analysis", type="secondary", use_container_width=True, key="top_new_analysis_fresh"):
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc842' in k.lower()]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
        
        st.markdown("---")
        
        # Display the memo using CleanMemoGenerator (like ASC 606)
        memo_generator_display = CleanMemoGenerator()
        memo_generator_display.display_clean_memo(memo_content, analysis_id, filename, entity_name)
        
        # Re-run policy note and "Analyze Another" button
        st.markdown("---")
        st.info("📋 Each analysis comes with one complimentary re-run within 14 days for input modifications or extractable text adjustments. If you'd like to request one, please contact support at support@veritaslogic.ai.")
        
        if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True, key="bottom_new_analysis_fresh"):
            # Clear session state for new analysis
            keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc842' in k.lower()]
            for key in keys_to_clear:
                del st.session_state[key]
            st.rerun()
        
        # Clear completion message after memo displays (but keep the important info above)
        completion_message_placeholder.empty()

    except Exception as e:
        st.error("❌ Analysis failed. Please try again. Contact support if this issue persists.")
        logger.error(f"ASC 842 analysis error for session {session_id[:8]}...: {str(e)}")
        st.session_state[analysis_key] = True  # Signal completion (even on error)
        
        # Complete analysis for database capture (failure)
        if 'analysis_id' in locals():
            analysis_manager.complete_analysis(analysis_id, success=False, error_message=str(e))


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