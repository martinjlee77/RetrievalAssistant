#!/usr/bin/env python3
"""
ASC 842 Leases Knowledge Base Seeding Script
Populates ChromaDB with ASC 842 authoritative and interpretative sources
Following proven ASC 340-40 pattern
"""

import os
import logging
import re
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as embedding_functions
from docx import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_bullet_formatting(text: str) -> str:
    """
    Fix bullet formatting issues like 'aTopic' -> 'a. Topic' and 'bCosts' -> 'b. Costs'
    """
    # Fix lettered bullets (a, b, c, etc.) followed immediately by capital letters
    text = re.sub(r'\b([a-z])\b([A-Z])', r'\1. \2', text)
    
    # Fix numbered sub-bullets like '1Topic' -> '1. Topic'  
    text = re.sub(r'\b(\d)([A-Z])', r'\1. \2', text)
    
    # Clean up navigation symbols from ASC text
    text = re.sub(r'[>·]', '', text)
    
    # Fix spacing issues around bullets
    text = re.sub(r'([a-z])\.\s*([A-Z])', r'\1. \2', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()


def chunk_by_paragraphs(text: str, min_chunk_size: int = 200) -> List[str]:
    """
    Split text by ASC paragraph numbers (e.g., 842-10-15-1) or by double newlines
    """
    chunks = []
    
    # First try to split by ASC paragraph numbers
    paragraph_pattern = r'(\d{3}-\d{2}-\d{2}-\d+)'
    parts = re.split(paragraph_pattern, text)
    
    if len(parts) > 3:  # Successfully found paragraph numbers
        current_chunk = ""
        current_paragraph = None
        
        for i, part in enumerate(parts):
            if re.match(paragraph_pattern, part):
                # This is a paragraph number
                if current_chunk and len(current_chunk) >= min_chunk_size:
                    chunks.append(current_chunk.strip())
                current_paragraph = part
                current_chunk = f"{part}\n"
            elif current_paragraph:
                # This is content following a paragraph number
                current_chunk += part
        
        # Add the last chunk
        if current_chunk and len(current_chunk) >= min_chunk_size:
            chunks.append(current_chunk.strip())
    
    # Fallback to double newline splitting if no paragraph numbers found
    if not chunks:
        paragraphs = text.split('\n\n')
        current_chunk = ""
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > min_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
    
    return [chunk for chunk in chunks if len(chunk.strip()) >= 50]


def extract_docx_text(filepath: Path) -> str:
    """Extract text from DOCX file"""
    try:
        doc = Document(filepath)
        text_content = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text.strip())
        
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_content.append(cell.text.strip())
        
        return '\n\n'.join(text_content)
    except Exception as e:
        logger.error(f"Error extracting text from {filepath}: {e}")
        return ""


def process_asc842_authoritative_file(filepath: Path) -> List[Dict[str, Any]]:
    """Process ASC 842 authoritative text file and return chunks with metadata"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean the content
        content = clean_bullet_formatting(content)
        
        # Extract section info from filename - ASC 842 structure
        filename = filepath.name.lower()
        
        # Map ASC 842 sections
        section_mapping = {
            'overview': {'section': '842-10-05', 'title': 'Overview and Background', 'topic': 'General'},
            'objectives': {'section': '842-10-10', 'title': 'Objectives', 'topic': 'General'},
            'scope': {'section': '842-10-15', 'title': 'Scope and Scope Exceptions', 'topic': 'General'},
            'glossary': {'section': '842-10-20', 'title': 'Glossary', 'topic': 'General'},
            'recognition': {'section': '842-10-25', 'title': 'Recognition', 'topic': 'General'},
            'measurement': {'section': '842-10-30', 'title': 'Initial Measurement', 'topic': 'Measurement'},
            'subsequent': {'section': '842-10-35', 'title': 'Subsequent Measurement', 'topic': 'Measurement'},
            'classification': {'section': '842-10-25', 'title': 'Lease Classification', 'topic': 'Classification'},
            'disclosure': {'section': '842-10-50', 'title': 'Disclosure', 'topic': 'Reporting'},
            'implementation': {'section': '842-10-55', 'title': 'Implementation Guidance', 'topic': 'Implementation'},
        }
        
        # Find matching section
        section_info = None
        for key, info in section_mapping.items():
            if key in filename:
                section_info = info
                break
        
        if not section_info:
            logger.warning(f"Unknown section for file: {filename}")
            section_info = {'section': 'Unknown', 'title': 'Unknown Section', 'topic': 'General'}
        
        # Split into chunks using paragraph-aware chunking
        chunks = chunk_by_paragraphs(content, min_chunk_size=200)
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunks.append({
                'content': chunk,
                'metadata': {
                    'source_file': filepath.name,
                    'source_type': 'authoritative',
                    'standard': 'ASC 842',
                    'section': section_info['section'],
                    'section_title': section_info['title'],
                    'topic': section_info['topic'],
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_id': f"asc842_auth_{filepath.stem}_{i}"
                }
            })
        
        logger.info(f"Processed {filepath.name}: {len(processed_chunks)} chunks")
        return processed_chunks
        
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return []


def process_ey_interpretative_file(filepath: Path) -> List[Dict[str, Any]]:
    """Process EY interpretative guidance file and return chunks with metadata"""
    try:
        # Extract text based on file type
        if filepath.suffix.lower() == '.docx':
            content = extract_docx_text(filepath)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        
        if not content.strip():
            logger.warning(f"No content extracted from {filepath}")
            return []
        
        # Clean the content
        content = clean_bullet_formatting(content)
        
        # Determine topic based on content keywords
        content_lower = content.lower()
        topic = 'General'
        if any(keyword in content_lower for keyword in ['classification', 'operating', 'finance']):
            topic = 'Classification'
        elif any(keyword in content_lower for keyword in ['measurement', 'present value', 'discount']):
            topic = 'Measurement'
        elif any(keyword in content_lower for keyword in ['disclosure', 'reporting']):
            topic = 'Reporting'
        elif any(keyword in content_lower for keyword in ['implementation', 'transition']):
            topic = 'Implementation'
        
        # Split into chunks
        chunks = chunk_by_paragraphs(content, min_chunk_size=300)
        
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunks.append({
                'content': chunk,
                'metadata': {
                    'source_file': filepath.name,
                    'source_type': 'interpretative',
                    'standard': 'ASC 842',
                    'firm': 'EY',
                    'topic': topic,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'chunk_id': f"asc842_ey_{filepath.stem}_{i}"
                }
            })
        
        logger.info(f"Processed {filepath.name}: {len(processed_chunks)} chunks, topic: {topic}")
        return processed_chunks
        
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return []


def create_asc842_knowledge_base():
    """Create and populate ASC 842 knowledge base"""
    
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path="./asc842_knowledge_base")
    
    # Set up embedding function
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model_name="text-embedding-ada-002"
    )
    
    # Create or get collection
    collection_name = "asc842_leases"
    try:
        # Try to delete existing collection
        client.delete_collection(name=collection_name)
        logger.info(f"Deleted existing collection: {collection_name}")
    except:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        embedding_function=openai_ef,
        metadata={"description": "ASC 842 Leases - Authoritative and Interpretative Guidance"}
    )
    
    # Process files from attached_assets
    attached_assets = Path("attached_assets")
    all_chunks = []
    
    # Process authoritative ASC 842 files (to be added)
    asc842_files = list(attached_assets.glob("*asc842*"))
    asc842_files.extend(list(attached_assets.glob("*842*")))
    
    for filepath in asc842_files:
        if filepath.is_file() and filepath.suffix.lower() in ['.txt', '.docx']:
            if 'ey' in filepath.name.lower():
                chunks = process_ey_interpretative_file(filepath)
            else:
                chunks = process_asc842_authoritative_file(filepath)
            all_chunks.extend(chunks)
    
    if not all_chunks:
        logger.warning("No ASC 842 files found in attached_assets. Please add:")
        logger.warning("- ASC 842 authoritative text files")
        logger.warning("- EY ASC 842 interpretative guidance")
        return
    
    # Prepare data for ChromaDB
    documents = [chunk['content'] for chunk in all_chunks]
    metadatas = [chunk['metadata'] for chunk in all_chunks]
    ids = [chunk['metadata']['chunk_id'] for chunk in all_chunks]
    
    # Add to collection in batches
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_metadata = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        
        collection.add(
            documents=batch_docs,
            metadatas=batch_metadata,
            ids=batch_ids
        )
        logger.info(f"Added batch {i//batch_size + 1}: {len(batch_docs)} chunks")
    
    # Summary statistics
    authoritative_count = len([c for c in all_chunks if c['metadata']['source_type'] == 'authoritative'])
    interpretative_count = len([c for c in all_chunks if c['metadata']['source_type'] == 'interpretative'])
    
    logger.info(f"Successfully created ASC 842 knowledge base:")
    logger.info(f"  Total chunks: {len(all_chunks)}")
    logger.info(f"  Authoritative: {authoritative_count}")
    logger.info(f"  Interpretative: {interpretative_count}")
    
    # Verify collection
    collection_count = collection.count()
    logger.info(f"Collection verification: {collection_count} documents in ChromaDB")
    
    return collection


if __name__ == "__main__":
    logger.info("Starting ASC 842 knowledge base seeding...")
    collection = create_asc842_knowledge_base()
    logger.info("ASC 842 knowledge base seeding complete!")