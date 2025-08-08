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
from functools import lru_cache

def _preprocess_markdown_for_html(memo_markdown: str) -> str:
    """
    ENHANCED: Comprehensive preprocessing for all HTML formatting fixes.
    Finds custom semantic tags and fixes all user-identified formatting issues.

    This function should run BEFORE the main markdown2 conversion.
    
    Args:
        memo_markdown: Raw markdown content with custom semantic tags
        
    Returns:
        Processed markdown with all formatting fixes applied
    """
    processed_text = memo_markdown

    # === CRITICAL HTML FORMATTING FIXES ===
    
    # 1. DOCUMENT TITLE
    processed_text = re.sub(r'^(#\s*)?TECHNICAL ACCOUNTING MEMORANDUM', '# TECHNICAL ACCOUNTING MEMORANDUM', processed_text, flags=re.MULTILINE)
    
    # 2. EXECUTIVE SUMMARY NUMBERING FIX - Remove "1." and "2." before subsections
    processed_text = re.sub(r'^1\.\s*EXECUTIVE SUMMARY', 'EXECUTIVE SUMMARY', processed_text, flags=re.MULTILINE)
    processed_text = re.sub(r'^1\.\s*(Overall Conclusion|KEY FINDINGS)', r'\1', processed_text, flags=re.MULTILINE)
    processed_text = re.sub(r'^2\.\s*(Overall Conclusion|KEY FINDINGS)', r'\1', processed_text, flags=re.MULTILINE)
    
    # 3. SUB-BULLET INDENTATION FIX - Convert to proper HTML structure
    lines = processed_text.split('\n')
    fixed_lines = []
    in_key_findings = False
    
    for line in lines:
        stripped = line.strip()
        
        # Track KEY FINDINGS section
        if 'KEY FINDINGS' in stripped:
            in_key_findings = True
            fixed_lines.append(line)
            continue
        elif stripped.startswith('##') or stripped.startswith('2.') or stripped.startswith('3.'):
            in_key_findings = False
        
        # Fix sub-bullet indentation in KEY FINDINGS
        if in_key_findings and stripped:
            if any(keyword in stripped for keyword in ['ASC 606 Contract Exists:', 'Performance Obligations:', 'Transaction Price:', 'Allocation:', 'Revenue Recognition:', 'Critical Judgments:']):
                fixed_lines.append('* ' + stripped.lstrip('•*- ').strip())
            elif any(keyword in stripped for keyword in ['License:', 'Provisioning:', 'Services:', 'Over Time', 'Point in Time', 'Estimating', 'Determining']) and not line.startswith('    '):
                fixed_lines.append('    * ' + stripped.lstrip('•*- ◦').strip())
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    processed_text = '\n'.join(fixed_lines)
    
    # 4. DUPLICATE HEADER REMOVAL - Remove "Financial Impact" duplicates
    processed_text = re.sub(r'Financial Impact\s*\n\s*(?=.*FINANCIAL IMPACT)', '', processed_text, flags=re.IGNORECASE)
    
    # 5. CONCLUSION HEADER FIX - Fix "6. CONCLUSION" formatting
    processed_text = re.sub(r'6\.\s*CONCLUSION\s*\n\s*\n', '## CONCLUSION\n\n', processed_text)
    processed_text = re.sub(r'## 6\. CONCLUSION', '## CONCLUSION', processed_text)
    
    # 6. HORIZONTAL LINE NORMALIZATION - Make consistent
    processed_text = re.sub(r'^-{3,}$', '---', processed_text, flags=re.MULTILINE)
    
    # === ORIGINAL SEMANTIC TAG PROCESSING ===
    
    # Convert [QUOTE]Your quote text[/QUOTE] to <blockquote>Your quote text</blockquote>
    processed_text = re.sub(
        r'\[QUOTE\](.*?)\[/QUOTE\]', 
        r'<blockquote>\1</blockquote>', 
        processed_text, 
        flags=re.DOTALL
    )

    # Convert [CITATION]Your citation text[/CITATION] to <span class="citation">...</span>
    processed_text = re.sub(
        r'\[CITATION\](.*?)\[/CITATION\]', 
        r'<span class="citation">\1</span>', 
        processed_text,
        flags=re.DOTALL
    )

    return processed_text

@lru_cache(maxsize=1)
def get_style_config() -> Dict[str, str]:
    """
    Configuration-driven styling for professional memos
    CACHED: This function is expensive to compute and rarely changes
    
    Returns:
        Dictionary containing all styling parameters
    """
    return {
        'font_family': 'system-ui, -apple-system, sans-serif',  # Default system fonts
        'font_size': '12pt',
        'page_width': '8.5in',
        'margins': '1in',
        'primary_color': '#000000',  # Black for all headers and text
        'secondary_color': '#000000',  # Black for consistency
        'border_color': '#000000',
        'line_height': '1.6',
        'header_size': '16pt',
        'subheader_size': '14pt',
        'memo_title_size': '18pt',  # Larger title for memo header
        'consistent_spacing': '12pt'  # Consistent spacing between sections
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
        body {{
            font-family: {style_config['font_family']};
            font-size: {style_config['font_size']};
            line-height: {style_config['line_height']};
            max-width: {style_config['page_width']};
            margin: 0 auto;
            padding: {style_config['margins']};
            background: white;
            color: #000;
        }}
        
        /* Header styling - all black, no colors */
        h1 {{
            font-size: {style_config['header_size']};
            font-weight: bold;
            text-align: center;
            margin-bottom: 24pt;
            color: #000000;
        }}
        
        h2 {{
            font-size: {style_config['subheader_size']};
            font-weight: bold;
            margin-top: 24pt;
            margin-bottom: 12pt;
            color: #000000;
        }}
        
        h3 {{
            font-size: {style_config['font_size']};
            font-weight: bold;
            margin-top: 12pt;
            margin-bottom: 6pt;
            color: #000000;
        }}
        
        /* Enhanced subsection headers - all black */
        .subsection-header {{
            font-size: 11pt;
            font-weight: bold;
            text-transform: uppercase;
            color: #000000;
            margin-top: 16pt;
            margin-bottom: 8pt;
            letter-spacing: 0.5px;
        }}
        
        /* Paragraph and text styling */
        p {{
            margin-bottom: 12pt;
            text-align: justify;
        }}
        
        /* Citation and quote styling - PROFESSIONAL MEMO STANDARDS */
        blockquote {{
            font-family: {style_config['font_family']};
            font-style: italic;
            font-size: {style_config['font_size']};
            color: #000000;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 3px;
            padding: 4pt 8pt;
            margin: 8pt 0;
        }}
        
        .citation {{
            font-weight: bold;
            font-style: normal;
            color: #000000;
            background-color: #f0f4f8;
            padding: 1px 4px;
            border-radius: 2px;
            font-size: 1em;
        }}
        
        /* Table styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
        }}
        
        th, td {{
            border: 1px solid {style_config['border_color']};
            padding: 10pt;
            text-align: left;
        }}
        
        th {{
            background-color: white;
            color: black;
            font-weight: bold;
            text-align: center;
            font-family: 'Segoe UI', sans-serif;
        }}
        
        /* Alternating row colors */
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        tr:nth-child(odd) {{
            background-color: white;
        }}
        
        /* List styling - Fix bullet icons and sub-bullets */
        ul {{
            margin: 12pt 0;
            padding-left: 24pt;
            list-style-type: disc;
        }}
        
        /* Sub-bullet indentation */
        ul ul {{
            margin: 6pt 0;
            padding-left: 20pt;
            list-style-type: circle;
        }}
        
        /* Third level bullets */
        ul ul ul {{
            padding-left: 20pt;
            list-style-type: square;
        }}
        
        ol {{
            margin: 12pt 0;
            padding-left: 24pt;
            list-style-type: decimal;
        }}
        
        li {{
            margin-bottom: 6pt;
            display: list-item;
        }}
        
        /* Memo header - remove color borders */
        .memo-header {{
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
            font-size: 10pt;
            color: #000000;
            text-align: center;
        }}
        
        /* Horizontal line consistency - add after each section */
        hr {{
            border: none;
            border-top: 1px solid #dee2e6;
            margin: 24pt 0;
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
    # Safe access to contract data fields
    if contract_data:
        customer_name = getattr(contract_data, 'customer_name', 
                               getattr(contract_data, 'analysis_title', 'Contract Analysis'))
    else:
        customer_name = 'Contract Analysis'
    
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
        <p>Generated by VeritasLogic.ai ASC 606 Analysis Platform | {current_date}</p>
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
        
        if pdf_bytes is None:
            raise ValueError("PDF generation returned None")
        
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

# Function removed - no longer needed with streamlined two-option model
# The "View in Browser" functionality has been replaced with embedded preview

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