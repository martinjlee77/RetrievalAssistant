# VeritasLogic.ai - Enterprise Accounting AI Platform

## Overview
VeritasLogic.ai is a premium enterprise AI platform designed for Big 4 accounting firms and large enterprise technical accounting teams. It provides audit-ready, professional-quality accounting analyses across multiple FASB standards (ASC 606, ASC 842, ASC 718, ASC 805, ASC 340-40) using advanced AI technology. The platform transforms weeks of manual analysis into professional memos within minutes, maintaining the rigor and citation quality expected in Big 4 environments, and allows professionals to focus on judgment and client advisory.

## User Preferences
- **Communication Style**: Simple, everyday language for technical explanations
- **Business Focus**: Enterprise-grade professional service targeting Big 4 and large enterprise teams
- **UI/UX Standards**: Professional, clean interfaces with Big 4 inspired design language and consistent dark gradient styling
- **Contact Handling**: All inquiries route through unified professional contact system at support@veritaslogic.ai

Critical Development Rules - Prompt Protection:
1. NEVER modify prompt text content without explicit user approval.
2. ALWAYS ask permission before changing any prompt text or templates.
3. Protected files requiring user approval for content changes:
   - `asc[XXX]/asc[XXX]_page.py` (form labels, help text, user-facing content)
   - `asc[XXX]/step_analyzer.py` (all prompt methods and analysis instructions)
   - Any file containing user-facing text or analysis instructions.
4. Safe technical changes (no approval needed): Bug fixes to code logic/structure, adding missing methods/functions, performance improvements, import statements and technical infrastructure.
5. When in doubt: Always ask the user before making ANY content changes.
6. Violation consequences: User has to re-review entire codebase, causing significant frustration and lost work.
7. MANDATORY ALERT PROTOCOL: If the AI agent cannot make a necessary change due to these prompt protection rules, it MUST explicitly alert the user with: "⚠️ PROMPT PROTECTION ALERT: I cannot modify [specific file/content] due to the prompt protection rules in replit.md. You will need to make this change manually. Here's exactly what needs to be changed: [specific instructions]".

## System Architecture

### Overview
The platform combines enterprise-grade business infrastructure with sophisticated technical accounting AI to serve Big 4 and large enterprise teams.

### Multi-Standard Platform Architecture
- **Frontend**: Streamlit multi-page application with a Home dashboard.
- **Core System**: Modular components for analyzers, data models, knowledge base management, and UI helpers.
- **Standard-Specific Pages**: Dedicated interfaces for different accounting standards.
- **Research Assistant**: Integrated RAG-powered chat interface for methodology development, supporting standard-specific knowledge base selection and comprehensive guidance with authoritative citations.
- **Knowledge Base**: Separated database architecture with dedicated ChromaDB instances per standard, using paragraph-aware chunking and topic classification.
- **Document Processing**: Unified document extractor for various formats, including multi-document processing.
- **Source Documents**: Standard-specific authoritative sources stored locally.

### Website & User Interface Architecture
- **Enterprise Web Platform**: Professional website with unified contact system, enterprise messaging, and sophisticated user account management.
- **Dashboard System**: Comprehensive analysis history tracking with detailed metrics for enterprise reporting.
- **Authentication Flow**: Secure user registration, login, and password recovery with unified professional styling.
- **Contact Management**: Unified inquiry system with conditional field logic for different service types.
- **Responsive Design**: Professional mobile-first design with consistent Big 4 inspired color schemes.
- **UI Consistency**: All forms use contact-form CSS classes for unified wide layout and dark gradient styling.
- **Navigation**: Consistent enterprise-focused navigation with professional service emphasis.
- **Pricing Display**: Enterprise credit packages ($500/$1000/$2000) with clear 12-month expiration policy.
- **Dashboard Standards**: Analysis history displays date completed (latest first), ASC standard, cost charged, document size, file count, and pricing tier.
- **Account Management**: Professional account balance display with comma formatting for thousands.

### Core Components and Design Decisions
- **Standard Development Architecture**: Follows a "Copy-Tweak-Go" methodology for rapid deployment of new accounting standards, based on proven architectural patterns from ASC 606.
- **Hybrid RAG System**: Combines metadata filtering with semantic search, enhanced by contract-specific term extraction, and a two-stage citation process for audit-ready evidence.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks to prevent truncation.
- **Professional Memo Generation**: Produces Big 4 quality accounting memos with narrative-driven analysis, professional formatting, dynamic table handling, and robust DOCX/HTML generation.
- **System/User Prompt Architecture**: Modular prompt system separating core AI instructions from task-specific context.
- **Knowledge Hierarchy System**: Enhanced prompt functions with systematic knowledge hierarchy (Contract Text → Authoritative Guidance → Interpretive Guidance) and IAC framework.
- **Hybrid Financial Calculation System**: Implemented "Extract-Then-Calculate" pattern for financial amounts, ensuring accuracy by using Python for calculations after AI extraction.
- **Modular Standard Modules**: Designed with re-usable architectural patterns across different accounting standards.

## External Dependencies
- **Streamlit**: Web application framework.
- **pandas**: Data manipulation and analysis.
- **unstructured**: Advanced PDF processing.
- **pdfplumber**: PDF text extraction.
- **PyPDF2**: Basic PDF handling.
- **ChromaDB**: Vector database for knowledge base.
- **OpenAI API**: Large language model interactions (`gpt-4o`, `gpt-4o-mini`, `gpt-5`).
- **FPDF**: PDF generation.
- **WeasyPrint**: HTML-to-PDF conversion.
- **python-docx**: Word document generation.
- **Camelot & Tabula-py**: Table extraction from PDFs.
- **PyMuPDF**: Coordinate-based layout analysis in PDF processing.