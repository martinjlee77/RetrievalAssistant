"""
ASC 842 Lease Accounting Analysis Page
"""

import streamlit as st
import logging
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

from shared.ui_components import SharedUIComponents
# CleanMemoGenerator import moved to initialization section
import tempfile
import os
from asc842.step_analyzer import ASC842StepAnalyzer
from asc842.knowledge_search import ASC842KnowledgeSearch
from utils.document_extractor import DocumentExtractor

logger = logging.getLogger(__name__)

def render_asc842_page():
    """Render the ASC 842 analysis page."""
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Page header
    st.title(":primary[ASC 842 Analyzer & Memo Generator (Lessee Only)]")
    with st.container(border=True):
        st.markdown(":primary[**Purpose:**] Automatically analyze lease contracts and generate a professional ASC 842 memo. Upload your lease documents and answer a few questions to analyze.")
    
    # Get user inputs with progressive disclosure
    contract_text, filename, user_inputs, additional_context, is_ready = get_asc842_inputs()

    # Critical user warning before analysis
    if is_ready:
        warning_placeholder = st.empty()  # Create a placeholder for the warning
        warning_placeholder.info(
            "⚠️ **IMPORTANT:** Keep this browser tab active during analysis!\n\n"
            "- Analysis takes **3-5 minutes** and costs significant API tokens\n"
            "- Switching tabs or closing the browser will stop the analysis\n"
            "- Stay on this tab until analysis is complete\n"
            "- You'll see a completion message when it's done"
        )
        if st.button("4️⃣ Analyze Lease Contract & Generate Memo",
                   type="primary",
                   use_container_width=True,
                   key="asc842_analyze"):
            warning_placeholder.empty()  # Clear the warning after the button is pressed
            if contract_text:  # Type guard to ensure contract_text is not None
                perform_asc842_analysis(contract_text, user_inputs, additional_context, filename)
    else:
        # Show disabled button with helpful message when not ready
        st.button("4️⃣ Analyze Lease Contract & Generate Memo", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc842_analyze_disabled")


def get_asc842_inputs() -> Tuple[Optional[str], Optional[str], Dict[str, Any], str, bool]:
    """Get ASC 842 specific inputs."""

    # 1. Document upload first
    contract_text, filename = _upload_and_process_asc842()

    # 2. Specific ASC 842 fields (only show if documents uploaded)
    user_inputs = {}
    if contract_text:
        user_inputs = _get_asc842_specific_fields()
    else:
        st.info("📄 Please upload lease documents first to continue with the analysis.")

    # 3. Additional info (optional) - only show if documents uploaded
    additional_context = ""
    if contract_text:
        additional_context = st.text_area(
            "3️⃣ Additional information or concerns (optional)",
            placeholder="Provide any guidance to the AI that is not included in the uploaded documents (e.g., verbal agreement details) or specify your areas of focus or concerns.",
            height=100)

    # Check completion status - contract text + required fields
    required_fields_complete = (
        contract_text and
        user_inputs.get('discount_rate') is not None and
        user_inputs.get('commencement_date') is not None and
        'related_party_flag' in user_inputs
    )

    return contract_text, filename, user_inputs, additional_context, required_fields_complete


def _upload_and_process_asc842() -> Tuple[Optional[str], Optional[str]]:
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

        # Finalize results
        if processed_filenames:
            filename_display = f"{len(processed_filenames)} document(s): {', '.join(processed_filenames)}"
            total_chars = len(combined_text)
            # st.success(f"📄 **Document processing complete:** {total_chars:,} total characters extracted")
            
            # Show preview option
#            if st.checkbox("🔍 Preview extracted text", key="preview_asc842_text"):
#                with st.expander("📄 Document Preview", expanded=False):
#                    preview_text = combined_text[:3000] + "..." if len(combined_text) > 3000 else combined_text
#                    st.text(preview_text)
            
            return combined_text, filename_display
        else:
            st.error("❌ No documents could be processed successfully. Please check your files and try again.")
            return None, None
            
    except Exception as e:
        st.error(f"❌ Error processing documents: {str(e)}")
        logger.error(f"Document processing error: {str(e)}")
        return None, None


def _get_asc842_specific_fields() -> Dict[str, Any]:
    """Get ASC 842 specific user input fields."""
    st.markdown("2️⃣ Required ASC 842 Analysis Inputs")
    
    user_inputs = {}
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Discount rate (required)
        discount_rate = st.number_input(
            "Discount rate (%)",
            min_value=0.01,
            max_value=50.0,
            value=6.0,
            step=0.01,
            format="%.2f",
            help="Enter the discount rate to apply (implicit rate if determinable, otherwise incremental borrowing rate)"
        )
        user_inputs['discount_rate'] = discount_rate
        
        # Optional basis tag
        discount_basis = st.selectbox(
            "Discount rate basis (optional)",
            ["Not specified", "Implicit rate", "Incremental borrowing rate", "Risk-free rate"],
            help="Optional: specify the basis for the discount rate"
        )
        if discount_basis != "Not specified":
            user_inputs['discount_rate_basis'] = discount_basis
             
    with col2:
        # Related-party lease (required)
        related_party = st.selectbox(
            "Related-party lease?",
            ["No", "Yes"],
            help="Is this lease between related parties?"
        )
        user_inputs['related_party_flag'] = (related_party == "Yes")
        
        # Related-party note (conditional)
        if related_party == "Yes":
            related_party_note = st.text_area(
                "Related-party details (optional)",
                placeholder="Brief note on any nonmarket or unenforceable terms",
                height=80,
                help="Optional: provide details about nonmarket terms or enforceability issues"
            )
            if related_party_note.strip():
                user_inputs['related_party_note'] = related_party_note

        # Commencement date (required)
        commencement_date = st.date_input(
            "Commencement (availability) date",
            value=date.today(),
            help="Date when the asset is made available for use by the lessee"
        )
        user_inputs['commencement_date'] = commencement_date.strftime("%Y-%m-%d")
    
    
    st.markdown("### Option Assessments")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        extend_assessment = st.selectbox(
            "Extension option reasonably certain?",
            ["N/A", "Yes", "No"],
            help="Is the lessee reasonably certain to exercise extension options?"
        )
        if extend_assessment != "N/A":
            user_inputs['extend_reasonably_certain'] = extend_assessment
    
    with col4:
        terminate_assessment = st.selectbox(
            "Termination option NOT exercised?",
            ["N/A", "Yes", "No"],
            help="Is the lessee reasonably certain NOT to exercise termination options?"
        )
        if terminate_assessment != "N/A":
            user_inputs['terminate_reasonably_not_exercised'] = terminate_assessment
    
    with col5:
        purchase_assessment = st.selectbox(
            "Purchase option reasonably certain?",
            ["N/A", "Yes", "No"],
            help="Is the lessee reasonably certain to exercise purchase options?"
        )
        if purchase_assessment != "N/A":
            user_inputs['purchase_option_reasonably_certain'] = purchase_assessment
    
    st.markdown("### Policy Elections")
    
    col6, col7 = st.columns(2)
    
    with col6:
        nonlease_expedient = st.selectbox(
            "Nonlease components policy",
            ["Separate components", "Elect not to separate", "Not applicable"],
            help="Election to not separate nonlease components by asset class"
        )
        if nonlease_expedient == "Elect not to separate":
            user_inputs['expedient_nonlease_not_separated'] = True
        elif nonlease_expedient == "Separate components":
            user_inputs['expedient_nonlease_not_separated'] = False
    
    with col7:
        short_term_policy = st.selectbox(
            "Short-term lease policy",
            ["Not elected", "Elected", "Not applicable"],
            help="Short-term lease policy election (12 months or less, no purchase option)"
        )
        if short_term_policy == "Elected":
            user_inputs['policy_short_term'] = True
        elif short_term_policy == "Not elected":
            user_inputs['policy_short_term'] = False
    
    return user_inputs


def perform_asc842_analysis(contract_text: str, user_inputs: Dict[str, Any], additional_context: str, filename: Optional[str]):
    """Perform the complete ASC 842 analysis."""
    
    # Generate unique analysis ID
    analysis_id = str(uuid.uuid4())[:8]
    
    try:
        # Initialize analyzer and knowledge search
        with st.spinner("🔧 Initializing ASC 842 analysis system..."):
            try:
                analyzer = ASC842StepAnalyzer()
                knowledge_search = ASC842KnowledgeSearch()
                
                # Check knowledge base availability
                kb_info = knowledge_search.get_user_kb_info()
                if kb_info.get("status") != "Active":
                    st.warning("📚 ASC 842 knowledge base not fully available. Analysis will proceed with general guidance.")
                else:
                    st.success(f"📚 {kb_info.get('standard')}: {kb_info.get('documents')} loaded successfully")
                    
            except Exception as e:
                logger.error(f"Error initializing ASC 842 analysis: {str(e)}")
                st.error(f"❌ Failed to initialize analysis system: {str(e)}")
                return

        # Extract entity name for analysis
        entity_name = _extract_entity_name(contract_text, user_inputs)
        
        # Create analysis title
        analysis_title = f"ASC 842 Lease Analysis - {entity_name} - {analysis_id}"
        
        # Search for authoritative guidance
        with st.spinner("🔍 Retrieving ASC 842 authoritative guidance..."):
            try:
                # Create comprehensive search query
                search_terms = [
                    "lease accounting", "ASC 842", "lease classification",
                    "lease measurement", "ROU asset", "lease liability"
                ]
                
                if user_inputs.get('policy_short_term'):
                    search_terms.append("short-term lease")
                if user_inputs.get('expedient_nonlease_not_separated'):
                    search_terms.append("practical expedient nonlease components")
                    
                search_query = " ".join(search_terms)
                authoritative_context = knowledge_search.search_general(search_query)
                
                logger.info("ASC 842 authoritative guidance retrieved successfully")
                
            except Exception as e:
                logger.error(f"Error retrieving guidance: {str(e)}")
                # Use fallback guidance
                authoritative_context = "ASC 842 lease accounting guidance - using general knowledge."
                st.warning("⚠️ Using general ASC 842 guidance due to knowledge base issues.")

        # Perform 5-step analysis
        with st.spinner("🔬 Performing 5-step ASC 842 analysis... This may take 3-5 minutes."):
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            
            try:
                # Show step-by-step progress
                status_placeholder.text("Starting comprehensive lease analysis...")
                progress_bar.progress(10)
                
                # Perform the analysis
                analysis_results = analyzer.analyze_lease_contract(
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    entity_name=entity_name,
                    analysis_title=analysis_title,
                    user_inputs=user_inputs,
                    additional_context=additional_context
                )
                
                progress_bar.progress(100)
                status_placeholder.text("Analysis complete!")
                
                # Store results in session state
                session_key = f'asc842_analysis_{analysis_id}'
                st.session_state[session_key] = {
                    'results': analysis_results,
                    'filename': filename,
                    'analysis_id': analysis_id,
                    'timestamp': datetime.now().isoformat()
                }
                st.session_state['current_asc842_analysis'] = session_key
                
                logger.info("ASC 842 analysis completed successfully")
                
                # Clear progress indicators
                progress_bar.empty()
                status_placeholder.empty()
                
                # Generate memo
                _generate_and_display_memo(analysis_results, filename, analysis_id)
                
            except Exception as e:
                progress_bar.empty()
                status_placeholder.empty()
                
                logger.error(f"ASC 842 analysis failed: {str(e)}")
                st.error(f"❌ Analysis failed: {str(e)}")
                
                # Show detailed error for debugging
                if st.checkbox("🔧 Show technical details", key=f"error_details_{analysis_id}"):
                    st.code(f"Error: {str(e)}")
                    
                return

    except Exception as e:
        logger.error(f"Unexpected error in ASC 842 analysis: {str(e)}")
        st.error(f"❌ Unexpected error: {str(e)}")


def _generate_and_display_memo(analysis_results: Dict[str, Any], filename: Optional[str], analysis_id: str):
    """Generate and display the professional memo."""
    
    st.markdown("---")
    st.markdown("## 📋 Professional ASC 842 Memorandum")
    
    try:
        with st.spinner("📝 Generating professional memorandum..."):
            # Import memo generator
            from asc842.clean_memo_generator import CleanMemoGenerator
            memo_generator = CleanMemoGenerator()
            
            # Add filename to results
            analysis_results['filename'] = filename or "Lease Documents"
            
            # Generate clean memo
            memo_content = memo_generator.combine_clean_steps(analysis_results)
            
            if memo_content and len(memo_content.strip()) > 100:
                st.success("✅ Memorandum generated successfully!")
                
                # Store memo in session state
                memo_key = f'asc842_memo_{analysis_id}'
                st.session_state[memo_key] = memo_content
                
                # Display the memo
                memo_generator.display_clean_memo(memo_content)
                
                # Show analysis summary
                _display_analysis_summary(analysis_results)
                
            else:
                st.error("❌ Memo generation failed - content too short or empty")
                if st.checkbox("🔧 Show technical details", key=f"memo_error_{analysis_id}"):
                    st.text(f"Memo content length: {len(memo_content) if memo_content else 0}")
                    if memo_content:
                        st.text(memo_content[:500])
                
    except Exception as e:
        logger.error(f"Memo generation failed: {str(e)}")
        st.error(f"❌ Memo generation failed: {str(e)}")


def _display_analysis_summary(analysis_results: Dict[str, Any]):
    """Display a summary of the analysis results."""
    
    with st.expander("📊 Analysis Summary", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Analysis Details:**")
            st.markdown(f"• Entity: {analysis_results.get('customer_name', 'Not specified')}")
            st.markdown(f"• Analysis Date: {analysis_results.get('analysis_date', 'Not specified')}")
            
            user_inputs = analysis_results.get('user_inputs', {})
            st.markdown(f"• Discount Rate: {user_inputs.get('discount_rate', 'Not specified')}%")
            st.markdown(f"• Commencement Date: {user_inputs.get('commencement_date', 'Not specified')}")
        
        with col2:
            st.markdown("**Steps Completed:**")
            steps = analysis_results.get('steps', {})
            for i in range(1, 6):
                step_key = f'step_{i}'
                if step_key in steps:
                    st.markdown(f"✅ Step {i}: Complete")
                else:
                    st.markdown(f"❌ Step {i}: Missing")
        
        # Show user inputs
        if user_inputs:
            st.markdown("**User Inputs:**")
            st.json(user_inputs)


def _extract_entity_name(contract_text: str, user_inputs: Dict[str, Any]) -> str:
    """Extract entity name from contract or use default."""
    
    # Try to extract from contract text (simple approach)
    contract_lower = contract_text.lower()
    
    # Common patterns for lessee identification
    patterns = [
        r'lessee[:\s]+([^,\n\.]+)',
        r'tenant[:\s]+([^,\n\.]+)',
        r'company[:\s]+([^,\n\.]+)',
    ]
    
    import re
    for pattern in patterns:
        match = re.search(pattern, contract_lower)
        if match:
            entity_name = match.group(1).strip().title()
            if len(entity_name) > 3 and len(entity_name) < 50:
                return entity_name
    
    # Default fallback
    return "Entity"


# Display current analysis results if available
def display_current_analysis():
    """Display current analysis results if available."""
    
    current_analysis_key = st.session_state.get('current_asc842_analysis')
    if current_analysis_key and current_analysis_key in st.session_state:
        analysis_data = st.session_state[current_analysis_key]
        
        st.markdown("---")
        st.markdown("## 📋 Current Analysis Results")
        
        # Show timestamp
        timestamp = analysis_data.get('timestamp', '')
        if timestamp:
            try:
                ts = datetime.fromisoformat(timestamp)
                st.markdown(f"*Generated: {ts.strftime('%B %d, %Y at %I:%M %p')}*")
            except:
                pass
        
        # Check for memo
        analysis_id = analysis_data.get('analysis_id', '')
        memo_key = f'asc842_memo_{analysis_id}'
        
        if memo_key in st.session_state:
            from asc842.clean_memo_generator import CleanMemoGenerator
            memo_generator = CleanMemoGenerator()
            memo_content = st.session_state[memo_key]
            
            memo_generator.display_clean_memo(memo_content)
            
            # Show analysis summary
            _display_analysis_summary(analysis_data.get('results', {}))


# Call display function if results exist
if st.session_state.get('current_asc842_analysis'):
    display_current_analysis()