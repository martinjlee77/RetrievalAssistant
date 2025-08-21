"""
Shared Memo Generation Module

This module handles professional memo generation for all accounting standards.
Uses template-based approach with natural language sections and includes
the innovative "Issues for Further Investigation" section.

Author: Accounting Platform Team
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import re

logger = logging.getLogger(__name__)

class SharedMemoGenerator:
    """
    Template-based memo generator for professional accounting memos.
    Supports Big 4 style formatting with natural language sections.
    """
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize memo generator with optional custom template.
        
        Args:
            template_path: Path to custom memo template (uses default if None)
        """
        self.template_path = template_path
        self.default_template = self._get_default_template()
    
    def generate_memo(self, 
                     memo_data: Dict[str, Any],
                     customer_name: str,
                     analysis_title: str,
                     standard_name: str) -> str:
        """
        Generate a professional memo using template and analysis data.
        
        Args:
            memo_data: Dictionary containing analysis results
            customer_name: Name of the customer/entity
            analysis_title: Title for the analysis
            standard_name: Accounting standard (e.g., "ASC 606")
            
        Returns:
            Formatted memo as markdown string
        """
        try:
            # Load template
            template = self._load_template()
            
            # Clean content formatting before template processing
            cleaned_memo_data = self._clean_memo_data_formatting(memo_data)
            
            # Prepare template variables
            template_vars = self._prepare_template_variables(
                cleaned_memo_data, customer_name, analysis_title, standard_name
            )
            
            # Replace template placeholders
            memo_content = self._replace_template_placeholders(template, template_vars)
            
            # Clean up and format
            final_memo = self._clean_and_format_memo(memo_content)
            
            logger.info(f"Generated memo for {customer_name} - {standard_name}")
            return final_memo
            
        except Exception as e:
            logger.error(f"Error generating memo: {str(e)}")
            return f"Error generating memo: {str(e)}"
    
    def _load_template(self) -> str:
        """Load memo template from file or use default."""
        if self.template_path:
            try:
                with open(self.template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Could not load template from {self.template_path}: {e}")
                
        return self.default_template
    
    def _get_default_template(self) -> str:
        """Default Big 4 style memo template."""
        return """
# ACCOUNTING MEMORANDUM

**TO:** Chief Accounting Officer  
**FROM:** Technical Accounting Team  
**DATE:** {current_date}  
**RE:** {analysis_title}

---

## EXECUTIVE SUMMARY

{executive_summary}

---

## BACKGROUND

{background_section}

---

## ANALYSIS

{analysis_section}

---

## CONCLUSION

{conclusion_section}

---

## ISSUES FOR FURTHER INVESTIGATION

{issues_section}

---

*This memorandum represents our preliminary analysis based on the contract documents provided. Final implementation should be reviewed with external auditors and may require additional documentation or analysis.*
"""
    
    def _prepare_template_variables(self, 
                                  memo_data: Dict[str, Any],
                                  customer_name: str,
                                  analysis_title: str,
                                  standard_name: str) -> Dict[str, str]:
        """Prepare all template variables from memo data."""
        
        # Basic variables
        template_vars = {
            'current_date': datetime.now().strftime("%B %d, %Y"),
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'standard_name': standard_name
        }
        
        # Extract sections from memo data
        template_vars.update({
            'executive_summary': self._extract_executive_summary(memo_data),
            'background_section': self._extract_background_section(memo_data, customer_name),
            'analysis_section': self._extract_analysis_section(memo_data, standard_name),
            'conclusion_section': self._extract_conclusion_section(memo_data),
            'issues_section': self._extract_issues_section(memo_data)
        })
        
        return template_vars
    
    def _extract_executive_summary(self, memo_data: Dict[str, Any]) -> str:
        """Extract or generate executive summary."""
        # Look for executive summary in memo data
        if 'executive_summary' in memo_data:
            return memo_data['executive_summary']
        
        if 'executive_conclusion' in memo_data:
            return memo_data['executive_conclusion']
            
        # Generate basic summary if not provided
        return "This memorandum presents our analysis of the contract under the applicable accounting standards."
    
    def _extract_background_section(self, memo_data: Dict[str, Any], customer_name: str) -> str:
        """Extract or generate background section."""
        # Debug logging removed - customer name issue resolved
        
        # Clean customer name to prevent contract text bleeding through
        clean_customer_name = customer_name.split('\n')[0].strip() if customer_name else "the client"
        if len(clean_customer_name) > 100:  # Likely contract text, not a customer name
            clean_customer_name = "the client"
            
        background = f"We have reviewed the contract documents provided by {clean_customer_name} to determine the appropriate revenue recognition treatment under ASC 606. "
        background += "This memorandum presents our analysis following the five-step ASC 606 methodology and provides recommendations for implementation."
            
        return background
    
    def _extract_analysis_section(self, memo_data: Dict[str, Any], standard_name: str) -> str:
        """Extract and format the main analysis section."""
        if 'analysis_content' in memo_data:
            return memo_data['analysis_content']
        
        # If analysis is structured by steps, combine them
        analysis_parts = []
        
        # Look for step-based analysis
        for key, value in memo_data.items():
            if 'step' in key.lower() and isinstance(value, str):
                step_num = self._extract_step_number(key)
                if step_num:
                    analysis_parts.append(f"### Step {step_num}: {key.replace('_', ' ').title()}\n\n{value}")
                else:
                    analysis_parts.append(f"### {key.replace('_', ' ').title()}\n\n{value}")
        
        if analysis_parts:
            return "\n\n".join(analysis_parts)
        
        # Fallback
        return f"The analysis under {standard_name} considers all relevant factors and guidance."
    
    def _extract_conclusion_section(self, memo_data: Dict[str, Any]) -> str:
        """Extract conclusion section."""
        if 'conclusion' in memo_data:
            return memo_data['conclusion']
        
        if 'final_conclusion' in memo_data:
            return memo_data['final_conclusion']
            
        return "Based on our analysis, the proposed accounting treatment is appropriate and complies with the applicable standards."
    
    def _extract_issues_section(self, memo_data: Dict[str, Any]) -> str:
        """Extract or generate issues for further investigation section."""
        issues = []
        
        # Look for explicit issues
        if 'issues_for_investigation' in memo_data:
            if isinstance(memo_data['issues_for_investigation'], list):
                issues.extend(memo_data['issues_for_investigation'])
            else:
                issues.append(memo_data['issues_for_investigation'])
        
        # Look for uncertainties or gaps mentioned in analysis
        if 'uncertainties' in memo_data:
            issues.extend(memo_data['uncertainties'])
        
        # Only show issues section if there are real issues
        if not issues:
            return ""  # Return empty string to hide the section
        
        # Filter out generic/default issues
        real_issues = []
        for issue in issues:
            issue_lower = issue.lower().strip()
            if not any(generic in issue_lower for generic in [
                'validate completeness', 'confirm implementation', 
                'review final accounting', 'external auditor', 'validate the completeness'
            ]):
                real_issues.append(issue.strip())
        
        # If only generic issues remain, don't show section
        if not real_issues:
            return ""
            
        # Format as professional list with section header
        formatted_issues = ["## ISSUES FOR FURTHER INVESTIGATION", "", "The following items require additional review or clarification:", ""]
        for i, issue in enumerate(real_issues, 1):
            formatted_issues.append(f"{i}. {issue}")
        
        formatted_issues.extend(["", "---"])
        return "\n".join(formatted_issues)
    
    def _extract_step_number(self, key: str) -> Optional[str]:
        """Extract step number from key."""
        match = re.search(r'step\s*(\d+)', key.lower())
        return match.group(1) if match else None
    
    def _clean_memo_data_formatting(self, memo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean common LLM formatting issues in memo data."""
        cleaned_data = memo_data.copy()
        
        # Content fields that need cleaning
        content_fields = ['analysis_content', 'executive_summary', 'conclusion', 
                         'background_section', 'analysis_section']
        
        for field in content_fields:
            if field in cleaned_data and cleaned_data[field]:
                cleaned_data[field] = self._clean_content_formatting(cleaned_data[field])
        
        return cleaned_data
    
    def _clean_content_formatting(self, content: str) -> str:
        """Clean common LLM formatting issues with minimal, essential patterns only."""
        if not content:
            return content
            
        # Essential fixes only - let the improved prompts handle the rest
        
        # 1. Fix HTML artifacts (always needed for template cleanup)
        content = re.sub(r'<br>\s*', '\n', content)
        content = re.sub(r'<[^>]+>', '', content)
        
        # 2. Fix duplicate headers (template-specific issue)
        content = re.sub(r'## EXECUTIVE SUMMARY\s*\n\s*Executive Summary[:\s]*\n?', '## EXECUTIVE SUMMARY\n\n', content)
        content = re.sub(r'EXECUTIVE SUMMARY\s*\n\s*Executive Summary[:\s]*\n?', 'EXECUTIVE SUMMARY\n\n', content)
        
        # 3. Ensure proper paragraph spacing (basic formatting)
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        # 4. Remove non-ASCII characters (prevents display issues)
        content = re.sub(r'[^\x00-\x7F]+', '', content)
        content = re.sub(r'[\x00-\x1F\x7F]', '', content)
        
        return content.strip()
    
    def combine_markdown_steps(self, analysis_results: Dict[str, Any]) -> str:
        """Combine markdown step results into complete memo."""
        customer_name = analysis_results.get('customer_name', 'Unknown')
        analysis_title = analysis_results.get('analysis_title', 'Contract Analysis')
        analysis_date = analysis_results.get('analysis_date', datetime.now().strftime("%B %d, %Y"))
        
        # Build memo header
        memo_parts = [
            "# ASC 606 REVENUE RECOGNITION MEMORANDUM",
            "",
            f"**TO:** Chief Accounting Officer",
            f"**FROM:** Technical Accounting Team - AI",
            f"**DATE:** {analysis_date}",
            f"**RE:** {analysis_title} - ASC 606 Revenue Recognition Analysis",
            "",
            "---",
            ""
        ]
        
        # Add executive summary if available
        if 'executive_summary' in analysis_results:
            memo_parts.extend([
                "## EXECUTIVE SUMMARY",
                "",
                analysis_results['executive_summary'],
                "",
                "---",
                ""
            ])
        
        # Add background
        memo_parts.extend([
            "## BACKGROUND",
            "",
            f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology and provides recommendations for implementation.",
            "",
            "---",
            "",
            "## ASC 606 ANALYSIS",
            ""
        ])
        
        # Add each step's markdown content
        logger.info(f"DEBUG: Analysis results keys: {list(analysis_results.keys())}")
        
        steps_added = 0
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            if step_key in analysis_results:
                step_data = analysis_results[step_key]
                logger.info(f"DEBUG: Step {step_num} data keys: {list(step_data.keys()) if isinstance(step_data, dict) else 'Not a dict'}")
                
                if isinstance(step_data, dict) and 'markdown_content' in step_data:
                    memo_parts.append(step_data['markdown_content'])
                    memo_parts.append("")
                    steps_added += 1
                    logger.info(f"DEBUG: Added step {step_num} markdown content ({len(step_data['markdown_content'])} chars)")
                else:
                    logger.warning(f"Step {step_num} missing markdown_content - Keys: {list(step_data.keys()) if isinstance(step_data, dict) else 'Not dict'}")
                    memo_parts.append(f"## Step {step_num}: Analysis Error")
                    memo_parts.append("Step analysis data not available in expected format.")
                    memo_parts.append("")
        
        logger.info(f"DEBUG: Total steps added to memo: {steps_added}/5")
        
        # Add conclusion if available
        if 'conclusion' in analysis_results:
            memo_parts.extend([
                "---",
                "",
                "## CONCLUSION",
                "",
                analysis_results['conclusion'],
                ""
            ])
        
        # Add footer
        memo_parts.extend([
            "---",
            "",
            "**PREPARED BY:** [Analyst Name] | [Title] | [Date]",
            "**REVIEWED BY:** [Reviewer Name] | [Title] | [Date]",
            "",
            "*This memorandum represents our preliminary analysis based on the contract documents provided. Final implementation should be reviewed with external auditors and may require additional documentation or analysis of specific implementation details.*"
        ])
        
        return "\n".join(memo_parts)
    
    def _replace_template_placeholders(self, template: str, variables: Dict[str, str]) -> str:
        """Replace all template placeholders with actual values."""
        content = template
        
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            content = content.replace(placeholder, str(value))
        
        return content
    
    def _clean_and_format_memo(self, memo_content: str) -> str:
        """Clean up and format the final memo."""
        # Remove excessive blank lines
        memo_content = re.sub(r'\n\s*\n\s*\n', '\n\n', memo_content)
        
        # Ensure consistent section spacing
        memo_content = re.sub(r'\n---\n', '\n\n---\n\n', memo_content)
        
        # Clean up any remaining formatting issues
        memo_content = memo_content.strip()
        
        return memo_content
    
    def display_memo(self, memo_content: str) -> None:
        """Display the generated memo in Streamlit with download option."""
        st.markdown("## 📋 Generated Memo")
        
        # Display memo content
        st.markdown(memo_content)
        
        # Add download button
        st.download_button(
            label="📥 Download Memo (Markdown)",
            data=memo_content,
            file_name=f"accounting_memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    
    def save_memo_to_file(self, memo_content: str, filename: str) -> bool:
        """Save memo content to a file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(memo_content)
            logger.info(f"Memo saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving memo to {filename}: {str(e)}")
            return False