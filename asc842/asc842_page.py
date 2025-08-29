"""
ASC 842 Lease Accounting Analysis Page
"""

import streamlit as st
import logging
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional

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
    st.title(":primary[ASC 842 Analyzer & Memo Generator]")
    with st.container(border=True):
        st.markdown(":primary[**Purpose:**] Automatically analyze lease contracts and generate a professional ASC 842 memo. Simply upload your lease documents to begin.")
    
    # Get user inputs with progressive disclosure
    contract_text, filename, additional_context, is_ready = get_asc842_inputs()

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
        if st.button("3️⃣ Analyze Lease Contract & Generate Memo",
                   type="primary",
                   use_container_width=True,
                   key="asc842_analyze"):
            warning_placeholder.empty()  # Clear the warning after the button is pressed
            if contract_text:  # Type guard to ensure contract_text is not None
                perform_asc842_analysis(contract_text, additional_context, filename)
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
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents (e.g., verbal agreement details) or specify your areas of focus or concerns.",
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
        st.error(f"❌ Error processing documents: {str(e)}")
        logger.error(f"Document processing error: {str(e)}")
        return None, None


def perform_asc842_analysis(contract_text: str, additional_context: str = "", filename=None):
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
                    pass  # Knowledge base is available
                    # st.success(f"📚 {kb_info.get('standard')}: {kb_info.get('documents')} loaded successfully")
                    
            except Exception as e:
                logger.error(f"Error initializing ASC 842 analysis: {str(e)}")
                st.error(f"❌ Failed to initialize analysis system: {str(e)}")
                return

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

        # Extract entity name for analysis
        entity_name = _extract_entity_name(contract_text)
        
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
                    
                search_query = " ".join(search_terms)
                authoritative_context = knowledge_search.search_general(search_query)
                
                logger.info("ASC 842 authoritative guidance retrieved successfully")
                
            except Exception as e:
                logger.error(f"Error retrieving guidance: {str(e)}")
                # Use fallback guidance
                authoritative_context = "ASC 842 lease accounting guidance - using general knowledge."
                st.warning("⚠️ Using general ASC 842 guidance due to knowledge base issues.")

        # Perform 5-step analysis
        with st.spinner("Performing 5-step ASC 842 analysis... This may take 3-5 minutes."):
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
                
                # Analysis complete - no summary needed
                
            else:
                st.error("❌ Memo generation failed - content too short or empty")
                if st.checkbox("🔧 Show technical details", key=f"memo_error_{analysis_id}"):
                    st.text(f"Memo content length: {len(memo_content) if memo_content else 0}")
                    if memo_content:
                        st.text(memo_content[:500])
                
    except Exception as e:
        logger.error(f"Memo generation failed: {str(e)}")
        st.error(f"❌ Memo generation failed: {str(e)}")



def _extract_entity_name(contract_text: str) -> str:
    """Extract entity name from contract or use default."""
    
    import re
    
    # Look for company names with common suffixes
    company_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc\.?|LLC|Corp\.?|Corporation|Company|Ltd\.?|Limited))',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Solutions(?:\s+Inc\.?)?)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Technologies(?:\s+Inc\.?)?)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Enterprises(?:\s+Inc\.?)?)'
    ]
    
    # Try to find proper company names first
    for pattern in company_patterns:
        matches = re.findall(pattern, contract_text)
        if matches:
            # Return the first found company name
            entity_name = matches[0].strip()
            if len(entity_name) > 5 and len(entity_name) < 80:
                return entity_name
    
    # Fallback: look for tenant/lessee patterns but be more selective
    contract_lower = contract_text.lower()
    fallback_patterns = [
        r'(?:lessee|tenant)[:\s]+"([^"]+)"',  # Quoted names
        r'(?:lessee|tenant)[:\s]+([A-Z][a-zA-Z\s]+(?:Inc\.?|LLC|Corp\.?))',  # Company-like names
    ]
    
    for pattern in fallback_patterns:
        match = re.search(pattern, contract_text)  # Use original case for fallback
        if match:
            entity_name = match.group(1).strip()
            if len(entity_name) > 5 and len(entity_name) < 80 and not entity_name.lower().startswith('hereby'):
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


# Call display function if results exist
if st.session_state.get('current_asc842_analysis'):
    display_current_analysis()