"""
HTML Export Utility for Professional ASC 606 Memos
Converts markdown memos to clean, professional HTML with Big 4 styling
"""

import markdown2
from datetime import datetime
from typing import Optional
import base64
import io

def convert_memo_to_html(memo_markdown: str, contract_data: Optional[dict] = None) -> str:
    """
    Convert markdown memo to professional HTML with Big 4 styling
    
    Args:
        memo_markdown: The markdown content of the memo
        contract_data: Optional contract data for enhanced metadata
    
    Returns:
        Complete HTML document with professional styling
    """
    
    # Convert markdown to HTML
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
    
    # Professional CSS styling
    professional_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Times+New+Roman:wght@400;700&display=swap');
        
        body {
            font-family: 'Times New Roman', serif;
            font-size: 12pt;
            line-height: 1.6;
            max-width: 8.5in;
            margin: 0 auto;
            padding: 1in;
            background: white;
            color: #000;
        }
        
        /* Header styling */
        h1 {
            font-size: 14pt;
            font-weight: bold;
            text-align: center;
            margin-bottom: 24pt;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        h2 {
            font-size: 13pt;
            font-weight: bold;
            margin-top: 18pt;
            margin-bottom: 12pt;
            border-bottom: 1px solid #000;
            padding-bottom: 3pt;
        }
        
        h3 {
            font-size: 12pt;
            font-weight: bold;
            margin-top: 12pt;
            margin-bottom: 6pt;
        }
        
        /* Paragraph styling */
        p {
            margin-bottom: 6pt;
            text-align: justify;
        }
        
        /* Table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
        }
        
        th, td {
            border: 1px solid #000;
            padding: 6pt;
            text-align: left;
            vertical-align: top;
        }
        
        th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        /* Quote styling */
        blockquote {
            margin: 12pt 0;
            padding: 6pt 12pt;
            border-left: 3px solid #333;
            background-color: #f9f9f9;
            font-style: italic;
        }
        
        /* Citation styling */
        .citation {
            font-weight: bold;
            color: #0066cc;
        }
        
        /* Emphasis styling */
        em {
            font-style: italic;
        }
        
        strong {
            font-weight: bold;
        }
        
        /* List styling */
        ul, ol {
            margin: 6pt 0;
            padding-left: 24pt;
        }
        
        li {
            margin-bottom: 3pt;
        }
        
        /* Professional memo header */
        .memo-header {
            text-align: center;
            margin-bottom: 24pt;
            border-bottom: 2px solid #000;
            padding-bottom: 12pt;
        }
        
        .memo-to-from {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24pt;
            margin: 12pt 0;
        }
        
        /* Footer */
        .memo-footer {
            margin-top: 36pt;
            padding-top: 12pt;
            border-top: 1px solid #ccc;
            font-size: 10pt;
            color: #666;
            text-align: center;
        }
        
        /* Print styles */
        @media print {
            body {
                margin: 0;
                padding: 0.5in;
            }
            
            .no-print {
                display: none;
            }
        }
        
        /* Responsive design */
        @media screen and (max-width: 768px) {
            body {
                padding: 12pt;
                font-size: 11pt;
            }
            
            .memo-to-from {
                grid-template-columns: 1fr;
                gap: 12pt;
            }
        }
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
    Enhance markdown content for better Streamlit display
    
    Args:
        memo_markdown: Raw markdown content
    
    Returns:
        Enhanced markdown with better formatting
    """
    
    # Improve citation formatting
    enhanced = memo_markdown.replace('**[CITATION]', '**📖 [CITATION]')
    enhanced = enhanced.replace('[/CITATION]**', '[/CITATION]**')
    
    # Improve quote formatting  
    enhanced = enhanced.replace('> [QUOTE]', '> 💬 **Contract Quote:**')
    enhanced = enhanced.replace('[/QUOTE]', '')
    
    # Add visual separators
    enhanced = enhanced.replace('---', '\n---\n')
    
    # Improve section headers
    enhanced = enhanced.replace('## ', '## 📋 ')
    enhanced = enhanced.replace('### ', '### ⚖️ ')
    
    return enhanced