# ASC 606 PDF Processing PoC

## Overview
This project is a multi-standard accounting analysis platform designed to generate comprehensive contract analyses under various accounting standards (e.g., ASC 606, ASC 842). It processes contracts to produce structured professional memos, adhering to specific methodologies and utilizing authoritative FASB guidance and Big 4 interpretative publications. The system aims to deliver audit-ready, professional-quality accounting memos, consistent with Big 4 standards for accuracy and presentation, envisioning a complete financial analysis platform.

## User Preferences
Preferred communication style: Simple, everyday language.
Critical Development Rules - Prompt Protection:
1. NEVER modify prompt text content without explicit user approval.
2. ALWAYS ask permission before changing any prompt text or templates.
3. Protected files requiring user approval for content changes:
   - `utils/step_prompts.py` (all prompt methods)
   - `utils/prompt.py` (all template content)
   - `pages/asc606.py` (form labels, help text, user-facing content)
   - Any file containing user-facing text or analysis instructions.
4. Safe technical changes (no approval needed): Bug fixes to code logic/structure, adding missing methods/functions, performance improvements, import statements and technical infrastructure.
5. When in doubt: Always ask the user before making ANY content changes.
6. Violation consequences: User has to re-review entire codebase, causing significant frustration and lost work.
7. MANDATORY ALERT PROTOCOL: If the AI agent cannot make a necessary change due to these prompt protection rules, it MUST explicitly alert the user with: "⚠️ PROMPT PROTECTION ALERT: I cannot modify [specific file/content] due to the prompt protection rules in replit.md. You will need to make this change manually. Here's exactly what needs to be changed: [specific instructions]".

## System Architecture

### Multi-Standard Platform Architecture
- **Frontend**: Streamlit multi-page application with a Home dashboard.
- **Core System**: Modular components for analyzers, data models, knowledge base management, and UI helpers.
- **Standard-Specific Pages**: Dedicated interfaces for different accounting standards.
- **Knowledge Base**: Multi-standard ChromaDB manager supporting collections per standard.
- **Document Processing**: Unified document extractor for various formats.
- **Source Documents**: Standard-specific authoritative sources stored locally.

### Core Components and Design Decisions
- **Hybrid RAG System**: Combines metadata filtering with semantic search, enhanced by contract-specific term extraction.
- **Knowledge Base**: Contains 1,894 authoritative documents (ASC 606 official guidance + EY interpretative literature) in a ChromaDB vector database.
- **Two-Stage Citation Process**: Extracts verbatim quotes and then assembles analysis with structured evidence for direct and auditable citations.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks to prevent truncation.
- **Multi-document Processing**: Handles up to 5 files (contracts, invoices, amendments).
- **Professional Memo Generation**: Produces Big 4 quality accounting memos with audit-ready features, including narrative-driven analysis, professional formatting, and integration of actual contract data.
- **Source Transparency**: Tracks hybrid RAG chunks used and relevance scores.
- **System Integrity Monitoring**: Comprehensive logging and validation for detecting silent failures and ensuring data quality.
- **Performance Optimization**: Utilizes caching for analyzers, persistent vector databases, and concurrent execution of analysis steps.
- **Data Flow**: Ensures all user inputs (customer name, dates, focus areas, materiality, audience) flow systematically to the LLM for targeted analysis.
- **UI/UX Design**: Prioritizes professional, clean interfaces with clear navigation, simplified input forms, and immediate access to primary actions. Styling uses Lato font and Big 4 inspired color schemes.
- **DOCX Generation**: Enhanced with robust bullet indentation (structure-based detection), comprehensive formatting (italic text support, dynamic table handling), and professional visual enhancements (enhanced heading hierarchy, professional table design, consistent HTML/DOCX styling).
- **System/User Prompt Architecture**: Implemented a modular system/user prompt architecture, separating core AI instructions (system prompts) from task-specific context (user prompts) for each ASC 606 step. LLM integration handles message arrays.
- **Judgment Consistency**: Implemented a shared `_filter_genuine_judgments()` function to ensure consistent filtering logic for judgments across executive summary, conclusion, and key professional judgments sections.
- **Executive Summary Enhancement**: Restructured executive summary to eliminate redundancy between OVERALL CONCLUSION (strategic narrative) and KEY FINDINGS (scannable dashboard). Implemented "ASC 606 Contract Exists: Yes/No" terminology and professional role separation aligned with Big 4 audit documentation standards.

### File Structure
```
├── home.py                               # Streamlit app entry point with navigation
├── pages/                                # Streamlit pages
│   ├── home_content.py                   # Home page dashboard content
│   ├── asc606.py                         # ASC 606 revenue recognition
│   └── asc842.py                         # ASC 842 lease analysis (placeholder)
├── assets/                               # Static assets
│   └── images/
│       └── logo.png                      # Controller.cpa logo
├── utils/                                # Core utilities
│   ├── llm.py                            # OpenAI API calls, knowledge base, debugging tools
│   ├── prompt.py                         # Centralized prompt templates
│   ├── auth.py                           # Authentication utilities (placeholder)
│   ├── document_extractor.py             # Multi-format document processing
│   └── asc606_analyzer.py                # Consolidated ASC 606 hybrid analyzer
├── core/                                 # Shared backend logic
│   ├── analyzers.py                      # Analyzer factory and base classes
│   ├── models.py                         # Centralized data models
│   ├── knowledge_base.py                 # Multi-standard knowledge base manager
│   └── ui_helpers.py                     # Shared UI components and styling
├── attached_assets/                      # Authoritative sources (cleaned)
├── asc606_knowledge_base/                # ChromaDB vector database (single source)
├── pyproject.toml                        # Dependencies
└── replit.md                             # Project documentation
```

## External Dependencies

- **Streamlit**: Web application framework.
- **pandas**: Data manipulation and analysis.
- **unstructured**: Advanced PDF processing.
- **pdfplumber**: PDF text extraction.
- **PyPDF2**: Basic PDF handling.
- **ChromaDB**: Vector database for knowledge base.
- **OpenAI API**: Large language model interactions (`gpt-4o`, `gpt-4o-mini`).
- **FPDF**: PDF generation.
- **WeasyPrint**: HTML-to-PDF conversion.
- **python-docx**: Word document generation.
- **Camelot & Tabula-py**: Table extraction from PDFs.
- **PyMuPDF**: Coordinate-based layout analysis in PDF processing.