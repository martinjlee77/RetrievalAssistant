# VeritasLogic.ai - Technical Accounting AI Platform

## Overview
VeritasLogic.ai is a premium enterprise AI platform designed for accounting firms and large enterprise technical accounting teams. It provides audit-ready, professional-quality accounting analyses across multiple FASB standards (ASC 606, ASC 842, ASC 718, ASC 805, ASC 340-40) using advanced AI technology. The platform transforms weeks of manual analysis into professional memos within minutes, maintaining the rigor and citation quality expected in professional environments, and allows professionals to focus on judgment and client advisory.

## Recent Changes

### October 19, 2025
- **Privacy Confirmation Screen (ASC 606)**: Implemented mandatory privacy review and confirmation step before analysis begins. After file upload, users see a confirmation screen showing:
  - Info box displaying party name replacements (e.g., "Acme Corp" → "the Company")
  - 4000-character preview of de-identified text that will be analyzed
  - Warning messages if de-identification fails, allowing user to proceed with original text if desired
  - File extraction failure warnings if some files couldn't be processed
  - Session-state caching with file-hash based cache invalidation to prevent stale data
  - "Go Back" and "Run Analysis" buttons for user control
- **Privacy Enhancement - Contract De-identification (ASC 606)**: Implemented automated dual-party extraction and de-identification system for ASC 606 revenue contracts. Uses GPT-5-mini to extract both vendor/seller (primary party) and customer/buyer (counterparty) names, then replaces them with generic terms ("the Company" and "the Customer") before analysis. De-identification now returns result dict instead of raising ValueError, enabling graceful fallback when extraction fails.
- **Privacy Documentation Updates**: Updated privacy.html and terms.html to accurately reflect OpenAI's 30-day data retention policy for abuse monitoring (replacing previous "data retention turned off" language). Added de-identification disclosure as privacy enhancement feature.

### October 14, 2025
- **ASC 805 Bug Fix**: Fixed NameError for undefined variables (`analysis_key`, `session_id`, `memo_key`) that caused memo generation to fail at final step. Added session initialization code matching ASC 842 pattern.
- **Header Visibility Fix**: Updated all ASC standards (606, 718, 842, 805, 340-40) to use white (#ffffff) text for h2/h3 headers in PDF memos for better contrast on dark backgrounds.

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
- **Initial Credits System**: New users receive $295 in credits upon signup ("run your first analysis free" model). Credits are awarded atomically during account creation with full audit trail. Email verification required before credit spending to prevent abuse.
- **Contact Management**: Unified inquiry system with conditional field logic for different service types.
- **Responsive Design**: Professional mobile-first design with consistent Big 4 inspired color schemes.
- **UI Consistency**: All forms use contact-form CSS classes for unified wide layout and dark gradient styling.
- **Navigation**: Consistent enterprise-focused navigation with professional service emphasis.
- **Pricing**: Pricing is per anlaysis and is tiered based on the number of words in the documents analyzed. $95 for 3000 words, $195 for 9000 words, $295 for 150000, $495 for 30000, $895 for 60000. For documents with words greater than 60000, support should be contacted.
- **Payment**: Enterprise credit packages ($500/$1000/$2000) with clear 12-month expiration policy. Credits can also be purchase at a custom amount.
- **Dashboard Standards**: Analysis history displays date completed (latest first), ASC standard, cost charged, document size, file count, and pricing tier.
- **Account Management**: Professional account balance display with comma formatting for thousands.
- **Admin Notifications**: Automated email alerts to support@veritaslogic.ai for new signups to monitor for potential abuse.

### Core Components and Design Decisions
- **Standard Development Architecture**: Follows a "Copy-Tweak-Go" methodology for rapid deployment of new accounting standards, based on proven architectural patterns from ASC 606.
- **Hybrid RAG System**: Combines metadata filtering with semantic search, enhanced by contract-specific term extraction, and a two-stage citation process for audit-ready evidence.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks to prevent truncation.
- **Professional Memo Generation**: Produces Big 4 quality accounting memos with narrative-driven analysis, professional formatting, dynamic table handling, and robust DOCX/HTML generation.
- **System/User Prompt Architecture**: Modular prompt system separating core AI instructions from task-specific context.
- **Knowledge Hierarchy System**: Enhanced prompt functions with systematic knowledge hierarchy (Contract Text → Authoritative Guidance → Interpretive Guidance) and IAC framework.
- **Hybrid Financial Calculation System**: Implemented "Extract-Then-Calculate" pattern for financial amounts, ensuring accuracy by using Python for calculations after AI extraction.
- **Modular Standard Modules**: Designed with re-usable architectural patterns across different accounting standards.
- **Unified LLM Request Architecture**: All ASC standards (606, 340-40, 718, 842, 805) implement standardized `_make_llm_request()` helper method for centralized API routing between GPT-5 (Responses API) and GPT-4o (Chat Completions API). Ensures consistent model handling and future-proof architecture for new OpenAI models.
- **Privacy Protection - Contract De-identification**: Automated dual-party extraction and text replacement system implemented for ASC 606 (planned rollout to other standards). Extracts both contract parties using GPT-5-mini JSON output, replaces names with generic identifiers before analysis. Standard-specific party mappings: ASC 606 (vendor/customer), ASC 842 (lessee/lessor), ASC 718 (granting company/recipient), ASC 805 (acquirer/target), ASC 340-40 (company/employee or third party).
  - **Comprehensive Text Normalization**: Handles PDF extraction artifacts including Unicode soft hyphens (U+00AD), hyphenated line breaks (e.g., "Smith-\nJones LLC"), and whitespace variations. Applies consistent normalization to both contract text and extracted party names.
  - **Flexible Pattern Matching**: Treats hyphens and spaces as equivalent in company names (pattern `(?:-|\s)`) to handle all variations from PDF extraction. Ensures "Smith-Jones LLC" matches both "Smith-Jones" and "Smith Jones" after line-wrap normalization.
  - **Privacy Gate Enforcement**: Hard stop (ValueError) if neither party name is successfully replaced, preventing data leakage to OpenAI API. User receives clear error message without being charged. Comprehensive logging tracks replacement counts for production monitoring.

## Deployment & Production Configuration

### Railway Production Deployment
The application is deployed to Railway using a custom `start.sh` script for production configuration.

**Critical File: `start.sh`**
- Railway automatically executes `start.sh` for deployment (takes precedence over Procfile/nixpacks.toml)
- Production server: Uses **Gunicorn** (production WSGI server) instead of Flask's development server
- Configuration: 4 workers, binds to Railway's `$PORT` environment variable (default: 8080)
- Access/error logs: Streamed to Railway console for monitoring

**Common Issue - Development Server Warning:**
```
WARNING: This is a development server. Do not use it in a production deployment.
```

**Root Cause:** If you see this warning in Railway logs, check `start.sh` - it's likely calling `python backend_api.py` instead of `gunicorn backend_api:app`

**Solution:**
```bash
# start.sh should contain:
exec gunicorn backend_api:app --bind 0.0.0.0:$PORT --workers 4 --access-logfile - --error-logfile -

# NOT:
exec python backend_api.py --port "$PORT"  # ❌ This uses Flask dev server
```

**Deployment Checklist:**
1. Verify `start.sh` uses Gunicorn command
2. Ensure `gunicorn` is in `requirements.txt`
3. Push changes to trigger Railway auto-deployment
4. Check logs for "Starting gunicorn" instead of "Werkzeug WARNING"

**File Priority on Railway:**
1. `start.sh` (if present) ← **Always checked first**
2. Custom Start Command (in Railway settings)
3. `nixpacks.toml`
4. `Procfile` (legacy, not used by Railway's Nixpacks)

### Database Schema Updates Needed

**IMPORTANT: Production Database Migration Required**

The production Railway database is missing the `error_message` column in the `analyses` table. This column is needed to track failure reasons for the "no charge on failure" policy.

**Migration SQL (to be run on Railway production database):**
```sql
ALTER TABLE analyses ADD COLUMN error_message TEXT;
```

**Temporary Workaround:** The backend code (backend_api.py line 1677) currently excludes this column from INSERT statements to prevent errors. Once the production database is updated, uncomment the error_message field in the INSERT statement.

**Status:** Development database has this column. Production database needs update.

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