"""
Simple PDF Generator for VeritasLogic using xhtml2pdf
Pure Python solution - no system dependencies required
"""

import logging
import markdown
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)

def generate_pdf_from_markdown(markdown_content: str) -> Optional[bytes]:
    """
    Generate PDF from markdown content using xhtml2pdf.
    
    Simple, reliable pipeline: Markdown → HTML → PDF
    
    Args:
        markdown_content: Markdown content to convert to PDF
        
    Returns:
        PDF bytes or None if generation failed
    """
    try:
        from xhtml2pdf import pisa
        
        logger.info("Converting markdown to HTML")
        
        # Convert markdown to HTML
        html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        # Add basic professional styling
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: "Times New Roman", serif;
                    font-size: 12pt;
                    line-height: 1.4;
                    margin: 1in;
                    color: #000;
                }}
                h1 {{
                    font-size: 16pt;
                    font-weight: bold;
                    margin-top: 24pt;
                    margin-bottom: 12pt;
                    text-align: center;
                }}
                h2 {{
                    font-size: 14pt;
                    font-weight: bold;
                    margin-top: 18pt;
                    margin-bottom: 6pt;
                }}
                h3 {{
                    font-size: 12pt;
                    font-weight: bold;
                    margin-top: 12pt;
                    margin-bottom: 6pt;
                }}
                p {{
                    margin-bottom: 6pt;
                    text-align: justify;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 12pt 0;
                }}
                th, td {{
                    border: 1pt solid #000;
                    padding: 6pt;
                    text-align: left;
                }}
                th {{
                    background-color: #f0f0f0;
                    font-weight: bold;
                }}
                strong {{
                    font-weight: bold;
                }}
                em {{
                    font-style: italic;
                }}
                small {{
                    font-size: 10pt;
                }}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        
        logger.info("Generating PDF from HTML using xhtml2pdf")
        
        # Create PDF
        result = BytesIO()
        pisa_status = pisa.CreatePDF(styled_html, dest=result)
        
        if pisa_status.err:
            logger.error(f"xhtml2pdf generation failed with {pisa_status.err} errors")
            return None
        
        pdf_bytes = result.getvalue()
        result.close()
        
        logger.info(f"PDF generation successful: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except ImportError as e:
        logger.error(f"xhtml2pdf not available: {e}")
        return None
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None

def generate_pdf_from_html(html_content: str) -> Optional[bytes]:
    """
    Generate PDF directly from HTML content using xhtml2pdf.
    
    Args:
        html_content: HTML content to convert to PDF
        
    Returns:
        PDF bytes or None if generation failed
    """
    try:
        from xhtml2pdf import pisa
        
        logger.info("Generating PDF from HTML using xhtml2pdf")
        
        # Create PDF
        result = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=result)
        
        if pisa_status.err:
            logger.error(f"xhtml2pdf generation failed with {pisa_status.err} errors")
            return None
        
        pdf_bytes = result.getvalue()
        result.close()
        
        logger.info(f"PDF generation successful: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except ImportError as e:
        logger.error(f"xhtml2pdf not available: {e}")
        return None
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None