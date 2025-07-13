"""
ASC 606 Hybrid RAG Knowledge Base
Combines metadata filtering with semantic search for precise, relevant results
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings
from docx import Document
from openai import OpenAI


@dataclass
class DocumentChunk:
    """Represents a chunk of text with metadata"""
    text: str
    source_file: str
    source_type: str  # 'authoritative' or 'interpretative'
    section: str
    paragraph_number: Optional[str] = None
    chunk_id: str = ""


class ASC606KnowledgeBase:
    """Hybrid RAG knowledge base for ASC 606 with metadata filtering + semantic search"""
    
    def __init__(self, persist_directory: str = "asc606_knowledge_base"):
        self.persist_directory = persist_directory
        self.logger = self._setup_logging()
        self.client = None
        self.collection = None
        self.chunks: List[DocumentChunk] = []
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def initialize_knowledge_base(self, force_rebuild: bool = False):
        """Initialize or load the knowledge base"""
        if force_rebuild or not self._knowledge_base_exists():
            self.logger.info("Building new ASC 606 knowledge base...")
            self._build_knowledge_base()
        else:
            self.logger.info("Loading existing ASC 606 knowledge base...")
            self._load_knowledge_base()
    
    def _knowledge_base_exists(self) -> bool:
        """Check if knowledge base already exists"""
        return Path(self.persist_directory).exists()
    
    def _build_knowledge_base(self):
        """Build the knowledge base from source documents"""
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection with OpenAI embeddings
        self.collection = self.client.get_or_create_collection(
            name="asc606_paragraphs",
            metadata={"description": "ASC 606 paragraphs with metadata filtering"},
            embedding_function=chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
        )
        
        # Load and chunk documents
        self._load_and_chunk_documents()
        
        # Add chunks to vector database
        self._add_chunks_to_collection()
        
        self.logger.info(f"Knowledge base built with {len(self.chunks)} chunks")
    
    def _load_knowledge_base(self):
        """Load existing knowledge base"""
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_collection("asc606_paragraphs")
        self.logger.info("Knowledge base loaded successfully")
    
    def _load_and_chunk_documents(self):
        """Load and chunk all ASC 606 documents"""
        assets_dir = Path("attached_assets")
        
        # ASC 606 authoritative sources
        asc_files = [
            "05_overview_background",
            "10_objectives", 
            "15_scope",
            "20_glossary",
            "25_recognition",
            "32_measurement",
            "45_other_presentation_matters",
            "50_disclosure",
            "55_implementation_guidance"
        ]
        
        # Load ASC 606 text files
        for file_prefix in asc_files:
            for file_path in assets_dir.glob(f"{file_prefix}*"):
                if file_path.suffix == '.txt':
                    self._chunk_asc_text_file(file_path, file_prefix)
        
        # Load EY interpretative guidance
        for file_path in assets_dir.glob("ey-*"):
            if file_path.suffix == '.docx':
                self._chunk_ey_document(file_path)
    
    def _chunk_asc_text_file(self, file_path: Path, section: str):
        """Chunk ASC 606 text file into paragraphs"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into paragraphs and extract paragraph numbers
            paragraphs = content.split('\n')
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph or len(paragraph) < 50:  # Skip very short paragraphs
                    continue
                
                # Extract ASC paragraph number if present
                paragraph_match = re.match(r'(\d+-\d+-\d+-\d+)', paragraph)
                paragraph_number = paragraph_match.group(1) if paragraph_match else None
                
                chunk = DocumentChunk(
                    text=paragraph,
                    source_file=file_path.name,
                    source_type="authoritative",
                    section=section,
                    paragraph_number=paragraph_number,
                    chunk_id=f"{section}_{len(self.chunks)}"
                )
                self.chunks.append(chunk)
                
        except Exception as e:
            self.logger.error(f"Error chunking {file_path}: {e}")
    
    def _chunk_ey_document(self, file_path: Path):
        """Chunk EY Word document into paragraphs"""
        try:
            doc = Document(file_path)
            
            for i, paragraph in enumerate(doc.paragraphs):
                text = paragraph.text.strip()
                if not text or len(text) < 50:  # Skip very short paragraphs
                    continue
                
                chunk = DocumentChunk(
                    text=text,
                    source_file=file_path.name,
                    source_type="interpretative",
                    section="ey_guidance",
                    chunk_id=f"ey_{i}"
                )
                self.chunks.append(chunk)
                
        except Exception as e:
            self.logger.error(f"Error chunking EY document {file_path}: {e}")
    
    def _add_chunks_to_collection(self):
        """Add chunks to ChromaDB collection"""
        texts = [chunk.text for chunk in self.chunks]
        metadatas = [
            {
                "source_file": chunk.source_file,
                "source_type": chunk.source_type,
                "section": chunk.section,
                "paragraph_number": chunk.paragraph_number or "",
                "chunk_id": chunk.chunk_id
            }
            for chunk in self.chunks
        ]
        ids = [chunk.chunk_id for chunk in self.chunks]
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            
            self.collection.add(
                documents=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
    
    def search_relevant_guidance(self, query: str, step_context: str, n_results: int = 5) -> List[Dict]:
        """
        Hybrid search: metadata filtering + semantic search
        
        Args:
            query: User's search query
            step_context: ASC 606 step context (e.g., "performance_obligations")
            n_results: Number of results to return
        """
        if not self.collection:
            raise ValueError("Knowledge base not initialized")
        
        # Step 1: Smart pre-filtering based on step context
        where_filter = self._get_step_filter(step_context)
        
        # Step 2: Semantic search within filtered results
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Step 3: Format results with citations
        formatted_results = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0]
        )):
            formatted_results.append({
                'text': doc,
                'source_type': metadata['source_type'],
                'section': metadata['section'],
                'paragraph_number': metadata['paragraph_number'],
                'source_file': metadata['source_file'],
                'relevance_score': 1 - distance,  # Convert distance to relevance
                'citation': self._format_citation(metadata)
            })
        
        return formatted_results
    
    def _get_step_filter(self, step_context: str) -> Dict:
        """Get metadata filter based on ASC 606 step context"""
        step_filters = {
            "contract_identification": {
                "$or": [
                    {"section": "05_overview_background"},
                    {"section": "10_objectives"},
                    {"section": "15_scope"}
                ]
            },
            "performance_obligations": {
                "$or": [
                    {"section": "25_recognition"},
                    {"section": "ey_guidance"}
                ]
            },
            "transaction_price": {
                "$or": [
                    {"section": "32_measurement"},
                    {"section": "ey_guidance"}
                ]
            },
            "price_allocation": {
                "$or": [
                    {"section": "32_measurement"},
                    {"section": "ey_guidance"}
                ]
            },
            "revenue_recognition": {
                "$or": [
                    {"section": "25_recognition"},
                    {"section": "55_implementation_guidance"},
                    {"section": "ey_guidance"}
                ]
            }
        }
        
        return step_filters.get(step_context, {})  # Return empty filter if no match
    
    def _format_citation(self, metadata: Dict) -> str:
        """Format citation based on source type"""
        if metadata['source_type'] == 'authoritative' and metadata['paragraph_number']:
            return f"ASC 606-{metadata['paragraph_number']}"
        elif metadata['source_type'] == 'interpretative':
            return f"EY Guidance - {metadata['source_file']}"
        else:
            return f"ASC 606 - {metadata['section']}"
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        if not self.collection:
            return {"status": "not_initialized"}
        
        total_chunks = self.collection.count()
        
        # Get breakdown by source type using chunk metadata
        authoritative_count = len([chunk for chunk in self.chunks if chunk.source_type == "authoritative"])
        interpretative_count = len([chunk for chunk in self.chunks if chunk.source_type == "interpretative"])
        
        return {
            "status": "ready",
            "total_chunks": total_chunks,
            "authoritative_chunks": authoritative_count,
            "interpretative_chunks": interpretative_count,
            "persist_directory": self.persist_directory
        }


# Singleton instance for application use
_knowledge_base = None

def get_knowledge_base() -> ASC606KnowledgeBase:
    """Get singleton knowledge base instance"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = ASC606KnowledgeBase()
        _knowledge_base.initialize_knowledge_base()
    return _knowledge_base


if __name__ == "__main__":
    # Test the knowledge base
    kb = ASC606KnowledgeBase()
    kb.initialize_knowledge_base(force_rebuild=True)
    
    # Test search
    results = kb.search_relevant_guidance(
        query="performance obligations distinct services",
        step_context="performance_obligations",
        n_results=3
    )
    
    print(f"Found {len(results)} relevant chunks:")
    for result in results:
        print(f"- {result['citation']}: {result['text'][:100]}...")