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
            
            # Perform focused analysis for each ASC 606 step with step-specific RAG
            failed_steps = []
            
            for step_num in range(1, 6):
                step_info = step_mapping[step_num]
                
                self.logger.info(f"Analyzing Step {step_num}: {step_info['title']}")
                
                # CRITICAL IMPROVEMENT: Step-specific RAG query
                step_specific_context = ""
                if self.kb_manager and contract_terms:
                    # Define step-specific search terms for targeted RAG
                    step_search_terms = {
                        1: ["contract approval", "enforceable rights", "commercial substance", "collectibility"],
                        2: ["distinct", "performance obligations", "series", "separately identifiable", "capable of being distinct"],
                        3: ["transaction price", "variable consideration", "financing component", "noncash consideration"],
                        4: ["standalone selling price", "allocation", "observable price", "discount allocation"],
                        5: ["over time", "point in time", "control transfer", "progress measurement"]
                    }
                    
                    # Enhanced search with step-specific terms
                    enhanced_terms = contract_terms + step_search_terms.get(step_num, [])
                    
                    step_rag_results = self.kb_manager.search_relevant_guidance(
                        standard="ASC 606",
                        query_texts=enhanced_terms,
                        step_context=f"step_{step_num}",
                        n_results=5  # Focused results per step
                    )
                    
                    if step_rag_results:
                        step_specific_context = f"\n\n**STEP {step_num} SPECIFIC GUIDANCE:**\n"
                        for result in step_rag_results:
                            step_specific_context += f"\n**{result['source']} - {result['section']}** (Relevance: {result['relevance_score']:.2f})\n"
                            step_specific_context += f"{result['content']}\n"
                
                # Generate focused prompt for this specific step
                step_prompt = StepAnalysisPrompts.get_step_specific_analysis_prompt(
                    step_number=step_num,
                    step_title=step_info['title'],
                    step_guidance=step_info['primary_guidance'],
                    contract_text=contract_text,
                    rag_context=retrieved_context + step_specific_context,  # Combined general + step-specific
                    contract_data=contract_data,
                    debug_config=debug_config or {}
                )
                
                # Get detailed analysis for this step
                try:
                    step_response = make_llm_call(
                        self.client,
                        step_prompt,
                        temperature=debug_config.get('temperature', 0.3) if debug_config else 0.3,
                        max_tokens=debug_config.get('max_tokens', 3000) if debug_config else 3000,
                        model=debug_config.get('model', 'gpt-4o') if debug_config else 'gpt-4o',
                        response_format={"type": "json_object"}
                    )
                    
                    # Parse JSON response
                    step_analysis = json.loads(step_response)
                    step_results[f"step_{step_num}"] = step_analysis
                    self.logger.info(f"Step {step_num} analysis completed: {len(step_response)} characters")
                    
                except (json.JSONDecodeError, Exception) as e:
                    self.logger.error(f"Step {step_num} failed: {e}")
                    failed_steps.append((step_num, step_info['title'], str(e)))
                    step_results[f"step_{step_num}"] = {
                        "step_name": step_info['title'],
                        "detailed_analysis": "Analysis failed - see error details",
                        "error": str(e)
                    }
            
            # CRITICAL UX IMPROVEMENT: Check for failures and halt if any occurred
            if failed_steps:
                import streamlit as st
                error_msg = "❌ **Analysis Failed** - The following steps encountered errors:\n\n"
                for step_num, title, error in failed_steps:
                    error_msg += f"• **Step {step_num} ({title})**: {error}\n"
                error_msg += "\nPlease try again or contact support if the issue persists."
                st.error(error_msg)
                raise Exception(f"Analysis failed for {len(failed_steps)} step(s): {[s[0] for s in failed_steps]}")
            
            # === STEP 3: GENERATE COMPREHENSIVE MEMO ===
            self.logger.info("Generating final comprehensive memo")
            
            # OPTIMIZATION: Lean final prompt with only essential data
            memo_prompt = StepAnalysisPrompts.get_final_memo_generation_prompt(
                step1_analysis=step_results.get("step_1", {}),
                step2_analysis=step_results.get("step_2", {}),
                step3_analysis=step_results.get("step_3", {}),
                step4_analysis=step_results.get("step_4", {}),
                step5_analysis=step_results.get("step_5", {}),
                analysis_title=getattr(contract_data, 'analysis_title', 'ASC 606 Analysis'),
                customer_name=getattr(contract_data, 'customer_name', 'Unknown'),
                memo_audience=getattr(contract_data, 'memo_audience', 'Technical Accounting Team'),
                debug_config=debug_config or {}
            )
            
            final_memo = make_llm_call(
                self.client,
                memo_prompt,
                temperature=debug_config.get('temperature', 0.3) if debug_config else 0.3,
                max_tokens=debug_config.get('max_tokens', 16000) if debug_config else 16000,  # INCREASED for complete memo
                model=debug_config.get('memo_model', 'gpt-4o') if debug_config else 'gpt-4o'  # Use full model for better completion
            )
            
            self.logger.info(f"Final memo generated: {len(final_memo)} characters")
            
            # === STEP 4: RETURN CLEAN, CONSOLIDATED ANALYSIS RESULT ===
            analysis_result = ASC606Analysis(
                professional_memo=final_memo,
                step_by_step_details=step_results,  # Single source of truth
                source_quality="Hybrid RAG - Step Analysis" if retrieved_context else "General Knowledge - Step Analysis",
                relevant_chunks=len(retrieved_context.split('\n\n')) if retrieved_context else 0,
                contract_overview={
                    "title": getattr(contract_data, 'analysis_title', 'ASC 606 Analysis'),
                    "customer": getattr(contract_data, 'customer_name', 'Unknown'),
                    "analysis_type": "Step-by-Step Detailed Analysis"
                }
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