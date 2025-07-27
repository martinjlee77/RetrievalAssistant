"""
Multi-Standard Knowledge Base Manager
Extends ASC 606 knowledge base to support multiple standards
"""

import chromadb
from chromadb.config import Settings
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import os

class KnowledgeBaseManager:
    """Manager for multi-standard knowledge bases using ChromaDB"""
    
    def __init__(self, persist_directory: str = "asc606_knowledge_base"):
        # Use the existing ASC 606 knowledge base directory
        self.persist_directory = persist_directory
        self.setup_logging()
        self.client = None
        self.collections = {}
        self.embedding_function = None
        self.initialize_client()
        self.initialize_embedding_function()
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize_client(self):
        """Initialize ChromaDB client"""
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.logger.info("ChromaDB client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def initialize_embedding_function(self):
        """Initialize embedding function with dependency injection pattern"""
        try:
            import chromadb.utils.embedding_functions as embedding_functions
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
            self.logger.info("Embedding function initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding function: {e}")
            raise
    
    def get_collection(self, standard: str):
        """Get or create collection for a specific standard"""
        # Map to existing ASC 606 collection name for backward compatibility
        if standard == "ASC 606":
            collection_name = "asc606_paragraphs"
        else:
            collection_name = f"kb_{standard.lower().replace(' ', '_')}"
        
        if collection_name not in self.collections:
            try:
                if self.client and self.embedding_function:
                    collection = self.client.get_or_create_collection(
                        name=collection_name,
                        metadata={"standard": standard},
                        embedding_function=self.embedding_function  # Use dependency injection
                    )
                    self.collections[collection_name] = collection
                    self.logger.info(f"Collection '{collection_name}' ready for {standard}")
                else:
                    raise Exception("Client or embedding function not initialized")
            except Exception as e:
                self.logger.error(f"Failed to get/create collection for {standard}: {e}")
                raise
        
        return self.collections[collection_name]
    
    def search_relevant_guidance(self, standard: str, query_texts: List[str], step_context: Optional[str] = None, n_results: int = 5) -> List[Dict]:
        """
        Search for relevant guidance in a specific standard's knowledge base
        
        Args:
            standard: Accounting standard code (e.g., "ASC 606")
            query_texts: List of search query terms (supports multiple terms for better RAG)
            step_context: Context for filtering (e.g., "performance_obligations")
            n_results: Number of results to return
        """
        try:
            collection = self.get_collection(standard)
            
            # Build where clause for metadata filtering - skip for now since our current data may not have this metadata
            # where_clause = {"standard": standard}
            # if step_context:
            #     where_clause["step_context"] = step_context
            
            # Perform search with multiple query terms
            results = collection.query(
                query_texts=query_texts,  # Use the list directly for better search
                n_results=n_results,
                # where=where_clause,  # Skip metadata filtering for now
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    
                    formatted_results.append({
                        'content': doc,
                        'source': metadata.get('source', 'ASC 606'),
                        'section': metadata.get('section', 'Unknown'),
                        'relevance_score': 1 - distance,  # Convert distance to relevance
                        'rank': i + 1,
                        'metadata': metadata,
                        'source_type': metadata.get('source_type', 'unknown'),
                        'citation': self._format_citation(metadata)
                    })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error searching guidance for {standard}: {e}")
            return []
    
    def _format_citation(self, metadata: Dict) -> str:
        """Format citation based on source type"""
        source_type = metadata.get('source_type', 'unknown')
        
        if source_type == 'authoritative':
            section = metadata.get('section', 'Unknown Section')
            paragraph = metadata.get('paragraph_number', '')
            if paragraph:
                return f"ASC 606-{section}-{paragraph}"
            else:
                return f"ASC 606-{section}"
        
        elif source_type == 'interpretative':
            source_file = metadata.get('source_file', 'Unknown Source')
            return f"EY Guidance: {source_file}"
        
        else:
            return "Unknown Source"
    
    def get_collection_stats(self, standard: str) -> Dict[str, Any]:
        """Get statistics for a specific standard's knowledge base"""
        try:
            collection = self.get_collection(standard)
            count = collection.count()
            
            # Use correct collection name for display
            if standard == "ASC 606":
                collection_name = "asc606_paragraphs"
            else:
                collection_name = f"kb_{standard.lower().replace(' ', '_')}"
            
            return {
                'standard': standard,
                'total_chunks': count,
                'collection_name': collection_name,
                'status': 'active' if count > 0 else 'empty'
            }
        except Exception as e:
            self.logger.error(f"Error getting stats for {standard}: {e}")
            # Use correct collection name for display
            if standard == "ASC 606":
                collection_name = "asc606_paragraphs"
            else:
                collection_name = f"kb_{standard.lower().replace(' ', '_')}"
            
            return {
                'standard': standard,
                'total_chunks': 0,
                'collection_name': collection_name,
                'status': 'error'
            }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all knowledge bases"""
        stats = {}
        
        # Get stats for available standards
        standards = ["ASC 606", "ASC 842", "ASC 815", "ASC 326"]
        
        for standard in standards:
            stats[standard] = self.get_collection_stats(standard)
        
        return stats
    
    # REMOVED: initialize_standard method to resolve circular dependency
    # Knowledge base population should be handled by separate seeding scripts
    # This manager only provides access to collections, not population logic

# Singleton instance
_knowledge_base_manager = None

def get_knowledge_base_manager() -> KnowledgeBaseManager:
    """Get singleton knowledge base manager instance"""
    global _knowledge_base_manager
    if _knowledge_base_manager is None:
        _knowledge_base_manager = KnowledgeBaseManager()
    return _knowledge_base_manager