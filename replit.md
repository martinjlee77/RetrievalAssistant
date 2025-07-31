# ASC 606 PDF Processing PoC

## Overview
This project is a multi-standard accounting analysis platform that generates complete contract analyses under various accounting standards (ASC 606, ASC 842, etc.). The system takes contracts as input and produces structured professional memos following the specific methodology of each standard. It uses authoritative FASB guidance and Big 4 interpretative publications as primary sources, with LLM general knowledge as fallback for edge cases. The business vision is to provide audit-ready, professional-quality accounting memos, adhering to Big 4 standards for accuracy and presentation, ultimately aiming for a comprehensive financial analysis platform.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Multi-Standard Platform Architecture
- **Frontend**: Streamlit multi-page application with a Home dashboard.
- **Core System**: Modular core components including analyzers, data models, knowledge base management, and UI helpers.
- **Standard-Specific Pages**: Dedicated interfaces for different accounting standards (e.g., ASC 606, ASC 842).
- **Knowledge Base**: Multi-standard ChromaDB manager supporting collections per standard.
- **Document Processing**: Unified document extractor supporting various formats.
- **Source Documents**: Standard-specific authoritative sources stored locally.

### Core Components
- **Hybrid RAG System**: Combines metadata filtering with semantic search for precise results, incorporating contract-specific term extraction for enhanced relevance.
- **Knowledge Base**: Contains 1,894 authoritative documents (ASC 606 official guidance + EY interpretative literature) in a ChromaDB vector database.
- **Two-Stage Citation Process**: Extracts verbatim quotes first, then assembles analysis using structured evidence to ensure direct and auditable citations.
- **Map-Reduce Contract Processing**: Analyzes full documents using overlapping chunks to prevent truncation.
- **Multi-document Processing**: Handles up to 5 files (contracts, invoices, amendments).
- **Professional Memo Generation**: Produces Big 4 quality accounting memos with audit-ready features, including narrative-driven analysis, professional formatting, and integration of actual contract data.
- **Source Transparency**: Tracks hybrid RAG chunks used and relevance scores.
- **System Integrity Monitoring**: Comprehensive logging and validation for detecting silent failures and ensuring data quality.
- **Performance Optimization**: Utilizes caching for analyzers and persistent vector databases, with concurrent execution of analysis steps and memo assembly for significant speed improvements.
- **Data Flow**: Ensures all user inputs (customer name, dates, focus areas, materiality, audience) flow systematically to the LLM for targeted analysis.
- **UI/UX Design**: Prioritizes professional, clean interfaces with clear navigation, simplified input forms using expanders and toggles, and immediate access to primary actions like document download and browser view. Styling adheres to a professional aesthetic with Times New Roman and Big 4 color schemes.

### File Structure
```
├── home.py                               # Streamlit app entry point with navigation
├── pages/                                # Streamlit pages
│   ├── home_content.py                   # Home page dashboard content
│   ├── asc606.py                         # ASC 606 revenue recognition
│   └── asc842.py                         # ASC 842 lease analysis (placeholder)
├── assets/                               # Static assets
│   └── images/
│       └── logo.png                      # Controller.cpa logo
├── utils/                                # Core utilities
│   ├── llm.py                           # OpenAI API calls, knowledge base, debugging tools
│   ├── prompt.py                        # Centralized prompt templates
│   ├── auth.py                          # Authentication utilities (placeholder)
│   ├── document_extractor.py            # Multi-format document processing
│   └── asc606_analyzer.py               # Consolidated ASC 606 hybrid analyzer
├── core/                                 # Shared backend logic
│   ├── analyzers.py                     # Analyzer factory and base classes
│   ├── models.py                        # Centralized data models
│   ├── knowledge_base.py                # Multi-standard knowledge base manager
│   └── ui_helpers.py                    # Shared UI components and styling
├── attached_assets/                      # Authoritative sources (cleaned)
├── asc606_knowledge_base/                # ChromaDB vector database (single source)
├── pyproject.toml                        # Dependencies
└── replit.md                             # Project documentation
```

## External Dependencies

- **Streamlit**: Primary framework for the web application interface.
- **pandas**: Used for data manipulation and analysis within the application.
- **unstructured**: Utilized for advanced PDF processing capabilities.
- **pdfplumber**: Employed for PDF text extraction.
- **PyPDF2**: Used for basic PDF handling.
- **ChromaDB**: Vector database for storing and managing the knowledge base.
- **OpenAI API**: For large language model (LLM) interactions, including `gpt-4o` for analysis and `gpt-4o-mini` for memo assembly.
- **FPDF**: For PDF generation.
- **WeasyPrint**: For HTML-to-PDF conversion, addressing Unicode issues.
- **python-docx**: For generating professional Word documents.
- **Camelot & Tabula-py**: Specialized tools for table extraction from PDFs.
- **PyMuPDF**: For coordinate-based layout analysis in PDF processing.