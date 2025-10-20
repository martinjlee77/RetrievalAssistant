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
from shared.wallet_manager import wallet_manager
from shared.analysis_manager import analysis_manager
# CleanMemoGenerator import moved to initialization section
import tempfile
import os
from utils.document_extractor import DocumentExtractor
from asc718.step_analyzer import ASC718StepAnalyzer
from asc718.knowledge_search import ASC718KnowledgeSearch

logger = logging.getLogger(__name__)

def render_asc718_page():
    """Render the ASC 718 analysis page."""
    
    # Authentication check - must be logged in to access
    if not require_authentication():
        return  # User will see login page
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

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
                       key="asc718_analyze"):
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
    
    # Create placeholder for the in-progress message
    progress_message_placeholder = st.empty()
    progress_message_placeholder.error(
        "🚨 **ANALYSIS IN PROGRESS - DO NOT CLOSE THIS TABS!**\n\n"
        "Your analysis is running and will take up to 3-20 minutes. "
        "Closing this browser will stop the analysis and forfeit your progress."
    )
    
    # Initialize analysis complete status with session isolation
    analysis_key = f'asc718_analysis_complete_{session_id}'
    if analysis_key not in st.session_state:
        st.session_state[analysis_key] = False
    
    # Start analysis tracking for database capture
    analysis_details = {
        'asc_standard': 'ASC 718',
        'total_words': len(str(pricing_result).split()),
        'file_count': len(pricing_result.get('file_details', [])),
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
                analyzer = ASC718StepAnalyzer()
                knowledge_search = ASC718KnowledgeSearch()
                from asc718.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator(
                    template_path="asc606/templates/memo_template.md")
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 718 knowledge base is not available. Try again and contact support if this persists.")
                st.stop()
                return

        # Extract entity name using LLM (with regex fallback)
        with st.spinner("🔁 Extracting customer name..."):
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
        
        # Run 5 ASC 718 steps with progress
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
                    entity_name=customer_name,
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
            executive_summary = analyzer.generate_executive_summary(conclusions_text, customer_name)
            background = analyzer.generate_background_section(conclusions_text, customer_name)
            conclusion = analyzer.generate_final_conclusion(conclusions_text)
            
            # Combine into the expected structure for memo generator
            final_results = {
                'customer_name': customer_name,
                'analysis_title': analysis_title,
                'analysis_date': datetime.now().strftime("%B %d, %Y"),
                'filename': filename_string,
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
            f"✅ **ANALYSIS COMPLETE!** Your professional ASC 718 memo is ready. Scroll down to view the results."
        )
        
        # Signal completion with session isolation
        st.session_state[analysis_key] = True
        
        # Complete analysis for database capture  
        if analysis_id:
            analysis_manager.complete_analysis(analysis_id, success=True)
        
        # Store memo data with session isolation
        memo_key = f'asc718_memo_data_{session_id}'
        st.session_state[memo_key] = {
            'memo_content': memo_content,
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y"),
            'analysis_id': analysis_id
        }
        
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
            if st.button("🔄 Start New Analysis", type="secondary", use_container_width=True, key="top_new_analysis_fresh"):
                keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc718' in k.lower()]
                for key in keys_to_clear:
                    del st.session_state[key]
                st.rerun()
        
        st.markdown("---")
        
        # Display the memo using CleanMemoGenerator
        memo_generator_display = CleanMemoGenerator()
        memo_generator_display.display_clean_memo(memo_content, analysis_id, filename_string, customer_name)
        
        # Re-run policy note and "Analyze Another" button
        st.markdown("---")
        st.info("📋 Each analysis comes with one complimentary re-run within 14 days for input modifications or extractable text adjustments. If you'd like to request one, please contact support at support@veritaslogic.ai.")
        
        if st.button("🔄 **Analyze Another Contract**", type="secondary", use_container_width=True, key="bottom_new_analysis_fresh"):
            # Clear session state for new analysis
            keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and 'asc718' in k.lower()]
            for key in keys_to_clear:
                del st.session_state[key]
            st.rerun()
        
        # Clear completion message after memo displays (but keep the important info above)
        completion_message_placeholder.empty()

    except Exception as e:
        # Clear the progress message even on error
        progress_message_placeholder.empty()
        st.error("❌ Analysis failed. Please try again. Contact support if this issue persists.")
        logger.error(f"ASC 718 analysis error for session {session_id[:8]}...: {str(e)}")
        st.session_state[analysis_key] = True  # Signal completion (even on error)
        
        # Complete analysis for database capture (failure)
        if 'analysis_id' in locals():
            analysis_manager.complete_analysis(analysis_id, success=False, error_message=str(e))

# OLD PARSING SYSTEM REMOVED - Using direct markdown approach only


# Executive summary generation moved to ASC606StepAnalyzer class


# Final conclusion generation moved to ASC606StepAnalyzer class


# Issues collection removed - issues are already included in individual step analyses


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