"""
Clean Memo Generator - No Text Processing
Displays clean GPT-4o output without any corruption.
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Dict, Any
from shared.disclaimer_generator import DisclaimerGenerator

logger = logging.getLogger(__name__)

class CleanMemoGenerator:
    """Clean memo generator that preserves GPT-4o text exactly as generated."""
    
    def __init__(self, template_path=None):
        """Initialize - template_path ignored for now."""
        pass
    
    def combine_clean_steps(self, analysis_results: Dict[str, Any]) -> str:
        """Combine clean step markdown into final memo - NO PROCESSING."""
        
        # Get basic info
        company_name = analysis_results.get('company_name', 'Company')
        analysis_title = analysis_results.get('analysis_title', 'Contract Analysis')
        analysis_date = datetime.now().strftime("%B %d, %Y")
        
        # Build memo with disclaimer at very top
        memo_lines = [
            DisclaimerGenerator.get_top_banner(),
            "",
            "# ASC 340-40 MEMORANDUM",
            "",
            f"**TO:** Chief Accounting Officer",
            f"**FROM:** Technical Accounting Team - AI", 
            f"**DATE:** {analysis_date}",
            f"**RE:** {analysis_title} - ASC 340-40 Contract Cost Analysis",
            f"**DOCUMENTS REVIEWED:** {analysis_results.get('filename', 'Contract Documents')}",
            "",
            ""
        ]
        
        # Add Executive Summary
        if 'executive_summary' in analysis_results:
            memo_lines.extend([
                "## EXECUTIVE SUMMARY",
                "",
                analysis_results['executive_summary'],
                "",
                ""
            ])
        
        # Add Background
        memo_lines.extend([
            "## BACKGROUND",
            ""
        ])
        
        if 'background' in analysis_results:
            memo_lines.extend([
                analysis_results['background'],
                "", 
                ""
            ])
        else:
            memo_lines.extend([
                f"We have reviewed the contract cost documents provided by {company_name} to determine the appropriate accounting treatment under ASC 340-40. This memorandum presents our analysis following the ASC 340-40 methodology.",
                "", 
                ""
            ])
        
        # Add Analysis Section Header
        memo_lines.extend([
            "## ASC 340-40 ANALYSIS",
        ])
        
        # Add each step's clean markdown content - check both locations
        steps_added = 0
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            step_data = None
            
            # Check if steps are in analysis_results directly
            if step_key in analysis_results:
                step_data = analysis_results[step_key]
            # Check if steps are in analysis_results['steps']
            elif 'steps' in analysis_results and step_key in analysis_results['steps']:
                step_data = analysis_results['steps'][step_key]
            
            if step_data and isinstance(step_data, dict) and 'markdown_content' in step_data:
                # Add clean content directly - ZERO PROCESSING
                clean_content = step_data['markdown_content']
                memo_lines.append(clean_content)
                memo_lines.append("")
                steps_added += 1
                logger.info(f"Added clean step {step_num} content ({len(clean_content)} chars)")
            else:
                logger.warning(f"Step {step_num} not found or missing markdown_content. Available keys: {list(analysis_results.keys())}")
        
        # Add Conclusion Section
        if 'conclusion' in analysis_results:
            memo_lines.extend([
                "",
                "## CONCLUSION",
                "",
                analysis_results['conclusion'],
                "",
            ])
        
        # Add footer with full disclaimer
        memo_lines.extend([
            "---",
            "",
            "**PREPARED BY:** [Analyst Name] | [Title] | [Date]",
            "**REVIEWED BY:** [Reviewer Name] | [Title] | [Date]",
            "",
            DisclaimerGenerator.get_full_disclaimer()
        ])
        
        # Join and return - NO PROCESSING
        final_memo = "\n".join(memo_lines)
        logger.info(f"Clean memo generated: {len(final_memo)} chars, {steps_added}/5 steps")
        return final_memo
    
    def display_clean_memo(self, memo_content: str) -> None:
        """Display clean memo content using HTML to preserve formatting."""
        
        # Validate memo content
        if not memo_content or memo_content.strip() == "":
            st.error("Memo content is empty. Please regenerate the analysis.")
            return
            
        # Log what we're about to display
        logger.info(f"Displaying clean memo sample: {repr(memo_content[:150])}")
        
        # Convert markdown to HTML manually to bypass Streamlit's markdown processor
        html_content = self._convert_markdown_to_html(memo_content)
        
        # Use HTML display which preserves formatting
        st.markdown(html_content, unsafe_allow_html=True)
        
        # Add blank line for spacing
        st.markdown("")
        
        # Download button - only show if content exists and session state is preserved
        # Check for session-isolated memo data
        session_id = st.session_state.get('user_session_id', '')
        memo_key = f'asc340_memo_data_{session_id}' if session_id else 'asc340_memo_data'
        analysis_key = f'asc340_analysis_complete_{session_id}' if session_id else 'asc340_analysis_complete'
        
        if memo_content and len(memo_content.strip()) > 10:  # Minimal validation - always allow download for any real content
            # Ensure session state persistence during download
            st.session_state[analysis_key] = True
            
            # Multiple download options in columns
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    label="📥 Download Memo (Markdown)",
                    data=memo_content,
                    file_name=f"ASC340_memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    key=f"memo_download_md_{hash(memo_content[:100])}"
                )
            
            with col2:
                # Convert to PDF using WeasyPrint
                try:
                    from shared.pdf_generator import PDFGenerator
                    pdf_generator = PDFGenerator()
                    pdf_bytes = pdf_generator.markdown_to_pdf(memo_content)
                    st.download_button(
                        label="📄 Download Memo (PDF)",
                        data=pdf_bytes,
                        file_name=f"ASC340_memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key=f"memo_download_pdf_{hash(memo_content[:100])}"
                    )
                except ImportError:
                    st.button("📄 PDF Download (Not Available)", disabled=True, help="PDF generation requires additional setup")
                except Exception as e:
                    logger.error(f"PDF generation failed: {str(e)}")
                    st.button("📄 PDF Download (Error)", disabled=True, help=f"PDF generation error: {str(e)}")
            
            with col3:
                # Convert to Word document using python-docx
                try:
                    from shared.docx_generator import DocxGenerator
                    docx_generator = DocxGenerator()
                    docx_bytes = docx_generator.markdown_to_docx(memo_content)
                    st.download_button(
                        label="📝 Download Memo (Word)",
                        data=docx_bytes,
                        file_name=f"ASC340_memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"memo_download_docx_{hash(memo_content[:100])}"
                    )
                except ImportError:
                    st.button("📝 Word Download (Not Available)", disabled=True, help="Word generation requires additional setup")
                except Exception as e:
                    logger.error(f"Word generation failed: {str(e)}")
                    st.button("📝 Word Download (Error)", disabled=True, help=f"Word generation error: {str(e)}")
        else:
            st.warning("Memo content too short for download. Please regenerate the analysis.")
    
    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML manually to preserve currency formatting."""
        
        # Split into lines and process each one
        lines = markdown_content.split('\n')
        html_lines = []
        in_list = False
        
        for line in lines:
            # Convert headers with better spacing
            if line.startswith('# '):
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<h1 style="margin: 20px 0 15px 0; font-weight: bold;">{line[2:]}</h1>')
            elif line.startswith('## '):
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<h2 style="margin: 18px 0 12px 0; border-bottom: 2px solid #e0e0e0; padding-bottom: 5px;">{line[3:]}</h2>')
            elif line.startswith('### '):
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<h3 style="margin: 16px 0 10px 0; font-weight: 600;">{line[4:]}</h3>')
            # Handle bullet points better
            elif line.strip().startswith('- '):
                if not in_list:
                    html_lines.append('<ul style="margin: 10px 0; padding-left: 25px;">')
                    in_list = True
                content = line.strip()[2:].strip()
                # Handle bold text in list items
                if '**' in content:
                    while '**' in content:
                        content = content.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
                html_lines.append(f'<li style="margin: 6px 0; line-height: 1.4;">{content}</li>')
            # Convert bold text in paragraphs
            elif '**' in line and line.strip():
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                # Handle multiple bold sections
                processed_line = line
                while '**' in processed_line:
                    processed_line = processed_line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
                html_lines.append(f'<p style="margin: 10px 0; line-height: 1.6;">{processed_line}</p>')
            # Skip horizontal rules (as requested)
            elif line.strip() == '---':
                continue
            # Empty lines - add small spacing
            elif line.strip() == '':
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                continue
            # Regular paragraphs
            elif line.strip():
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(f'<p style="margin: 10px 0; line-height: 1.6;">{line}</p>')
        
        # Close any open lists
        if in_list:
            html_lines.append('</ul>')
        
        # Join with improved styling
        html_content = f"""
        <div style="font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; 
        line-height: 1.6; max-width: 850px; padding: 30px; 
        border: 1px solid #e1e5e9; 
        border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            {''.join(html_lines)}
        </div>
        """
        
        return html_content