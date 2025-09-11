"""
Audit Pack Generator for VeritasLogic Platform
Creates audit-ready export packages with citations, assumptions, and references
"""

import logging
import re
from typing import Dict, Any, List, Optional
from fpdf import FPDF
from datetime import datetime
import tempfile

logger = logging.getLogger(__name__)

class AuditPackGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_citations_from_memo(self, memo_content: str) -> List[Dict[str, str]]:
        """
        Extract ASC paragraph citations from memo content
        
        Args:
            memo_content: The memo markdown content
            
        Returns:
            List of citation dictionaries with paragraph and context
        """
        citations = []
        
        # Pattern to match ASC citations (e.g., ASC 606-10-25-1, ASC 842-10-15-3)
        citation_pattern = r'ASC\s+(\d{3}-\d{2}-\d{2}-\d+)'
        
        lines = memo_content.split('\n')
        for i, line in enumerate(lines):
            matches = re.finditer(citation_pattern, line)
            for match in matches:
                citation = {
                    'paragraph': match.group(0),  # Full ASC reference
                    'context': line.strip(),      # Line containing the citation
                    'section': self._find_section_header(lines, i)  # Section this appears in
                }
                if citation not in citations:  # Avoid duplicates
                    citations.append(citation)
        
        return citations
    
    def extract_assumptions_from_memo(self, memo_content: str) -> List[str]:
        """
        Extract key assumptions and judgments from memo content
        
        Args:
            memo_content: The memo markdown content
            
        Returns:
            List of assumption statements
        """
        assumptions = []
        
        # Keywords that indicate assumptions or judgments
        assumption_keywords = [
            'assume', 'assumed', 'assumption', 'judgment', 'conclude', 'concluded',
            'determine', 'determined', 'estimate', 'estimated', 'believe', 'likely',
            'probable', 'based on management', 'in our view', 'we conclude'
        ]
        
        lines = memo_content.split('\n')
        for line in lines:
            line_lower = line.lower().strip()
            
            # Skip headers and empty lines
            if not line_lower or line.startswith('#'):
                continue
                
            # Check if line contains assumption language
            for keyword in assumption_keywords:
                if keyword in line_lower:
                    clean_line = line.strip(' -•*')
                    if len(clean_line) > 20:  # Filter out very short matches
                        assumptions.append(clean_line)
                    break
        
        return list(set(assumptions))  # Remove duplicates
    
    def extract_references_from_memo(self, memo_content: str, filename: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Extract source document references
        
        Args:
            memo_content: The memo markdown content
            filename: Original uploaded filename
            
        Returns:
            List of reference dictionaries
        """
        references = []
        
        # Add the primary source document
        if filename:
            references.append({
                'type': 'Source Document',
                'description': f'Primary contract analyzed: {filename}',
                'usage': 'Contract terms, provisions, and financial data'
            })
        
        # Add authoritative guidance reference
        # Extract ASC standard from memo content
        asc_pattern = r'ASC\s+(\d{3})'
        asc_matches = re.findall(asc_pattern, memo_content)
        
        if asc_matches:
            asc_standard = asc_matches[0]  # Get first/primary standard
            references.append({
                'type': 'Authoritative Guidance',
                'description': f'FASB Accounting Standards Codification (ASC) {asc_standard}',
                'usage': 'Primary accounting guidance and implementation requirements'
            })
        
        # Add general references
        references.append({
            'type': 'Professional Standards',
            'description': 'FASB Accounting Standards Codification',
            'usage': 'Authoritative accounting guidance'
        })
        
        return references
    
    def _find_section_header(self, lines: List[str], current_line: int) -> str:
        """
        Find the most recent section header before the current line
        
        Args:
            lines: All lines in the memo
            current_line: Current line index
            
        Returns:
            Section header or 'Unknown Section'
        """
        # Look backwards for the most recent header
        for i in range(current_line, -1, -1):
            line = lines[i].strip()
            if line.startswith('##') and not line.startswith('###'):
                return line.replace('#', '').strip()
        
        return 'Unknown Section'
    
    def generate_audit_pack_pdf(self, memo_content: str, analysis_id: str, 
                               filename: Optional[str] = None, customer_name: Optional[str] = None) -> bytes:
        """
        Generate audit pack PDF with citations, assumptions, and references
        
        Args:
            memo_content: The memo markdown content
            analysis_id: Memo ID
            filename: Original filename
            customer_name: Customer name
            
        Returns:
            PDF bytes
        """
        try:
            # Extract audit pack components
            citations = self.extract_citations_from_memo(memo_content)
            assumptions = self.extract_assumptions_from_memo(memo_content)
            references = self.extract_references_from_memo(memo_content, filename)
            
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            
            # Title
            pdf.cell(0, 10, 'Audit Pack - Supporting Documentation', ln=True, align='C')
            pdf.ln(5)
            
            # Memo details
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Memo ID: {analysis_id}', ln=True)
            if customer_name:
                pdf.cell(0, 8, f'Entity: {customer_name}', ln=True)
            if filename:
                pdf.cell(0, 8, f'Source Document: {filename}', ln=True)
            pdf.cell(0, 8, f'Generated: {datetime.now().strftime("%B %d, %Y")}', ln=True)
            pdf.ln(10)
            
            # ASC Citations Section
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, '1. ASC Paragraph Citations', ln=True)
            pdf.set_font('Arial', '', 11)
            
            if citations:
                for i, citation in enumerate(citations, 1):
                    pdf.cell(0, 6, f'{i}. {citation["paragraph"]}', ln=True)
                    pdf.cell(0, 6, f'   Context: {citation["context"][:80]}...', ln=True)
                    pdf.cell(0, 6, f'   Section: {citation["section"]}', ln=True)
                    pdf.ln(2)
            else:
                pdf.cell(0, 8, 'No specific ASC citations found in memo.', ln=True)
            
            pdf.ln(5)
            
            # Key Assumptions Section
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, '2. Key Assumptions and Judgments', ln=True)
            pdf.set_font('Arial', '', 11)
            
            if assumptions:
                for i, assumption in enumerate(assumptions[:10], 1):  # Limit to top 10
                    # Wrap long assumptions
                    assumption_text = assumption if len(assumption) <= 80 else assumption[:77] + '...'
                    pdf.cell(0, 6, f'{i}. {assumption_text}', ln=True)
                    pdf.ln(1)
            else:
                pdf.cell(0, 8, 'No specific assumptions identified in memo.', ln=True)
            
            pdf.ln(5)
            
            # References Section
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, '3. Source References', ln=True)
            pdf.set_font('Arial', '', 11)
            
            for i, ref in enumerate(references, 1):
                pdf.cell(0, 6, f'{i}. {ref["type"]}: {ref["description"]}', ln=True)
                pdf.cell(0, 6, f'   Usage: {ref["usage"]}', ln=True)
                pdf.ln(2)
            
            # Footer
            pdf.ln(10)
            pdf.set_font('Arial', 'I', 10)
            pdf.cell(0, 6, 'This audit pack was automatically generated by VeritasLogic.ai', ln=True, align='C')
            pdf.cell(0, 6, 'Review all citations and assumptions for accuracy before relying on this analysis', ln=True, align='C')
            
            pdf_output = pdf.output(dest='S')
            # Handle different output types (bytes, bytearray, or str)
            if isinstance(pdf_output, str):
                return pdf_output.encode('latin-1')
            elif isinstance(pdf_output, bytearray):
                return bytes(pdf_output)
            return pdf_output
            
        except Exception as e:
            logger.error(f"Audit pack generation error: {e}")
            # Return minimal PDF on error
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f'Audit Pack for Memo {analysis_id}', ln=True)
            pdf.cell(0, 10, 'Error generating detailed audit pack.', ln=True)
            pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%B %d, %Y")}', ln=True)
            pdf_output = pdf.output(dest='S')
            # Handle different output types (bytes, bytearray, or str)
            if isinstance(pdf_output, str):
                return pdf_output.encode('latin-1')
            elif isinstance(pdf_output, bytearray):
                return bytes(pdf_output)
            return pdf_output
    
    def add_audit_pack_download(self, memo_content: str, analysis_id: str, 
                               filename: Optional[str] = None, customer_name: Optional[str] = None) -> None:
        """
        Add audit pack download button to Streamlit interface
        
        Args:
            memo_content: The memo markdown content
            analysis_id: Memo ID
            filename: Original filename
            customer_name: Customer name
        """
        import streamlit as st
        
        try:
            audit_pack_pdf = self.generate_audit_pack_pdf(
                memo_content, analysis_id, filename, customer_name
            )
            
            st.download_button(
                label="📋 Download Audit Pack",
                data=audit_pack_pdf,
                file_name=f"audit_pack_{analysis_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
                help="Download audit support package with citations, assumptions, and references"
            )
            
        except Exception as e:
            logger.error(f"Audit pack download error: {e}")
            st.button(
                "📋 Audit Pack", 
                disabled=True, 
                use_container_width=True, 
                help="Audit pack generation failed"
            )