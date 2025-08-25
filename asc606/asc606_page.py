"""
ASC 606 Contract Analysis Page
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Dict, Any, List

from shared.ui_components import SharedUIComponents
# CleanMemoGenerator import moved to initialization section
from shared.document_processor import SharedDocumentProcessor
from asc606.step_analyzer import ASC606StepAnalyzer
from asc606.knowledge_search import ASC606KnowledgeSearch

logger = logging.getLogger(__name__)


def render_asc606_page():
    """Render the ASC 606 analysis page."""
    
    # File uploader key initialization (for clearing file uploads)
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Page header
    st.title(":primary[ASC 606 Analyzer & Memo Generator]")
    with st.container(border=True):
        st.markdown(":primary[**Purpose:**] Automatically analyze revenue contracts and generate a professional ASC 606 memo. Simply upload your documents to begin.")
    
    # Get user inputs with progressive disclosure
    contract_text, filename, additional_context, is_ready = get_asc606_inputs()

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
        if st.button("3️⃣ Analyze Contract & Generate Memo",
                   type="primary",
                   use_container_width=True,
                   key="asc606_analyze"):
            warning_placeholder.empty()  # Clear the warning after the button is pressed
            if contract_text:  # Type guard to ensure contract_text is not None
                perform_asc606_analysis(contract_text, additional_context)
    else:
        # Show disabled button with helpful message when not ready
        st.button("3️⃣ Analyze Contract & Generate Memo", 
                 disabled=True, 
                 use_container_width=True,
                 key="asc606_analyze_disabled")


def get_asc606_inputs():
    """Get ASC 606 specific inputs."""

    # Document upload
    processor = SharedDocumentProcessor()
    contract_text, filename = processor.upload_and_process(
        "1️⃣ Upload a **complete contract and related documents**, e.g., executed agreement, standard T&Cs, MSA, SOW, purchase order, invoice (required)")

    # Additional info (optional)
    additional_context = st.text_area(
        "2️⃣ Additional information or concerns (optional)",
        placeholder="Provide any guidance to the AI that is not included in the uploaded documents (e.g., verbal agreement) or specificy your areas of focus or concerns.",
        height=100)

    # Check completion status - only contract text required
    is_ready = bool(contract_text)

    return contract_text, filename, additional_context, is_ready


# Old validation function removed - using progressive disclosure approach instead


def perform_asc606_analysis(contract_text: str, additional_context: str = ""):
    """Perform the complete ASC 606 analysis and display results."""
    
    # Create placeholder for the in-progress message
    progress_message_placeholder = st.empty()
    progress_message_placeholder.error(
        "🚨 **ANALYSIS IN PROGRESS - DO NOT CLOSE OR SWITCH TABS!**\n\n"
        "Your analysis is running and will take up to 3-5 minutes. "
        "Switching to another tab or closing this browser will stop the analysis and forfeit your progress."
    )
    
    # Initialize analysis complete status in session state (if not already present)
    if 'asc606_analysis_complete' not in st.session_state:
        st.session_state.asc606_analysis_complete = False
    
    # Auto-extract customer name and generate analysis title
    customer_name = _extract_customer_name(contract_text)
    analysis_title = _generate_analysis_title()

    try:
        # Initialize components
        with st.spinner("Initializing analysis components..."):
            try:
                analyzer = ASC606StepAnalyzer()
                knowledge_search = ASC606KnowledgeSearch()
                from asc606.clean_memo_generator import CleanMemoGenerator
                memo_generator = CleanMemoGenerator(
                    template_path="asc606/templates/memo_template.md")
                from shared.ui_components import SharedUIComponents
                ui = SharedUIComponents()
            except RuntimeError as e:
                st.error(f"❌ Critical Error: {str(e)}")
                st.error("ASC 606 knowledge base is not available. Try again and contact support if this persists.")
                st.stop()
                return

        # Display progress
        steps = [
            "Processing", "Step 1", "Step 2", "Step 3", "Step 4",
            "Step 5", "Memo Generation"
        ]
        progress_placeholder = st.empty()

        # Step-by-step analysis with progress indicators
        analysis_results = {}
        
        # Run 5 ASC 606 steps with progress
        for step_num in range(1, 6):
            with progress_placeholder:
                st.subheader(f"🔄 Analyzing Step {step_num}")
                ui.analysis_progress(steps, step_num)

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
        with progress_placeholder:
            st.subheader("📋 Generating additional sections...")
            ui.analysis_progress(steps, 6)

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
                'steps': analysis_results,
                'executive_summary': executive_summary,
                'background': background,
                'conclusion': conclusion
            }
            
            
            # Generate memo directly from complete analysis results
            memo_content = memo_generator.combine_clean_steps(final_results)

        # Store memo data in session state and clear progress message
        progress_message_placeholder.empty()  # Correctly clears the in-progress message
        st.success(
            f"✅ **ANALYSIS COMPLETE!** Your professional ASC 606 memo is ready. Scroll down to view the results."
        )
        
        # Signal completion
        st.session_state.asc606_analysis_complete = True
        
        # Store memo data for the memo page
        st.session_state.asc606_memo_data = {
            'memo_content': memo_content,
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y")
        }
             
        # Display memo inline instead of switching pages
        st.markdown("---")

        with st.container(border=True):
            st.markdown("""Your ASC 606 memo is displayed below. To save the results, you can either:
            
- **Copy and Paste:** Select all the text below and copy & paste it into your document editor (Word, Google Docs, etc.).
- **Download as Markdown:**  Download the memo as a Markdown file for later use (download link below).
                """)
        
        # Display the memo using CleanMemoGenerator
        memo_generator_display = CleanMemoGenerator()
        memo_generator_display.display_clean_memo(memo_content)
        
        if st.button("🔄 Analyze Another Contract", type="primary", use_container_width=True):
            # Clear file uploader and analysis state for fresh start
            st.session_state.file_uploader_key = st.session_state.get('file_uploader_key', 0) + 1
            if 'asc606_memo_data' in st.session_state:
                del st.session_state.asc606_memo_data

            st.rerun()

    except Exception as e:
        # Clear the progress message even on error
        progress_message_placeholder.empty()
        st.error("❌ Analysis failed. Please try again. Contact support if this issue persists.")
        logger.error(f"ASC 606 analysis error: {str(e)}")
        st.session_state.asc606_analysis_complete = True  # Signal completion (even on error)

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
    """Auto-extract customer name from contract text using simple patterns."""
    try:
        import re
        
        # Look for common patterns in first 1000 characters
        text_sample = contract_text[:1000]
        
        # Common patterns for customer identification
        patterns = [
            r'Customer[:\s]+([A-Za-z0-9\s,\.&-]+?)(?:[\n,;]|$)',
            r'(?:Client|Company)[:\s]+([A-Za-z0-9\s,\.&-]+?)(?:[\n,;]|$)',
            r'Bill\s+To[:\s]+([A-Za-z0-9\s,\.&-]+?)(?:[\n,;]|$)',
            r'([A-Za-z\s&-]+(?:Corp|Corporation|Inc|LLC|Ltd|Co))',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_sample, re.IGNORECASE)
            if matches:
                customer_name = matches[0].strip()
                # Filter reasonable length names
                if 3 < len(customer_name) < 80:
                    return customer_name
        
        # Fallback: look for capitalized words that might be company names
        words = re.findall(r'\b[A-Z][a-zA-Z]+\b', text_sample[:200])
        if len(words) >= 2:
            return ' '.join(words[:2])  # Take first two capitalized words
        
        return "Customer"  # Default fallback
        
    except Exception as e:
        logger.error(f"Error extracting customer name: {str(e)}")
        return "Customer"


def _generate_analysis_title() -> str:
    """Generate analysis title with timestamp."""
    return f"ASC606_Analysis_{datetime.now().strftime('%m%d_%H%M%S')}"


# For direct execution/testing
if __name__ == "__main__":
    render_asc606_page()
