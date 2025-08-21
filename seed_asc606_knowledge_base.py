#!/usr/bin/env python3
"""
ASC 606 Knowledge Base Seeding Script

This script processes ASC 606 revenue recognition guidance documents and loads them
into ChromaDB for use by the ASC 606 analysis system.

Usage:
    python seed_asc606_knowledge_base.py

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

class ASC606KnowledgeBaseSeeder:
    """Seed ASC 606 knowledge base with authoritative guidance."""
    
    def __init__(self):
        self.db_path = "./asc606_knowledge_base"
        self.collection_name = "asc606_guidance"
        self.source_files = [
            "attached_assets/05_overview_background_1755741832788.txt",
            "attached_assets/10_objectives_1755741832788.txt", 
            "attached_assets/15_scope_1755741832789.txt",
            "attached_assets/20_glossary_1755741832790.txt",
            "attached_assets/25_recognition_1755741832790.txt",
            "attached_assets/32_measurement_1755741832791.txt",
            "attached_assets/45_other_presentation_matters_1755741832791.txt",
            "attached_assets/50_disclosure_1755741832792.txt",
            "attached_assets/55_implementation_guidance_1755741832793.txt"
        ]
        
    def initialize_database(self):
        """Initialize ChromaDB and create collection."""
        logger.info("Initializing ChromaDB for ASC 606...")
        
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
            existing_collection = self.client.get_collection(self.collection_name)
            self.client.delete_collection(self.collection_name)
            logger.info("Deleted existing ASC 606 collection")
        except Exception:
            pass
        
        # Initialize OpenAI embedding function (same as knowledge base)
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
        embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name="text-embedding-3-small"
        )
        
        # Create new collection with OpenAI embeddings
        self.collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=embedding_function,
            metadata={"description": "ASC 606 Revenue Recognition Authoritative Guidance"}
        )
        
        logger.info(f"Created collection: {self.collection_name}")
        
    def load_and_process_files(self) -> List[Dict[str, Any]]:
        """Load and process all ASC 606 source files."""
        documents = []
        
        for file_path in self.source_files:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
                
            logger.info(f"Processing: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract section info from filename and content
            section_info = self._extract_section_info(file_path, content)
            
            # Split into paragraphs for better chunking
            chunks = self._create_chunks(content, section_info)
            documents.extend(chunks)
            
        logger.info(f"Created {len(documents)} document chunks from {len(self.source_files)} files")
        return documents
        
    def _extract_section_info(self, file_path: str, content: str) -> Dict[str, str]:
        """Extract section metadata from file."""
        filename = os.path.basename(file_path)
        
        # Map filenames to section info
        section_mapping = {
            "05_overview_background": {
                "section_number": "05", 
                "section_name": "Overview and Background",
                "topic": "general"
            },
            "10_objectives": {
                "section_number": "10",
                "section_name": "Objectives", 
                "topic": "general"
            },
            "15_scope": {
                "section_number": "15",
                "section_name": "Scope and Scope Exceptions",
                "topic": "general"
            },
            "20_glossary": {
                "section_number": "20",
                "section_name": "Glossary",
                "topic": "definitions"
            },
            "25_recognition": {
                "section_number": "25", 
                "section_name": "Recognition",
                "topic": "contract_identification|performance_obligations"
            },
            "32_measurement": {
                "section_number": "32",
                "section_name": "Measurement", 
                "topic": "transaction_price|allocation"
            },
            "45_other_presentation": {
                "section_number": "45",
                "section_name": "Other Presentation Matters",
                "topic": "presentation"
            },
            "50_disclosure": {
                "section_number": "50",
                "section_name": "Disclosure",
                "topic": "disclosure"
            },
            "55_implementation_guidance": {
                "section_number": "55",
                "section_name": "Implementation Guidance and Illustrations",
                "topic": "implementation|examples"
            }
        }
        
        # Find matching section
        for key, info in section_mapping.items():
            if key in filename:
                return info
                
        return {
            "section_number": "unknown",
            "section_name": "Unknown Section", 
            "topic": "general"
        }
        
    def _create_chunks(self, content: str, section_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Create semantically meaningful chunks from content."""
        chunks = []
        
        # Split by ASC paragraph numbers (e.g., "606-10-25-1")
        asc_pattern = r'(606-\d+-\d+-\d+[A-Z]*)'
        parts = re.split(asc_pattern, content)
        
        current_chunk = ""
        current_paragraph = None
        
        for i, part in enumerate(parts):
            if re.match(asc_pattern, part):
                # Save previous chunk if it exists
                if current_chunk.strip() and current_paragraph:
                    chunks.append(self._create_chunk_metadata(
                        current_chunk.strip(), 
                        current_paragraph,
                        section_info
                    ))
                
                # Start new chunk
                current_paragraph = part
                current_chunk = part
                
            else:
                current_chunk += part
                
                # If chunk is getting large, split it
                if len(current_chunk) > 2000:
                    if current_paragraph:
                        chunks.append(self._create_chunk_metadata(
                            current_chunk.strip(),
                            current_paragraph, 
                            section_info
                        ))
                    current_chunk = ""
                    current_paragraph = None
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk_metadata(
                current_chunk.strip(),
                current_paragraph or "general",
                section_info
            ))
            
        # If no ASC patterns found, create chunks by content length
        if not chunks:
            text_chunks = self._chunk_by_length(content, 1500)
            for i, chunk_text in enumerate(text_chunks):
                chunks.append(self._create_chunk_metadata(
                    chunk_text,
                    f"{section_info['section_number']}-chunk-{i+1}",
                    section_info
                ))
        
        return chunks
        
    def _chunk_by_length(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks by length, preserving sentence boundaries."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
        
    def _create_chunk_metadata(self, text: str, paragraph_ref: str, section_info: Dict[str, str]) -> Dict[str, Any]:
        """Create chunk with comprehensive metadata."""
        
        # Determine step relevance
        step_relevance = self._determine_step_relevance(text, paragraph_ref)
        
        return {
            "text": text,
            "metadata": {
                "source": "ASC 606 Authoritative Guidance",
                "section_number": section_info["section_number"],
                "section_name": section_info["section_name"],
                "paragraph_reference": paragraph_ref,
                "topic": section_info["topic"],
                "step_relevance": "|".join(step_relevance),
                "document_type": "authoritative",
                "chunk_length": len(text)
            }
        }
        
    def _determine_step_relevance(self, text: str, paragraph_ref: str) -> List[str]:
        """Determine which ASC 606 steps this content is relevant to."""
        text_lower = text.lower()
        relevance = []
        
        # Step 1: Contract identification
        step1_keywords = ["contract", "agreement", "enforceable", "approved", "commercial substance", "collectibility", "probable"]
        if any(keyword in text_lower for keyword in step1_keywords) or "606-10-25-1" in paragraph_ref:
            relevance.append("step_1")
            
        # Step 2: Performance obligations
        step2_keywords = ["performance obligation", "distinct", "good", "service", "bundle", "separately identifiable"]
        if any(keyword in text_lower for keyword in step2_keywords) or "606-10-25-14" in paragraph_ref:
            relevance.append("step_2")
            
        # Step 3: Transaction price
        step3_keywords = ["transaction price", "consideration", "variable", "financing", "noncash", "time value"]
        if any(keyword in text_lower for keyword in step3_keywords) or "606-10-32-2" in paragraph_ref:
            relevance.append("step_3")
            
        # Step 4: Allocation
        step4_keywords = ["allocate", "allocation", "standalone selling price", "discount", "relative"]
        if any(keyword in text_lower for keyword in step4_keywords) or "606-10-32-28" in paragraph_ref:
            relevance.append("step_4")
            
        # Step 5: Recognition
        step5_keywords = ["recognize revenue", "satisfy", "performance obligation", "control", "over time", "point in time"]
        if any(keyword in text_lower for keyword in step5_keywords) or "606-10-25-27" in paragraph_ref:
            relevance.append("step_5")
            
        return relevance if relevance else ["general"]
        
    def add_documents_to_collection(self, documents: List[Dict[str, Any]]):
        """Add processed documents to ChromaDB collection."""
        logger.info("Adding documents to ChromaDB collection...")
        
        # Prepare data for ChromaDB
        ids = []
        texts = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            ids.append(f"asc606_chunk_{i+1}")
            texts.append(doc["text"])
            metadatas.append(doc["metadata"])
            
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))
            
            self.collection.add(
                ids=ids[i:batch_end],
                documents=texts[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
            
            logger.info(f"Added batch {i//batch_size + 1}: documents {i+1}-{batch_end}")
            
        logger.info(f"Successfully added {len(documents)} documents to collection")
        
    def verify_collection(self):
        """Verify the collection was created successfully."""
        logger.info("Verifying ASC 606 knowledge base...")
        
        # Get collection stats
        count = self.collection.count()
        logger.info(f"Total documents in collection: {count}")
        
        # Test a sample query
        results = self.collection.query(
            query_texts=["contract identification criteria"],
            n_results=3
        )
        
        logger.info("Sample query results:")
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            logger.info(f"  Result {i+1}: {metadata.get('paragraph_reference', 'N/A')} - {doc[:100]}...")
            
        return count > 0
        
    def run_seeding(self):
        """Execute the complete seeding process."""
        logger.info("Starting ASC 606 knowledge base seeding...")
        
        try:
            # Initialize database
            self.initialize_database()
            
            # Load and process files
            documents = self.load_and_process_files()
            
            if not documents:
                logger.error("No documents processed. Check source files.")
                return False
                
            # Add to collection
            self.add_documents_to_collection(documents)
            
            # Verify collection
            success = self.verify_collection()
            
            if success:
                logger.info("✅ ASC 606 knowledge base seeding completed successfully!")
                return True
            else:
                logger.error("❌ Knowledge base verification failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Seeding failed: {str(e)}")
            return False

def main():
    """Main entry point."""
    seeder = ASC606KnowledgeBaseSeeder()
    success = seeder.run_seeding()
    
    if success:
        print("\n🎉 ASC 606 Knowledge Base is ready!")
        print("You can now use the ASC 606 analysis system with full authoritative guidance.")
    else:
        print("\n❌ Seeding failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()