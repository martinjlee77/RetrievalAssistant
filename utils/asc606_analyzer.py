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
# Note: streamlit imported dynamically where needed to avoid import errors


class ASC606Analyzer:
    """ASC 606 analyzer using hybrid RAG with ChromaDB knowledge base"""
    
    # Configurable constants for RAG tuning
    GENERAL_RAG_RESULTS_COUNT = 8
    STEP_SPECIFIC_RAG_RESULTS_COUNT = 5
    
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

    def _sanitize_llm_json(self, data: Any) -> Any:
        """
        Recursively traverses a JSON object from the LLM and cleans up
        common string formatting issues like character splitting.
        """
        if isinstance(data, dict):
            return {key: self._sanitize_llm_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_llm_json(item) for item in data]
        elif isinstance(data, str):
            # 1. Fix the "s p a c e d o u t" text issue
            # This regex finds single characters separated by one or more spaces
            # and joins them back together, but preserves spaces around currency symbols
            sanitized_str = re.sub(r'\b([a-zA-Z])\s(?=[a-zA-Z]\b)', r'\1', data)

            # 2. Preserve proper spacing around currency symbols and punctuation
            # Ensure space before currency symbols like $, €, £
            sanitized_str = re.sub(r'(\w)(\$€£¥)', r'\1 \2', sanitized_str)
            # Ensure space after currency amounts
            sanitized_str = re.sub(r'(\$\d+\.?\d*),(\w)', r'\1, \2', sanitized_str)

            # 3. Collapse multiple spaces into a single space
            sanitized_str = re.sub(r'\s+', ' ', sanitized_str).strip()

            return sanitized_str
        else:
            return data
    
    def analyze_contract(self, contract_text: str, contract_data: Any, debug_config: Optional[Dict] = None) -> ASC606Analysis:
        """Analyze contract using step-by-step detailed analysis with extensive citations"""
        import time
        analysis_start_time = time.time()
        
        try:
            # === STEP 1: RETRIEVAL-AUGMENTED GENERATION WORKFLOW ===
            retrieved_context = ""
            contract_terms = []
            if self.kb_manager:
                # Extract contract-specific terms for better RAG results
                contract_terms = extract_contract_terms(
                    client=self.client,
                    contract_text=contract_text,
                    step_context="comprehensive_analysis"
                )
                
                rag_results = []  # Initialize rag_results as empty list
                if contract_terms:
                    self.logger.info(f"Extracted contract terms: {contract_terms}")
                    
                    # Query knowledge base with extracted terms using improved manager
                    rag_results = self.kb_manager.search_relevant_guidance(
                        standard="ASC 606",
                        query_texts=contract_terms,  # Pass as list for better search
                        step_context="comprehensive_analysis",
                        n_results=self.GENERAL_RAG_RESULTS_COUNT
                    )
                    
                    # Enhanced logging with relevance insights
                    if rag_results:
                        max_relevance = max(r['relevance_score'] for r in rag_results)
                        self.logger.info(f"RAG search returned {len(rag_results)} results with max relevance of {max_relevance:.2f}")
                    else:
                        self.logger.info("RAG search returned 0 results.")
                else:
                    self.logger.warning("No contract terms extracted - RAG search will be skipped.")
                
                # CORRECTED PLACEMENT: Process RAG results if they exist
                if rag_results:
                    # Categorize results by source type with robust industry keyword matching
                    INDUSTRY_KEYWORDS = ['ey', 'ernst', 'pwc', 'deloitte', 'kpmg']
                    asc_results = []
                    ey_results = []
                    
                    for result in rag_results:
                        source = result.get('source', '').lower()
                        if any(keyword in source for keyword in INDUSTRY_KEYWORDS):
                            ey_results.append(result)
                        else:
                            asc_results.append(result)
                    
                    # Format retrieved context with clear categorization
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
            else:
                self.logger.error("Knowledge base manager not initialized - using general knowledge only")
            
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
                        n_results=self.STEP_SPECIFIC_RAG_RESULTS_COUNT  # Focused results per step
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
                    step_analysis_raw = json.loads(step_response) if step_response else {}
                    
                    step_analysis_sanitized = self._sanitize_llm_json(step_analysis_raw)
                    
                    step_results[f"step_{step_num}"] = step_analysis_sanitized
                    self.logger.info(f"Step {step_num} analysis completed: {len(step_response) if step_response else 0} characters")
                    
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
            
            # === STEP 3: PYTHON-DRIVEN MEMO ASSEMBLY ===
            self.logger.info("Assembling final comprehensive memo section by section...")
            
            # Get step results for easy reference
            s1, s2, s3, s4, s5 = [step_results.get(f"step_{i}", {}) for i in range(1, 6)]
            
            # 0. CRITICAL: Consistency Check (GEMINI'S NEW REQUIREMENT)
            self.logger.info("Performing consistency check across all 5 steps...")
            consistency_prompt = StepAnalysisPrompts.get_consistency_check_prompt(s1, s2, s3, s4, s5)
            consistency_result = make_llm_call(
                self.client, consistency_prompt,
                model='gpt-4o', max_tokens=1000, temperature=0.1  # Use best model with low temp for accuracy
            )
            
            # Check if analysis is inconsistent and halt if needed
            if consistency_result and "ANALYSIS CONSISTENT" not in str(consistency_result):
                import streamlit as st
                st.error(f"❌ **Analysis Consistency Issue Detected**\n\n{consistency_result}\n\nPlease review the contract and try again.")
                raise Exception(f"Analysis consistency check failed: {consistency_result[:200]}...")
            
            self.logger.info("✅ Consistency check passed - all steps align")
            
            # 1. Generate Executive Summary (focused LLM call)
            summary_prompt = StepAnalysisPrompts.get_executive_summary_prompt(s1, s2, s3, s4, s5, contract_data)
            executive_summary = make_llm_call(
                self.client, summary_prompt, 
                model='gpt-4o-mini', max_tokens=800, temperature=0.3
            )
            
            # 2. Generate Background (focused LLM call) 
            background_prompt = StepAnalysisPrompts.get_background_prompt(contract_data)
            background = make_llm_call(
                self.client, background_prompt,
                model='gpt-4o-mini', max_tokens=600, temperature=0.3
            )
            
            # 3. Assemble Detailed Analysis (Python formatting - NO LLM CALL)
            detailed_analysis_sections = []
            step_names = [
                "Identify the Contract",
                "Identify Performance Obligations", 
                "Determine the Transaction Price",
                "Allocate the Transaction Price",
                "Recognize Revenue"
            ]
            
            for i in range(1, 6):
                step_data = step_results.get(f"step_{i}", {})
                formatted_step = StepAnalysisPrompts.format_step_detail_as_markdown(
                    step_data, i, step_names[i-1]
                )
                detailed_analysis_sections.append(formatted_step)
            
            detailed_analysis = "\n\n".join(detailed_analysis_sections)
            
            # 4. Generate Key Judgments (focused LLM call)
            judgments_prompt = StepAnalysisPrompts.get_key_judgments_prompt(s1, s2, s3, s4, s5)
            key_judgments = make_llm_call(
                self.client, judgments_prompt,
                model='gpt-4o-mini', max_tokens=1000, temperature=0.3
            )
            
            # 5. Generate Financial Impact (focused LLM call)
            financial_prompt = StepAnalysisPrompts.get_financial_impact_prompt(
                s1, s2, s3, s4, s5, 
                getattr(contract_data, 'customer_name', 'Customer'),
                getattr(contract_data, 'memo_audience', 'Technical Accounting Team')
            )
            financial_impact = make_llm_call(
                self.client, financial_prompt,
                model='gpt-4o-mini', max_tokens=1000, temperature=0.3
            )
            
            # 6. Generate Conclusion (focused LLM call)
            conclusion_prompt = StepAnalysisPrompts.get_conclusion_prompt(
                s1, s2, s3, s4, s5,
                getattr(contract_data, 'customer_name', 'Customer'),
                getattr(contract_data, 'memo_audience', 'Technical Accounting Team')
            )
            conclusion = make_llm_call(
                self.client, conclusion_prompt,
                model='gpt-4o-mini', max_tokens=800, temperature=0.3
            )
            
            # Clean any blockquote formatting that might create boxes
            if conclusion and isinstance(conclusion, str):
                # Remove any leading > characters that create blockquotes
                conclusion = '\n'.join(line.lstrip('> ') for line in conclusion.split('\n'))
            
            # 7. Python Assembly of Final Memo with Professional Formatting
            contract_data_table = self._create_contract_data_table(contract_data)
            
            memo_header = f"""#TECHNICAL ACCOUNTING MEMORANDUM

**TO:** {getattr(contract_data, 'memo_audience', 'Technical Accounting Team / Audit File')}  
**FROM:** ASC 606 AI Analyst
**DATE:** {datetime.now().strftime('%B %d, %Y')}  
**RE:** ASC 606 Revenue Recognition Analysis - {getattr(contract_data, 'analysis_title', 'Revenue Contract Analysis')}
**DOCUMENT CLASSIFICATION:** Internal Use Only  
**REVIEW STATUS:** Preliminary Analysis \n\n\n
"""
            
            final_memo_sections = [
                memo_header,
                f"## 1. EXECUTIVE SUMMARY\n\n{executive_summary}",
                f"## 2. CONTRACT OVERVIEW\n\n{contract_data_table}\n\n{background}", 
                f"## 3. DETAILED ASC 606 ANALYSIS\n\n{detailed_analysis}",
                f"## 4. KEY PROFESSIONAL JUDGMENTS\n\n{key_judgments}",
                f"## 5. FINANCIAL IMPACT ASSESSMENT\n\n{financial_impact}",
                f"## 6. CONCLUSION AND RECOMMENDATIONS\n\n{conclusion}",
                f"\n---\n\n**CONFIDENTIAL:** This memorandum contains confidential and proprietary information. Distribution is restricted to authorized personnel only.\n\n**PREPARED BY:** ASC 606 AI Analyst \n**REVIEWED BY:** [To be completed] \n**APPROVED BY:** [To be completed]"
            ]
            
            final_memo = "\n\n".join(final_memo_sections)
            
            self.logger.info(f"Python-assembled memo completed: {len(final_memo)} characters with all 6 sections")
            
            # === STEP 4: RETURN CLEAN, CONSOLIDATED ANALYSIS RESULT ===
            analysis_duration = time.time() - analysis_start_time
            
            # Determine complexity based on analysis patterns
            complexity_indicators = [
                bool(getattr(contract_data, 'is_modification', False)),
                bool(getattr(contract_data, 'variable_consideration_involved', False)), 
                bool(getattr(contract_data, 'financing_component_involved', False)),
                bool(getattr(contract_data, 'principal_agent_involved', False)),
                len(getattr(contract_data, 'key_focus_areas', '') or '') > 100,
                analysis_duration > 180  # Complex if takes more than 3 minutes
            ]
            complexity_score = sum(complexity_indicators)
            if complexity_score >= 4:
                complexity = "Complex"
            elif complexity_score >= 2:
                complexity = "Medium"
            else:
                complexity = "Simple"
            
            # Metrics disabled to prevent errors
            analysis_result = ASC606Analysis(
                professional_memo=final_memo,
                step_by_step_details=step_results,  # Single source of truth
                source_quality="RAG Enabled",
                relevant_chunks=0,
                analysis_complexity=complexity,
                analysis_duration_seconds=int(analysis_duration),
                contract_overview={
                    "title": getattr(contract_data, 'analysis_title', 'ASC 606 Analysis'),
                    "customer": getattr(contract_data, 'customer_name', 'Unknown'),
                    "analysis_type": "Step-by-Step Detailed Analysis"
                }
            )
            
            # Store debug information if enabled
            try:
                import streamlit as st
                if debug_config and debug_config.get("show_raw_response"):
                    st.session_state.raw_response = final_memo
                    
                if debug_config and debug_config.get("show_prompts"):
                    st.session_state.enhanced_prompt = f"Step-by-step analysis with {len(step_results)} detailed steps"
            except ImportError:
                # Streamlit not available, skip debug storage
                pass
                
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise

    def _create_contract_data_table(self, contract_data) -> str:
        """Create a professional contract data overview table."""
        customer = getattr(contract_data, 'customer_name', 'Not specified')
        start_date = getattr(contract_data, 'contract_start', 'Not specified')
        end_date = getattr(contract_data, 'contract_end', 'Not specified')
        currency = getattr(contract_data, 'currency', 'USD')
        modification = getattr(contract_data, 'is_modification', False)
        
        # Add documents reviewed list
        documents_list = self._format_documents_list()
        
        return f"""**CONTRACT DATA SUMMARY**

| **Element** | **Details** |
|-------------|-------------|
| **Customer** | {customer} |
| **Contract Period** | {start_date} to {end_date} |
| **Currency** | {currency} |
| **Modification Status** | {'Yes - Amendment/Modification' if modification else 'No - Original Contract'} |
| **Analysis Scope** | {getattr(contract_data, 'key_focus_areas', 'Standard ASC 606 five-step analysis') or 'Standard ASC 606 five-step analysis'} |
| **Materiality Threshold** | ${getattr(contract_data, 'materiality_threshold', 'Not specified'):,} |

**DOCUMENTS REVIEWED**

{documents_list}"""

    def _format_documents_list(self) -> str:
        """Format the list of documents reviewed for the analysis."""
        import streamlit as st
        
        try:
            # Get uploaded files from session state
            documents = []
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'uploaded_files'):
                uploaded_files = st.session_state.uploaded_files
                if uploaded_files:
                    for file in uploaded_files:
                        file_name = getattr(file, 'name', str(file))
                        documents.append(f"• {file_name}")
            
            if not documents:
                documents = ["• Contract document (uploaded file)"]
                
            return "\n".join(documents)
            
        except Exception as e:
            self.logger.warning(f"Could not retrieve document list: {e}")
            return "• Contract document (uploaded file)"
    
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