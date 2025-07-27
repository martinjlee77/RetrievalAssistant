"""
LLM Utilities - Following Streamlit Best Practices
Handles OpenAI API calls, error handling, caching, and file conversion utilities
"""
import os
import streamlit as st
from openai import OpenAI
from typing import Dict, List, Any, Optional, Union, cast
import json
import time
import io
from docx import Document
from fpdf import FPDF

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    """Initialize and cache OpenAI client"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please check your secrets configuration.")
        st.stop()
    return OpenAI(api_key=api_key)

def make_llm_call(
    messages: List[Dict[str, str]], 
    model: str = "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
    temperature: float = 0.3,
    response_format: Optional[Dict[str, Any]] = None,
    max_tokens: Optional[int] = None
) -> Optional[str]:
    """
    Make LLM API call with error handling and rate limiting
    Following Streamlit best practices for API management
    """
    client = get_openai_client()
    
    try:
        with st.spinner("Analyzing with AI..."):
            # Cast messages to proper type for OpenAI
            openai_messages = cast(List[Any], messages)
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
            }
            
            # Add optional parameters if provided
            if response_format:
                request_params["response_format"] = response_format
            if max_tokens:
                request_params["max_tokens"] = max_tokens
                
            response = client.chat.completions.create(**request_params)
        return response.choices[0].message.content
    
    except Exception as e:
        handle_llm_error(e)
        return None

def handle_llm_error(error: Exception):
    """Handle LLM API errors with user-friendly messages"""
    error_message = str(error).lower()
    
    if "rate limit" in error_message:
        st.error("⏱️ API rate limit reached. Please wait a moment and try again.")
    elif "quota" in error_message or "billing" in error_message:
        st.error("💳 API quota exceeded. Please check your OpenAI billing settings.")
    elif "invalid api key" in error_message or "unauthorized" in error_message:
        st.error("🔑 Invalid API key. Please check your OpenAI API key configuration.")
    elif "context length" in error_message or "token" in error_message:
        st.error("📄 Content too long. Please try with a shorter document or input.")
    else:
        st.error(f"🚫 AI service error: {str(error)}")
    
    # Log error for debugging (in production, send to logging service)
    if st.session_state.get("debug_mode", False):
        st.write(f"Debug info: {error}")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cached_llm_call(
    prompt: str, 
    system_message: str = None,
    model: str = "gpt-4o",
    temperature: float = 0.3
) -> Optional[str]:
    """
    Cached LLM call for frequently requested analysis
    Follows Streamlit best practices for caching expensive operations
    """
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    
    result = make_llm_call(messages, model, temperature)
    return result if result else ""

def stream_llm_response(
    messages: List[Dict[str, str]], 
    model: str = "gpt-4o",
    temperature: float = 0.3
):
    """
    Stream LLM response for real-time display
    Uses st.write_stream for token-by-token display
    """
    client = get_openai_client()
    
    try:
        # Cast messages to proper type for OpenAI
        openai_messages = cast(List[Any], messages)
        response = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            stream=True
        )
        
        def response_generator():
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        
        return st.write_stream(response_generator())
    
    except Exception as e:
        handle_llm_error(e)
        return None

def get_model_options() -> Dict[str, str]:
    """Get available model options for debugging UI"""
    return {
        "GPT-4o (Latest)": "gpt-4o",
        "GPT-4o Mini": "gpt-4o-mini",
        "GPT-4 Turbo": "gpt-4-turbo-preview"
    }

def create_debug_sidebar():
    """
    Create debugging sidebar for prompt engineering
    Following Streamlit best practices for experimentation
    """
    with st.sidebar:
        st.subheader("🔧 AI Debug Controls")
        
        model_options = get_model_options()
        selected_model = st.selectbox(
            "Model",
            options=list(model_options.keys()),
            index=0
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.3,
            step=0.1,
            help="Higher values make output more creative but less focused"
        )
        
        max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=2000,
            step=100,
            help="Maximum response length"
        )
        
        return {
            "model": model_options[selected_model],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

def validate_api_key() -> bool:
    """Validate OpenAI API key is properly configured"""
    try:
        client = get_openai_client()
        # Test with minimal API call
        openai_messages = cast(List[Any], [{"role": "user", "content": "test"}])
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=openai_messages,
            max_tokens=5
        )
        return True
    except Exception:
        return False

def create_docx_from_text(text_content, contract_data=None):
    """Creates a professional accounting memo in DOCX format with full Big 4 standards."""
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.shared import OxmlElement, qn
    from datetime import datetime
    import re
    
    document = Document()
    
    # === PHASE 1: PROFESSIONAL DOCUMENT STRUCTURE ===
    
    # Set default font to Times New Roman 12pt (accounting standard)
    style = document.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    
    # Configure paragraph spacing (6pt after paragraphs)
    paragraph_format = style.paragraph_format
    paragraph_format.space_after = Pt(6)
    paragraph_format.line_spacing = 1.15
    
    # Set standard accounting memo margins (1" all sides)
    sections = document.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Add header with Controller.cpa branding
    header = document.sections[0].header
    header_para = header.paragraphs[0]
    header_para.text = "Controller.cpa"
    header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header_para.runs[0]
    header_run.font.name = 'Times New Roman'
    header_run.font.size = Pt(10)
    header_run.font.color.rgb = RGBColor(70, 70, 70)
    
    # Add footer with page numbers
    footer = document.sections[0].footer
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_para.runs[0] if footer_para.runs else footer_para.add_run()
    footer_run.font.name = 'Times New Roman'
    footer_run.font.size = Pt(10)
    # Add page number field
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.text = "PAGE"
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    footer_run._r.append(fldChar1)
    footer_run._r.append(instrText)
    footer_run._r.append(fldChar2)
    
    # === PROFESSIONAL MEMO HEADER ===
    
    # Main title
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title.add_run("TECHNICAL ACCOUNTING MEMORANDUM")
    title_run.font.name = 'Times New Roman'
    title_run.font.size = Pt(16)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0, 51, 102)  # Professional blue
    
    document.add_paragraph()  # Spacing
    
    # Professional memo header table
    header_table = document.add_table(rows=4, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    header_table.style = 'Table Grid'
    
    # Configure table width
    header_table.columns[0].width = Inches(1.2)
    header_table.columns[1].width = Inches(5.8)
    
    # Header content
    current_date = datetime.now().strftime("%B %d, %Y")
    analyst_name = "ASC 606 AI Analyst"
    
    memo_data = [
        ("TO:", "Technical Accounting Team / Management"),
        ("FROM:", analyst_name),
        ("DATE:", current_date),
        ("SUBJECT:", f"ASC 606 Revenue Recognition Analysis")
    ]
    
    if contract_data:
        memo_data[3] = ("SUBJECT:", f"ASC 606 Analysis: {getattr(contract_data, 'analysis_title', 'Contract Analysis')}")
        if hasattr(contract_data, 'memo_audience'):
            memo_data[0] = ("TO:", contract_data.memo_audience)
    
    for i, (label, content) in enumerate(memo_data):
        row = header_table.rows[i]
        label_cell = row.cells[0]
        content_cell = row.cells[1]
        
        # Format label cell
        label_para = label_cell.paragraphs[0]
        label_run = label_para.add_run(label)
        label_run.font.name = 'Times New Roman'
        label_run.font.size = Pt(11)
        label_run.font.bold = True
        
        # Format content cell
        content_para = content_cell.paragraphs[0]
        content_run = content_para.add_run(content)
        content_run.font.name = 'Times New Roman'
        content_run.font.size = Pt(11)
    
    document.add_paragraph()  # Spacing after header
    
    # === PHASE 2: CONTENT PARSING AND FORMATTING ===
    
    # Parse and format the memo content
    _parse_and_format_memo_content(document, text_content)
    
    # === PHASE 3: AUDIT-READY FEATURES ===
    
    # Add document metadata section
    document.add_page_break()
    
    metadata_heading = document.add_paragraph()
    metadata_run = metadata_heading.add_run("DOCUMENT METADATA")
    metadata_run.font.name = 'Times New Roman'
    metadata_run.font.size = Pt(14)
    metadata_run.font.bold = True
    metadata_run.font.color.rgb = RGBColor(0, 51, 102)
    
    metadata_table = document.add_table(rows=5, cols=2)
    metadata_table.style = 'Table Grid'
    metadata_table.columns[0].width = Inches(2)
    metadata_table.columns[1].width = Inches(5)
    
    metadata_info = [
        ("Document Version:", "Final"),
        ("Analysis Date:", current_date),
        ("Analyst:", analyst_name),
        ("Review Status:", "Pending Management Review"),
        ("File Classification:", "Internal Accounting Analysis")
    ]
    
    for i, (label, content) in enumerate(metadata_info):
        row = metadata_table.rows[i]
        row.cells[0].text = label
        row.cells[1].text = content
        
        # Format cells
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(10)
    
    # Add signature section
    document.add_paragraph()
    signature_para = document.add_paragraph()
    signature_run = signature_para.add_run("ANALYST CERTIFICATION")
    signature_run.font.name = 'Times New Roman'
    signature_run.font.size = Pt(12)
    signature_run.font.bold = True
    
    cert_text = document.add_paragraph()
    cert_run = cert_text.add_run(
        "I certify that this analysis has been prepared in accordance with ASC 606 "
        "requirements and represents my professional judgment based on the contract "
        "documentation provided and applicable authoritative guidance."
    )
    cert_run.font.name = 'Times New Roman'
    cert_run.font.size = Pt(11)
    cert_run.font.italic = True
    
    # Signature line
    document.add_paragraph()
    sig_line = document.add_paragraph()
    sig_line.add_run("_" * 50)
    sig_name = document.add_paragraph()
    sig_name.add_run(f"{analyst_name}, Technical Accounting")
    
    bio = io.BytesIO()
    document.save(bio)
    bio.seek(0)
    return bio.getvalue()

def create_pdf_from_text(text_content, title="", contract_data=None):
    """Creates a professional accounting memo in PDF format with Big 4 standards."""
    from fpdf import FPDF
    from datetime import datetime
    import re
    
    class ProfessionalMemo(FPDF):
        def header(self):
            """Add header to each page"""
            self.set_font('Arial', 'I', 10)  # Arial supports Unicode better
            self.set_text_color(70, 70, 70)
            self.cell(0, 10, 'Controller.cpa', 0, 0, 'R')
            self.ln(15)
        
        def footer(self):
            """Add footer with page numbers"""
            self.set_y(-15)
            self.set_font('Arial', 'I', 10)
            self.set_text_color(70, 70, 70)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    pdf = ProfessionalMemo()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # === PROFESSIONAL MEMO HEADER ===
    
    # Main title
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 51, 102)  # Professional blue
    pdf.cell(0, 15, 'TECHNICAL ACCOUNTING MEMORANDUM', 0, 1, 'C')
    pdf.ln(5)
    
    # Reset color for body text
    pdf.set_text_color(0, 0, 0)
    
    # Memo header information
    current_date = datetime.now().strftime("%B %d, %Y")
    analyst_name = "ASC 606 AI Analyst"
    
    memo_info = [
        ("TO:", "Technical Accounting Team / Management"),
        ("FROM:", analyst_name),
        ("DATE:", current_date),
        ("SUBJECT:", "ASC 606 Revenue Recognition Analysis")
    ]
    
    if contract_data:
        memo_info[3] = ("SUBJECT:", f"ASC 606 Analysis: {getattr(contract_data, 'analysis_title', 'Contract Analysis')}")
        if hasattr(contract_data, 'memo_audience'):
            memo_info[0] = ("TO:", contract_data.memo_audience)
    
    # Header table simulation with consistent spacing
    pdf.set_font('Arial', '', 11)
    for label, content in memo_info:
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(25, 8, label, 0, 0, 'L')
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 8, content, 0, 1, 'L')
    
    pdf.ln(8)
    
    # === CONTENT FORMATTING ===
    
    # Parse content and apply formatting
    _parse_and_format_pdf_content(pdf, text_content)
    
    # === DOCUMENT METADATA PAGE ===
    
    pdf.add_page()
    
    # Metadata section
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, 'DOCUMENT METADATA', 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 11)
    
    metadata_info = [
        ("Document Version:", "Final"),
        ("Analysis Date:", current_date),
        ("Analyst:", analyst_name),
        ("Review Status:", "Pending Management Review"),
        ("File Classification:", "Internal Accounting Analysis")
    ]
    
    for label, content in metadata_info:
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(50, 8, label, 0, 0, 'L')
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 8, content, 0, 1, 'L')
    
    # Certification section
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'ANALYST CERTIFICATION', 0, 1, 'L')
    
    pdf.set_font('Arial', 'I', 11)
    certification_text = (
        "I certify that this analysis has been prepared in accordance with ASC 606 "
        "requirements and represents my professional judgment based on the contract "
        "documentation provided and applicable authoritative guidance."
    )
    pdf.multi_cell(0, 6, certification_text)
    
    # Signature line
    pdf.ln(10)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, '_' * 50, 0, 1, 'L')
    pdf.cell(0, 8, f'{analyst_name}, Technical Accounting', 0, 1, 'L')
    
    return pdf.output(dest='S')

def _parse_and_format_memo_content(document, text_content):
    """Parse LLM memo content and apply professional formatting to DOCX"""
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import re
    
    lines = text_content.split('\n')
    current_section = None
    toc_entries = []  # For table of contents
    section_number = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # === EXECUTIVE SUMMARY SPECIAL FORMATTING ===
        if 'executive summary' in line.lower() and ('##' in line or line.isupper()):
            para = document.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            # Add executive summary in highlighted box
            run = para.add_run("EXECUTIVE SUMMARY")
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 51, 102)
            
            # Add to TOC
            toc_entries.append((section_number, "Executive Summary"))
            section_number += 1
            continue
            
        # === MAIN SECTION HEADERS (##) ===
        if line.startswith('##') or (line.isupper() and len(line) > 10 and line.replace(' ', '').isalpha()):
            header_text = line.replace('#', '').strip()
            
            para = document.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            # Section numbering
            numbered_header = f"{section_number}. {header_text.upper()}"
            run = para.add_run(numbered_header)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 51, 102)
            
            # Add to TOC
            toc_entries.append((section_number, header_text))
            section_number += 1
            continue
            
        # === SUB-SECTION HEADERS (###) ===
        if line.startswith('###'):
            sub_header_text = line.replace('#', '').strip()
            
            para = document.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            run = para.add_run(sub_header_text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(51, 51, 51)
            continue
            
        # === SEMANTIC MARKER PARSING (ROBUST) ===
        # Contract quotes with semantic markers
        if line.startswith('[QUOTE]') and line.endswith('[/QUOTE]'):
            quote_text = line[7:-8]  # Remove [QUOTE] and [/QUOTE]
            para = document.add_paragraph()
            para.left_indent = Pt(36)  # Indent contract quotes
            para.right_indent = Pt(18)
            
            run = para.add_run(quote_text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(11)
            run.font.italic = True
            run.font.color.rgb = RGBColor(51, 51, 51)
            continue
            
        # ASC citations with semantic markers
        if line.startswith('[CITATION]') and line.endswith('[/CITATION]'):
            citation_text = line[10:-12]  # Remove [CITATION] and [/CITATION]
            para = document.add_paragraph()
            
            run = para.add_run(citation_text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0, 102, 51)  # Green for citations
            continue
            
        # === FALLBACK HEURISTIC PARSING (BACKUP) ===
        # Keep fallback for backwards compatibility, but semantic markers take priority
        if ('contract states' in line.lower() or 'agreement provides' in line.lower() or 
            line.startswith('"')) and not line.startswith('['):
            para = document.add_paragraph()
            para.left_indent = Pt(36)
            para.right_indent = Pt(18)
            
            run = para.add_run(line)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(11)
            run.font.italic = True
            run.font.color.rgb = RGBColor(51, 51, 51)
            continue
            
        if ('asc 606' in line.lower() or 'asc-606' in line.lower()) and not line.startswith('['):
            para = document.add_paragraph()
            
            # Find and highlight ASC citations
            citation_pattern = r'(ASC\s*606[-\s]\d{2}[-\s]\d{2}[-\s]\d{1,2})'
            
            parts = re.split(citation_pattern, line, flags=re.IGNORECASE)
            for i, part in enumerate(parts):
                run = para.add_run(part)
                run.font.name = 'Times New Roman'
                run.font.size = Pt(12)
                
                # Highlight ASC citations
                if re.match(citation_pattern, part, re.IGNORECASE):
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0, 102, 51)
            continue
            
        # === BULLET POINTS ===
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            para = document.add_paragraph()
            para.style = 'List Bullet'
            
            bullet_text = line[1:].strip() if line[0] in ['•', '-', '*'] else line
            run = para.add_run(bullet_text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            continue
            
        # === FINANCIAL TABLES ===
        if '$' in line and ('|' in line or '\t' in line):
            # Simple table parsing for financial data
            table_data = line.split('|') if '|' in line else line.split('\t')
            if len(table_data) > 1:
                table = document.add_table(rows=1, cols=len(table_data))
                table.style = 'Table Grid'
                
                for i, cell_data in enumerate(table_data):
                    cell = table.cell(0, i)
                    cell.text = cell_data.strip()
                    
                    # Format financial numbers
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.name = 'Times New Roman'
                            run.font.size = Pt(11)
                            if '$' in cell_data:
                                run.font.bold = True
                continue
                
        # === REGULAR PARAGRAPHS ===
        para = document.add_paragraph()
        
        # Apply bold formatting for **text**
        bold_pattern = r'\*\*(.*?)\*\*'
        parts = re.split(bold_pattern, line)
        
        for i, part in enumerate(parts):
            run = para.add_run(part)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            
            # Make every other part bold (the captured groups)
            if i % 2 == 1:
                run.font.bold = True
    
    # === TABLE OF CONTENTS REMOVED ===
    # Following Gemini's feedback: TOC placement at document end is incorrect
    # Professional accounting memos typically don't require TOC for documents under 10 pages
    # Removed complex TOC logic to maintain clean, reliable output

def _parse_and_format_pdf_content(pdf, text_content):
    """Parse LLM memo content and apply professional formatting to PDF"""
    import re
    
    lines = text_content.split('\n')
    section_number = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # === MAIN SECTION HEADERS ===
        if line.startswith('##') or (line.isupper() and len(line) > 10 and line.replace(' ', '').isalpha()):
            header_text = line.replace('#', '').strip()
            
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(0, 51, 102)
            
            numbered_header = f"{section_number}. {header_text.upper()}"
            pdf.cell(0, 12, numbered_header, 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            section_number += 1
            continue
            
        # === SUB-SECTION HEADERS ===
        if line.startswith('###'):
            sub_header_text = line.replace('#', '').strip()
            
            pdf.ln(3)
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(51, 51, 51)
            pdf.cell(0, 10, sub_header_text, 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            continue
            
        # === SEMANTIC MARKER PARSING (ROBUST) ===
        # Contract quotes with semantic markers
        if line.startswith('[QUOTE]') and line.endswith('[/QUOTE]'):
            quote_text = line[7:-8]  # Remove [QUOTE] and [/QUOTE]
            pdf.set_font('Arial', 'I', 11)
            pdf.set_text_color(51, 51, 51)
            pdf.ln(3)
            pdf.cell(20, 6, '', 0, 0)  # Indent using cell instead of margin
            pdf.multi_cell(0, 6, quote_text)
            pdf.set_text_color(0, 0, 0)
            continue
            
        # ASC citations with semantic markers  
        if line.startswith('[CITATION]') and line.endswith('[/CITATION]'):
            citation_text = line[10:-12]  # Remove [CITATION] and [/CITATION]
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(0, 102, 51)  # Green for citations
            pdf.multi_cell(0, 6, citation_text)
            pdf.set_text_color(0, 0, 0)
            continue
            
        # === FALLBACK HEURISTIC PARSING (BACKUP) ===
        # ASC citations (fallback)
        if ('asc 606' in line.lower()) and not line.startswith('['):
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(0, 102, 51)  # Green for citations
            pdf.multi_cell(0, 6, line)
            pdf.set_text_color(0, 0, 0)
            continue
            
        # Contract quotes (fallback)
        if (line.startswith('"') or 'contract states' in line.lower()) and not line.startswith('['):
            pdf.set_font('Arial', 'I', 11)
            pdf.set_text_color(51, 51, 51)
            pdf.ln(3)
            pdf.cell(20, 6, '', 0, 0)  # Indent using cell instead of margin
            pdf.multi_cell(0, 6, line)
            pdf.set_text_color(0, 0, 0)
            continue
            
        # === BULLET POINTS ===
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            bullet_text = line[1:].strip() if line[0] in ['•', '-', '*'] else line
            pdf.set_font('Arial', '', 11)
            pdf.cell(15, 6, '- ', 0, 0, 'L')  # Use dash instead of bullet
            pdf.multi_cell(0, 6, bullet_text)
            continue
            
        # === REGULAR PARAGRAPHS ===
        pdf.set_font('Arial', '', 11)
        
        # Handle bold text **text**
        if '**' in line:
            # Simple bold handling for PDF
            line = line.replace('**', '')
            pdf.set_font('Arial', 'B', 11)
            pdf.multi_cell(0, 6, line)
            pdf.set_font('Arial', '', 11)
        else:
            pdf.multi_cell(0, 6, line)
        
        pdf.ln(2)  # Small spacing between paragraphs

def get_knowledge_base():
    """Get or initialize the ASC 606 knowledge base (consolidated from legacy file)"""
    # Import here to avoid circular imports
    import chromadb
    from chromadb.config import Settings
    import os
    
    persist_directory = "asc606_knowledge_base"
    
    try:
        client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        import chromadb.utils.embedding_functions as embedding_functions
        collection = client.get_or_create_collection(
            name="asc606_paragraphs",
            metadata={"description": "ASC 606 paragraphs with metadata filtering"},
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
        )
        return collection
    except Exception as e:
        st.error(f"Failed to load knowledge base: {e}")
        return None

def extract_contract_terms(
    client: OpenAI,
    contract_text: str, 
    step_context: str
) -> List[str]:
    """
    Extract contract-specific terms relevant to a particular ASC 606 step
    This makes semantic search more precise and adaptable
    """
    step_descriptions = {
        "contract_identification": "contract formation, enforceability, legal validity, agreement terms",
        "performance_obligations": "deliverables, services, goods, obligations, commitments, work to be performed",
        "transaction_price": "payment terms, pricing, fees, consideration, amounts, variable payments",
        "price_allocation": "allocation methods, relative values, standalone prices, bundling",
        "revenue_recognition": "timing, milestones, completion, transfer of control, satisfaction"
    }
    
    description = step_descriptions.get(step_context, "relevant contract terms")
    
    prompt = f"""Extract 5-7 key terms from this contract that are most relevant to {description}.

Focus on:
- Specific terminology used in this contract (not generic accounting terms)
- Industry-specific language
- Unique aspects of this arrangement
- Terms that would help find relevant ASC 606 guidance

Contract text:
{contract_text[:2000]}...

Return only the terms as a comma-separated list, no explanations."""

    try:
        openai_messages = cast(List[Any], [{"role": "user", "content": prompt}])
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,
            max_tokens=100,
            temperature=0.1
        )
        
        if response.choices[0].message.content:
            terms_text = response.choices[0].message.content.strip()
            terms = [term.strip() for term in terms_text.split(',')]
            return terms[:7]  # Limit to 7 terms max
        return []
        
    except Exception as e:
        st.warning(f"Could not extract contract terms: {e}")
        return []

# Removed: query_knowledge_base function replaced by KnowledgeBaseManager.search_relevant_guidance

def create_debug_sidebar_advanced() -> Dict[str, Any]:
    """Create debugging controls in sidebar for development"""
    with st.sidebar.expander("🔧 Debug Controls", expanded=False):
        st.markdown("**AI Model Settings**")
        
        model = st.selectbox(
            "Model",
            ["gpt-4o", "gpt-4o-mini", "gpt-4"],
            index=0,
            help="Choose AI model for analysis"
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="Controls creativity vs consistency"
        )
        
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=2000,
            step=100,
            help="Maximum response length"
        )
        
        st.markdown("**Development Tools**")
        
        debug_mode = st.checkbox(
            "Debug Mode",
            value=st.session_state.get("debug_mode", False),
            help="Show additional debugging information"
        )
        
        show_prompts = st.checkbox(
            "Show AI Prompts",
            value=st.session_state.get("show_prompts", False),
            help="Display prompts sent to AI"
        )
        
        show_raw_response = st.checkbox(
            "Show Raw AI Response",
            value=st.session_state.get("show_raw_response", False),
            help="Display unformatted AI responses"
        )
        
        # Store in session state
        st.session_state.debug_mode = debug_mode
        st.session_state.show_prompts = show_prompts
        st.session_state.show_raw_response = show_raw_response
        
        return {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "debug_mode": debug_mode,
            "show_prompts": show_prompts,
            "show_raw_response": show_raw_response
        }