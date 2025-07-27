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
from utils.step_prompts import StepAnalysisPrompts
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
        """Analyze contract using step-by-step detailed analysis with extensive citations"""
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
                        # Categorize results by source type
                        asc_results = []
                        ey_results = []
                        
                        for result in rag_results:
                            source = result.get('source', '').lower()
                            if 'ey' in source or 'ernst' in source or 'frdbb' in source:
                                ey_results.append(result)
                            else:
                                asc_results.append(result)
                        
                        # Format retrieved context with clear categorization
                        retrieved_context = ""
                        
                        if asc_results:
                            retrieved_context += "\n\n**RETRIEVED ASC 606 AUTHORITATIVE GUIDANCE:**\n"
                            retrieved_context += "Use these sources for 'Relevant ASC 606 citations' in your analysis:\n"
                            for result in asc_results:
                                retrieved_context += f"\n**{result['source']} - {result['section']}** (Relevance: {result['relevance_score']:.2f})\n"
                                retrieved_context += f"{result['content']}\n"
                        
                        if ey_results:
                            retrieved_context += "\n\n**RETRIEVED INDUSTRY INTERPRETATIONS:**\n"
                            retrieved_context += "Use these EY professional guidance sources for 'Relevant industry interpretations' in your analysis:\n"  
                            for result in ey_results:
                                retrieved_context += f"\n**{result['source']} - {result['section']}** (Relevance: {result['relevance_score']:.2f})\n"
                                retrieved_context += f"{result['content']}\n"
                        
                        retrieved_context += "\n---\n"
            
            # === STEP 2: STEP-BY-STEP DETAILED ANALYSIS ===
            step_results = {}
            step_mapping = StepAnalysisPrompts.get_step_guidance_mapping()
            
            # Perform focused analysis for each ASC 606 step
            for step_num in range(1, 6):
                step_info = step_mapping[step_num]
                
                self.logger.info(f"Analyzing Step {step_num}: {step_info['title']}")
                
                # Generate focused prompt for this specific step
                step_prompt = StepAnalysisPrompts.get_step_specific_analysis_prompt(
                    step_number=step_num,
                    step_title=step_info['title'],
                    step_guidance=step_info['primary_guidance'],
                    contract_text=contract_text,
                    rag_context=retrieved_context,
                    contract_data=contract_data,
                    debug_config=debug_config or {}
                )
                
                # Get detailed analysis for this step
                step_response = make_llm_call(
                    self.client,
                    step_prompt,
                    temperature=debug_config.get('temperature', 0.3) if debug_config else 0.3,
                    max_tokens=debug_config.get('max_tokens', 3000) if debug_config else 3000,
                    model=debug_config.get('model', 'gpt-4o') if debug_config else 'gpt-4o',
                    response_format={"type": "json_object"}
                )
                
                # Parse JSON response
                try:
                    step_analysis = json.loads(step_response)
                    step_results[f"step_{step_num}"] = step_analysis
                    self.logger.info(f"Step {step_num} analysis completed: {len(step_response)} characters")
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON parsing failed for Step {step_num}: {e}")
                    # Fallback to text response
                    step_results[f"step_{step_num}"] = {
                        "step_name": step_info['title'],
                        "detailed_analysis": step_response,
                        "error": "JSON parsing failed, using raw response"
                    }
            
            # === STEP 3: GENERATE COMPREHENSIVE MEMO ===
            self.logger.info("Generating final comprehensive memo")
            
            memo_prompt = StepAnalysisPrompts.get_final_memo_generation_prompt(
                step1_analysis=step_results.get("step_1", {}),
                step2_analysis=step_results.get("step_2", {}),
                step3_analysis=step_results.get("step_3", {}),
                step4_analysis=step_results.get("step_4", {}),
                step5_analysis=step_results.get("step_5", {}),
                contract_data=contract_data,
                debug_config=debug_config or {}
            )
            
            final_memo = make_llm_call(
                self.client,
                memo_prompt,
                temperature=debug_config.get('temperature', 0.3) if debug_config else 0.3,
                max_tokens=debug_config.get('max_tokens', 6000) if debug_config else 6000,
                model=debug_config.get('model', 'gpt-4o') if debug_config else 'gpt-4o'
            )
            
            self.logger.info(f"Final memo generated: {len(final_memo)} characters")
            
            # === STEP 4: RETURN COMPREHENSIVE ANALYSIS RESULT ===
            analysis_result = ASC606Analysis(
                five_step_analysis=final_memo,
                source_quality="Hybrid RAG - Step Analysis" if retrieved_context else "General Knowledge - Step Analysis",
                relevant_chunks=len(retrieved_context.split('\n\n')) if retrieved_context else 0,
                analysis_timestamp=datetime.now().isoformat(),
                step_by_step_details=step_results  # Store detailed step analysis
            )
            
            # Store debug information if enabled
            if debug_config and debug_config.get("show_raw_response"):
                st.session_state.raw_response = final_memo
                
            if debug_config and debug_config.get("show_prompts"):
                st.session_state.enhanced_prompt = f"Step-by-step analysis with {len(step_results)} detailed steps"
                
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
                reconciliation_analysis={"confirmations": [], "discrepancies": []},
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