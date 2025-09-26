"""
Pure Python PDF Generator for VeritasLogic using ReportLab
No system dependencies required - works in any environment
"""

import logging
from typing import Optional
from io import BytesIO
import re

logger = logging.getLogger(__name__)

def generate_pdf_from_markdown(markdown_content: str) -> Optional[bytes]:
    """
    Generate PDF from markdown content using ReportLab.
    
    Pure Python solution with zero system dependencies.
    
    Args:
        markdown_content: Markdown content to convert to PDF
        
    Returns:
        PDF bytes or None if generation failed
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        
        logger.info("Generating PDF using ReportLab")
        
        # Create PDF buffer
        buffer = BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles for professional memo
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=12,
            alignment=1,  # Center
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            fontName='Helvetica',
            leftIndent=0,
            rightIndent=0
        )
        
        # Parse markdown and build story
        story = []
        lines = markdown_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                story.append(Spacer(1, 6))
                continue
                
            # Headers
            if line.startswith('# '):
                text = line[2:].strip()
                story.append(Paragraph(text, title_style))
            elif line.startswith('## '):
                text = line[3:].strip()
                story.append(Paragraph(text, heading_style))
            elif line.startswith('### '):
                text = line[4:].strip()
                story.append(Paragraph(text, heading_style))
            # Bold text
            elif line.startswith('**') and line.endswith('**'):
                text = line[2:-2].strip()
                story.append(Paragraph(f"<b>{text}</b>", normal_style))
            # Regular paragraph
            else:
                # Convert markdown formatting
                text = line
                # Bold formatting
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                # Italic formatting  
                text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                
                story.append(Paragraph(text, normal_style))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"PDF generation successful: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except ImportError as e:
        logger.error(f"ReportLab not available: {e}")
        return None
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None

def generate_pdf_from_html(html_content: str) -> Optional[bytes]:
    """
    Generate PDF from HTML content using ReportLab.
    
    Note: This is a simple implementation for basic HTML.
    For complex HTML, consider using the markdown version.
    
    Args:
        html_content: HTML content to convert to PDF
        
    Returns:
        PDF bytes or None if generation failed
    """
    try:
        # For now, strip HTML tags and treat as plain text
        import re
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        # Convert to simple markdown format
        clean_text = clean_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        
        return generate_pdf_from_markdown(clean_text)
        
    except Exception as e:
        logger.error(f"HTML to PDF conversion failed: {e}")
        return None