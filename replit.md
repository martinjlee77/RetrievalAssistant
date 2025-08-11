# ASC 606 PDF Processing PoC

## Overview
This project is a multi-standard accounting analysis platform designed to generate comprehensive contract analyses under various accounting standards (e.g., ASC 606, ASC 340-40). It processes contracts to produce structured professional memos, adhering to specific methodologies and utilizing authoritative FASB guidance and Big 4 interpretative publications. The system aims to deliver audit-ready, professional-quality accounting memos, consistent with Big 4 standards for accuracy and presentation, envisioning a complete financial analysis platform.

## User Preferences
Preferred communication style: Simple, everyday language.
Critical Development Rules - Prompt Protection:
1. NEVER modify prompt text content without explicit user approval.
2. ALWAYS ask permission before changing any prompt text or templates.
3. Protected files requiring user approval for content changes:
   - `utils/step_prompts.py` (all prompt methods)
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
- **Judgment Consistency**: Implemented a shared `_filter_genuine_judgments()` function to ensure consistent filtering logic for judgments across executive summary, conclusion, and key professional judgments sections. Enhanced Key Professional Judgments prompt with structured data extraction from all 5 steps, providing complexity indicators and contextual evaluation criteria for more accurate judgment significance assessment.
- **Executive Summary Enhancement**: Restructured executive summary to eliminate redundancy between OVERALL CONCLUSION (strategic narrative) and KEY FINDINGS (scannable dashboard). Implemented "ASC 606 Contract Exists: Yes/No" terminology and professional role separation aligned with Big 4 audit documentation standards. Added comprehensive data extraction for all Key Findings items (contract status, performance obligations, transaction price, allocation method, recognition methods, and filtered critical judgments) to ensure consistency with other system prompts and eliminate unreliable LLM improvisation.
- **Knowledge Hierarchy System**: Enhanced all prompt functions with systematic knowledge hierarchy (Contract Text → Authoritative Guidance → Interpretative Guidance) and IAC framework for professional judgment defensibility.
- **GPT-5 Integration**: Updated to use GPT-5 model for enhanced analysis quality (August 2025 release).
- **Legacy Code Cleanup**: Removed unused `utils/prompt.py` file - system now fully consolidated on `utils/step_prompts.py`.
- **Hybrid Financial Calculation System**: Implemented "Extract-Then-Calculate" pattern to eliminate mathematical errors in transaction price determination. AI extracts structured fee components, Python performs reliable calculations. Ensures 100% accuracy for financial amounts in Step 3 analysis and memo generation.
- **Unified Financial Data Flow**: Fixed architectural inconsistency where financial impact section was performing separate calculations instead of using completed Step 3, 4, and 5 results. Journal entries now derive amounts exclusively from the hybrid calculation system, eliminating calculation discrepancies. Extended calculated financial facts injection to Step 4 allocation analysis to ensure consistent transaction price usage across all steps (August 2025).
- **Comprehensive Cleanup**: Removed 99+ development note files, placeholder authentication pages, unused utility files, and old memo outputs. Retained only essential authoritative guidance (10 text files) and sample contracts (7 PDFs). Cleaned directory structure for next development phase (August 2025).
- **ASC 340-40 Contract Costs Module**: Implemented complete ASC 340-40 module following proven ASC 606 architecture patterns. Added 4-step policy framework (Scope Assessment, Cost Classification, Measurement & Amortization Policy, Illustrative Financial Impact), RAG-enabled knowledge base with 139 chunks (37 authoritative + 102 EY interpretative), dedicated analyzer with hybrid search capabilities, and professional policy memorandum generation. Integrated into multi-standard platform with navigation and home page updates (August 2025).
- **ASC 340-40 V2 Radical UI Simplification**: Complete UI/UX overhaul removing tabbed interface in favor of clean single-page design. Implemented 12 specific refinements: required document upload with cost-focused labeling, "Primary Cost Categories in Scope" multiselect replacing confusing contract types, optional policy effective date (defaults to generation), removed unnecessary fields (Cost Timing Focus, Primary Memo Audience, Materiality Threshold), hard-coded memo audience to "Technical Accounting Team". Enhanced validation logic and streamlined data flow for policy-focused analysis (August 2025).

### File Structure
```
├── home.py                               # Streamlit app entry point with navigation
├── pages/                                # Streamlit pages
│   ├── home_content.py                   # Home page dashboard content
│   └── asc606.py                         # ASC 606 revenue recognition analysis
├── assets/                               # Static assets
│   └── images/
│       └── logo.png                      # Controller.cpa logo
├── utils/                                # Core utilities
│   ├── llm.py                            # OpenAI API calls, DOCX/HTML generation (GPT-4o)
│   ├── step_prompts.py                   # Enhanced prompt system with knowledge hierarchy
│   ├── document_extractor.py             # Multi-format document processing
│   ├── asc606_analyzer.py                # ASC 606 hybrid analyzer with extract-then-calculate
│   └── html_export.py                    # Professional HTML memo generation
├── core/                                 # Shared backend logic
│   ├── analyzers.py                      # Analyzer factory and base classes
│   ├── models.py                         # Centralized data models
│   ├── knowledge_base.py                 # Multi-standard knowledge base manager
│   └── ui_helpers.py                     # Shared UI components and styling
├── attached_assets/                      # Essential authoritative sources only
│   ├── 05_overview_background_*.txt      # ASC 606 official guidance sections
│   ├── 10_objectives_*.txt               # (9 total ASC 606 text files)
│   ├── netflix_*.pdf                     # Sample contract files (5 PDFs)
│   └── contract_review_questions_*.txt   # Contract analysis framework
├── asc606_knowledge_base/                # ChromaDB vector database
├── seed_knowledge_base.py                # Knowledge base initialization
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