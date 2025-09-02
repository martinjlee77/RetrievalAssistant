#!/usr/bin/env python3
"""
ASC 606 Revenue Recognition Knowledge Base Seeding Script
Populates ChromaDB with ASC 606 authoritative and interpretative sources
Following proven ASC 340-40 superior pattern
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
    Split text by ASC paragraph numbers (e.g., 606-10-25-1) or by double newlines
    """
    chunks = []
    
    # First try to split by ASC paragraph numbers
    paragraph_pattern = r'(\d{3}-\d{2}-\d{2}-\d+[A-Z]*)'
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
        potential_chunks = text.split('\n\n')
        current_chunk = ""
        
        for chunk in potential_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
                
            if len(current_chunk + chunk) < 1200:  # Target chunk size
                current_chunk += f"\n\n{chunk}" if current_chunk else chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = chunk
        
        if current_chunk:
            chunks.append(current_chunk.strip())
    
    return [chunk for chunk in chunks if len(chunk.strip()) >= min_chunk_size]


def process_asc606_authoritative_file(filepath: Path) -> List[Dict[str, Any]]:
    """Process ASC 606 authoritative text file and return chunks with metadata"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean bullet formatting issues
        content = clean_bullet_formatting(content)
        
        # Create chunks based on paragraph structure
        chunks = chunk_by_paragraphs(content)
        
        documents = []
        for i, chunk in enumerate(chunks):
            # Extract paragraph number if present
            paragraph_match = re.search(r'(606-\d{2}-\d{2}-\d+[A-Z]*)', chunk)
            paragraph_number = paragraph_match.group(1) if paragraph_match else None
            
            # Determine section from paragraph number or filename
            section = "Unknown"
            section_title = "Unknown Section"
            
            if paragraph_number:
                section_part = paragraph_number.split('-')[2]
                section_mapping = {
                    '05': 'Overview and Background',
                    '10': 'Objectives',
                    '15': 'Scope and Scope Exceptions', 
                    '20': 'Glossary',
                    '25': 'Recognition',
                    '32': 'Measurement',
                    '45': 'Other Presentation Matters',
                    '50': 'Disclosure',
                    '55': 'Implementation Guidance and Illustrations'
                }
                section_title = section_mapping.get(section_part, 'Unknown Section')
                section = f"606-{section_part}"
            else:
                # Extract from filename for section identification
                filename = filepath.name.lower()
                if 'overview' in filename or '05_overview' in filename:
                    section = "606-10-05"
                    section_title = "Overview and Background"
                elif 'objectives' in filename or '10_objectives' in filename:
                    section = "606-10-10"
                    section_title = "Objectives"
                elif 'scope' in filename or '15_scope' in filename:
                    section = "606-10-15" 
                    section_title = "Scope and Scope Exceptions"
                elif 'glossary' in filename or '20_glossary' in filename:
                    section = "606-10-20"
                    section_title = "Glossary"
                elif 'recognition' in filename or '25_recognition' in filename:
                    section = "606-10-25"
                    section_title = "Recognition"
                elif 'measurement' in filename or '32_measurement' in filename:
                    section = "606-10-32"
                    section_title = "Measurement"
                elif 'presentation' in filename or '45_other' in filename:
                    section = "606-10-45"
                    section_title = "Other Presentation Matters"
                elif 'disclosure' in filename or '50_disclosure' in filename:
                    section = "606-10-50"
                    section_title = "Disclosure"
                elif 'implementation' in filename or '55_implementation' in filename:
                    section = "606-10-55"
                    section_title = "Implementation Guidance and Illustrations"
            
            documents.append({
                'content': chunk,
                'metadata': {
                    'source': f"ASC {section}" if paragraph_number else "ASC 606",
                    'source_file': filepath.name,
                    'section': section,
                    'section_title': section_title,
                    'paragraph_number': paragraph_number or "unknown",
                    'source_type': 'authoritative',
                    'chunk_index': str(i),
                    'standard': 'ASC 606'
                }
            })
        
        logger.info(f"Processed {filepath.name}: {len(documents)} chunks")
        return documents
        
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return []


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks (matching ASC 340 approach)"""
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


def process_ey_interpretative_file(filepath: Path) -> List[Dict[str, Any]]:
    """Process EY interpretative guidance document using ASC 340 pattern"""
    try:
        if filepath.suffix.lower() == '.docx':
            doc = Document(filepath)
            content = '\n'.join([para.text for para in doc.paragraphs if para.text and para.text.strip()])
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Clean bullet formatting
        content = clean_bullet_formatting(content)
        
        # Use same chunking as ASC 340 - smaller chunk size for token limits
        chunks = chunk_text(content, chunk_size=800, overlap=100)
        
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                'content': chunk,
                'metadata': {
                    'source': 'EY ASC 606 Guide',
                    'source_file': filepath.name,
                    'section': f'Section {i+1}',
                    'section_title': 'EY Interpretative Guidance',
                    'source_type': 'interpretative',
                    'chunk_index': str(i),
                    'standard': 'ASC 606'
                }
            })
        
        logger.info(f"Processed {filepath.name}: {len(documents)} chunks")
        return documents
        
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return []


def initialize_chromadb_client(persist_dir: str = "asc606_knowledge_base"):
    """Initialize ChromaDB client with embedding function"""
    try:
        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        
        logger.info("ChromaDB client initialized successfully")
        return client, embedding_function
        
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB client: {e}")
        raise


def seed_asc606_knowledge_base():
    """Main function to seed ASC 606 knowledge base"""
    
    print("=== ASC 606 REVENUE RECOGNITION KNOWLEDGE BASE SEEDING ===\n")
    
    # Initialize ChromaDB
    client, embedding_function = initialize_chromadb_client()
    
    # Create ASC 606 collection
    collection_name = "asc606_guidance"
    try:
        # Check if collection exists and delete if so
        try:
            existing_collections = [col.name for col in client.list_collections()]
            if collection_name in existing_collections:
                client.delete_collection(name=collection_name)
                logger.info(f"Deleted existing collection: {collection_name}")
        except Exception as e:
            logger.info(f"Collection cleanup: {str(e)}, proceeding with creation")
        
        collection = client.create_collection(
            name=collection_name,
            metadata={"standard": "ASC 606"},
            embedding_function=embedding_function
        )
        logger.info(f"Collection '{collection_name}' ready")
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        return
    
    # Process source files
    all_documents = []
    
    # ASC 606 source files (authoritative)
    asc606_files = [
        "attached_assets/05_overview_background_1756771341995.txt",
        "attached_assets/10_objectives_1756771341996.txt", 
        "attached_assets/15_scope_1756771341997.txt",
        "attached_assets/20_glossary_1756771341998.txt",
        "attached_assets/25_recognition_1756771341999.txt",
        "attached_assets/32_measurement_1756771341999.txt",
        "attached_assets/45_other_presentation_matters_1756771342000.txt",
        "attached_assets/50_disclosure_1756771342000.txt",
        "attached_assets/55_implementation_guidance_1756771342001.txt"
    ]
    
    # Process ASC 606 authoritative files
    for file_path in asc606_files:
        asc_file = Path(file_path)
        if asc_file.exists():
            logger.info(f"Processing authoritative file: {asc_file.name}")
            asc_documents = process_asc606_authoritative_file(asc_file)
            all_documents.extend(asc_documents)
            logger.info(f"Added {len(asc_documents)} authoritative chunks")
        else:
            logger.error(f"Authoritative file not found: {asc_file}")
    
    # Look for EY interpretative guides (if any exist)
    ey_files = list(Path("attached_assets").glob("*ey*606*.docx"))
    ey_files.extend(list(Path("attached_assets").glob("*606*ey*.docx")))
    
    for ey_file in ey_files:
        if ey_file.exists():
            logger.info(f"Processing interpretative file: {ey_file.name}")
            ey_documents = process_ey_interpretative_file(ey_file)
            all_documents.extend(ey_documents)
            logger.info(f"Added {len(ey_documents)} interpretative chunks")
    
    # Load into ChromaDB
    if all_documents:
        try:
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            
            for i, doc in enumerate(all_documents):
                ids.append(f"asc606_chunk_{i}")
                documents.append(doc['content'])
                metadatas.append(doc['metadata'])
            
            # Add to collection in batches
            batch_size = 100
            for i in range(0, len(all_documents), batch_size):
                batch_end = min(i + batch_size, len(all_documents))
                
                collection.add(
                    ids=ids[i:batch_end],
                    documents=documents[i:batch_end],
                    metadatas=metadatas[i:batch_end]
                )
                
                logger.info(f"Added batch {i//batch_size + 1}: {batch_end - i} chunks")
            
            logger.info(f"Successfully loaded {len(all_documents)} chunks into {collection_name}")
            
            # Verify the load
            count = collection.count()
            logger.info(f"Collection now contains {count} documents")
            
            # Show sample of what was loaded
            sample_results = collection.query(
                query_texts=["contract identification criteria"],
                n_results=3,
                include=["documents", "metadatas"]
            )
            
            print("\n=== SAMPLE LOADED CONTENT ===")
            for i, doc in enumerate(sample_results['documents'][0][:2]):
                metadata = sample_results['metadatas'][0][i]
                print(f"\nSample {i+1}:")
                print(f"Source: {metadata.get('source', 'Unknown')}")
                print(f"Type: {metadata.get('source_type', 'Unknown')}")
                print(f"Section: {metadata.get('section_title', 'Unknown')}")
                print(f"Content preview: {doc[:200]}...")
            
            print(f"\n✅ ASC 606 knowledge base seeding completed successfully!")
            print(f"   - Authoritative chunks: {len([d for d in all_documents if d['metadata']['source_type'] == 'authoritative'])}")
            print(f"   - Interpretative chunks: {len([d for d in all_documents if d['metadata']['source_type'] == 'interpretative'])}")
            print(f"   - Total chunks: {len(all_documents)}")
            
        except Exception as e:
            logger.error(f"Failed to load documents into ChromaDB: {e}")
            raise
    else:
        logger.error("No documents to load")


if __name__ == "__main__":
    try:
        seed_asc606_knowledge_base()
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        print(f"❌ Seeding failed: {e}")