"""
Shared Knowledge Base Module

This module provides a clean interface to ChromaDB for all accounting standards.
Each standard has its own database but uses the same search functionality.

Author: Accounting Platform Team
"""

import chromadb
import openai
import os
import logging
from typing import List, Dict, Any, Optional
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class SharedKnowledgeBase:
    """
    Simple, clean interface to knowledge base search for any accounting standard.
    """
    
    def __init__(self, database_path: str, collection_name: str):
        """
        Initialize knowledge base for a specific accounting standard.
        
        Args:
            database_path: Path to the ChromaDB database directory
            collection_name: Name of the collection (e.g., "asc606_guidance")
        """
        self.database_path = database_path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embedding_function = None
        
        # Initialize the knowledge base
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=self.database_path)
            logger.info(f"ChromaDB client initialized for {self.database_path}")
            
            # Initialize embedding function - use OpenAI model to match existing knowledge bases
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
                
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=openai_api_key,
                model_name="text-embedding-3-small"
            )
            logger.info("Embedding function initialized successfully")
            
            # Get the collection with the correct embedding function
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Collection '{self.collection_name}' loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {str(e)}")
            raise
    
    def search(self, query: str, max_results: int = 10) -> str:
        """
        Search the knowledge base and return formatted context.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            Formatted context string ready for LLM consumption
        """
        try:
            if not self.collection:
                raise ValueError("Knowledge base not properly initialized")
            
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=max_results
            )
            
            if not results or not results.get('documents') or not results['documents'] or not results['documents'][0]:
                logger.warning(f"No results found for query: {query[:100]}...")
                return "No relevant guidance found in the knowledge base."
            
            # Format results for LLM consumption
            formatted_context = self._format_search_results(results)
            
            logger.info(f"Retrieved {len(results['documents'][0]) if results.get('documents') and results['documents'][0] else 0} relevant guidance chunks")
            return formatted_context
            
        except Exception as e:
            logger.error(f"Knowledge base search error: {str(e)}")
            return f"Error searching knowledge base: {str(e)}"
    
    def _format_search_results(self, results: Any) -> str:
        """
        Format search results into clean, readable context for the LLM.
        
        Args:
            results: Raw results from ChromaDB query
            
        Returns:
            Formatted context string
        """
        if not results or not results.get('documents') or not results['documents'][0]:
            return "No relevant guidance found."
        
        documents = results['documents'][0]
        metadatas = results.get('metadatas', [None])[0] or []
        
        formatted_chunks = []
        
        for i, doc in enumerate(documents):
            # Get metadata if available
            metadata = metadatas[i] if i < len(metadatas) else {}
            source = metadata.get('source', 'Unknown Source')
            section = metadata.get('section', '')
            
            # Create a clean chunk with source information
            chunk_header = f"Source: {source}"
            if section:
                chunk_header += f" - {section}"
            
            chunk = f"{chunk_header}\n{doc.strip()}\n"
            formatted_chunks.append(chunk)
        
        # Combine all chunks with clear separators
        context = "\n" + "="*50 + "\n".join(formatted_chunks) + "="*50 + "\n"
        
        return context
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about the knowledge base.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            if not self.collection:
                return {"error": "Knowledge base not initialized"}
            
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "database_path": self.database_path,
                "document_count": count,
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {str(e)}")
            return {"error": str(e)}


class ASC606KnowledgeBase(SharedKnowledgeBase):
    """ASC 606 specific knowledge base interface."""
    
    def __init__(self):
        super().__init__(
            database_path="asc606_knowledge_base",
            collection_name="asc606_guidance"
        )


class ASC340KnowledgeBase(SharedKnowledgeBase):
    """ASC 340-40 specific knowledge base interface."""
    
    def __init__(self):
        super().__init__(
            database_path="asc340_knowledge_base", 
            collection_name="asc340_contract_costs"
        )


class ASC842KnowledgeBase(SharedKnowledgeBase):
    """ASC 842 specific knowledge base interface."""
    
    def __init__(self):
        super().__init__(
            database_path="asc842_knowledge_base",
            collection_name="asc842_guidance"
        )