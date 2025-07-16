# ASC 606 Contract Analyzer - System Overview for Gemini LLM

## Project Purpose
A sophisticated AI-powered accounting analysis platform that analyzes uploaded contracts (PDF/Word) and generates complete professional accounting memos following ASC 606 revenue recognition standards. The system combines authoritative FASB literature with Big 4 interpretative guidance to produce audit-ready analyses with forensic-level precision.

## Core Architecture: Hybrid RAG System
- **Hybrid RAG**: Combines metadata filtering with semantic search for precise guidance retrieval
- **Two-Stage Citation**: Stage 1 extracts verbatim contract quotes, Stage 2 assembles professional analysis
- **ChromaDB Vector Database**: Stores 1,510 chunks from 9 ASC 606 sections + EY guidance
- **Dynamic Semantic Search**: Adapts queries based on contract-specific terminology
- **Professional Memo Generation**: Creates Big 4 quality memos using CREW framework

## Directory Structure & File Purposes

### Core Application Files (85KB total)

#### `contract_analyzer_app.py` (40KB)
**Purpose**: Main Streamlit web application interface
**Key Functions**:
- User interface for file upload (supports up to 5 files: contracts, invoices, amendments)
- Contract data input forms with 4-tab structure (Basic Info, Performance Obligations, Transaction Price, Additional Details)
- Analysis results display with step-by-step ASC 606 breakdown
- Professional memo preview and download
- Trust-but-verify reconciliation analysis showing confirmations/discrepancies
- Multi-standard platform ready (ASC 606 active, ASC 842/815/326 planned)

#### `hybrid_asc606_analyzer.py` (25KB)
**Purpose**: Core analysis engine using hybrid RAG system
**Key Functions**:
- Contract evidence extraction with verbatim quote capture
- Dynamic semantic query generation for each ASC 606 step
- Hybrid search combining metadata filtering + semantic similarity
- Two-stage analysis: evidence extraction → memo assembly
- Professional memo generation with CREW framework (Conclusion-Rule-Evidence-Work/Why)
- ASC606Analysis dataclass for structured results

#### `asc606_knowledge_base.py` (13KB)
**Purpose**: ChromaDB vector database management
**Key Functions**:
- Persistent vector database with 1,510 knowledge chunks
- Metadata filtering by ASC 606 step context
- Semantic search using OpenAI embeddings
- Source categorization (authoritative ASC 606 vs interpretative EY guidance)
- Knowledge base statistics and validation

#### `comprehensive_analysis_framework.py` (16KB)
**Purpose**: Analysis framework and prompt engineering
**Key Functions**:
- Comprehensive ASC 606 question framework integration
- Professional memo prompt templates
- Evidence formatting and citation structures
- Scaffold-based analysis approach (baseline + emergent considerations)

#### `document_extractor.py` (9KB)
**Purpose**: Multi-format document text extraction
**Key Functions**:
- PDF processing using pdfplumber and PyPDF2 fallback
- Word document processing via python-docx
- Text cleaning and normalization
- Extraction quality validation
- Garbled text detection

### Knowledge Base Assets (2.5MB total)

#### ASC 606 Authoritative Sources (9 files, 435KB)
```
05_overview_background_*.txt (6KB) - ASC 606 background and overview
10_objectives_*.txt (2KB) - Revenue recognition objectives
15_scope_*.txt (4KB) - Standard scope and applicability
20_glossary_*.txt (14KB) - Key definitions and terminology
25_recognition_*.txt (43KB) - Core recognition principles
32_measurement_*.txt (32KB) - Measurement and allocation guidance
45_other_presentation_matters_*.txt (3KB) - Presentation requirements
50_disclosure_*.txt (16KB) - Disclosure requirements
55_implementation_guidance_*.txt (320KB) - Detailed implementation examples
```

#### Analysis Framework
```
contract_review_questions_*.txt (16KB) - Comprehensive ASC 606 question framework
```

#### Interpretative Guidance
```
ey-frdbb3043-09-24-2024_*.docx (2MB) - EY Big 4 interpretative guidance
```

### System Database

#### `asc606_knowledge_base/` (160KB)
**Purpose**: ChromaDB persistent vector database
**Contents**:
- `chroma.sqlite3` - Vector embeddings and metadata for 1,510 knowledge chunks
- Indexed by ASC 606 step, source type, and semantic content

### Configuration Files

#### `pyproject.toml`
**Purpose**: Python dependencies and project configuration
**Key Dependencies**:
- `streamlit` - Web application framework
- `openai` - GPT-4o API integration
- `chromadb` - Vector database
- `pdfplumber`, `pypdf2` - PDF processing
- `python-docx` - Word document processing

#### `replit.md`
**Purpose**: Project documentation and user preferences
**Contents**:
- Development history and architectural decisions
- User communication preferences (simple, everyday language)
- System architecture documentation
- Recent changes and implementation notes

## Key System Capabilities

### 1. **Multi-Document Processing**
- Handles contracts, invoices, amendments, change orders
- Combines multiple files into unified analysis
- Quality validation for extraction accuracy

### 2. **Hybrid RAG Intelligence**
- Metadata filtering by ASC 606 step context
- Dynamic semantic query generation from contract content
- Authoritative source prioritization over interpretative guidance

### 3. **Professional Memo Generation**
- Big 4 accounting firm quality standards
- CREW framework (Conclusion-Rule-Evidence-Work/Why)
- Structured sections: Executive Summary, Background, Analysis, Key Judgments, Financial Impact
- Verbatim contract quotes with precise ASC 606 citations

### 4. **Trust-But-Verify Analysis**
- Reconciliation between user preliminary assessment and contract evidence
- Confirmation/discrepancy identification
- Supporting rationale for all findings

### 5. **Audit-Ready Output**
- CFO/audit committee ready deliverables
- Forensic-level analysis with complete audit trail
- Source transparency showing knowledge chunks used

## Technical Implementation Details

### Cost Structure
- ~18 cents per analysis using GPT-4o
- ChromaDB provides persistent storage (no rebuild required)
- Optimized for production deployment

### Performance Optimizations
- Cached analyzer initialization
- Persistent vector database
- Streamlit session state management
- Parallel document processing

### Quality Assurance
- Two-stage citation system prevents paraphrasing
- Verbatim quote extraction with source verification
- Professional memo validation
- Knowledge base statistics tracking

## Deployment Status
- Production-ready codebase
- Clean directory structure (1MB+ development artifacts removed)
- All premium features functional
- Ready for Replit deployment

This system represents a sophisticated blend of traditional accounting knowledge with modern AI capabilities, designed specifically for professional accounting analysis with Big 4 firm quality standards.