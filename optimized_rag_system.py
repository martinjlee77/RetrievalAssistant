"""
Optimized RAG System for Production Use
Handles initialization gracefully without blocking UI
"""

import os
import json
import numpy as np
from typing import Dict, List, Any, Optional
import streamlit as st
from rag_system import ASC606KnowledgeBase, initialize_rag_system, search_asc606_guidance
import threading
import time

class OptimizedRAGSystem:
    """
    Production-ready RAG system with non-blocking initialization
    """
    
    def __init__(self):
        self.status = "not_initialized"
        self.kb = None
        self.error_message = None
        self.initialization_thread = None
        
    def initialize_async(self):
        """Initialize RAG system asynchronously"""
        if self.status == "initializing":
            return
            
        self.status = "initializing"
        self.initialization_thread = threading.Thread(target=self._initialize_rag)
        self.initialization_thread.daemon = True
        self.initialization_thread.start()
        
    def _initialize_rag(self):
        """Internal method to initialize RAG system"""
        try:
            # Load knowledge base
            self.kb = ASC606KnowledgeBase()
            load_results = self.kb.load_authoritative_sources()
            
            if load_results["total_chunks"] > 0:
                # Create embeddings (this is the slow part)
                embedding_results = self.kb.create_embeddings()
                
                if embedding_results["total_embeddings"] > 0:
                    self.status = "ready"
                else:
                    self.status = "failed"
                    self.error_message = "Failed to create embeddings"
            else:
                self.status = "failed"
                self.error_message = "No content loaded from sources"
                
        except Exception as e:
            self.status = "failed"
            self.error_message = str(e)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of RAG system"""
        return {
            "status": self.status,
            "error": self.error_message,
            "ready": self.status == "ready",
            "chunks": len(self.kb.chunks) if self.kb else 0
        }
    
    def search_guidance(self, query: str, max_tokens: int = 3000) -> str:
        """Search guidance with fallback"""
        if self.status == "ready" and self.kb:
            return self.kb.get_relevant_context(query, max_tokens)
        else:
            return ""
    
    def get_fallback_guidance(self) -> str:
        """Get fallback guidance when RAG is not ready"""
        return """
        FALLBACK: ASC 606 CORE PRINCIPLES
        
        The five-step revenue recognition model:
        1. Identify the contract with a customer
        2. Identify the performance obligations in the contract
        3. Determine the transaction price
        4. Allocate the transaction price to performance obligations
        5. Recognize revenue when performance obligations are satisfied
        
        Note: Full authoritative guidance is loading in the background.
        """

# Global RAG instance
optimized_rag = OptimizedRAGSystem()

def get_rag_status() -> Dict[str, Any]:
    """Get RAG system status"""
    return optimized_rag.get_status()

def initialize_rag_if_needed():
    """Initialize RAG system if not already started"""
    if optimized_rag.status == "not_initialized":
        optimized_rag.initialize_async()

def search_with_fallback(query: str, max_tokens: int = 3000) -> str:
    """Search with fallback for when RAG is not ready"""
    if optimized_rag.status == "ready":
        return optimized_rag.search_guidance(query, max_tokens)
    else:
        return optimized_rag.get_fallback_guidance()

def render_rag_status():
    """Render RAG system status in Streamlit"""
    status = get_rag_status()
    
    if status["status"] == "ready":
        st.success("✅ RAG System Active")
        st.caption(f"Knowledge base loaded: {status['chunks']} chunks")
    elif status["status"] == "initializing":
        st.info("🔄 RAG System Initializing...")
        st.caption("Loading authoritative ASC 606 sources...")
        # Auto-refresh every 5 seconds during initialization
        time.sleep(1)
        st.rerun()
    elif status["status"] == "failed":
        st.error("❌ RAG System Failed")
        st.caption(f"Error: {status['error']}")
        if st.button("🔄 Retry Initialization"):
            optimized_rag.status = "not_initialized"
            optimized_rag.initialize_async()
            st.rerun()
    else:
        st.warning("⚠️ RAG System Not Started")
        if st.button("🚀 Initialize Knowledge Base"):
            optimized_rag.initialize_async()
            st.rerun()