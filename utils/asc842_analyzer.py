#!/usr/bin/env python3
"""
ASC 842 Lease Accounting Analyzer
Hybrid RAG system for lease classification, measurement, and journal entry generation
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import chromadb.utils.embedding_functions as embedding_functions

from core.models import ASC842Analysis, LeaseClassificationData
from utils.llm import call_openai_api
from utils.asc842_step_prompts import ASC842StepPrompts

logger = logging.getLogger(__name__)


class ASC842Analyzer:
    """ASC 842 Lease Accounting Analyzer with RAG-enabled knowledge base"""
    
    def __init__(self, knowledge_base_path: str = "asc842_knowledge_base"):
        self.knowledge_base_path = knowledge_base_path
        self.collection = None
        self._initialize_knowledge_base()
        
    def _initialize_knowledge_base(self):
        """Initialize ChromaDB connection"""
        try:
            openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.environ.get("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
            
            client = chromadb.PersistentClient(
                path=self.knowledge_base_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = client.get_collection(
                name="asc842_leases",
                embedding_function=openai_ef
            )
            
            logger.info(f"ASC 842 knowledge base initialized: {self.collection.count()} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize ASC 842 knowledge base: {e}")
            raise
    
    def _search_knowledge_base(
        self,
        query: str,
        topic_filter: Optional[str] = None,
        source_type: Optional[str] = None,
        n_results: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Search ASC 842 knowledge base with hybrid filtering
        
        Args:
            query: Search query text
            topic_filter: Filter by topic (Classification, Measurement, etc.)
            source_type: Filter by source type (authoritative, interpretative)
            n_results: Number of results to return
        """
        try:
            # Build metadata filter
            where_filter = {}
            if topic_filter:
                where_filter["topic"] = topic_filter
            if source_type:
                where_filter["source_type"] = source_type
            
            # Perform hybrid search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                formatted_results.append({
                    'content': doc,
                    'metadata': metadata,
                    'relevance_score': 1 - distance,  # Convert distance to relevance
                    'rank': i + 1
                })
            
            logger.info(f"ASC 842 search: '{query[:50]}...' → {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            return []
    
    def analyze_lease_classification(
        self, 
        contract_text: str,
        lease_data: LeaseClassificationData
    ) -> ASC842Analysis:
        """
        Analyze lease contract for classification (Operating vs Finance)
        
        Args:
            contract_text: Full lease contract text
            lease_data: Structured lease data from user input
            
        Returns:
            ASC842Analysis with classification results
        """
        logger.info("Starting ASC 842 lease classification analysis")
        
        try:
            # Search for classification guidance
            classification_query = f"lease classification finance operating ownership transfer purchase option lease term present value alternative use {lease_data.asset_type}"
            
            classification_chunks = self._search_knowledge_base(
                query=classification_query,
                topic_filter="Classification",
                n_results=10
            )
            
            # Search for asset-specific guidance
            asset_query = f"{lease_data.asset_type} lease accounting classification criteria"
            asset_chunks = self._search_knowledge_base(
                query=asset_query,
                n_results=5
            )
            
            # Combine search results
            all_chunks = classification_chunks + asset_chunks
            
            # Prepare context for LLM
            rag_context = self._format_rag_context(all_chunks)
            
            # Generate classification analysis
            system_prompt = ASC842StepPrompts.get_classification_system_prompt()
            user_prompt = ASC842StepPrompts.get_classification_user_prompt(
                contract_text=contract_text,
                lease_data=lease_data,
                rag_context=rag_context
            )
            
            # Get AI analysis
            classification_response = call_openai_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o",
                temperature=0.3
            )
            
            # Create analysis result - using the actual ASC842Analysis structure
            analysis = ASC842Analysis(
                lease_classification=classification_response,
                initial_measurement="",  # Not used in classification module
                subsequent_measurement="",  # Not used in classification module
                presentation_disclosure="",  # Not used in classification module
                professional_memo="",  # Generated separately
                implementation_guidance="",  # Not used in classification module
                citations=self._extract_sources(all_chunks),
                not_applicable_items=[]  # None for classification
            )
            
            # Store classification data and chunks for reference
            analysis._classification_data = lease_data
            analysis._rag_chunks_used = len(all_chunks)
            
            logger.info("ASC 842 classification analysis completed")
            return analysis
            
        except Exception as e:
            logger.error(f"Classification analysis failed: {e}")
            raise
    
    def _format_rag_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format RAG search results into context for LLM"""
        if not chunks:
            return "No relevant guidance found in knowledge base."
        
        context_parts = ["=== RELEVANT ASC 842 GUIDANCE ===\n"]
        
        for i, chunk in enumerate(chunks[:12], 1):  # Limit to prevent token overflow
            metadata = chunk['metadata']
            content = chunk['content']
            relevance = chunk['relevance_score']
            
            # Format source information
            source_info = f"Source: {metadata.get('standard', 'ASC 842')}"
            if metadata.get('source_type') == 'authoritative':
                source_info += f" - {metadata.get('section', '')}"
                if metadata.get('paragraph_number'):
                    source_info += f" ({metadata.get('paragraph_number')})"
            else:
                source_info += f" - {metadata.get('firm', 'EY')} Interpretative"
            
            source_info += f" | Topic: {metadata.get('topic', 'General')}"
            source_info += f" | Relevance: {relevance:.3f}"
            
            context_parts.append(f"[{i}] {source_info}")
            context_parts.append(content.strip())
            context_parts.append("")  # Blank line
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Extract unique sources from RAG chunks"""
        sources = set()
        for chunk in chunks:
            metadata = chunk['metadata']
            if metadata.get('source_type') == 'authoritative':
                source = f"ASC 842-{metadata.get('section', '')}"
                if metadata.get('paragraph_number'):
                    source += f" ({metadata.get('paragraph_number')})"
            else:
                source = f"{metadata.get('firm', 'EY')} ASC 842 Guide"
            sources.add(source)
        
        return sorted(list(sources))
    
    def generate_classification_memo(self, analysis: ASC842Analysis, lease_data: LeaseClassificationData) -> str:
        """Generate professional lease classification memorandum"""
        try:
            # Search for memo-specific guidance
            memo_chunks = self._search_knowledge_base(
                query="lease classification memo documentation disclosure",
                topic_filter="Implementation",
                n_results=5
            )
            
            memo_context = self._format_rag_context(memo_chunks)
            
            # Generate memo
            system_prompt = ASC842StepPrompts.get_memo_system_prompt()
            user_prompt = ASC842StepPrompts.get_memo_user_prompt(
                analysis=analysis,
                lease_data=lease_data,
                rag_context=memo_context
            )
            
            memo = call_openai_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o",
                temperature=0.2
            )
            
            logger.info("ASC 842 classification memo generated")
            return memo
            
        except Exception as e:
            logger.error(f"Memo generation failed: {e}")
            return "Error generating memorandum. Please try again."


import os