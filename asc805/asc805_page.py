"""
ASC 805 Business Combination Analysis Page
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
from asc805.step_analyzer import ASC805StepAnalyzer
from asc805.knowledge_search import ASC805KnowledgeSearch
from utils.document_extractor import DocumentExtractor

logger = logging.getLogger(__name__)

def render_asc805_page():
    """Render the ASC 805 analysis page."""
    
    # Authentication check - must be logged in to access
    if not require_authentication():
        return  # User will see login page
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Page header
    st.title(":primary[ASC 805: Business Combinations]")
    st.info("**Purpose:** Automatically analyze business combination transactions and generate a first draft of professional ASC 805 memo. Simply upload your documents to begin.")
    
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
            st.success("✅ **Analysis Complete!**")
            st.markdown("### 📄 Generated ASC 805 Memo")
            
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
            
            # Add rerun functionality for existing completed memo
            from shared.rerun_manager import RerunManager
            rerun_manager = RerunManager()
            if analysis_id:
                rerun_manager.add_rerun_button(str(analysis_id))
            
            # Add sidebar rerun access
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 🔄 Request Changes")
                if st.button("Request Memo Rerun", type="secondary", use_container_width=True, key="sidebar_rerun"):
                    st.session_state[f'show_rerun_form_{analysis_id}'] = True
                    st.rerun()
            
            # Add "Analyze Another Contract" button
            st.markdown("---")
            if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True):
                # Reset analysis state for new analysis including file uploaders
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and ('asc805' in k.lower() or 'upload' in k.lower() or 'file' in k.lower())]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
            return  # Exit early, don't show file upload interface
    
    # Get user inputs with progressive disclosure  
    uploaded_files, additional_context, is_ready = get_asc805_inputs_new()

    # Show pricing information immediately when files are uploaded (regardless of is_ready)
    pricing_result = None
    if uploaded_files:
        # Process files for pricing - dynamic cost updating with progress indicator
        with st.spinner("📄 Analyzing document content and calculating costs. Please be patient for large files."):
            pricing_result = preflight_pricing.process_files_for_pricing(uploaded_files)
        
        if pricing_result['success']:
            # Display pricing information dynamically
            st.markdown("### :primary[Analysis Pricing]")
            st.info(pricing_result['billing_summary'])
            
            # Show file processing details
            if pricing_result.get('processing_errors'):
                st.warning(f"⚠️ **Some files had issues:** {'; '.join(pricing_result['processing_errors'])}")
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
                # Check if this contains multiple scanned PDF messages
                if "🔍 **Scanned/Image-Based PDF Detected" in pricing_result['error']:
                    # Multiple scanned PDFs - use HTML line breaks within single error box
                    error_msg = pricing_result['error'].replace('\n\n', '<br><br>')
                    st.error(error_msg, unsafe_allow_html=True)
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
                "⚠️ **IMPORTANT:** Keep this browser tab active during analysis!\n\n"
                "- Analysis takes **3-5 minutes**\n"
                "- Switching tabs or closing the browser will stop the analysis\n"
                "- Stay on this tab until analysis is complete\n"
                "- You'll see a completion message when it's done"
            )
            
            if st.button("3️⃣ Confirm, Start Analysis & Generate Memo",
                       type="primary",
                       use_container_width=True,
                       key="asc805_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()  # Clear the warning 
                pricing_container.empty()    # Clear pricing information
                credit_container.empty()     # Clear credit balance info
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                perform_asc805_analysis_new(pricing_result, additional_context, user_token)
        else:
            st.button("3️⃣ Insufficient Credits", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc805_analyze_disabled")
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Analyze Contract & Generate Memo", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc805_analyze_disabled")


def get_asc805_inputs_new():
    """Get ASC 805 specific inputs with new preflight system."""
    
    # Document upload section       
    uploaded_files = st.file_uploader(
        "1️⃣ Upload business combination documents - PDF or DOCX files, max 5 files - **FILE SIZE LIMIT:** Widget shows 200MB but our businsss limit is 50MB per file (required)",
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

    # Custom file size validation (50MB limit per our business rules)
    MAX_FILE_SIZE_MB = 50
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    if uploaded_files:
        # Validate file sizes
        oversized_files = []
        for file in uploaded_files:
            if file.size > MAX_FILE_SIZE_BYTES:
                oversized_files.append(f"{file.name} ({file.size / (1024*1024):.1f}MB)")
        
        if oversized_files:
            st.error(f"❌ **File size limit exceeded (50MB maximum):**\n" + 
                    "\n".join([f"• {f}" for f in oversized_files]))
            st.info("💡 **Tip:** The widget shows 200MB (Streamlit's technical limit), but our business limit is 50MB per file.")
            is_ready = False
        else:
            is_ready = True
    else:
        is_ready = False
    
    return uploaded_files, additional_context, is_ready


def perform_asc805_analysis_new(pricing_result: Dict[str, Any], additional_context: str, user_token: str):
    """Perform ASC 805 analysis with new billing system integration."""
    
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
        
        analysis_id = analysis_manager.start_analysis(analysis_details)
        
        # Step 2: Charge wallet
        charge_result = wallet_manager.charge_for_analysis(user_token, pricing_result['tier_info']['price'], analysis_details)
        
        if not charge_result['success']:
            st.error(f"❌ **Payment Failed**\n\n{charge_result['message']}")
            if analysis_id:
                analysis_manager.end_analysis(analysis_id, 'failed')
            return
            
        # Progress message that will be cleared later
        progress_message_placeholder = st.empty()
        progress_message_placeholder.info("🔄 **Analysis in progress...** Please stay on this tab.")
        
        # Get contract text from pricing result
        contract_text = pricing_result.get('combined_text', '')
        filename = pricing_result.get('filename', 'Business Combination Documents')
        customer_name = pricing_result.get('customer_name', 'Entity')
        analysis_title = f"Business Combination Analysis for {customer_name}"

        # Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC805StepAnalyzer()
                knowledge_search = ASC805KnowledgeSearch()
                from asc805.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator()
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 805 knowledge base is not available. Try again and contact support if this persists.")
                st.stop()
                return

        # Extract entity name using LLM (with regex fallback)
        with st.spinner("🏢 Extracting entity name..."):
            try:
                customer_name = analyzer.extract_entity_name_llm(contract_text)
                logger.info(f"LLM extracted customer : {customer_name}")
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {str(e)}, falling back to regex")
                customer_name = _extract_customer_name(contract_text)
                logger.info(f"Regex fallback customer name: {customer_name}")

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
        
        # Run 5 ASC 805 steps with progress
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
                    customer_name=customer_name,
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
            executive_summary = analyzer.generate_executive_summary(conclusions_text, customer_name)
            background = analyzer.generate_background_section(conclusions_text, customer_name)
            conclusion = analyzer.generate_conclusion_section(conclusions_text)
            
            # Combine into the expected structure for memo generator
            final_results = {
                'customer_name': customer_name,
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
            f"✅ **ANALYSIS COMPLETE!** Your professional ASC 805 memo is ready. Scroll down to view the results."
        )
        
        # Signal completion with session isolation
        st.session_state[analysis_key] = True
        
        # Store memo data with session isolation
        memo_key = f'asc805_memo_data_{session_id}'
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
             
        # Display memo inline instead of switching pages
        st.markdown("---")

        with st.container(border=True):
            st.markdown("""Your ASC 805 memo is displayed below. To save the results, you can either:
            
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
            
            # Clean up session-specific data
            memo_key = f'asc805_memo_data_{session_id}'
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
        logger.error(f"ASC 805 analysis error for session {session_id[:8]}...: {str(e)}")


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

def perform_asc805_analysis(contract_text: str, additional_context: str = ""):
    """Perform the complete ASC 805 analysis and display results with session isolation."""
    
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
    analysis_key = f'asc805_analysis_complete_{session_id}'
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = False
    
    # Generate analysis title
    analysis_title = _generate_analysis_title()

    try:
        # Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC805StepAnalyzer()
                knowledge_search = ASC805KnowledgeSearch()
                from asc805.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator(
                    template_path="asc805/templates/memo_template.md")
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 805 knowledge base is not available. Try again and contact support if this persists.")
                st.stop()
                return

        # Extract entity name using LLM (with regex fallback)
        with st.spinner("🏢 Extracting customer name..."):
            try:
                customer_name = analyzer.extract_entity_name_llm(contract_text)
                logger.info(f"LLM extracted customer : {customer_name}")
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {str(e)}, falling back to regex")
                customer_name = _extract_customer_name(contract_text)
                logger.info(f"Regex fallback customer name: {customer_name}")

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
        
        # Run 5 ASC 805 steps with progress
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
                    customer_name=customer_name,
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
            executive_summary = analyzer.generate_executive_summary(conclusions_text, customer_name)
            background = analyzer.generate_background_section(conclusions_text, customer_name)
            conclusion = analyzer.generate_conclusion_section(conclusions_text)
            
            # Combine into the expected structure for memo generator
            final_results = {
                'customer_name': customer_name,
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
            f"✅ **ANALYSIS COMPLETE!** Your professional ASC 805 memo is ready. Scroll down to view the results."
        )
        
        # Signal completion with session isolation
        st.session_state[analysis_key] = True
        
        # Store memo data with session isolation
        memo_key = f'asc805_memo_data_{session_id}'
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
             
        # Display memo inline instead of switching pages
        st.markdown("---")

        with st.container(border=True):
            st.markdown("""Your ASC 805 memo is displayed below. To save the results, you can either:
            
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
            
            # Clean up session-specific data
            memo_key = f'asc805_memo_data_{session_id}'
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
        logger.error(f"ASC 805 analysis error: {str(e)}")
        
        # End analysis tracking on error
        if analysis_id:
            analysis_manager.end_analysis(analysis_id, 'failed')
            
    finally:
        # Always end analysis tracking
        if analysis_id:
            analysis_manager.end_analysis(analysis_id, 'completed')

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