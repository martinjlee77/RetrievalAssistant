"""
Isolated PDF Generator Module for VeritasLogic
Uses deterministic WeasyPrint import strategy to avoid Streamlit module pollution
"""

import logging
import sys
import importlib
from typing import Optional

logger = logging.getLogger(__name__)

def generate_pdf_from_html(html_content: str, base_url: str = None) -> Optional[bytes]:
    """
    Generate PDF from HTML using isolated WeasyPrint import
    
    STRATEGIC FIX: This function imports WeasyPrint in a clean environment
    to avoid Streamlit's module pollution that causes PDF class conflicts.
    
    Args:
        html_content: HTML content to convert to PDF
        base_url: Base URL for resolving relative paths
        
    Returns:
        PDF bytes or None if generation failed
    """
    try:
        # Clear specific conflicting modules before WeasyPrint import
        conflicting_modules = ['pdf', 'streamlit.elements.pdf']
        cleared_modules = {}
        
        for module_name in conflicting_modules:
            if module_name in sys.modules:
                cleared_modules[module_name] = sys.modules.pop(module_name)
                logger.info(f"Cleared conflicting module: {module_name}")
        
        # Import WeasyPrint in clean environment
        logger.info("Importing WeasyPrint with clean module cache")
        wp = importlib.import_module('weasyprint')
        
        # Create HTML document
        logger.info("Creating HTML document for PDF generation")
        if base_url:
            html_doc = wp.HTML(string=html_content, base_url=base_url)
        else:
            html_doc = wp.HTML(string=html_content)
        
        # Generate PDF
        logger.info("Generating PDF from HTML document")
        pdf_bytes = html_doc.write_pdf()
        
        # Restore cleared modules
        for module_name, module_obj in cleared_modules.items():
            if module_obj is not None:
                sys.modules[module_name] = module_obj
        
        logger.info(f"PDF generation successful: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        
        # Restore cleared modules on error
        for module_name, module_obj in cleared_modules.items():
            if module_obj is not None:
                sys.modules[module_name] = module_obj
        
        return None

def generate_styled_pdf(markdown_content: str, memo_id: str) -> Optional[bytes]:
    """
    Generate styled PDF from markdown content with VeritasLogic styling
    
    Args:
        markdown_content: Markdown content to convert
        memo_id: Memo ID for the document
        
    Returns:
        PDF bytes or None if generation failed
    """
    try:
        import os
        import markdown
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        
        # Get absolute paths to font files
        font_dir = os.path.abspath('assets/fonts')
        
        # Add CSS styling with @font-face declarations for DejaVu Serif
        css_styled_html = f"""
        <html>
        <head>
            <style>
                /* DejaVu Serif font family with all variants */
                @font-face {{
                    font-family: 'VLSerif';
                    src: url('file://{font_dir}/DejaVuSerif.ttf') format('truetype');
                    font-weight: 400;
                    font-style: normal;
                }}
                @font-face {{
                    font-family: 'VLSerif';
                    src: url('file://{font_dir}/DejaVuSerif-Italic.ttf') format('truetype');
                    font-weight: 400;
                    font-style: italic;
                }}
                @font-face {{
                    font-family: 'VLSerif';
                    src: url('file://{font_dir}/DejaVuSerif-Bold.ttf') format('truetype');
                    font-weight: 700;
                    font-style: normal;
                }}
                @font-face {{
                    font-family: 'VLSerif';
                    src: url('file://{font_dir}/DejaVuSerif-BoldItalic.ttf') format('truetype');
                    font-weight: 700;
                    font-style: italic;
                }}
                
                body {{
                    font-family: 'VLSerif', serif;
                    margin: 10px;
                    line-height: 1.5;
                    font-size: 11px;
                }}
                /* Remove borders from HTML content for clean PDF */
                div {{
                    border: none !important;
                    box-shadow: none !important;
                    border-radius: 0 !important;
                }}
                h1 {{
                    border-bottom: 2px solid #bdc3c7;
                    padding-bottom: 5px;
                    margin: 20px 0 15px 0;
                }}
                h2 {{
                    color: #2c3e50;
                    margin: 15px 0 10px 0;
                    font-size: 14px;
                }}
                h3 {{
                    color: #34495e;
                    margin: 12px 0 8px 0;
                    font-size: 12px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                .memo-header {{
                    text-align: center;
                    margin-bottom: 20px;
                    font-size: 10px;
                    color: #666;
                }}
                /* Prevent page breaks inside important elements */
                h1, h2, h3 {{
                    page-break-after: avoid;
                }}
                table {{
                    page-break-inside: avoid;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF using isolated WeasyPrint
        return generate_pdf_from_html(css_styled_html, base_url=os.getcwd())
        
    except Exception as e:
        logger.error(f"Styled PDF generation failed: {e}")
        return None