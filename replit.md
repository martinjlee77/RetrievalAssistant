# ASC 606 PDF Processing PoC

## Overview

This project is a RAG-based contract analysis tool that generates complete ASC 606 revenue recognition analyses. The system takes revenue contracts as input and produces structured professional memos following the 5-step ASC 606 model, using authoritative FASB guidance and Big 4 interpretative publications as primary sources, with LLM general knowledge as fallback for edge cases.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

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

### Frontend Architecture
- **Framework**: Streamlit web application
- **Layout**: Wide layout with expandable sidebar configuration
- **State Management**: Streamlit session state for processing results and checkpoints
- **User Interface**: Clean, professional interface with progress tracking and results visualization

### Backend Architecture
- **Processing Pipeline**: Modular processor architecture with separate concerns
- **Core Components**:
  - PDF extraction and parsing
  - Intelligent chunking with semantic awareness
  - Quality validation and scoring
  - Metadata enrichment
- **Error Handling**: Comprehensive logging and graceful error recovery

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