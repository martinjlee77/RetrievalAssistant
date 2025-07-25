"""
ASC 606 Analyzer - Hybrid RAG System with Authoritative Sources
Implements full Retrieval-Augmented Generation workflow
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI

from core.models import ASC606Analysis
from utils.llm import make_llm_call, extract_contract_terms
from core.knowledge_base import get_knowledge_base_manager
from utils.prompt import ASC606PromptTemplates
import streamlit as st


class ASC606Analyzer:
    """ASC 606 analyzer using hybrid RAG with ChromaDB knowledge base"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.logger = logging.getLogger(__name__)
        self.kb_manager = None
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base manager for RAG"""
        try:
            self.kb_manager = get_knowledge_base_manager()
            self.logger.info("Knowledge base manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Knowledge base manager initialization failed: {e}")
            self.kb_manager = None
    
    def analyze_contract(self, contract_text: str, contract_data: Any, debug_config: Optional[Dict] = None) -> ASC606Analysis:
        """Analyze contract using full RAG workflow with ASC 606 framework"""
        try:
            # === STEP 1: RETRIEVAL-AUGMENTED GENERATION WORKFLOW ===
            retrieved_context = ""
            if self.kb_manager:
                # Extract contract-specific terms for better RAG results
                contract_terms = extract_contract_terms(
                    client=self.client,
                    contract_text=contract_text,
                    step_context="comprehensive_analysis"
                )
                
                if contract_terms:
                    # Query knowledge base with extracted terms using improved manager
                    rag_results = self.kb_manager.search_relevant_guidance(
                        standard="ASC 606",
                        query_texts=contract_terms,  # Pass as list for better search
                        step_context="comprehensive_analysis",
                        n_results=8
                    )
                    
                    if rag_results:
                        # Format retrieved context for prompt injection
                        retrieved_context = "\n\n**RETRIEVED AUTHORITATIVE GUIDANCE:**\n"
                        for result in rag_results:
                            retrieved_context += f"\n**{result['source']} - {result['section']}** (Relevance: {result['relevance_score']:.2f})\n"
                            retrieved_context += f"{result['content']}\n"
                        retrieved_context += "\n---\n"
            
            # === STEP 2: ENHANCED PROMPT WITH RAG CONTEXT ===
            base_prompt = ASC606PromptTemplates.get_analysis_prompt(
                contract_text=contract_text,
                user_inputs=contract_data.__dict__ if hasattr(contract_data, '__dict__') else {}
            )
            
            # Inject retrieved context into prompt
            enhanced_prompt = f"{base_prompt}\n\n{retrieved_context}" if retrieved_context else base_prompt
            
            # Add JSON formatting instruction
            enhanced_prompt += """\n\nIMPORTANT: Format your entire response as a single JSON object with the following structure:
{
  "step1": {"analysis": "your analysis", "conclusion": "your conclusion"},
  "step2": {"analysis": "your analysis", "conclusion": "your conclusion"},
  "step3": {"analysis": "your analysis", "conclusion": "your conclusion"},
  "step4": {"analysis": "your analysis", "conclusion": "your conclusion"},
  "step5": {"analysis": "your analysis", "conclusion": "your conclusion"},
  "memo": "complete professional memo text",
  "citations": ["list of ASC citations used"],
  "source_quality": "percentage based on authoritative sources used"
}"""
            
            # === STEP 3: LLM CALL WITH JSON MODE ===
            model = debug_config.get("model", "gpt-4o") if debug_config else "gpt-4o"
            temperature = debug_config.get("temperature", 0.3) if debug_config else 0.3
            max_tokens = debug_config.get("max_tokens", 3000) if debug_config else 3000
            
            messages = [
                {"role": "system", "content": "You are a senior technical accountant from a Big 4 firm specializing in ASC 606. Provide comprehensive analysis using authoritative sources."},
                {"role": "user", "content": enhanced_prompt}
            ]
            
            response = make_llm_call(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Use OpenAI's native JSON mode
            )
            
            # === STEP 4: ROBUST PARSING ===
            analysis_result = self._parse_analysis_response(response or "")
            
            # Store debug information if enabled
            if debug_config and debug_config.get("show_raw_response"):
                st.session_state.raw_response = response
                
            if debug_config and debug_config.get("show_prompts"):
                st.session_state.enhanced_prompt = enhanced_prompt
                
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise
    
    def _parse_analysis_response(self, response: str) -> ASC606Analysis:
        """Parse LLM response into structured analysis with robust JSON handling"""
        try:
            # === ROBUST JSON PARSING ===
            json_content = None
            
            # Method 1: Try direct JSON parsing (for JSON mode responses)
            try:
                json_content = json.loads(response.strip())
            except json.JSONDecodeError:
                pass
            
            # Method 2: Extract JSON from markdown code blocks
            if not json_content:
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
                if json_match:
                    try:
                        json_content = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
            
            # Method 3: Find JSON object within response text
            if not json_content:
                json_match = re.search(r"(\{.*\})", response, re.DOTALL)
                if json_match:
                    try:
                        json_content = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
            
            # === CREATE ANALYSIS OBJECT ===
            if json_content:
                return ASC606Analysis(
                    step1_contract_identification=json_content.get("step1", {"analysis": "Analysis not available"}),
                    step2_performance_obligations=json_content.get("step2", {"analysis": "Analysis not available"}), 
                    step3_transaction_price=json_content.get("step3", {"analysis": "Analysis not available"}),
                    step4_price_allocation=json_content.get("step4", {"analysis": "Analysis not available"}),
                    step5_revenue_recognition=json_content.get("step5", {"analysis": "Analysis not available"}),
                    professional_memo=json_content.get("memo", response),
                    reconciliation_analysis={"confirmations": [], "discrepancies": []},
                    contract_overview={
                        "title": "RAG-Enhanced ASC 606 Analysis", 
                        "summary": "Analysis using authoritative sources and enhanced 5-step assessment"
                    },
                    citations=json_content.get("citations", []),
                    implementation_guidance=json_content.get("implementation", []),
                    not_applicable_items=json_content.get("not_applicable", []),
                    source_quality=json_content.get("source_quality", "Hybrid RAG")
                )
            else:
                # Fallback: treat entire response as memo with enhanced metadata
                return ASC606Analysis(
                    step1_contract_identification={"analysis": "See detailed analysis in professional memo"},
                    step2_performance_obligations={"analysis": "See detailed analysis in professional memo"},
                    step3_transaction_price={"analysis": "See detailed analysis in professional memo"}, 
                    step4_price_allocation={"analysis": "See detailed analysis in professional memo"},
                    step5_revenue_recognition={"analysis": "See detailed analysis in professional memo"},
                    professional_memo=response,
                    reconciliation_analysis={"confirmations": [], "discrepancies": []},
                    contract_overview={
                        "title": "RAG-Enhanced ASC 606 Analysis", 
                        "summary": "Analysis using authoritative sources and enhanced 5-step assessment"
                    },
                    citations=[],
                    implementation_guidance=[],
                    not_applicable_items=[],
                    source_quality="Hybrid RAG"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to parse analysis response: {e}")
            # Return error-safe analysis structure
            return ASC606Analysis(
                step1_contract_identification={"analysis": "Parsing error - see professional memo", "error": str(e)},
                step2_performance_obligations={"analysis": "Parsing error - see professional memo", "error": str(e)},
                step3_transaction_price={"analysis": "Parsing error - see professional memo", "error": str(e)},
                step4_price_allocation={"analysis": "Parsing error - see professional memo", "error": str(e)}, 
                step5_revenue_recognition={"analysis": "Parsing error - see professional memo", "error": str(e)},
                professional_memo=response or "Analysis failed to generate",
                reconciliation_analysis={"confirmations": [], "discrepancies": [], "error": "parsing failed"},
                contract_overview={
                    "title": "ASC 606 Analysis", 
                    "summary": "Analysis attempted with enhanced 5-step assessment", 
                    "error": "parsing failed"
                },
                citations=[],
                implementation_guidance=[],
                not_applicable_items=[],
                source_quality="Error"
            )
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics for debugging purposes"""
        try:
            if self.kb_manager:
                # Get ASC 606 collection stats from manager
                stats = self.kb_manager.get_collection_stats("ASC 606")
                stats.update({
                    "type": "ChromaDB with OpenAI embeddings",
                    "rag_enabled": True,
                    "manager_type": "KnowledgeBaseManager"
                })
                return stats
            else:
                return {
                    "status": "not_loaded", 
                    "error": "Knowledge base manager not initialized",
                    "rag_enabled": False
                }
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "rag_enabled": False
            }