"""
ASC 606 RAG System
Professional retrieval-augmented generation system using authoritative ASC 606 sources
"""

import os
import json
import numpy as np
import tiktoken
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
from pathlib import Path
import faiss
from docx import Document
import logging

@dataclass
class DocumentChunk:
    """Represents a chunk of ASC 606 content"""
    content: str
    source: str
    section: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

class ASC606KnowledgeBase:
    """
    Professional ASC 606 knowledge base using authoritative sources
    """
    
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.embeddings_index: Optional[faiss.Index] = None
        self.tokenizer = tiktoken.encoding_for_model("gpt-4o")
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for RAG operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_authoritative_sources(self) -> Dict[str, Any]:
        """
        Load all ASC 606 authoritative sources from attached_assets
        """
        self.logger.info("Loading ASC 606 authoritative sources...")
        
        # ASC 606 text files mapping
        asc_files = {
            "05_overview_background": "Overview and Background",
            "10_objectives": "Objectives", 
            "15_scope": "Scope and Scope Exceptions",
            "20_glossary": "Glossary",
            "25_recognition": "Recognition",
            "32_measurement": "Measurement", 
            "45_other_presentation_matters": "Other Presentation Matters",
            "50_disclosure": "Disclosure",
            "55_implementation_guidance": "Implementation Guidance and Illustrations"
        }
        
        sources_loaded = 0
        
        # Load ASC 606 section files
        for file_prefix, section_name in asc_files.items():
            file_path = self._find_file_by_prefix(file_prefix)
            if file_path:
                self._load_asc_section(file_path, section_name)
                sources_loaded += 1
                self.logger.info(f"Loaded {section_name}")
        
        # Load EY publication
        ey_file = self._find_file_by_prefix("ey-frdbb3043")
        if ey_file:
            self._load_ey_publication(ey_file)
            sources_loaded += 1
            self.logger.info("Loaded EY publication")
        
        self.logger.info(f"Successfully loaded {sources_loaded} authoritative sources")
        self.logger.info(f"Total chunks created: {len(self.chunks)}")
        
        return {
            "sources_loaded": sources_loaded,
            "total_chunks": len(self.chunks),
            "chunk_distribution": self._get_chunk_distribution()
        }
    
    def _find_file_by_prefix(self, prefix: str) -> Optional[str]:
        """Find file by prefix in attached_assets"""
        assets_dir = Path("attached_assets")
        for file_path in assets_dir.glob(f"{prefix}*"):
            return str(file_path)
        return None
    
    def _load_asc_section(self, file_path: str, section_name: str):
        """Load ASC 606 section file and create chunks"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse ASC content into meaningful chunks
            chunks = self._parse_asc_content(content, section_name)
            
            for chunk_content, metadata in chunks:
                if len(chunk_content.strip()) > 50:  # Filter out very short chunks
                    chunk = DocumentChunk(
                        content=chunk_content,
                        source=f"ASC 606 - {section_name}",
                        section=section_name,
                        metadata=metadata
                    )
                    self.chunks.append(chunk)
                    
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {str(e)}")
    
    def _parse_asc_content(self, content: str, section_name: str) -> List[Tuple[str, Dict]]:
        """Parse ASC content into structured chunks"""
        chunks = []
        
        # Split by ASC paragraph references (e.g., 606-10-25-1)
        paragraphs = re.split(r'(606-10-\d{2}-\d+[A-Z]?)', content)
        
        current_paragraph = None
        current_content = ""
        
        for i, part in enumerate(paragraphs):
            if re.match(r'606-10-\d{2}-\d+[A-Z]?', part):
                # Save previous paragraph if exists
                if current_paragraph and current_content.strip():
                    chunks.append((
                        current_content.strip(),
                        {
                            "paragraph": current_paragraph,
                            "section": section_name,
                            "type": "ASC_paragraph"
                        }
                    ))
                
                current_paragraph = part
                current_content = ""
            else:
                current_content += part
        
        # Handle last paragraph
        if current_paragraph and current_content.strip():
            chunks.append((
                current_content.strip(),
                {
                    "paragraph": current_paragraph,
                    "section": section_name,
                    "type": "ASC_paragraph"
                }
            ))
        
        # If no paragraphs found, chunk by sections
        if not chunks:
            # Split by major sections (indicated by '>' markers)
            sections = re.split(r'(>\s*[A-Z][^>]*)', content)
            for i in range(0, len(sections), 2):
                if i + 1 < len(sections):
                    section_title = sections[i + 1].strip()
                    section_content = sections[i + 2] if i + 2 < len(sections) else ""
                    
                    if section_content.strip():
                        chunks.append((
                            section_content.strip(),
                            {
                                "subsection": section_title,
                                "section": section_name,
                                "type": "ASC_section"
                            }
                        ))
        
        return chunks
    
    def _load_ey_publication(self, file_path: str):
        """Load EY publication and create chunks"""
        try:
            # Load Word document
            doc = Document(file_path)
            
            current_section = "Introduction"
            current_content = ""
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                
                if not text:
                    continue
                
                # Detect section headers (typically styled differently)
                if self._is_section_header(text):
                    # Save previous section
                    if current_content.strip():
                        chunk = DocumentChunk(
                            content=current_content.strip(),
                            source="EY Revenue Recognition Guide",
                            section=current_section,
                            metadata={
                                "section": current_section,
                                "type": "EY_guidance",
                                "publisher": "Ernst & Young"
                            }
                        )
                        self.chunks.append(chunk)
                    
                    current_section = text
                    current_content = ""
                else:
                    current_content += text + "\n"
                
                # Create chunk if content gets too long
                if len(current_content) > 2000:
                    chunk = DocumentChunk(
                        content=current_content.strip(),
                        source="EY Revenue Recognition Guide",
                        section=current_section,
                        metadata={
                            "section": current_section,
                            "type": "EY_guidance",
                            "publisher": "Ernst & Young"
                        }
                    )
                    self.chunks.append(chunk)
                    current_content = ""
            
            # Handle final section
            if current_content.strip():
                chunk = DocumentChunk(
                    content=current_content.strip(),
                    source="EY Revenue Recognition Guide",
                    section=current_section,
                    metadata={
                        "section": current_section,
                        "type": "EY_guidance",
                        "publisher": "Ernst & Young"
                    }
                )
                self.chunks.append(chunk)
                
        except Exception as e:
            self.logger.error(f"Error loading EY publication: {str(e)}")
    
    def _is_section_header(self, text: str) -> bool:
        """Detect if text is a section header"""
        # Common indicators of section headers
        indicators = [
            text.isupper() and len(text) < 100,
            text.startswith("Step "),
            text.startswith("Chapter "),
            text.endswith(":") and len(text) < 100,
            re.match(r'^\d+\.', text),
            len(text.split()) < 10 and text.istitle()
        ]
        
        return any(indicators)
    
    def _get_chunk_distribution(self) -> Dict[str, int]:
        """Get distribution of chunks by source"""
        distribution = {}
        for chunk in self.chunks:
            distribution[chunk.source] = distribution.get(chunk.source, 0) + 1
        return distribution
    
    def create_embeddings(self) -> Dict[str, Any]:
        """
        Create embeddings for all chunks using OpenAI's text-embedding-3-small
        """
        self.logger.info("Creating embeddings for knowledge base...")
        
        from openai import OpenAI
        
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        embeddings = []
        failed_chunks = 0
        
        for i, chunk in enumerate(self.chunks):
            try:
                # Create embedding
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=chunk.content
                )
                
                embedding = np.array(response.data[0].embedding, dtype=np.float32)
                chunk.embedding = embedding
                embeddings.append(embedding)
                
                if (i + 1) % 50 == 0:
                    self.logger.info(f"Created embeddings for {i + 1}/{len(self.chunks)} chunks")
                    
            except Exception as e:
                self.logger.error(f"Failed to create embedding for chunk {i}: {str(e)}")
                failed_chunks += 1
                # Create zero embedding as fallback
                embeddings.append(np.zeros(1536, dtype=np.float32))
        
        # Create FAISS index
        if embeddings:
            embeddings_matrix = np.vstack(embeddings)
            
            # Use Inner Product for cosine similarity
            self.embeddings_index = faiss.IndexFlatIP(embeddings_matrix.shape[1])
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings_matrix)
            self.embeddings_index.add(embeddings_matrix)
            
            self.logger.info(f"Created FAISS index with {len(embeddings)} embeddings")
        
        return {
            "total_embeddings": len(embeddings),
            "failed_chunks": failed_chunks,
            "index_created": self.embeddings_index is not None
        }
    
    def search_knowledge_base(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using semantic similarity
        """
        if not self.embeddings_index:
            self.logger.error("Embeddings index not created. Call create_embeddings() first.")
            return []
        
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Create query embedding
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=query
            )
            
            query_embedding = np.array([response.data[0].embedding], dtype=np.float32)
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            scores, indices = self.embeddings_index.search(query_embedding, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.chunks):
                    chunk = self.chunks[idx]
                    results.append({
                        "content": chunk.content,
                        "source": chunk.source,
                        "section": chunk.section,
                        "metadata": chunk.metadata,
                        "similarity_score": float(score)
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching knowledge base: {str(e)}")
            return []
    
    def get_relevant_context(self, query: str, max_tokens: int = 3000) -> str:
        """
        Get relevant context from knowledge base for a query
        """
        search_results = self.search_knowledge_base(query, top_k=15)
        
        if not search_results:
            return ""
        
        # Build context from search results
        context_parts = []
        total_tokens = 0
        
        for result in search_results:
            content = result["content"]
            source = result["source"]
            
            # Format the context piece
            context_piece = f"**{source}**\n{content}\n"
            
            # Check token count
            tokens = len(self.tokenizer.encode(context_piece))
            if total_tokens + tokens > max_tokens:
                break
            
            context_parts.append(context_piece)
            total_tokens += tokens
        
        return "\n".join(context_parts)
    
    def validate_knowledge_base(self) -> Dict[str, Any]:
        """
        Validate the knowledge base quality
        """
        validation_results = {
            "total_chunks": len(self.chunks),
            "sources_count": len(set(chunk.source for chunk in self.chunks)),
            "sections_count": len(set(chunk.section for chunk in self.chunks)),
            "has_embeddings": self.embeddings_index is not None,
            "avg_chunk_length": np.mean([len(chunk.content) for chunk in self.chunks]),
            "source_distribution": self._get_chunk_distribution()
        }
        
        # Quality checks
        validation_results["quality_checks"] = {
            "sufficient_asc_coverage": validation_results["sources_count"] >= 9,
            "has_ey_guidance": any("EY" in chunk.source for chunk in self.chunks),
            "adequate_chunk_size": 100 <= validation_results["avg_chunk_length"] <= 2000,
            "embeddings_created": validation_results["has_embeddings"]
        }
        
        validation_results["overall_quality"] = all(validation_results["quality_checks"].values())
        
        return validation_results

# Initialize global knowledge base instance
asc606_kb = ASC606KnowledgeBase()

def initialize_rag_system() -> Dict[str, Any]:
    """
    Initialize the complete RAG system
    """
    try:
        # Load authoritative sources
        load_results = asc606_kb.load_authoritative_sources()
        
        # Create embeddings
        embedding_results = asc606_kb.create_embeddings()
        
        # Validate knowledge base
        validation_results = asc606_kb.validate_knowledge_base()
        
        return {
            "status": "success",
            "load_results": load_results,
            "embedding_results": embedding_results,
            "validation_results": validation_results,
            "ready_for_analysis": validation_results["overall_quality"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "ready_for_analysis": False
        }

def search_asc606_guidance(query: str, max_context_tokens: int = 3000) -> str:
    """
    Search ASC 606 guidance and return relevant context
    """
    return asc606_kb.get_relevant_context(query, max_context_tokens)