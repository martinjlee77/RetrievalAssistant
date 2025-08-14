# ASC 606 PDF Processing PoC

## Overview
This project is a multi-standard accounting analysis platform designed to generate comprehensive contract analyses under various accounting standards (e.g., ASC 606, ASC 340-40, ASC 842). It processes contracts to produce structured professional memos, adhering to specific methodologies and utilizing authoritative FASB guidance and Big 4 interpretative publications. The system aims to deliver audit-ready, professional-quality accounting memos, consistent with Big 4 standards for accuracy and presentation, envisioning a complete financial analysis platform with high accuracy and efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes
- **Complete GPT-5 Migration Across All Standards** (August 14, 2025): Successfully migrated all three analyzers (ASC 606, ASC 340-40, ASC 842) from GPT-4o to GPT-5. Key compatibility fixes: max_tokens→max_completion_tokens, temperature=1 enforcement, response_format parameter removal for GPT-5. All 16 model references updated. Platform now runs consistently on GPT-5 across all accounting standards.
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