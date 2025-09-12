"""
ASC 340-40 Contract Analysis Page
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
from asc340.step_analyzer import ASC340StepAnalyzer
from asc340.knowledge_search import ASC340KnowledgeSearch

logger = logging.getLogger(__name__)


def render_asc340_page():
    """Render the ASC 340-40 analysis page."""
    
    # Authentication check - must be logged in to access
    if not require_authentication():
        return  # User will see login page
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Page header
    st.title(":primary[ASC 340-40 Commission Cost Analyzer]")
    with st.container(border=True):
        st.markdown("""
        :primary[**Purpose:**] Automatically analyze commission and related documents and generate a professional policy memo. Simply upload your documents to begin. 

:primary[**Note:**] This tool only analyzes the cost of obtaining a contract, not the costs to fulfill a contract. 
        """)
    
    # Check for active analysis first
    if analysis_manager.show_active_analysis_warning():
        return  # User has active analysis, show warning and exit
    
    # Check for existing completed analysis in session state (restore persistence)
    session_id = st.session_state.get('user_session_id', '')
    if session_id:
        analysis_key = f'asc340_analysis_complete_{session_id}'
        memo_key = f'asc340_memo_data_{session_id}'
        
        # If analysis is complete and memo exists, show results instead of file upload
        if st.session_state.get(analysis_key, False) and st.session_state.get(memo_key):
            st.success("✅ **Analysis Complete!**")
            st.markdown("### 📄 Generated ASC 340-40 Memo")
            
            # Display the existing memo with enhanced downloads
            from asc340.clean_memo_generator import CleanMemoGenerator
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
            rerun_manager.add_rerun_button(analysis_id)
            
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
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and ('asc340' in k.lower() or 'upload' in k.lower() or 'file' in k.lower())]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
            return  # Exit early, don't show file upload interface
    
    # Get user inputs with progressive disclosure  
    uploaded_files, additional_context, is_ready = get_asc340_inputs_new()

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
                "⚠️ **IMPORTANT:** Analysis takes up to **3-5 minutes**. Please don't close this tab until complete"
            )
            
            if st.button("3️⃣ Confirm, Start Analysis & Generate Memo",
                       type="primary",
                       use_container_width=True,
                       key="asc340_analyze"):
                # Clear all UI elements that should disappear during analysis
                warning_placeholder.empty()  # Clear the warning 
                # Keep pricing information visible during analysis (it's helpful)
                credit_container.empty()     # Clear credit balance info
                if not user_token:
                    st.error("❌ Authentication required. Please refresh the page and log in again.")
                    return
                perform_asc340_analysis_new(pricing_result, additional_context, user_token)
        else:
            st.button("3️⃣ Insufficient Credits", 
                     disabled=True, 
                     use_container_width=True,
                     key="asc340_analyze_disabled")
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Analyze Contract & Generate Memo", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc340_analyze_disabled")


def get_asc340_inputs_new():
    """Get ASC 340-40 specific inputs with new preflight system."""
    
    # Document upload section       
    uploaded_files = st.file_uploader(
        "1️⃣ Upload commission and related documents - PDF or DOCX files (required)",
        type=['pdf', 'docx'],
        accept_multiple_files=True,
        help="Upload commission plans, compensation policies, SPIFF announcements, channel agreements, etc. for ASC 340-40 analysis",
        key=f"asc340_uploader_{st.session_state.get('file_uploader_key', 0)}"
    )

    # Additional info (optional)
    additional_context = st.text_area(
        "2️⃣ Additional information or concerns (optional)",
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents or specify your areas of focus or concerns.",
        height=100)
    
    # Determine if ready to proceed (no file size limits for enterprise)
    if uploaded_files:
        is_ready = True
    else:
        is_ready = False
    
    return uploaded_files, additional_context, is_ready

def get_asc340_inputs():
    """Get ASC 340-40 specific inputs."""

    # Document upload with ASC 340-40 specific help text
    contract_text, filename = _upload_and_process_asc340()

    # Additional info (optional)
    additional_context = st.text_area(
        "2️⃣ Additional information or concerns (optional)",
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents or specificy your areas of focus or concerns.",
        height=100)

    # Check completion status - only contract text required
    is_ready = bool(contract_text)

    return contract_text, filename, additional_context, is_ready


def _upload_and_process_asc340():
    """Handle file upload and processing specifically for ASC 340-40 analysis."""
    # Use session state to control file uploader key for clearing
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
        
    uploaded_files = st.file_uploader(
        "1️⃣ Upload a **sales commission plan and related documents**, e.g., plan documents, compensation policy handbooks, SPIFF/contest announcements, channel/partner agreements, quota sheets (required)",
        type=['pdf', 'docx'],
        help="Upload up to 5 relevant commission and contract cost documents (PDF or DOCX) for ASC 340-40 analysis. Complete documentation supports accurate capitalization and amortization analysis.",
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
                else:
                    st.warning(f"⚠️ No readable content extracted from {uploaded_file.name}")
        
        if not combined_text.strip():
            st.error("❌ No readable content found in any uploaded files. Please check your documents and try again.")
            return None, None
        
        # Create comma-separated filename string
        filename_string = ", ".join(processed_filenames)
        
        return combined_text.strip(), filename_string
        
    except Exception as e:
        logger.error(f"Error processing uploaded files: {str(e)}")
        st.error(f"❌ Error processing files: {str(e)}")
        return None, None


# Old validation function removed - using progressive disclosure approach instead


def perform_asc340_analysis_new(pricing_result: Dict[str, Any], additional_context: str, user_token: str):
    """Perform ASC 340-40 analysis with new billing system integration."""
    
    analysis_id = None
    
    try:
        # Step 1: Start analysis tracking
        analysis_details = {
            'asc_standard': 'ASC 340-40',
            'total_words': pricing_result['total_words'],
            'file_count': pricing_result['file_count'],
            'tier_info': pricing_result['tier_info'],
            'cost_charged': pricing_result['tier_info']['price']
        }
        
        analysis_id = analysis_manager.start_analysis(analysis_details)
        
        # Step 2: Charge wallet
        charge_result = wallet_manager.charge_for_analysis(user_token, pricing_result['tier_info']['price'], analysis_details)
        
        if not charge_result['success']:
            analysis_manager.complete_analysis(analysis_id, success=False, error_message=f"Payment failed: {charge_result['error']}")
            st.error(f"❌ **Payment Failed**\\n\\n{charge_result['error']}")
            return
        
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
            
            # Auto-credit the user since analysis can't proceed
            if analysis_id:
                billing_manager.auto_credit_on_failure(user_token, pricing_result['tier_info']['price'], analysis_id)
                analysis_manager.complete_analysis(analysis_id, success=False, error_message="File content reconstruction not implemented")
            
            st.success("💰 **Refund Processed**: The full amount has been credited back to your wallet.")
            return
        
        # Step 4: Show analysis warning and proceed with full workflow
        progress_message_placeholder = st.empty()
        progress_message_placeholder.error(
            "🚨 **ANALYSIS IN PROGRESS - DO NOT CLOSE THIS TAB!**\n\n"
            "Your analysis is running and will take up to 3-5 minutes. "
            "Closing this browser will stop the analysis and forfeit your progress."
        )
        
        # Step 5: Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC340StepAnalyzer()
                knowledge_search = ASC340KnowledgeSearch()
                from asc340.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator(template_path="asc340/templates/memo_template.md")
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                analysis_manager.complete_analysis(analysis_id, success=False, error_message=f"Component initialization failed: {str(e)}")
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 340-40 knowledge base is not available. Try again and contact support if this persists.")
                return

        # Extract customer name
        with st.spinner("🏢 Extracting customer name..."):
            try:
                customer_name = analyzer.extract_entity_name_llm(combined_text)
                logger.info(f"LLM extracted customer: {customer_name}")
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {str(e)}, falling back to regex")
                customer_name = "Unknown Customer"  # Simple fallback
                    
        # Setup progress tracking
        steps = [
            "Processing", "Step 1", "Step 2", "Memo Generation"
        ]
        progress_placeholder = st.empty()
        progress_indicator_placeholder = st.empty()
        
        # Run 2 ASC 340-40 steps with progress indicators
        analysis_results = {}
        
        for step_num in range(1, 3):
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
                    logger.info(f"Completed ASC 340-40 Step {step_num}")
                except Exception as e:
                    logger.error(f"Error in Step {step_num}: {str(e)}")
                    # Continue with other steps
                    analysis_results[f'step_{step_num}'] = {
                        'markdown_content': f"Error in Step {step_num}: {str(e)}",
                        'title': f"Step {step_num}: Error",
                        'step_num': str(step_num)
                    }
        
        # Show memo generation progress
        ui.analysis_progress(steps, 3, progress_indicator_placeholder)
        
        # Generate memo
        with st.spinner("📄 Generating professional memo..."):
            try:
                # Extract conclusions and generate additional sections
                conclusions_text = analyzer._extract_conclusions_from_steps(analysis_results)
                executive_summary = analyzer.generate_executive_summary(conclusions_text, customer_name)
                background = analyzer.generate_background_section(conclusions_text, customer_name) 
                final_conclusion = analyzer.generate_final_conclusion(analysis_results)
                
                # Prepare analysis_results dict with all components for CleanMemoGenerator
                memo_analysis_results = {
                    **analysis_results,  # Include all step results
                    'customer_name': customer_name,
                    'filename': filename,
                    'executive_summary': executive_summary,
                    'background': background,
                    'conclusion': final_conclusion,
                    'additional_context': additional_context
                }
                
                # Generate clean memo using the memo generator
                memo_result = memo_generator.combine_clean_steps(memo_analysis_results)
                
                # Mark analysis as successful
                analysis_manager.complete_analysis(analysis_id, success=True)
                
                # Clear progress and warning message, show results
                progress_indicator_placeholder.empty()
                progress_message_placeholder.empty()  # Remove the warning
                
                # memo_result is a string (markdown content), not a dict
                if memo_result:
                    
                    # Store memo in session state for persistence
                    if 'user_session_id' not in st.session_state:
                        st.session_state.user_session_id = str(uuid.uuid4())
                    
                    session_id = st.session_state.user_session_id
                    memo_key = f'asc340_memo_data_{session_id}'
                    analysis_key = f'asc340_analysis_complete_{session_id}'
                    
                    # Store memo data and completion state
                    st.session_state[memo_key] = memo_result
                    st.session_state[analysis_key] = True
                                            
                    with st.container(border=True):
                        st.info("""**IMPORTANT:** Your ASC 340-40 memo is displayed below. To save the results, you can either:

• **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).  
• **Download:** Download the memo as a Markdown, PDF, or Word (.docx) file for later use (scroll down to the end for download buttons).
                            """)
                    
                    # Use the CleanMemoGenerator's display method
                    memo_generator.display_clean_memo(memo_result)
                    
                    # Add "Analyze Another Contract" button
                    st.markdown("---")
                    if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True):
                        # Reset analysis state for new analysis including file uploaders
                        keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and ('asc340' in k.lower() or 'upload' in k.lower() or 'file' in k.lower())]
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
        logger.error(f"Critical error in new ASC 340-40 analysis: {str(e)}")
        
        # Auto-credit user for failed analysis
        if analysis_id:
            billing_manager.auto_credit_on_failure(user_token, pricing_result['tier_info']['price'], analysis_id)
            analysis_manager.complete_analysis(analysis_id, success=False, error_message=str(e))
        
        st.error(f"❌ **Analysis Failed**: {str(e)}")
        st.info("💰 **Refund Processed**: The full amount has been credited back to your wallet.")


def perform_asc340_analysis(contract_text: str, filename: str, additional_context: str = ""):
    """Perform the complete ASC 340-40 analysis and display results with session isolation."""
    
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
    analysis_key = f'asc340_analysis_complete_{session_id}'
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = False
    
    # Generate analysis title
    analysis_title = _generate_analysis_title()

    try:
        # Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC340StepAnalyzer()
                knowledge_search = ASC340KnowledgeSearch()
                from asc340.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator(
                    template_path="asc340/templates/memo_template.md")
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 340-40 knowledge base is not available. Try again and contact support if this persists.")
                st.stop()
                return

        # Extract entity name using LLM (with regex fallback) 
        with st.spinner("🏢 Extracting the company name..."):
            try:
                customer_name = analyzer.extract_entity_name_llm(contract_text)
                logger.info(f"LLM extracted company name: {customer_name}")
            except Exception as e:
                logger.warning(f"LLM entity extraction failed: {str(e)}, falling back to regex")
                customer_name = _extract_customer_name(contract_text)
                logger.info(f"Regex fallback company name: {customer_name}")

        # Display progress (match ASC 606 - no memo generation step shown)
        steps = [
            "Processing", "Step 1", "Step 2"
        ]
        progress_placeholder = st.empty()

        # Step-by-step analysis with progress indicators
        analysis_results = {}
        
        # Create a separate placeholder for progress indicators that can be cleared
        progress_indicator_placeholder = st.empty()
        
        # Run 2 ASC 340-40 steps with progress
        for step_num in range(1, 3):
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
        # Don't show memo generation step indicator to match ASC 606

        with st.spinner("Generating Executive Summary, Background, and Conclusion..."):
            # Extract conclusions from the 2 steps
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
            f"✅ **ANALYSIS COMPLETE!** Your professional ASC 340-40 policy memo is ready. Scroll down to view the results."
        )
        
        # Signal completion with session isolation
        st.session_state[analysis_key] = True
        
        # Store memo data with session isolation
        memo_key = f'asc340_memo_data_{session_id}'
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
             
        # Display memo inline instead of switching pages
        st.markdown("---")

        with st.container(border=True):
            st.markdown("""Your ASC 340-40 policy memo is displayed below. To save the results, you can either:
            
- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).
- **Download as Markdown:**  Download the memo as a Markdown file for later use (download link below).
                """)
        
        # Display the memo using CleanMemoGenerator
        memo_generator_display = CleanMemoGenerator()
        memo_generator_display.display_clean_memo(memo_content)
        
        # Clear completion message immediately after memo displays
        completion_message_placeholder.empty()
        
        if st.button("🔄 Analyze Another Plan", type="primary", use_container_width=True):
            # Clear analysis state for fresh start with session isolation
            st.session_state.file_uploader_key = st.session_state.get('file_uploader_key', 0) + 1
            
            # Clean up session-specific data
            memo_key = f'asc340_memo_data_{session_id}'
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
        logger.error(f"ASC 340-40 analysis error for session {session_id[:8]}...: {str(e)}")
        st.session_state[analysis_key] = True  # Signal completion (even on error)

# OLD PARSING SYSTEM REMOVED - Using direct markdown approach only


# Executive summary generation moved to ASC340StepAnalyzer class


# Final conclusion generation moved to ASC340StepAnalyzer class


# Issues collection removed - issues are already included in individual step analyses


# Configure logging
logging.basicConfig(level=logging.INFO)


# Main function for Streamlit navigation
def main():
    """Main function called by Streamlit navigation."""
    render_asc340_page()




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
    return f"ASC340_Analysis_{datetime.now().strftime('%m%d_%H%M%S')}"


# For direct execution/testing
if __name__ == "__main__":
    render_asc340_page()
