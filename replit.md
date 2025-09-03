# Multi-Standard Accounting Analysis Platform

## Overview
This is a multi-standard accounting analysis platform designed to generate comprehensive analyses under various accounting standards (e.g., ASC 606, ASC 842, ASC 718, ASC 805 and ASC 340-40). It processes contracts or relevant documents to produce structured professional memos, adhering to specific methodologies and utilizing authoritative FASB guidance via hybrid RAG. The system aims to deliver audit-ready, professional-quality accounting memos, consistent with Big 4 standards for accuracy and presentation, envisioning a complete financial analysis platform with high accuracy and efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

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

### Multi-Standard Platform Architecture
- **Frontend**: Streamlit multi-page application with a Home dashboard.
- **Core System**: Modular components for analyzers, data models, knowledge base management, and UI helpers.
- **Standard-Specific Pages**: Dedicated interfaces for different accounting standards (ASC 606, ASC 340-40, ASC 842).
- **Research Assistant**: Integrated RAG-powered chat interface for methodology development, supporting standard-specific knowledge base selection and comprehensive guidance with authoritative citations.
- **Knowledge Base**: Separated database architecture with dedicated ChromaDB instances per standard, using paragraph-aware chunking and topic classification.
- **Document Processing**: Unified document extractor for various formats, including multi-document processing.
- **Source Documents**: Standard-specific authoritative sources stored locally.

### Core Components and Design Decisions
- **Standard Development Architecture**: Follows a "Copy-Tweak-Go" methodology for rapid deployment of new accounting standards, based on proven architectural patterns from ASC 606. This involves defining core methodology frameworks, contract term extraction matrices, knowledge search queries, decision point frameworks, and professional memo structures.
- **Hybrid RAG System**: Combines metadata filtering with semantic search, enhanced by contract-specific term extraction, and a two-stage citation process for audit-ready evidence.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks to prevent truncation.
- **Professional Memo Generation**: Produces Big 4 quality accounting memos with narrative-driven analysis, professional formatting, dynamic table handling, and robust DOCX/HTML generation.
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
- **Modular Standard Modules**: Designed with re-usable architectural patterns across different accounting standards.

## External Dependencies

- **Streamlit**: Web application framework.
- **pandas**: Data manipulation and analysis.
- **unstructured**: Advanced PDF processing.
- **pdfplumber**: PDF text extraction.
- **PyPDF2**: Basic PDF handling.
- **ChromaDB**: Vector database for knowledge base.
- **OpenAI API**: Large language model interactions (`gpt-4o`, `gpt-4o-mini`, `gpt-5` for complex research).
- **FPDF**: PDF generation.
- **WeasyPrint**: HTML-to-PDF conversion.
- **python-docx**: Word document generation.
- **Camelot & Tabula-py**: Table extraction from PDFs.
- **PyMuPDF**: Coordinate-based layout analysis in PDF processing.

## Copy-Tweak-Go Standard Development Architecture

This section provides the systematic template for rapidly deploying new accounting standards using the proven ASC 606 architecture as foundation. To build a new standard tool, simply provide the methodology details below and the AI agent will generate all required components.

### Standard Development Template: [ASC XXX]

**🎯 Core Methodology Framework:**
```
Step 1: [METHODOLOGY_STEP_1_TITLE]
├── Focus: [KEY_ACCOUNTING_CONCEPT]  
├── Key Points: [DECISION_CRITERIA_LIST - includes embedded decision logic]
├── Citations: [ASC_PARAGRAPH_REFERENCES]
└── Expected Output: [ANALYSIS_CONCLUSION_TYPE]

Step 2: [METHODOLOGY_STEP_2_TITLE]  
├── Focus: [KEY_ACCOUNTING_CONCEPT]
├── Key Points: [DECISION_CRITERIA_LIST - includes embedded decision logic] 
├── Citations: [ASC_PARAGRAPH_REFERENCES]
└── Expected Output: [ANALYSIS_CONCLUSION_TYPE]

[Continue for all steps...]
```


**📋 What You Need to Provide for New ASC Standard:**

**ONLY provide the core methodology - I'll generate everything else automatically:**

```
🎯 METHODOLOGY REQUIREMENTS:

Step 1: [Step Title]
├── Focus: [What this step analyzes]  
├── Key Points: [Bullet list of evaluation criteria with embedded decision logic]
├── Citations: [Specific ASC paragraph references]

Step 2: [Step Title]  
├── Focus: [What this step analyzes]
├── Key Points: [Bullet list of evaluation criteria with embedded decision logic]
├── Citations: [Specific ASC paragraph references]

[Continue for all steps in your standard...]
```

**✅ What I'll Generate Automatically:**
- Knowledge search queries (based on your methodology concepts)
- Contract term extraction logic (derived from your key points and focus areas)  
- All technical components (step_analyzer.py, page.py, etc.)
- Professional memo template
- UI integration

**📝 Professional Memo Structure:**
```
Required sections:
- Executive Summary
- Background  
- [STANDARD_NAME] Analysis (contains all step results)
- Conclusion
- Issues for Further Investigation (if applicable)
```

**🚀 Deployment Instructions:**
Once methodology is provided, AI agent will automatically:

1. **Create Core Components:**
   - `asc[XXX]/step_analyzer.py` - Main analysis orchestration (ASC[XXX]StepAnalyzer class)
   - `asc[XXX]/knowledge_search.py` - Step-specific RAG queries (ASC[XXX]KnowledgeSearch class)
   - `asc[XXX]/asc[XXX]_page.py` - Streamlit UI interface (render_asc[XXX]_page function)
   - `asc[XXX]/templates/memo_template.md` - Professional memo template

2. **Configure Technical Architecture:**
   - Multi-call markdown generation system (adapted to standard's step count)
   - Step-specific prompt engineering with key_points containing decision logic
   - Contract term extraction logic for enhanced RAG queries
   - Knowledge base integration (existing asc[XXX]_knowledge_base/)

3. **Test Integration:**
   - RAG query optimization using Research Assistant
   - Citation validation against authoritative guidance  
   - End-to-end memo generation workflow
   - UI/UX consistency with existing standards

**⚠️ DEVELOPMENT PROTOCOL:**
- AI agent will build complete working tool based on methodology provided
- No user coding required - just provide accounting methodology details
- Follows same architectural patterns as proven ASC 606 system
- Maintains prompt protection rules for all user-provided content
- Leverages existing shared components (document processing, knowledge base, memo generation)

### Standard Development Status Tracker:
- ✅ ASC 606: Complete production system
- ✅ ASC 340-40: Complete production system  
- ✅ ASC 842: Complete production system (Copy-Tweak-Go deployment successful)
- ✅ ASC 805: Complete production system (Copy-Tweak-Go deployment successful)
- ✅ ASC 718: Complete production system (Copy-Tweak-Go deployment successful)
- 📋 Future standards: Template ready for rapid deployment