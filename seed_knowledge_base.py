#!/usr/bin/env python3
"""
Knowledge Base Seeding Script
Populates ChromaDB with ASC 606 authoritative sources from attached_assets
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as embedding_functions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Find the last sentence boundary within the chunk
        if end < len(text):
            last_period = text.rfind('.', start, end)
            if last_period > start + chunk_size // 2:  # Only adjust if reasonable
                end = last_period + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def process_asc606_file(filepath: Path) -> List[Dict[str, Any]]:
    """Process ASC 606 text file and return chunks with metadata"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract section info from filename
        filename = filepath.name.lower()
        
        # Map filenames to section info
        section_mapping = {
            '05_overview_background': {'section': '10-05', 'title': 'Overview and Background'},
            '10_objectives': {'section': '10-10', 'title': 'Objectives'},
            '15_scope': {'section': '10-15', 'title': 'Scope and Scope Exceptions'},
            '20_glossary': {'section': '10-20', 'title': 'Glossary'},
            '25_recognition': {'section': '10-25', 'title': 'Recognition'},
            '32_measurement': {'section': '10-32', 'title': 'Measurement'},
            '45_other_presentation_matters': {'section': '10-45', 'title': 'Other Presentation Matters'},
            '50_disclosure': {'section': '10-50', 'title': 'Disclosure'},
            '55_implementation_guidance': {'section': '10-55', 'title': 'Implementation Guidance'},
        }
        
        # Find matching section
        section_info = None
        for key, info in section_mapping.items():
            if key in filename:
                section_info = info
                break
        
        if not section_info:
            logger.warning(f"Unknown section for file: {filename}")
            section_info = {'section': 'Unknown', 'title': 'Unknown Section'}
        
        # Create chunks
        chunks = chunk_text(content, chunk_size=1200, overlap=150)
        
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                'content': chunk,
                'metadata': {
                    'source': f"ASC 606-{section_info['section']}",
                    'source_file': filepath.name,
                    'section': section_info['section'],
                    'section_title': section_info['title'],
                    'source_type': 'authoritative',
                    'chunk_index': i,
                    'standard': 'ASC 606'
                }
            })
        
        logger.info(f"Processed {filepath.name}: {len(documents)} chunks")
        return documents
        
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return []

def process_ey_document(filepath: Path) -> List[Dict[str, Any]]:
    """Process EY interpretative guidance document"""
    try:
        if filepath.suffix.lower() == '.docx':
            from docx import Document
            doc = Document(filepath)
            content = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        
        chunks = chunk_text(content, chunk_size=1500, overlap=200)
        
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                'content': chunk,
                'metadata': {
                    'source': 'EY FRDBB3043',
                    'source_file': filepath.name,
                    'section': f'Section {i+1}',
                    'section_title': 'EY Interpretative Guidance',
                    'source_type': 'interpretative',
                    'chunk_index': i,
                    'standard': 'ASC 606'
                }
            })
        
        logger.info(f"Processed EY document {filepath.name}: {len(documents)} chunks")
        return documents
        
    except Exception as e:
        logger.error(f"Error processing EY document {filepath}: {e}")
        return []

def seed_knowledge_base():
    """Main function to seed the knowledge base"""
    
    # Initialize ChromaDB
    persist_directory = "asc606_knowledge_base"
    client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )
    
    # Initialize embedding function
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"
    )
    
    # Reset collection if it exists
    collection_name = "asc606_paragraphs"
    try:
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing collection: {collection_name}")
    except Exception:
        pass  # Collection might not exist
    
    # Create fresh collection
    collection = client.create_collection(
        name=collection_name,
        metadata={"standard": "ASC 606"},
        embedding_function=embedding_function
    )
    logger.info(f"Created collection: {collection_name}")
    
    # Process all documents
    all_documents = []
    assets_dir = Path("attached_assets")
    
    # Process ASC 606 text files
    asc_files = list(assets_dir.glob("*_*.txt"))
    for filepath in asc_files:
        if any(pattern in filepath.name.lower() for pattern in ['05_overview', '10_objectives', '15_scope', '20_glossary', '25_recognition', '32_measurement', '45_other', '50_disclosure', '55_implementation']):
            documents = process_asc606_file(filepath)
            all_documents.extend(documents)
    
    # Process EY guidance documents
    ey_files = list(assets_dir.glob("*ey*.docx")) + list(assets_dir.glob("*frdbb*.docx"))
    for filepath in ey_files:
        documents = process_ey_document(filepath)
        all_documents.extend(documents)
    
    if not all_documents:
        logger.error("No documents found to process!")
        return
    
    # Add to ChromaDB in batches
    batch_size = 100
    total_added = 0
    
    for i in range(0, len(all_documents), batch_size):
        batch = all_documents[i:i + batch_size]
        
        documents = [doc['content'] for doc in batch]
        metadatas = [doc['metadata'] for doc in batch]
        ids = [f"doc_{total_added + j}" for j in range(len(batch))]
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        total_added += len(batch)
        logger.info(f"Added batch {i//batch_size + 1}: {len(batch)} documents (Total: {total_added})")
    
    # Verify seeding
    final_count = collection.count()
    logger.info(f"✅ SEEDING COMPLETE! Total documents in collection: {final_count}")
    
    # Test search functionality
    test_results = collection.query(
        query_texts=["performance obligations"],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    
    logger.info("✅ TEST SEARCH SUCCESSFUL!")
    for i, (doc, meta, distance) in enumerate(zip(test_results['documents'][0], test_results['metadatas'][0], test_results['distances'][0])):
        logger.info(f"  Result {i+1}: {meta['source']} - {meta['section']} (Distance: {distance:.3f})")
        logger.info(f"    Preview: {doc[:100]}...")

if __name__ == "__main__":
    try:
        seed_knowledge_base()
        print("🎉 Knowledge base seeding completed successfully!")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise