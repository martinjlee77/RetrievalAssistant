#!/usr/bin/env python3
"""
ASC 805 Knowledge Base Seeding Script

This script processes ASC 805 business combinations guidance documents and loads them
into ChromaDB for use by the ASC 805 analysis system.

Usage:
    python seed_asc805_knowledge_base.py

Author: Accounting Platform Team
"""

import os
import sys
import logging
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ASC805KnowledgeBaseSeeder:
    """Seed ASC 805 knowledge base with authoritative guidance."""
    
    def __init__(self):
        self.db_path = "./asc805_knowledge_base"
        self.collection_name = "asc805_guidance"
        self.source_files = [
            "attached_assets/10 Overall_1756770557561.txt",
            "attached_assets/20 Identifiable Assets and Liabilities, and Any Noncontrolling Interest_1756770557563.txt", 
            "attached_assets/30 Goodwill or Gain from Bargain Purchase, Including Consideration Transferred_1756770557564.txt",
            "attached_assets/40 Reverse Acquisitions_1756770557564.txt",
            "attached_assets/50 Related Issues_1756770557564.txt",
            "attached_assets/60 Joint Venture Formations_1756770557565.txt"
        ]
        
    def initialize_database(self):
        """Initialize ChromaDB and create collection."""
        logger.info("Initializing ChromaDB for ASC 805...")
        
        # Create database directory
        os.makedirs(self.db_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Delete existing collection if it exists
        try:
            existing_collections = [col.name for col in self.client.list_collections()]
            if self.collection_name in existing_collections:
                self.client.delete_collection(name=self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} does not exist, creating new one")
        except Exception as e:
            logger.info(f"Collection cleanup: {str(e)}, proceeding with creation")
        
        # Create new collection with OpenAI embeddings
        self.collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-ada-002"
            )
        )
        
        logger.info(f"Created collection: {self.collection_name}")
    
    def load_and_process_files(self) -> List[Dict[str, Any]]:
        """Load and process all ASC 805 source files."""
        all_chunks = []
        
        for file_path in self.source_files:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
                
            logger.info(f"Processing {file_path}...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract section name from filename for metadata
                section_name = os.path.basename(file_path).split('_')[0]
                
                # Split into chunks
                chunks = self.create_chunks(content, section_name)
                all_chunks.extend(chunks)
                
                logger.info(f"Created {len(chunks)} chunks from {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                continue
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
    
    def create_chunks(self, text: str, section: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Create overlapping chunks from text content."""
        # Clean the text
        text = self.clean_text(text)
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            # Calculate end position
            end = start + chunk_size
            
            # If this isn't the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings within the overlap zone
                search_start = max(start + chunk_size - overlap, start + chunk_size // 2)
                search_end = min(end + overlap, len(text))
                
                # Find the best break point (period, exclamation, or question mark followed by space/newline)
                best_break = end
                for i in range(search_end - 1, search_start - 1, -1):
                    if text[i] in '.!?' and i + 1 < len(text) and text[i + 1] in ' \n\t':
                        best_break = i + 1
                        break
                
                end = best_break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Only add non-empty chunks
                chunks.append({
                    'id': f"{section}_{chunk_id}",
                    'text': chunk_text,
                    'metadata': {
                        'source': section,
                        'chunk_id': chunk_id,
                        'content_type': 'asc805_guidance'
                    }
                })
                chunk_id += 1
            
            # Move start position with overlap
            start = max(end - overlap, start + 1)  # Ensure we make progress
        
        return chunks
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\(\)\[\]\-\$\%\&\@\#\+\=\*\/\\\'\"]', ' ', text)
        
        # Clean up multiple spaces again after character removal
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def add_chunks_to_collection(self, chunks: List[Dict[str, Any]]):
        """Add processed chunks to ChromaDB collection."""
        if not chunks:
            logger.warning("No chunks to add to collection")
            return
        
        # Prepare data for batch insertion
        ids = [chunk['id'] for chunk in chunks]
        documents = [chunk['text'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        
        # Add to collection in batches to avoid memory issues
        batch_size = 100
        
        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))
            
            self.collection.add(
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
            
            logger.info(f"Added batch {i//batch_size + 1}: {batch_end - i} chunks")
        
        logger.info(f"Successfully added {len(chunks)} total chunks to collection")
    
    def verify_collection(self):
        """Verify the collection was created properly."""
        try:
            count = self.collection.count()
            logger.info(f"Collection verification: {count} documents in {self.collection_name}")
            
            # Test a simple query
            results = self.collection.query(
                query_texts=["business combination"],
                n_results=3
            )
            
            if results and results['documents']:
                logger.info("Sample query successful - collection is working properly")
                logger.info(f"Sample result: {results['documents'][0][0][:100]}...")
            else:
                logger.warning("Sample query returned no results")
                
        except Exception as e:
            logger.error(f"Collection verification failed: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the seeded knowledge base."""
        try:
            total_docs = self.collection.count()
            
            # Get sample of documents to analyze
            sample_results = self.collection.get()
            
            if sample_results and sample_results['documents']:
                # Calculate average document length
                doc_lengths = [len(doc) for doc in sample_results['documents']]
                avg_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0
                
                # Count documents by source
                source_counts = {}
                if sample_results['metadatas']:
                    for metadata in sample_results['metadatas']:
                        source = metadata.get('source', 'unknown')
                        source_counts[source] = source_counts.get(source, 0) + 1
                
                return {
                    'total_documents': total_docs,
                    'average_document_length': round(avg_length, 1),
                    'source_distribution': source_counts,
                    'files_processed': len(self.source_files)
                }
            else:
                return {
                    'total_documents': total_docs,
                    'average_document_length': 0,
                    'source_distribution': {},
                    'files_processed': len(self.source_files)
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {'error': str(e)}

def main():
    """Main execution function."""
    logger.info("Starting ASC 805 Knowledge Base seeding process...")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    try:
        # Initialize seeder
        seeder = ASC805KnowledgeBaseSeeder()
        
        # Initialize database
        seeder.initialize_database()
        
        # Load and process files
        chunks = seeder.load_and_process_files()
        
        if not chunks:
            logger.error("No chunks created from source files")
            sys.exit(1)
        
        # Add chunks to collection
        seeder.add_chunks_to_collection(chunks)
        
        # Verify collection
        seeder.verify_collection()
        
        # Get and display statistics
        stats = seeder.get_statistics()
        logger.info("ASC 805 Knowledge Base Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("ASC 805 Knowledge Base seeding completed successfully!")
        
    except Exception as e:
        logger.error(f"Fatal error during seeding process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()