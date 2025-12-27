# VeritasLogic.ai - Technical Accounting Managed Service

## Overview
VeritasLogic.ai is a premium managed service for accounting firms and large enterprise technical accounting teams, providing audit-ready, professional-quality technical accounting memos. The platform combines proprietary AI technology (the vLogic Engine) with expert human oversight to deliver flat-fee technical memos across multiple FASB standards (ASC 606, ASC 842, ASC 718, ASC 805, ASC 340-40) within 24-48 hours. The business model has pivoted from SaaS to a managed service, offering standard memos, complex transaction analysis, and custom engagements. The website now promotes professional services, with the Streamlit analysis app used internally.

## User Preferences
- **Communication Style**: Simple, everyday language for technical explanations
- **Business Focus**: Enterprise-grade professional service targeting Big 4 and large enterprise teams
- **UI/UX Standards**: Professional, clean interfaces with Big 4 inspired design language and consistent dark gradient styling
- **Contact Handling**: All inquiries route through unified professional contact system at support@veritaslogic.ai
- **CSS/Styling Rule**: NEVER use inline styles in HTML files. Always use CSS classes defined in styles.css for maintainability.
- **CSS Replacement Rule**: When updating CSS, REPLACE existing rules instead of adding new ones. Delete old/deprecated CSS blocks to prevent accumulation of legacy styles. Never let styles.css grow beyond ~4000 lines.
- **Critical Development Rules - Prompt Protection**:
    1. NEVER modify prompt text content without explicit user approval.
    2. ALWAYS ask permission before changing any prompt text or templates.
    3. Protected files requiring user approval for content changes:
       - `asc[XXX]/asc[XXX]_page.py` (form labels, help text, user-facing content)
       - `asc[XXX]/step_analyzer.py` (all prompt methods and analysis instructions)
       - Any file containing user-facing text or analysis instructions.
    4. Safe technical changes (no approval needed): Bug fixes to code logic/structure, adding missing methods/functions, performance improvements, import statements and technical infrastructure.
    5. When in doubt: Always ask the user before making ANY content changes.
    6. MANDATORY ALERT PROTOCOL: If the AI agent cannot make a necessary change due to these prompt protection rules, it MUST explicitly alert the user with: "⚠️ PROMPT PROTECTION ALERT: I cannot modify [specific file/content] due to the prompt protection rules in replit.md. You will need to make this change manually. Here's exactly what needs to be changed: [specific instructions]".

## System Architecture

### Overview
The platform integrates enterprise-grade business infrastructure with sophisticated technical accounting AI, serving Big 4 and large enterprise teams.

### Multi-Standard Platform Architecture
- **Frontend**: Streamlit multi-page application with a Home dashboard.
- **Core System**: Modular components for analyzers, data models, knowledge base management, and UI helpers.
- **Standard-Specific Pages**: Dedicated interfaces for different accounting standards.
- **Research Assistant**: RAG-powered chat for methodology development, supporting standard-specific knowledge bases and comprehensive guidance with citations.
- **Knowledge Base**: Separated database architecture with dedicated ChromaDB instances per standard, utilizing paragraph-aware chunking and topic classification.
- **Document Processing**: Unified document extractor for various formats, including multi-document processing.
- **Monthly Close Platform**: A separate Streamlit instance (`close_platform/`) on port 5001 for month-end close management. Features include a close checklist with task rollover, trial balance substantiation with QuickBooks Online (QBO) integration (OAuth2 with Fernet-encrypted tokens), and flux analysis with audit controls. Supports Excel export of close packages.

### Website & User Interface Architecture
- **Enterprise Web Platform**: Professional website with unified contact system and enterprise messaging.
- **Dashboard System**: Comprehensive analysis history tracking with detailed metrics.
- **Authentication Flow**: Secure user registration, login, and password recovery.
- **Subscription Model**: Managed service pricing ($750-$1500+/memo) replaces previous subscription tiers.
- **Stripe Integration**: Previously used for subscription management, now removed from public-facing pricing pages.
- **Responsive Design**: Professional mobile-first design with consistent Big 4 inspired color schemes and dark gradient styling.

### Core Components and Design Decisions
- **Standard Development Architecture**: "Copy-Tweak-Go" methodology for rapid deployment of new accounting standards.
- **Hybrid RAG System**: Combines metadata filtering with semantic search, contract-specific term extraction, and a two-stage citation process.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks.
- **Professional Memo Generation**: Produces Big 4 quality accounting memos with narrative analysis, professional formatting, dynamic table handling, and robust DOCX/HTML generation.
- **System/User Prompt Architecture**: Modular prompt system separating core AI instructions from task-specific context.
- **Knowledge Hierarchy System**: Enhanced prompt functions with systematic knowledge hierarchy (Contract Text → Authoritative Guidance → Interpretive Guidance) and IAC framework.
- **Hybrid Financial Calculation System**: "Extract-Then-Calculate" pattern for financial amounts, using Python for calculations after AI extraction.
- **Unified LLM Request Architecture**: Standardized `_make_llm_request()` for centralized API routing between GPT-5 (Responses API) and GPT-4o (Chat Completions API) across all ASC standards.
- **Sequential Execution Architecture**: All ASC standards now use sequential step execution with accumulated context passing, ensuring consistency. Each step receives full markdown output from all prior steps.
- **Memo Review Feature**: Allows users to upload an existing memo and source contract for comparison against vLogic-generated analysis. Generates review comments categorized as Missing Analysis, Different Conclusions, Different Analysis, and Documentation Gaps.
- **Privacy Protection - Contract De-identification**: Automated dual-party extraction and text replacement across all ASC standards using GPT-5-mini JSON output. Replaces names with generic identifiers and extracts/replaces parenthetical aliases. Includes graceful fallback.

## External Dependencies
- **Streamlit**: Web application framework.
- **pandas**: Data manipulation and analysis.
- **unstructured**, **pdfplumber**, **PyPDF2**, **PyMuPDF**: PDF text extraction and handling.
- **ChromaDB**: Vector database for knowledge base.
- **OpenAI API**: Large language model interactions (`gpt-4o`, `gpt-4o-mini`, `gpt-5`).
- **FPDF**, **WeasyPrint**, **python-docx**: Document generation (PDF, HTML-to-PDF, Word).
- **Camelot & Tabula-py**: Table extraction from PDFs.
- **Postmark**: Email delivery service for transactional emails.
- **QuickBooks Online API**: For the Monthly Close Platform's trial balance substantiation.