"""
HTML Export Utility for Professional ASC 606 Memos
Converts markdown memos to clean, professional HTML with Big 4 styling
"""

import markdown2
from datetime import datetime
from typing import Optional, Dict, Any
import base64
import io
import re

def _preprocess_markdown_for_html(memo_markdown: str) -> str:
    """
    Finds custom semantic tags ([QUOTE], [CITATION]) and converts them to
    standard HTML tags with appropriate classes that our CSS can style.

    This function should run BEFORE the main markdown2 conversion.
    
    Args:
        memo_markdown: Raw markdown content with custom semantic tags
        
    Returns:
        Processed markdown with custom tags converted to HTML
    """
    processed_text = memo_markdown

    # 1. Convert [QUOTE]Your quote text[/QUOTE] to <blockquote>Your quote text</blockquote>
    # The regex looks for the opening tag, captures the text inside (non-greedy),
    # and finds the closing tag. It replaces the whole thing with an HTML blockquote.
    processed_text = re.sub(
        r'\[QUOTE\](.*?)\[/QUOTE\]', 
        r'<blockquote>\1</blockquote>', 
        processed_text, 
        flags=re.DOTALL
    )

    # 2. Convert [CITATION]Your citation text[/CITATION] to <span class="citation">...</span>
    # This wraps the citation in a <span> tag and gives it the "citation" class,
    # which our CSS already knows how to style.
    processed_text = re.sub(
        r'\[CITATION\](.*?)\[/CITATION\]', 
        r'<span class="citation">\1</span>', 
        processed_text,
        flags=re.DOTALL
    )

    return processed_text

def get_style_config() -> Dict[str, str]:
    """
    Configuration-driven styling for professional memos
    
    Returns:
        Dictionary containing all styling parameters
    """
    return {
        'font_family': 'Times New Roman',
        'font_size': '11pt',
        'page_width': '8.5in',
        'margins': '1in',
        'primary_color': '#000000',
        'secondary_color': '#666666',
        'border_color': '#000000',
        'line_height': '1.6',
        'header_size': '14pt',
        'subheader_size': '12pt'
    }

def convert_memo_to_html(memo_markdown: str, contract_data: Optional[dict] = None) -> str:
    """
    Convert markdown memo to professional HTML with Big 4 styling
    
    Args:
        memo_markdown: The markdown content of the memo
        contract_data: Optional contract data for enhanced metadata
    
    Returns:
        Complete HTML document with professional styling
        
    Raises:
        ValueError: If memo content is empty or conversion fails
    """
    
    # Input validation
    if not memo_markdown or not memo_markdown.strip():
        raise ValueError("Empty memo content provided")
    
    # Pre-process the markdown to handle our custom tags FIRST
    preprocessed_markdown = _preprocess_markdown_for_html(memo_markdown)
    
    # Convert the PREPROCESSED markdown to HTML with error handling
    try:
        html_content = markdown2.markdown(
            preprocessed_markdown,  # Use the pre-processed version!
            extras=[
                'fenced-code-blocks',
                'tables',
                'break-on-newline',
                'cuddled-lists',
                'metadata'
            ]
        )
    except Exception as e:
        raise ValueError(f"Markdown conversion failed: {e}")
    
    # Get styling configuration
    style_config = get_style_config()
    
    # Generate professional CSS with configuration
    professional_css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Times+New+Roman:wght@400;700&display=swap');
        
        body {{
            font-family: '{style_config['font_family']}', serif;
            font-size: {style_config['font_size']};
            line-height: {style_config['line_height']};
            max-width: {style_config['page_width']};
            margin: 0 auto;
            padding: {style_config['margins']};
            background: white;
            color: #000;
        }}
        
        /* Header styling */
        h1 {{
            font-size: {style_config['header_size']};
            font-weight: bold;
            text-align: center;
            margin-bottom: 24pt;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: {style_config['primary_color']};
        }}
        
        h2 {{
            font-size: {style_config['subheader_size']};
            font-weight: bold;
            margin-top: 18pt;
            margin-bottom: 12pt;
            border-bottom: 1px solid {style_config['primary_color']};
            padding-bottom: 3pt;
            color: {style_config['primary_color']};
        }}
        
        h3 {{
            font-size: {style_config['font_size']};
            font-weight: bold;
            margin-top: 12pt;
            margin-bottom: 6pt;
        }}
        
        /* Paragraph and text styling */
        p {{
            margin-bottom: 12pt;
            text-align: justify;
        }}
        
        /* Citation and quote styling - PROFESSIONAL MEMO STANDARDS */
        blockquote {{
            font-family: '{style_config['font_family']}', serif; /* Same as body font for consistency */
            font-style: italic;
            font-size: {style_config['font_size']}; /* Same size as body text */
            color: #333333; /* Professional dark grey */
            background-color: #f8f9fa; /* Very subtle light background */
            border: 1px solid #dee2e6; /* Light professional border */
            /* Removed left border line as requested */
            border-radius: 3px; /* Minimal rounded corners */
            padding: 8pt 12pt; /* Tighter top/bottom padding, keep left/right */
            margin: 12pt 0; /* Reduced margin for tighter appearance */
        }}
        
        .citation {{
            font-weight: bold;
            font-style: normal;
            color: #000000; /* Black font as requested */
            background-color: #f0f4f8; /* Keep the highlight background */
            padding: 1px 4px;
            border-radius: 2px;
            font-size: 1em; /* Same size as body text */
        }}
        
        /* Table styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
        }}
        
        th, td {{
            border: 1px solid {style_config['border_color']};
            padding: 8pt;
            text-align: left;
        }}
        
        th {{
            background-color: #f0f0f0;
            font-weight: bold;
        }}
        
        /* List styling */
        ul, ol {{
            margin: 12pt 0;
            padding-left: 24pt;
        }}
        
        li {{
            margin-bottom: 6pt;
        }}
        
        /* Memo header */
        .memo-header {{
            border-bottom: 2px solid {style_config['primary_color']};
            padding-bottom: 12pt;
            margin-bottom: 24pt;
        }}
        
        .memo-to-from {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24pt;
            margin: 12pt 0;
        }}
        
        /* Footer */
        .memo-footer {{
            margin-top: 36pt;
            padding-top: 12pt;
            border-top: 1px solid {style_config['border_color']};
            font-size: 10pt;
            color: {style_config['secondary_color']};
            text-align: center;
        }}
        
        /* Prevent nested styling issues */
        blockquote blockquote {{
            border: none;
            background: none;
            padding: 8pt;
            margin: 8pt 0;
            font-style: normal;
        }}
        
        /* Remove any special styling from conclusion paragraphs */
        .conclusion-content,
        .conclusion-content p {{
            background: none !important;
            border: none !important;
            padding: 0 !important;
            margin: 12pt 0 !important;
            font-style: normal !important;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                margin: 0;
                padding: 0.5in;
            }}
            
            .no-print {{
                display: none;
            }}
        }}
        
        /* Responsive design */
        @media screen and (max-width: 768px) {{
            body {{
                padding: 12pt;
                font-size: 11pt;
            }}
            
            .memo-to-from {{
                grid-template-columns: 1fr;
                gap: 12pt;
            }}
        }}
    </style>
    """
    
    # Generate complete HTML document
    current_date = datetime.now().strftime("%B %d, %Y")
    customer_name = contract_data.get('customer_name', 'Contract Analysis') if contract_data else 'Contract Analysis'
    
    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASC 606 Analysis: {customer_name}</title>
    {professional_css}
</head>
<body>
    {html_content}
    
    <div class="memo-footer">
        <p>Generated by Controller.cpa ASC 606 Analysis Platform | {current_date}</p>
        <p class="no-print">This document is optimized for printing and professional review.</p>
    </div>
</body>
</html>"""
    
    return html_document

def create_pdf_from_html(html_content: str, filename: str = "asc606_memo.pdf") -> bytes:
    """
    Generate PDF from HTML using WeasyPrint - eliminates Unicode issues
    
    Args:
        html_content: Complete HTML document string
        filename: Desired filename (for reference only)
    
    Returns:
        PDF document as bytes
        
    Raises:
        ValueError: If HTML content is invalid or PDF generation fails
    """
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        # Validate input
        if not html_content or not html_content.strip():
            raise ValueError("Empty HTML content provided")
        
        # Configure font handling for better Unicode support
        font_config = FontConfiguration()
        
        # Generate PDF from HTML
        pdf_bytes = HTML(string=html_content).write_pdf(
            font_config=font_config,
            optimize_size=('fonts', 'images')
        )
        
        return pdf_bytes
        
    except ImportError:
        raise ValueError("WeasyPrint not installed. Please install with: pip install weasyprint")
    except Exception as e:
        raise ValueError(f"PDF generation failed: {e}")

def create_html_download_link(html_content: str, filename: str = "asc606_memo.html") -> str:
    """
    Create a base64 encoded download link for HTML content
    
    Args:
        html_content: The complete HTML document
        filename: Desired filename for download
    
    Returns:
        Base64 encoded download URL
    """
    # Encode HTML content
    html_bytes = html_content.encode('utf-8')
    b64_html = base64.b64encode(html_bytes).decode()
    
    # Create download URL
    download_url = f"data:text/html;base64,{b64_html}"
    return download_url

def enhance_markdown_for_display(memo_markdown: str) -> str:
    """
    Enhance markdown content for better Streamlit display - NO EMOJIS for professional memos
    
    Args:
        memo_markdown: Raw markdown content
    
    Returns:
        Enhanced markdown with better formatting (professional, no emojis)
        
    Raises:
        ValueError: If input is empty
    """
    if not memo_markdown or not memo_markdown.strip():
        raise ValueError("Empty markdown content provided")
    
    try:
        # Professional formatting without emojis
        enhanced = memo_markdown
        
        # Clean citation formatting (no emojis)
        enhanced = enhanced.replace('**[CITATION]', '**[CITATION]')
        enhanced = enhanced.replace('[/CITATION]**', '[/CITATION]**')
        
        # Clean quote formatting (no emojis)
        enhanced = enhanced.replace('> [QUOTE]', '> **Contract Quote:**')
        enhanced = enhanced.replace('[/QUOTE]', '')
        
        # Add visual separators
        enhanced = enhanced.replace('---', '\n---\n')
        
        return enhanced
        
    except Exception as e:
        raise ValueError(f"Markdown enhancement failed: {e}")