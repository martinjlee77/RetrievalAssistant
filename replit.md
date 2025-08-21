# ASC 606 PDF Processing PoC

## Overview
This project is a multi-standard accounting analysis platform designed to generate comprehensive contract analyses under various accounting standards (e.g., ASC 606, ASC 340-40, ASC 842). It processes contracts to produce structured professional memos, adhering to specific methodologies and utilizing authoritative FASB guidance and Big 4 interpretative publications. The system aims to deliver audit-ready, professional-quality accounting memos, consistent with Big 4 standards for accuracy and presentation, envisioning a complete financial analysis platform with high accuracy and efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes
- **ASC 606 Formatting Issues Resolved** (August 21, 2025): Fixed root cause of persistent formatting problems - discovered conflicting prompt instructions between system and user prompts causing LLM confusion. Removed duplicate formatting rules from system prompt, consolidated all formatting instructions in user prompt only. Enhanced parsing robustness and added targeted formatting fixes applied directly to parsed content. Maintained 5-call architecture for analysis quality while improving formatting reliability. System now generates clean professional memos with proper currency formatting and text spacing.
- **Simplified Architecture Implementation Complete** (August 20, 2025): Completely rebuilt the system with simplified, modular architecture. Removed complex JSON schemas in favor of natural language template-based memo generation. Implemented shared components (document processor, knowledge base, memo generator, UI components) that work across all standards. Created new simplified ASC 606 module with step analyzer and knowledge search. Added "Issues for Further Investigation" section to memos. Cleaned up unused legacy files (old analyzers, complex core modules). The system now has clear separation between standards while sharing common functionality.
- **Knowledge Base Architecture Separation Complete** (August 14, 2025): Implemented clean separation with dedicated databases per standard. Fixed critical ASC 340-40 chunking issue (was only 9 chunks, now properly 126 chunks). Final architecture: ASC 606 (1,557 pure revenue chunks, 32MB), ASC 340-40 (126 contract cost chunks - 48 authoritative + 78 interpretative), ASC 842 (563 lease chunks, 14MB). The ASC 340-40 RAG system is now functional - previously was relying only on LLM general knowledge. Updated KnowledgeBaseManager with automatic standard-to-database routing.
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

## ASC 606 Fine-Tuning Roadmap

### Priority Files for Review/Editing (in order of importance):

**1. asc606/step_analyzer.py** - CRITICAL
- Contains all step-by-step analysis logic and prompts
- Key areas to review: step_prompts, system_prompt, prompt generation logic
- Fine-tune the 5-step methodology prompts for better analysis quality

**2. asc606/knowledge_search.py** - HIGH PRIORITY  
- Optimizes knowledge base search queries for each step
- Review: step-specific query building, search term extraction
- Note: Currently knowledge base collection doesn't exist (needs ASC 606 guidance loaded)

**3. asc606/templates/memo_template.md** - HIGH PRIORITY
- Controls final memo formatting and structure
- Review: Professional language, section organization, Big 4 style formatting

**4. shared/memo_generator.py** - MEDIUM PRIORITY
- Template processing and section extraction logic
- Review: How analysis results are formatted into memo sections

**5. asc606/asc606_page.py** - MEDIUM PRIORITY
- UI workflow and user experience
- Review: Progress display, error handling, result presentation

**6. shared/ui_components.py** - LOW PRIORITY
- Shared UI elements and validation
- Review: Input validation, user feedback, consistent styling

**7. shared/knowledge_base.py** - LOW PRIORITY (infrastructure)
- Knowledge base interface (works but needs ASC 606 collection created)

**8. shared/document_processor.py** - LOW PRIORITY (working)
- Document upload and processing (currently working well)

### Known Issues to Address:
- ASC 606 knowledge base collection doesn't exist (needs to be created/loaded)
- Step analysis prompts may need refinement for better quality
- Memo template may need professional formatting improvements

## System Architecture

### Multi-Standard Platform Architecture
- **Frontend**: Streamlit multi-page application with a Home dashboard.
- **Core System**: Modular components for analyzers, data models, knowledge base management, and UI helpers.
- **Standard-Specific Pages**: Dedicated interfaces for different accounting standards (ASC 606, ASC 340-40, ASC 842).
- **Knowledge Base**: Separated database architecture with dedicated ChromaDB instances per standard (asc606_knowledge_base/, asc340_knowledge_base/, asc842_knowledge_base/), using paragraph-aware chunking and topic classification.
- **Document Processing**: Unified document extractor for various formats, including multi-document processing.
- **Source Documents**: Standard-specific authoritative sources stored locally.

### Core Components and Design Decisions
- **Hybrid RAG System**: Combines metadata filtering with semantic search, enhanced by contract-specific term extraction, and a two-stage citation process for audit-ready evidence.
- **Knowledge Base**: Contains comprehensive authoritative and interpretative guidance for ASC 606, ASC 340-40, and ASC 842.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks to prevent truncation.
- **Professional Memo Generation**: Produces Big 4 quality accounting memos (Technical Accounting Memos, Accounting Policy Memos) with narrative-driven analysis, professional formatting, dynamic table handling, and robust DOCX/HTML generation.
- **System Integrity Monitoring**: Comprehensive logging and validation for data quality.
- **Performance Optimization**: Utilizes caching, persistent vector databases, and concurrent execution.
- **Data Flow**: Ensures all user inputs flow systematically to the LLM for targeted analysis.
- **UI/UX Design**: Prioritizes professional, clean interfaces with clear navigation, simplified input forms, and Big 4 inspired color schemes.
- **System/User Prompt Architecture**: Modular prompt system separating core AI instructions from task-specific context.
- **Judgment Consistency**: Implemented shared filtering logic and structured data extraction for professional judgments.
- **Executive Summary Enhancement**: Restructured to clearly separate overall conclusion from scannable key findings with comprehensive data extraction.
- **Knowledge Hierarchy System**: Enhanced prompt functions with systematic knowledge hierarchy (Contract Text → Authoritative Guidance → Interpretive Guidance) and IAC framework.
- **Hybrid Financial Calculation System**: Implemented "Extract-Then-Calculate" pattern for financial amounts, ensuring accuracy by using Python for calculations after AI extraction.
- **Unified Financial Data Flow**: Ensures journal entries and financial impacts derive amounts exclusively from the hybrid calculation system.
- **Modular Standard Modules**: Designed with re-usable architectural patterns across different accounting standards (ASC 606, ASC 340-40, ASC 842).

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