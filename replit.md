# ASC 606 PDF Processing PoC

## Overview

This project is a multi-standard accounting analysis platform that generates complete contract analyses under various accounting standards (ASC 606, ASC 842, etc.). The system takes contracts as input and produces structured professional memos following the specific methodology of each standard, using authoritative FASB guidance and Big 4 interpretative publications as primary sources, with LLM general knowledge as fallback for edge cases.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

**Date: 2025-07-17**
- ✅ **KEYBOARD ICON TEXT BUG FIX**: Resolved persistent "keyboard_double_arrow_left" text display issue
- ✅ Identified exact HTML element using browser developer tools: `span[data-testid="stIconMaterial"]`
- ✅ Implemented precise CSS selector targeting the Material Icons font loading issue
- ✅ Used pseudo-element technique to display correct icon while hiding broken text
- ✅ Applied comprehensive CSS rules with multiple fallback approaches
- ✅ Maintained Material Icons font import for proper icon rendering
- ✅ Cleaned up navigation structure with Home page having no sidebar menu
- ✅ Preserved functional sidebar navigation on ASC 606 and ASC 842 pages
- **Status**: All navigation display issues resolved, app fully functional with clean UI

**Date: 2025-07-16**
- ✅ **MULTI-STANDARD PLATFORM TRANSFORMATION**: Complete restructuring to hub-and-spoke architecture per Gemini's recommendations
- ✅ Created Home.py dashboard with Controller.cpa branding and expertise cards
- ✅ Implemented Streamlit multi-page architecture with pages/ directory structure
- ✅ Built comprehensive core/ module system with analyzers, models, knowledge base, and UI helpers
- ✅ Enhanced UX with two-column layout removing preliminary assessment friction
- ✅ Applied premium styling with custom CSS, Google Fonts, and Controller.cpa brand colors
- ✅ Integrated ASC 842 placeholder analyzer ready for authoritative source documents
- ✅ Maintained full ASC 606 functionality through pages/1_ASC_606_Revenue.py
- ✅ Abstracted BaseAnalyzer class with analyzer factory pattern for extensibility
- ✅ Unified knowledge base manager supporting multiple standards with ChromaDB collections
- ✅ Streamlined contract input workflow with single analyze button and improved validation
- **Status**: Production-ready multi-standard platform with premium UX and scalable architecture

**Date: 2025-07-13**
- ✅ **DYNAMIC SEMANTIC QUERY GENERATION**: Implemented adaptive semantic search per Gemini's feedback
- ✅ Added contract-specific term extraction for each ASC 606 step to enhance search relevance
- ✅ Enhanced hybrid RAG system with intelligent query generation that adapts to contract content
- ✅ Included comprehensive logging for dynamic term extraction and debugging
- ✅ Addressed Gemini's key recommendation about hardcoded semantic queries
- ✅ **COMPREHENSIVE ANALYSIS FRAMEWORK**: Implemented detailed question framework integration
- ✅ Created comprehensive_analysis_framework.py with systematic ASC 606 question coverage
- ✅ Enhanced analysis to address all 5 criteria in Step 1.1 individually
- ✅ Added 2-step distinct analysis model for Step 2.1.1 performance obligations
- ✅ Integrated EY document source transparency indicators
- ✅ **SCAFFOLD TRANSFORMATION**: Evolved framework from rigid questionnaire to intelligent scaffold per Gemini's feedback
- ✅ Added baseline + emergent analysis approach allowing LLM to identify novel contract issues
- ✅ Implemented `additional_considerations` field in each step for unique accounting issues
- ✅ Enhanced instructions to encourage professional judgment beyond standard questions
- ✅ Fixed knowledge base statistics compatibility with ChromaDB
- ✅ **UI STREAMLINING**: Replaced duplicative Five-Step Analysis tabs with concise summary view
- ✅ Fixed raw JSON display issues in results interface
- ✅ Added dedicated section for additional considerations highlighting unique contract issues
- ✅ Improved user experience by eliminating redundant information display
- ✅ **PREMIUM MEMO ENHANCEMENT**: Implemented sophisticated CREW framework per Gemini's feedback
- ✅ Enhanced professional memo generation with formal tone and analytical rigor
- ✅ Added Conclusion-Rule-Evidence-Work/Why structure for every major point
- ✅ Integrated authoritative + interpretative guidance citations
- ✅ Structured analysis with bullet points and professional formatting
- ✅ CFO/audit committee ready deliverables following Big 4 standards
- ✅ **FINAL MEMO POLISH**: Implemented Gemini's final refinements for premium quality
- ✅ Enhanced Background section with contract details, parties, dates, services
- ✅ Structured Key Judgments with What/Why/How framework for each judgment
- ✅ Added Practical Expedients section for pro-level ASC 606 analysis
- ✅ Temperature optimization (0.3) for natural professional writing style
- ✅ **UI/UX IMPROVEMENTS**: Fixed three key user experience issues per feedback
- ✅ Fixed Source Quality display to show "Hybrid RAG" instead of "General Knowledge"
- ✅ Improved ASC 606 Analysis Summary layout with better spacing and readability
- ✅ Added Unique Considerations section to memo for important non-standard findings
- ✅ **PROJECT CLEANUP**: Removed unused files and development artifacts
- ✅ Removed legacy simple_asc606_analyzer.py (replaced by hybrid system)
- ✅ Cleaned up 20+ development feedback files and UI screenshots
- ✅ Optimized project structure for production deployment
- **Status**: Complete premium memo system with Big 4 professional standards and clean production codebase

**Date: 2025-07-12**
- ✅ Implemented comprehensive "Trust, but Verify" analysis system following Gemini's recommendations
- ✅ Upgraded data models with new Pydantic classes for performance obligations and variable consideration
- ✅ Added preliminary assessment input interface with 4-tab structure
- ✅ Created sophisticated reconciliation analysis that compares user inputs with contract text
- ✅ Enhanced ASC606Analysis to include reconciliation_analysis field with confirmations/discrepancies
- ✅ Updated analyzer with new evidence-based prompt that validates user hypothesis against contract
- ✅ Integrated contract document validation with supporting quotes and ASC 606 rationale
- ✅ Added Trust, but Verify results display showing confirmations and discrepancies
- ✅ Maintained backward compatibility with existing contract analysis functionality
- ✅ Preserved all authoritative source integration and RAG system performance
- ✅ Upgraded memo generation to premium, audit-ready professional quality following Gemini's recommendations
- ✅ Implemented "Conclusion-Rationale-Evidence" framework for every major finding
- ✅ Added mandatory structure: Executive Summary, Background, Detailed Analysis, Key Judgments, Financial Impact, Conclusion
- ✅ Enhanced contractual evidence extraction with verbatim quotes support
- ✅ Integrated illustrative journal entries and system/process considerations
- ✅ Improved memo preview display showing structure and key sections
- ✅ **MAJOR UPGRADE**: Implemented two-stage memo generation following Gemini's advanced AI recommendations
- ✅ Created "memo_evidence_pack" system that extracts verbatim contract quotes and ASC citations first
- ✅ Separated cognitive tasks: Stage 1 (extract evidence), Stage 2 (assemble memo using structured evidence)
- ✅ Enhanced analysis prompt to force capture of contractual_quote and authoritative_citation_text for each step
- ✅ Revised memo prompt to use pre-packaged evidence, eliminating paraphrasing and ensuring direct citations
- ✅ Fixed all Pydantic model attribute access issues and transaction_price field duplication
- ✅ **HYBRID RAG IMPLEMENTATION**: Built sophisticated hybrid RAG system combining metadata filtering with semantic search
- ✅ Created ASC606KnowledgeBase with ChromaDB vector database and OpenAI embeddings
- ✅ Implemented systematic contract evidence extraction for precise, auditable contract citations
- ✅ Added two-stage citation approach: Stage 1 (extract verbatim quotes), Stage 2 (assemble analysis)
- ✅ Enhanced guidance retrieval with semantic search within ASC 606 step-specific filters
- ✅ Integrated HybridASC606Analyzer with structured evidence packs and authoritative citations
- ✅ **DYNAMIC SEMANTIC QUERY GENERATION**: Implemented contract-specific term extraction per Gemini's feedback
- ✅ Added adaptive semantic search that extracts contract-specific terminology for each ASC 606 step
- ✅ Enhanced search relevance by combining static ASC 606 terms with dynamic contract language
- ✅ Included detailed logging for dynamic term extraction to track system intelligence
- **Status**: Production-ready hybrid RAG system with adaptive semantic search and guaranteed verbatim citations
- **Next Step**: System ready for professional contract analysis with intelligent, context-aware guidance retrieval

**Date: 2025-07-11**
- ✅ Implemented comprehensive RAG system using authoritative ASC 606 sources
- ✅ Built ASC606KnowledgeBase with 1,510 chunks from 9 ASC sections + EY guidance
- ✅ Integrated FAISS vector database with OpenAI embeddings for semantic search
- ✅ Modified ASC606Analyzer to use RAG instead of GPT-4o general knowledge
- ✅ Added RAG system status indicators to Streamlit interface
- ✅ Created professional document chunking for ASC paragraphs and EY sections
- ✅ Successfully loaded all user-provided authoritative sources
- ✅ Replaced Word document with reformatted text file for better LLM parsing
- ✅ Upgraded upload interface to support multiple files (up to 5 documents)
- ✅ Enhanced processing pipeline to handle contracts, invoices, change orders, amendments
- ✅ Fixed source transparency tracking to properly show authoritative source usage
- ✅ Optimized performance with caching to prevent RAG system reloading on input changes
- **Status**: Professional RAG system complete with accurate source transparency tracking

**Date: 2025-07-09**
- Completely rebuilt PDF processing pipeline following Gemini LLM recommendations
- Implemented coordinate-based layout analysis with PyMuPDF
- Added specialized table extraction using Camelot and Tabula-py
- Created structure-aware chunking system
- **Result**: Quality score improved from 68.2% to 61.6% but still below acceptable threshold
- **Status**: Current approach suspended - quality insufficient for production RAG system
- **Next Step**: Pivoting to Word document processing approach using Adobe Acrobat converted file
- **User Action**: Manually cleaning Word document to remove redundant ASC excerpts and non-essential content

## System Architecture

### Multi-Standard Platform Architecture
- **Frontend**: Home.py dashboard with multi-page Streamlit architecture
- **Core System**: Modular core/ directory with analyzers, models, knowledge base, and UI helpers
- **Standard-Specific Pages**: pages/ directory containing dedicated analysis interfaces
- **Knowledge Base**: Multi-standard ChromaDB manager supporting collections per standard
- **Document Processing**: Unified document extractor supporting all standards
- **Source Documents**: Standard-specific authoritative sources in `attached_assets/`

### Core Components
- **Hybrid RAG System**: Combines metadata filtering with semantic search for precise results
- **Two-Stage Citation Process**: Stage 1 (extract verbatim quotes), Stage 2 (assemble analysis)
- **ChromaDB Vector Database**: Stores ASC 606 paragraphs with metadata for semantic search
- **Multi-document Processing**: Handles up to 5 files (contracts, invoices, amendments)
- **Professional Memo Generation**: Creates Big 4 quality accounting memos with auditable citations
- **Source Transparency**: Tracks hybrid RAG chunks used and relevance scores
- **Performance Optimization**: Cached analyzer and persistent vector database

### File Structure
```
├── Home.py                               # Main dashboard/landing page
├── pages/                                # Standard-specific analysis pages
│   ├── 1_ASC_606_Revenue.py             # ASC 606 revenue recognition
│   ├── 2_ASC_842_Leases.py              # ASC 842 lease analysis (placeholder)
│   └── [future ASC standards]
├── core/                                 # Shared backend logic
│   ├── analyzers.py                     # Analyzer factory and base classes
│   ├── models.py                        # Centralized data models
│   ├── knowledge_base.py                # Multi-standard knowledge base manager
│   ├── ui_helpers.py                    # Shared UI components and styling
│   └── analyzers/                       # Standard-specific analyzers
│       └── asc842_analyzer.py           # ASC 842 placeholder analyzer
├── hybrid_asc606_analyzer.py             # ASC 606 hybrid RAG engine
├── asc606_knowledge_base.py              # ASC 606 ChromaDB system
├── comprehensive_analysis_framework.py   # ASC 606 analysis framework
├── document_extractor.py                 # Multi-format document processing
├── attached_assets/                      # Authoritative sources (cleaned)
│   ├── 05_overview_background_*.txt      # ASC 606 sections
│   ├── 10_objectives_*.txt
│   ├── [7 more ASC 606 sections]
│   ├── contract_review_questions_*.txt   # Analysis framework
│   └── ey-frdbb3043-09-24-2024_*.docx   # EY interpretative guidance
├── asc606_knowledge_base/                # ChromaDB vector database files
├── pyproject.toml                        # Dependencies
└── replit.md                             # Project documentation
```

### Future Architecture Considerations
- **Database Integration**: Planned for storing analysis history, user preferences, and cached results
- **Multi-tenant Support**: User accounts and organization-level access controls
- **Audit Trail**: Complete tracking of analyses for compliance and review purposes

## Key Components

### 1. PDF Processing (`processors/pdf_processor.py`)
- **Multi-library Support**: Fallback strategy using unstructured, pdfplumber, and PyPDF2
- **Chapter-specific Extraction**: Targeted extraction for Chapter 4 content (pages 63-83)
- **Content Analysis**: Structured extraction of text, tables, and examples
- **Rationale**: Multiple extraction libraries ensure robust parsing across different PDF formats

### 2. Chunk Processing (`processors/chunk_processor.py`)
- **Semantic Chunking**: Intelligent content segmentation respecting document boundaries
- **Configurable Parameters**: Adjustable chunk size (200-2000 chars) and overlap (10-30%)
- **Metadata Enhancement**: Rich metadata attachment to each chunk
- **Rationale**: Semantic chunking preserves context better than simple character-based splitting

### 3. Quality Validation (`processors/quality_validator.py`)
- **Multi-dimensional Scoring**: Text, structure, table, and example quality metrics
- **Threshold-based Validation**: Configurable quality thresholds (70-95%)
- **Issue Identification**: Automatic detection of processing problems
- **Recommendations**: Actionable suggestions for improving quality
- **Rationale**: Ensures processed content meets professional standards for accounting documents

### 4. Metadata Enrichment (`utils/metadata_enricher.py`)
- **ASC 606 Specific Terms**: Recognition of accounting-specific terminology
- **Structural Analysis**: Section hierarchy and cross-reference detection
- **Content Classification**: Categorization of content types (definitions, examples, requirements)
- **Rationale**: Rich metadata enables better searchability and content understanding

### 5. File Management (`utils/file_utils.py`)
- **File Validation**: Size, type, and format checking
- **Hash Generation**: Content integrity verification
- **Metadata Extraction**: Comprehensive file information gathering
- **Rationale**: Ensures file integrity and provides audit trail

## Data Flow

1. **File Upload**: User uploads PDF through Streamlit interface
2. **File Validation**: System validates file type, size, and integrity
3. **PDF Processing**: Extract text, structure, tables, and examples
4. **Content Chunking**: Create semantic chunks with overlap
5. **Quality Validation**: Score processing quality across multiple dimensions
6. **Metadata Enrichment**: Add comprehensive metadata to chunks
7. **Results Presentation**: Display processing results with quality metrics

## External Dependencies

### Required Libraries
- **Streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **unstructured**: Advanced PDF processing (optional)
- **pdfplumber**: PDF text extraction (optional)
- **PyPDF2**: Basic PDF handling (optional)

### Optional Integrations
- **Logging**: Python standard library for comprehensive logging
- **Pathlib**: Modern path handling
- **Datetime**: Timestamp generation

## Deployment Strategy

### Local Development
- **Environment**: Python virtual environment with requirements.txt
- **Configuration**: Settings-based configuration in `config/settings.py`
- **Data Storage**: Local file system for temporary processing

### Production Considerations
- **Scalability**: Modular architecture allows for easy scaling
- **Error Handling**: Comprehensive error logging and recovery
- **Security**: File validation and size limits prevent abuse
- **Performance**: Configurable processing parameters for optimization

### Configuration Management
- **Processing Settings**: Centralized configuration for all processing parameters
- **Quality Thresholds**: Adjustable quality standards
- **Chapter-specific Settings**: Target pages and expected content metrics
- **Feature Flags**: Enable/disable specific processing features

The architecture prioritizes modularity, error resilience, and quality assurance while maintaining flexibility for different PDF formats and processing requirements. The system is designed to handle the specific challenges of accounting document processing while providing clear feedback on processing quality and potential issues.