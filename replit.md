# VeritasLogic.ai - Technical Accounting AI Platform

## Overview
VeritasLogic.ai is a premium enterprise AI platform for accounting firms and large enterprise technical accounting teams. It provides audit-ready, professional-quality accounting analyses across multiple FASB standards (ASC 606, ASC 842, ASC 718, ASC 805, ASC 340-40) using advanced AI. The platform transforms weeks of manual analysis into professional memos within minutes, maintaining professional rigor and citation quality, allowing professionals to focus on judgment and client advisory.

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

### Website & User Interface Architecture
- **Enterprise Web Platform**: Professional website with unified contact system, enterprise messaging, and sophisticated user account management.
- **Dashboard System**: Comprehensive analysis history tracking with detailed metrics for enterprise reporting.
- **Authentication Flow**: Secure user registration, login, and password recovery with unified professional styling.
- **Initial Credits System**: New users receive $295 in credits upon signup ("run your first analysis free" model); email verification required.
- **Pricing**: Per analysis, tiered by word count ($95 for 3000 words to $895 for 60000 words).
- **Payment**: Enterprise credit packages ($500/$1000/$2000) with 12-month expiration; custom amounts available.
- **Responsive Design**: Professional mobile-first design with consistent Big 4 inspired color schemes and dark gradient styling.

### Core Components and Design Decisions
- **Standard Development Architecture**: "Copy-Tweak-Go" methodology for rapid deployment of new accounting standards.
- **Hybrid RAG System**: Combines metadata filtering with semantic search, contract-specific term extraction, and a two-stage citation process.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks.
- **Professional Memo Generation**: Produces Big 4 quality accounting memos with narrative-driven analysis, professional formatting, dynamic table handling, and robust DOCX/HTML generation.
- **System/User Prompt Architecture**: Modular prompt system separating core AI instructions from task-specific context.
- **Knowledge Hierarchy System**: Enhanced prompt functions with systematic knowledge hierarchy (Contract Text → Authoritative Guidance → Interpretive Guidance) and IAC framework.
- **Hybrid Financial Calculation System**: "Extract-Then-Calculate" pattern for financial amounts, using Python for calculations after AI extraction.
- **Unified LLM Request Architecture**: Standardized `_make_llm_request()` helper method for centralized API routing between GPT-5 (Responses API) and GPT-4o (Chat Completions API) across all ASC standards.
- **Privacy Protection - Contract De-identification**: Automated dual-party extraction and text replacement system across ALL ASC standards.
  - Extracts both contract parties using GPT-5-mini JSON output, replaces names with generic identifiers (e.g., "the Company", "the Customer").
  - Includes comprehensive text normalization and base name extraction (removing legal suffixes) to catch standalone references.
  - **Alias Extraction**: Automatically detects and replaces quoted parenthetical aliases in contracts. Pattern extracts all quoted strings from parentheses following company names, supporting multi-alias patterns like "InnovateTech Solutions Inc. ('InnovateTech' or 'Provider')" → extracts and replaces both "InnovateTech" and "Provider". Conservative quoted-string approach prevents false positives from descriptive clauses.
  - Graceful Fallback: If extraction fails, users can still proceed with original text, making de-identification an enhancement rather than a blocking requirement.
- **Deployment**: Production deployment uses Gunicorn via `start.sh` on Railway. The `analyses` table in the production database requires an `error_message` column for failure tracking.

## External Dependencies
- **Streamlit**: Web application framework.
- **pandas**: Data manipulation and analysis.
- **unstructured**: Advanced PDF processing.
- **pdfplumber**, **PyPDF2**, **PyMuPDF**: PDF text extraction and handling.
- **ChromaDB**: Vector database for knowledge base.
- **OpenAI API**: Large language model interactions (`gpt-4o`, `gpt-4o-mini`, `gpt-5`).
- **FPDF**, **WeasyPrint**, **python-docx**: Document generation (PDF, HTML-to-PDF, Word).
- **Camelot & Tabula-py**: Table extraction from PDFs.
- **Postmark**: Email delivery service for transactional emails (verification, password resets, notifications).