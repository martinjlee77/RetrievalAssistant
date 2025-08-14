#!/usr/bin/env python3
"""
Enhanced ASC 606 Knowledge Base Seeding Script
Uses paragraph-aware chunking architecture with proper file filtering
Populates ChromaDB with pure ASC 606 content only
"""

import os
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as embedding_functions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_asc_paragraphs(text: str) -> List[Tuple[str, str, str]]:
    """
    Extract ASC 606 paragraphs with proper structure preservation
    Returns: List of (paragraph_number, content, section_context)
    """
    paragraphs = []
    
    # Enhanced pattern to match ASC 606 paragraph numbers (606-10-XX-XX)
    paragraph_pattern = r'(606-10-\d{2}-\d{1,3}(?:[A-Za-z])*)'
    
    # Split by paragraph numbers but keep the numbers
    parts = re.split(f'({paragraph_pattern})', text)
    
    current_section = "Unknown"
    
    for i in range(1, len(parts), 2):  # Skip empty parts
        if i + 1 < len(parts):
            paragraph_num = parts[i].strip()
            content = parts[i + 1].strip()
            
            if content and len(content) > 50:  # Filter out very short content
                # Extract section context from paragraph number
                section_match = re.match(r'606-10-(\d{2})', paragraph_num)
                if section_match:
                    section_code = section_match.group(1)
                    section_map = {
                        '05': 'Overview and Background',
                        '10': 'Objectives',
                        '15': 'Scope',
                        '20': 'Glossary',
                        '25': 'Recognition',
                        '32': 'Measurement',
                        '45': 'Other Presentation Matters', 
                        '50': 'Disclosure',
                        '55': 'Implementation Guidance'
                    }
                    current_section = section_map.get(section_code, f"Section {section_code}")
                
                paragraphs.append((paragraph_num, content, current_section))
    
    # Fallback: if no paragraphs found, use sentence-based chunking
    if not paragraphs:
        sentences = text.split('. ')
        chunk_size = 800
        overlap = 100
        
        for i in range(0, len(sentences), max(1, chunk_size // 100)):
            chunk_sentences = sentences[i:i + (chunk_size // 100)]
            chunk_content = '. '.join(chunk_sentences)
            
            if len(chunk_content) > 100:
                paragraphs.append((f"chunk_{i}", chunk_content, current_section))
    
    return paragraphs

def chunk_interpretative_content(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    """
    Advanced chunking for EY interpretative guidance with topic awareness
    """
    chunks = []
    
    # Split by major topic indicators first
    topic_patterns = [
        r'\n(?=Step \d)',  # Revenue steps
        r'\n(?=Question \d)',  # Q&A sections
        r'\n(?=[A-Z][a-z]+ considerations?)',  # Considerations sections
        r'\n(?=Example \d)',  # Examples
        r'\n(?=Illustration \d)',  # Illustrations
    ]
    
    # Try topic-based splitting first
    sections = [text]
    for pattern in topic_patterns:
        new_sections = []
        for section in sections:
            new_sections.extend(re.split(pattern, section))
        sections = new_sections
    
    # Process each section
    for section in sections:
        section = section.strip()
        if len(section) < 200:  # Skip very short sections
            continue
            
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            # Break down large sections with overlap
            start = 0
            while start < len(section):
                end = start + chunk_size
                
                # Find good break point (sentence or paragraph)
                if end < len(section):
                    # Look for paragraph break first
                    para_break = section.rfind('\n\n', start, end)
                    if para_break > start + chunk_size // 2:
                        end = para_break + 2
                    else:
                        # Look for sentence break
                        sent_break = section.rfind('. ', start, end)
                        if sent_break > start + chunk_size // 2:
                            end = sent_break + 2
                
                chunk = section[start:end].strip()
                if chunk and len(chunk) > 100:
                    chunks.append(chunk)
                
                start = end - overlap
                if start >= len(section):
                    break
    
    return chunks

def process_asc606_file(filepath: Path) -> List[Dict[str, Any]]:
    """Process ASC 606 text file with paragraph-aware chunking"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract section info from filename
        filename = filepath.name.lower()
        
        # Map filename patterns to sections
        section_map = {
            '05_overview': ('05', 'Overview and Background'),
            '10_objectives': ('10', 'Objectives'),
            '15_scope': ('15', 'Scope'),
            '20_glossary': ('20', 'Glossary'),
            '25_recognition': ('25', 'Recognition'),
            '32_measurement': ('32', 'Measurement'),
            '45_other': ('45', 'Other Presentation Matters'),
            '50_disclosure': ('50', 'Disclosure'),
            '55_implementation': ('55', 'Implementation Guidance')
        }
        
        section_code = None
        section_title = 'Unknown Section'
        
        for pattern, (code, title) in section_map.items():
            if pattern in filename:
                section_code = code
                section_title = title
                break
        
        # Use paragraph-aware extraction
        paragraphs = extract_asc_paragraphs(content)
        
        documents = []
        for i, (paragraph_num, paragraph_content, context_section) in enumerate(paragraphs):
            documents.append({
                'content': paragraph_content,
                'metadata': {
                    'source': f'ASC {paragraph_num}' if paragraph_num.startswith('606') else f'ASC 606-10-{section_code}',
                    'source_file': filepath.name,
                    'section': section_code or 'Unknown',
                    'section_title': context_section,
                    'paragraph_number': paragraph_num,
                    'source_type': 'authoritative',
                    'chunk_index': i,
                    'standard': 'ASC 606',
                    'content_type': 'paragraph'
                }
            })
        
        logger.info(f"Processed {filepath.name}: {len(documents)} paragraphs")
        return documents
        
    except Exception as e:
        logger.error(f"Error processing file {filepath}: {e}")
        return []

def process_ey_document(filepath: Path) -> List[Dict[str, Any]]:
    """Process EY ASC 606 interpretative guidance document with advanced chunking"""
    try:
        if filepath.suffix.lower() == '.docx':
            from docx import Document
            doc = Document(filepath)
            content = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Use advanced interpretative chunking
        chunks = chunk_interpretative_content(content, chunk_size=1200, overlap=150)
        
        documents = []
        for i, chunk in enumerate(chunks):
            # Determine topic from chunk content
            topic = "General Guidance"
            if "Step 1" in chunk or "contract" in chunk[:100].lower():
                topic = "Contract Identification"
            elif "Step 2" in chunk or "performance obligation" in chunk[:100].lower():
                topic = "Performance Obligations"
            elif "Step 3" in chunk or "transaction price" in chunk[:100].lower():
                topic = "Transaction Price"
            elif "Step 4" in chunk or "allocat" in chunk[:100].lower():
                topic = "Price Allocation"
            elif "Step 5" in chunk or "recogni" in chunk[:100].lower():
                topic = "Revenue Recognition"
            elif "Question" in chunk[:50]:
                topic = "Q&A Implementation"
            elif "Example" in chunk[:50] or "Illustration" in chunk[:50]:
                topic = "Practical Examples"
            
            documents.append({
                'content': chunk,
                'metadata': {
                    'source': 'EY ASC 606 Interpretative Guide',
                    'source_file': filepath.name,
                    'section': f'Topic-{i+1}',
                    'section_title': topic,
                    'source_type': 'interpretative',
                    'chunk_index': i,
                    'standard': 'ASC 606',
                    'content_type': 'interpretative',
                    'topic_classification': topic.lower().replace(' ', '_')
                }
            })
        
        logger.info(f"Processed EY ASC 606 guide {filepath.name}: {len(documents)} chunks")
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
    
    # Process ONLY ASC 606 EY guidance documents (fixed contamination issue)
    ey_asc606_patterns = [
        "*ey*asc606*.docx",
        "*ey*606*.docx", 
        "*frd*606*.docx",
        "*frdbb*606*.docx"
    ]
    
    ey_files = []
    for pattern in ey_asc606_patterns:
        ey_files.extend(list(assets_dir.glob(pattern)))
    
    # Remove duplicates
    ey_files = list(set(ey_files))
    
    # Filter out non-ASC 606 files explicitly
    filtered_ey_files = []
    for filepath in ey_files:
        filename_lower = filepath.name.lower()
        # Skip files that are clearly for other standards
        if any(std in filename_lower for std in ['340-40', '340_40', '842', 'lessee', 'lease']):
            logger.info(f"Skipping non-ASC 606 file: {filepath.name}")
            continue
        # Only include if it's clearly ASC 606 related
        if any(indicator in filename_lower for indicator in ['asc606', '606', 'revenue']):
            filtered_ey_files.append(filepath)
            logger.info(f"Including ASC 606 EY file: {filepath.name}")
    
    for filepath in filtered_ey_files:
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