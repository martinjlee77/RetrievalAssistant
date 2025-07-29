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
    client,
    prompt: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    model: str = "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
    response_format: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Make LLM API call with error handling and rate limiting
    Following Streamlit best practices for API management
    """
    try:
        with st.spinner("Analyzing with AI..."):
            # Prepare messages format
            messages = [{"role": "user", "content": prompt}]
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
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

def extract_contract_terms(client, contract_text: str, step_context: str = "comprehensive_analysis") -> List[str]:
    """
    Extract key contract terms for enhanced RAG search
    
    Args:
        client: OpenAI client
        contract_text: Full contract text
        step_context: Analysis step context
        
    Returns:
        List of extracted contract terms for semantic search
    """
    try:
        prompt = f"""
        Extract 5-7 key terms and phrases from this contract that would be most relevant for ASC 606 revenue recognition analysis:
        
        CONTRACT TEXT:
        {contract_text[:3000]}...
        
        Focus on:
        - Service/product descriptions
        - Performance obligations
        - Payment terms
        - Contract timing/duration
        - Customer responsibilities
        
        Return only the key terms, one per line, no explanations.
        """
        
        response = make_llm_call(
            client=client,
            prompt=prompt,
            model="gpt-4o-mini",
            max_tokens=200,
            temperature=0.3
        )
        
        if response:
            # Split response into individual terms
            terms = [term.strip() for term in response.split('\n') if term.strip()]
            return terms[:7]  # Limit to 7 terms
        
        return []
        
    except Exception as e:
        st.warning(f"Contract term extraction failed: {e}")
        return []

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
    from docx.oxml.parser import OxmlElement
    from docx.oxml.ns import qn
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
    
    # === PHASE 2: CONTENT PARSING AND FORMATTING (ENHANCED) ===
    # This enhanced parser understands Markdown headings, bold, tables, and lists,
    # and applies the document's pre-defined styles to match HTML output quality.
    
    # Enhanced styles for better formatting
    def configure_heading_styles():
        """Configure custom heading styles to match HTML output"""
        try:
            # Heading 1 - Main sections (matches HTML h2)
            heading1_style = document.styles.add_style('Custom Heading 1', 1)
            heading1_style.font.name = 'Times New Roman'
            heading1_style.font.size = Pt(14)
            heading1_style.font.bold = True
            heading1_style.font.color.rgb = RGBColor(0, 51, 102)
            heading1_style.paragraph_format.space_before = Pt(12)
            heading1_style.paragraph_format.space_after = Pt(6)
        except:
            # Style already exists, get it
            heading1_style = document.styles['Heading 1']
            
        try:
            # Heading 2 - Subsections (matches HTML h3)
            heading2_style = document.styles.add_style('Custom Heading 2', 1)
            heading2_style.font.name = 'Times New Roman'
            heading2_style.font.size = Pt(13)
            heading2_style.font.bold = True
            heading2_style.font.color.rgb = RGBColor(51, 51, 51)
            heading2_style.paragraph_format.space_before = Pt(8)
            heading2_style.paragraph_format.space_after = Pt(4)
        except:
            heading2_style = document.styles['Heading 2']
            
        try:
            # Heading 3 - Sub-subsections
            heading3_style = document.styles.add_style('Custom Heading 3', 1)
            heading3_style.font.name = 'Times New Roman'
            heading3_style.font.size = Pt(12)
            heading3_style.font.bold = True
            heading3_style.paragraph_format.space_before = Pt(6)
            heading3_style.paragraph_format.space_after = Pt(3)
        except:
            heading3_style = document.styles['Heading 3']
    
    configure_heading_styles()
    
    # Preprocess content to handle HTML-like formatting and tables
    def preprocess_content(content):
        """Preprocess content to extract tables and clean formatting"""
        # Extract and store contract overview tables
        table_pattern = r'\|\s*\*\*.*?\*\*\s*\|.*?\|\s*\n(?:\|.*?\|\s*\n)*'
        tables = re.findall(table_pattern, content, re.MULTILINE | re.DOTALL)
        
        # Remove tables from content for now, we'll add them back specially
        for table in tables:
            content = content.replace(table, '\n[TABLE_PLACEHOLDER]\n')
        
        return content, tables
    
    processed_content, extracted_tables = preprocess_content(text_content)
    
    # Split the entire text_content into individual lines for processing
    lines = processed_content.split('\n')
    table_index = 0
    
    # Define helper functions before the main loop
    def _parse_text_formatting(paragraph, text):
        """Parse bold text and other formatting within a paragraph"""
        # Split the line by the bold delimiter '**'
        parts = text.split('**')
        for i, part in enumerate(parts):
            if not part:
                continue # Skip empty strings that can result from splitting
                
            # Text between the delimiters (at odd indices) should be bold
            if i % 2 == 1:
                paragraph.add_run(part).bold = True
            else:
                paragraph.add_run(part)
    
    def _add_contract_table(doc, table_markdown):
        """Add a professional contract overview table to match HTML styling"""
        lines = table_markdown.strip().split('\n')
        if len(lines) < 2:
            return
            
        # Parse table headers and rows
        headers = [cell.strip().strip('|').strip('*').strip() for cell in lines[0].split('|') if cell.strip()]
        
        # Skip separator line, get data rows
        data_rows = []
        for line in lines[2:]:
            if '|' in line:
                row_data = [cell.strip().strip('|').strip('*').strip() for cell in line.split('|') if cell.strip()]
                if row_data:
                    data_rows.append(row_data)
        
        if not headers or not data_rows:
            return
            
        # Create table
        table = doc.add_table(rows=len(data_rows) + 1, cols=len(headers))
        table.style = 'Table Grid'
        
        # Set column widths
        if len(headers) == 2:
            table.columns[0].width = Inches(2.5)
            table.columns[1].width = Inches(4.5)
        
        # Add headers
        header_row = table.rows[0]
        for i, header in enumerate(headers):
            if i < len(header_row.cells):
                cell = header_row.cells[i]
                cell.text = header
                # Format header
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(11)
        
        # Add data rows
        for row_idx, row_data in enumerate(data_rows):
            table_row = table.rows[row_idx + 1]
            for col_idx, cell_data in enumerate(row_data):
                if col_idx < len(table_row.cells):
                    cell = table_row.cells[col_idx]
                    cell.text = cell_data
                    # Format data
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.name = 'Times New Roman'
                            run.font.size = Pt(10)
        
        doc.add_paragraph()  # Add spacing after table

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue  # Skip empty lines to avoid extra paragraphs
            
        # Handle table placeholders
        if stripped_line == '[TABLE_PLACEHOLDER]' and table_index < len(extracted_tables):
            _add_contract_table(document, extracted_tables[table_index])
            table_index += 1
            continue
        
        # Handle headings by checking the start of the line
        if stripped_line.startswith('# '):
            # Use custom 'Heading 1' style for main sections
            try:
                document.add_paragraph(stripped_line.lstrip('# ').strip(), style='Custom Heading 1')
            except:
                document.add_paragraph(stripped_line.lstrip('# ').strip(), style='Heading 1')
        elif stripped_line.startswith('## '):
            # Use custom 'Heading 2' style for subsections
            try:
                document.add_paragraph(stripped_line.lstrip('## ').strip(), style='Custom Heading 2')
            except:
                document.add_paragraph(stripped_line.lstrip('## ').strip(), style='Heading 2')
        elif stripped_line.startswith('### '):
            # Use custom 'Heading 3' style
            try:
                document.add_paragraph(stripped_line.lstrip('### ').strip(), style='Custom Heading 3')
            except:
                document.add_paragraph(stripped_line.lstrip('### ').strip(), style='Heading 3')
                
        # Handle bullet points
        elif stripped_line.startswith('* ') or stripped_line.startswith('- '):
            # Use Word's built-in 'List Bullet' style
            text = stripped_line[2:].strip()
            bullet_para = document.add_paragraph()
            _parse_text_formatting(bullet_para, text)
            bullet_para.style = 'List Bullet'
            
        # Handle numbered lists
        elif re.match(r'^\d+\.\s', stripped_line):
            # Use Word's built-in 'List Number' style
            text = re.sub(r'^\d+\.\s', '', stripped_line)
            num_para = document.add_paragraph()
            _parse_text_formatting(num_para, text)
            num_para.style = 'List Number'
            
        # Handle blockquotes (contract evidence boxes)
        elif stripped_line.startswith('>'):
            quote_text = stripped_line.lstrip('> ').strip()
            quote_para = document.add_paragraph()
            _parse_text_formatting(quote_para, quote_text)
            # Style as a quote with indentation
            quote_para.paragraph_format.left_indent = Inches(0.5)
            quote_para.paragraph_format.right_indent = Inches(0.5)
            for run in quote_para.runs:
                run.font.italic = True
                run.font.color.rgb = RGBColor(70, 70, 70)
                
        # Handle horizontal rules (section separators)
        elif stripped_line.startswith('---'):
            # Add a line break for section separation
            document.add_paragraph()
            
        # Handle normal paragraphs, including those with bold text
        else:
            p = document.add_paragraph()
            _parse_text_formatting(p, stripped_line)
    
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

# Legacy PDF generation removed - replaced with WeasyPrint HTML-to-PDF approach
# See utils/html_export.py create_pdf_from_html() for new implementation
