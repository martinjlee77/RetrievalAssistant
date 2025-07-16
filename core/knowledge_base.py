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
    
    def __init__(self, persist_directory: str = "knowledge_bases"):
        self.persist_directory = persist_directory
        self.setup_logging()
        self.client = None
        self.collections = {}
        self.initialize_client()
    
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
    
    def get_collection(self, standard: str):
        """Get or create collection for a specific standard"""
        collection_name = f"kb_{standard.lower().replace(' ', '_')}"
        
        if collection_name not in self.collections:
            try:
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"standard": standard}
                )
                self.collections[collection_name] = collection
                self.logger.info(f"Collection '{collection_name}' ready for {standard}")
            except Exception as e:
                self.logger.error(f"Failed to get/create collection for {standard}: {e}")
                raise
        
        return self.collections[collection_name]
    
    def search_relevant_guidance(self, standard: str, query: str, step_context: str = None, n_results: int = 5) -> List[Dict]:
        """
        Search for relevant guidance in a specific standard's knowledge base
        
        Args:
            standard: Accounting standard code (e.g., "ASC 606")
            query: Search query
            step_context: Context for filtering (e.g., "performance_obligations")
            n_results: Number of results to return
        """
        try:
            collection = self.get_collection(standard)
            
            # Build where clause for metadata filtering
            where_clause = {"standard": standard}
            if step_context:
                where_clause["step_context"] = step_context
            
            # Perform search
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'text': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0,
                        'source_type': results['metadatas'][0][i].get('source_type', 'unknown') if results['metadatas'] else 'unknown',
                        'citation': self._format_citation(results['metadatas'][0][i] if results['metadatas'] else {})
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
            
            return {
                'standard': standard,
                'total_chunks': count,
                'collection_name': f"kb_{standard.lower().replace(' ', '_')}",
                'status': 'active' if count > 0 else 'empty'
            }
        except Exception as e:
            self.logger.error(f"Error getting stats for {standard}: {e}")
            return {
                'standard': standard,
                'total_chunks': 0,
                'collection_name': f"kb_{standard.lower().replace(' ', '_')}",
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
    
    def initialize_standard(self, standard: str, force_rebuild: bool = False):
        """Initialize knowledge base for a specific standard"""
        if standard == "ASC 606":
            # Use existing ASC 606 knowledge base
            from asc606_knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            kb.initialize_knowledge_base(force_rebuild=force_rebuild)
            self.logger.info(f"ASC 606 knowledge base initialized")
        
        elif standard == "ASC 842":
            # Placeholder for ASC 842 - will be implemented when documents are available
            self.logger.info(f"ASC 842 knowledge base placeholder - awaiting authoritative documents")
        
        else:
            self.logger.warning(f"No initialization available for {standard}")

# Singleton instance
_knowledge_base_manager = None

def get_knowledge_base_manager() -> KnowledgeBaseManager:
    """Get singleton knowledge base manager instance"""
    global _knowledge_base_manager
    if _knowledge_base_manager is None:
        _knowledge_base_manager = KnowledgeBaseManager()
    return _knowledge_base_manager