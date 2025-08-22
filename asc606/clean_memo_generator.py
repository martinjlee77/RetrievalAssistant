"""
Clean Memo Generator - No Text Processing
Displays clean GPT-4o output without any corruption.
"""

import streamlit as st
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CleanMemoGenerator:
    """Clean memo generator that preserves GPT-4o text exactly as generated."""
    
    def __init__(self, template_path=None):
        """Initialize - template_path ignored for now."""
        pass
    
    def combine_clean_steps(self, analysis_results: Dict[str, Any]) -> str:
        """Combine clean step markdown into final memo - NO PROCESSING."""
        
        # Get basic info
        customer_name = analysis_results.get('customer_name', 'Customer')
        analysis_title = analysis_results.get('analysis_title', 'Contract Analysis')
        analysis_date = datetime.now().strftime("%d %b, %Y")
        
        # Build memo with header
        memo_lines = [
            "# ASC 606 MEMORANDUM",
            "",
            f"**TO:** Chief Accounting Officer",
            f"**FROM:** Technical Accounting Team - AI", 
            f"**DATE:** {analysis_date}",
            f"**RE:** {analysis_title} - ASC 606 Revenue Recognition Analysis",
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
                f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology.",
                "", 
                ""
            ])
        
        # Add Analysis Section Header
        memo_lines.extend([
            "## ASC 606 ANALYSIS",
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
        
        # Add footer
        memo_lines.extend([
            "---",
            "",
            "**PREPARED BY:** [Analyst Name] | [Title] | [Date]",
            "**REVIEWED BY:** [Reviewer Name] | [Title] | [Date]", 
            "",
            "This memorandum represents our preliminary analysis based on the contract documents provided. Final implementation should be reviewed with external auditors and may require additional documentation or analysis of specific implementation details."
        ])
        
        # Join and return - NO PROCESSING
        final_memo = "\n".join(memo_lines)
        logger.info(f"Clean memo generated: {len(final_memo)} chars, {steps_added}/5 steps")
        return final_memo
    
    def display_clean_memo(self, memo_content: str) -> None:
        """Display clean memo content using HTML to preserve formatting."""
        st.markdown("## 📋 Generated Memo")
        
        # Log what we're about to display
        logger.info(f"Displaying clean memo sample: {repr(memo_content[:150])}")
        
        # Convert markdown to HTML manually to bypass Streamlit's markdown processor
        html_content = self._convert_markdown_to_html(memo_content)
        
        # Use HTML display which preserves formatting
        st.markdown(html_content, unsafe_allow_html=True)
        
        # Download button
        st.download_button(
            label="📥 Download Memo (Markdown)",
            data=memo_content,
            file_name=f"accounting_memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    
    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML manually to preserve currency formatting."""
        
        # Split into lines and process each one
        lines = markdown_content.split('\n')
        html_lines = []
        
        for line in lines:
            # Convert headers with inline styles for tighter spacing
            if line.startswith('# '):
                html_lines.append(f'<h1 style="margin: 16px 0 12px 0;">{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2 style="margin: 14px 0 10px 0;">{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3 style="margin: 12px 0 8px 0;">{line[4:]}</h3>')
            # Convert bold text
            elif '**' in line:
                # Simple bold conversion with reduced paragraph margins
                line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
                html_lines.append(f'<p style="margin: 8px 0;">{line}</p>')
            # Convert horizontal rules
            elif line.strip() == '---':
                html_lines.append('<hr style="margin: 25px 0;">')
            # Empty lines - skip them to reduce spacing
            elif line.strip() == '':
                continue  # Don't add empty breaks
            # Regular paragraphs with reduced margins
            else:
                html_lines.append(f'<p style="margin: 8px 0;">{line}</p>')
        
        # Join with safer inline-only styling
        html_content = f"""
        <div style="font-family: Georgia, 'Times New Roman', sans-serif; 
        line-height: 1.5; max-width: 800px; padding: 25px; background-color: #f8f9fa;">
            {''.join(html_lines)}
        </div>
        """
        
        return html_content