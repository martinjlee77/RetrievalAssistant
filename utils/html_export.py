"""
HTML Export Utility for Professional ASC 606 Memos
Converts markdown memos to clean, professional HTML with Big 4 styling
"""

import markdown2
from datetime import datetime
from typing import Optional, Dict, Any
import base64
import io

def get_style_config() -> Dict[str, str]:
    """
    Configuration-driven styling for professional memos
    
    Returns:
        Dictionary containing all styling parameters
    """
    return {
        'font_family': 'Times New Roman',
        'font_size': '12pt',
        'page_width': '8.5in',
        'margins': '1in',
        'primary_color': '#003366',
        'secondary_color': '#666666',
        'border_color': '#cccccc',
        'line_height': '1.6',
        'header_size': '16pt',
        'subheader_size': '14pt'
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
    
    # Convert markdown to HTML with error handling
    try:
        html_content = markdown2.markdown(
            memo_markdown,
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
        
        /* Citation and quote styling */
        blockquote {{
            margin: 12pt 24pt;
            padding: 12pt;
            background-color: #f8f9fa;
            border-left: 4px solid {style_config['primary_color']};
            font-style: italic;
        }}
        
        .citation {{
            font-weight: bold;
            color: {style_config['primary_color']};
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
    <div class="memo-header">
        <h1>Technical Accounting Memorandum</h1>
        <div class="memo-to-from">
            <div>
                <strong>TO:</strong> Technical Accounting Team / Audit File<br>
                <strong>FROM:</strong> ASC 606 AI Analyst<br>
            </div>
            <div>
                <strong>DATE:</strong> {current_date}<br>
                <strong>SUBJECT:</strong> ASC 606 Analysis: {customer_name}
            </div>
        </div>
    </div>
    
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
    Enhance markdown content for better Streamlit display using regex
    
    Args:
        memo_markdown: Raw markdown content
    
    Returns:
        Enhanced markdown with better formatting
        
    Raises:
        ValueError: If input is empty
    """
    import re
    
    if not memo_markdown or not memo_markdown.strip():
        raise ValueError("Empty markdown content provided")
    
    try:
        # Use regex for more precise replacements
        enhanced = re.sub(r'^##\s', '## 📋 ', memo_markdown, flags=re.MULTILINE)
        enhanced = re.sub(r'^###\s', '### ⚖️ ', enhanced, flags=re.MULTILINE)
        
        # Improve citation formatting
        enhanced = enhanced.replace('**[CITATION]', '**📖 [CITATION]')
        enhanced = enhanced.replace('[/CITATION]**', '[/CITATION]**')
        
        # Improve quote formatting  
        enhanced = enhanced.replace('> [QUOTE]', '> 💬 **Contract Quote:**')
        enhanced = enhanced.replace('[/QUOTE]', '')
        
        # Add visual separators
        enhanced = enhanced.replace('---', '\n---\n')
        
        return enhanced
        
    except Exception as e:
        raise ValueError(f"Markdown enhancement failed: {e}")