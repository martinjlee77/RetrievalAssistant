# VeritasLogic.ai - Technical Accounting AI Platform

## Overview
VeritasLogic.ai is a premium enterprise AI platform for accounting firms and large enterprise technical accounting teams. It provides audit-ready, professional-quality accounting analyses across multiple FASB standards (ASC 606, ASC 842, ASC 718, ASC 805, ASC 340-40) using advanced AI. The platform transforms weeks of manual analysis into professional memos within minutes, maintaining professional rigor and citation quality, allowing professionals to focus on judgment and client advisory.

## Recent Changes (December 8, 2025)
1. **Sequential Execution Architecture for All ASC Standards**: Refactored all ASC standards (606, 842, 718, 805, 340-40) from parallel to sequential step execution with accumulated context passing.
   - Each step receives full markdown output from ALL prior steps for perfect consistency
   - Prior steps context injected with approved prompt language: "The following conclusions have been established in prior steps of this analysis. Use these as facts - do not re-analyze these determinations."
   - Removed ASC 606-specific two-phase `_extract_po_summary_from_step2` pattern - replaced with universal sequential approach
   - Removed ThreadPoolExecutor imports (no longer parallel)
   - Updated `analyze_contract`, `_analyze_step_with_retry`, `_analyze_step`, and `_get_step_markdown_prompt` methods across all analyzers
   - Cleaned up `workers/analysis_worker.py` to remove legacy PO extraction logic
   - Performance tradeoff: 2-3x slower but dramatically improved accuracy and consistency

## Recent Changes (December 7, 2025)
1. **Memo Review Feature (Phase 1, 2 & 3 Complete)**: Tool allowing users to upload an existing memo and source contract for comparison against vLogic-generated analysis with review comments.
   - New page: `pages/memo_review.py` with ASC standard selector, dual file upload
   - Job runner: `pages/memo_review_job_runner.py` for background job submission
   - Worker function: `run_memo_review_analysis` in `workers/analysis_worker.py`
   - Database: Added `analysis_type` (default 'standard', also 'review') and `source_memo_filename` columns to analyses table
   - Billing: Charges combined contract + uploaded memo word counts
   - Privacy: De-identification applied to BOTH contract and uploaded memo
   - Button text: "Analyze & Review"
   - **Phase 2**: Review comment generation comparing uploaded memo vs vLogic analysis
     - Helper functions: `_generate_review_comments()` and `_format_review_comments_section()`
     - Categories: Missing Analysis, Different Conclusions, Different Analysis (methodology/reasoning differences + technical accuracy), Documentation Gaps
     - Full vLogic analysis content (not just summaries) used for comparison
     - Review comments appended to output memo as a dedicated section
   - **Phase 3 - Complete Separation of Analysis vs Review**:
     - Session state key separation: `review_asc606_*` prefix for reviews vs `asc606_*` for regular analyses
     - Backend API updates: Status endpoint returns `analysis_type` and `source_memo_filename`
     - Analysis History validation: Filters out incomplete entries (must have memo_content > 100 chars)
     - Dashboard badges: "Analysis" (green) and "Review" (amber) badges to distinguish entry types
     - History click-through: Review entries route to `/memo_review` page, not ASC analysis page
     - Review page layout: Review Comments displayed FIRST, vLogic memo in collapsible expander
     - Download options: "Full Review" and "Comments Only" download buttons
     - Styling fix: Review comments headers use white text for dark backgrounds

## Recent Changes (December 5, 2025)
1. **Major Pricing Update**: 10-20x increase in word allowances across all tiers:
   - Trial: 9K → 20K words
   - Professional: 15K → 150K words/month
   - Team: 30K → 400K words/month
   - Enterprise: 100K → 1M words/month
2. **Updated All Pricing References**: pricing.html, signup.html, terms.html, privacy.html, dashboard.js, pricing_config.py, and database schema files now reflect new word allowances.
3. **Enhanced Rollover Policy Language**: Terms now clearly state words are deducted on FIFO basis (oldest first) and expire 12 months from when earned.
4. **Stripe Subscription Cancellation Fix**: `handle_subscription_updated` and `handle_subscription_deleted` webhooks now properly extract and save `cancel_at_period_end` from Stripe events.

## User Preferences
- **Communication Style**: Simple, everyday language for technical explanations
- **Business Focus**: Enterprise-grade professional service targeting Big 4 and large enterprise teams
- **UI/UX Standards**: Professional, clean interfaces with Big 4 inspired design language and consistent dark gradient styling
- **Contact Handling**: All inquiries route through unified professional contact system at support@veritaslogic.ai
- **CSS/Styling Rule**: NEVER use inline styles in HTML files. Always use CSS classes defined in styles.css for maintainability.
- **CSS Replacement Rule**: When updating CSS, REPLACE existing rules instead of adding new ones. Delete old/deprecated CSS blocks to prevent accumulation of legacy styles. Never let styles.css grow beyond ~4000 lines.

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
- **Subscription Model**: Three tiers (Professional $295/mo, Team $595/mo, Enterprise $1195/mo) with monthly word allowances (150K, 400K, 1M). 14-day trial with 20K words included. All tiers are single-user accounts (customers share login credentials). Unused words roll over for 12 months (FIFO deduction).
- **Stripe Integration**: Subscription management with Customer Portal for upgrades, downgrades, payment updates, and invoice history.
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
- **Subscription Model Architecture**: All ASC standards (606, 340-40, 718, 805, 842) use consistent subscription model pattern. Job analysis runners accept `allowance_result`, `org_id`, and `total_words` parameters. Legacy `pricing_result` and `tier_info` references have been removed. Page files extract org_id from user session and pass all required parameters for word deduction tracking.
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