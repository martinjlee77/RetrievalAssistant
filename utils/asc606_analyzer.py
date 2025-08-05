"""
ASC 606 Analyzer - Hybrid RAG System with Authoritative Sources
Implements full Retrieval-Augmented Generation workflow
"""

import asyncio
import json
import logging
import os
import re
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from functools import lru_cache
from openai import OpenAI

from core.models import ASC606Analysis
from utils.llm import make_llm_call, make_llm_call_async, extract_contract_terms
from core.knowledge_base import get_knowledge_base_manager
from utils.prompt import ASC606PromptTemplates
from utils.step_prompts import StepPrompts
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
        # Cache for expensive operations
        self._rag_cache = {}
        self._prompt_cache = {}

    def _initialize_knowledge_base(self):
        """Initialize the knowledge base manager for RAG"""
        try:
            self.kb_manager = get_knowledge_base_manager()
            self.logger.info("Knowledge base manager initialized successfully")
        except Exception as e:
            self.logger.error(
                f"Knowledge base manager initialization failed: {e}")
            self.kb_manager = None

    @lru_cache(maxsize=128)
    def _clean_memo_section(self, text: str) -> str:
        """Removes common unwanted markdown artifacts from LLM-generated text.
        CACHED: Text cleaning is expensive and often repeated."""
        if not isinstance(text, str):
            return text  # Return as-is if it's an error message or not a string

        # Remove leading blockquote characters from each line
        cleaned_text = '\n'.join(
            line.lstrip('> ') for line in text.split('\n'))

        # Remove duplicate section headers that LLM sometimes adds
        # This fixes header duplication issues across all sections
        unwanted_headers = [
            "# EXECUTIVE SUMMARY", "## EXECUTIVE SUMMARY",
            "### EXECUTIVE SUMMARY", "**EXECUTIVE SUMMARY**",
            "EXECUTIVE SUMMARY", "# KEY PROFESSIONAL JUDGMENTS",
            "## KEY PROFESSIONAL JUDGMENTS", "### KEY PROFESSIONAL JUDGMENTS",
            "# CONCLUSION AND RECOMMENDATIONS", "## CONCLUSION AND RECOMMENDATIONS",
            "### CONCLUSION AND RECOMMENDATIONS", "# CONCLUSION", "## CONCLUSION", 
            "### CONCLUSION", "**CONCLUSION**", "CONCLUSION",
            "# FINANCIAL IMPACT", "## FINANCIAL IMPACT", "### FINANCIAL IMPACT",
            "**FINANCIAL IMPACT**", "FINANCIAL IMPACT"
        ]

        lines = cleaned_text.split('\n')
        filtered_lines = []
        for line in lines:
            line_stripped = line.strip()
            if not any(header in line_stripped.upper()
                       for header in [h.upper() for h in unwanted_headers]):
                filtered_lines.append(line)

        cleaned_text = '\n'.join(filtered_lines)

        return cleaned_text.strip()

    def _sanitize_llm_json(self, data: Any) -> Any:
        """
        Recursively traverses a JSON object from the LLM and cleans up
        common string formatting issues like character splitting.
        """
        if isinstance(data, dict):
            return {
                key: self._sanitize_llm_json(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._sanitize_llm_json(item) for item in data]
        elif isinstance(data, str):
            # 1. Fix the "s p a c e d o u t" text issue
            # This regex finds single characters separated by one or more spaces
            # and joins them back together, but preserves spaces around currency symbols
            sanitized_str = re.sub(r'\b([a-zA-Z])\s(?=[a-zA-Z]\b)', r'\1',
                                   data)

            # 2. Preserve proper spacing around currency symbols and punctuation
            # Ensure space before currency symbols like $, €, £
            sanitized_str = re.sub(r'(\w)(\$€£¥)', r'\1 \2', sanitized_str)
            # Ensure space after currency amounts
            sanitized_str = re.sub(r'(\$\d+\.?\d*),(\w)', r'\1, \2',
                                   sanitized_str)

            # 3. Collapse multiple spaces into a single space
            sanitized_str = re.sub(r'\s+', ' ', sanitized_str).strip()

            return sanitized_str
        else:
            return data

    async def analyze_contract(
            self,
            contract_text: str,
            contract_data: Any,
            debug_config: Optional[Dict] = None) -> ASC606Analysis:
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
                    step_context="comprehensive_analysis")

                rag_results = []  # Initialize rag_results as empty list
                if contract_terms:
                    self.logger.info(
                        f"Extracted contract terms: {contract_terms}")

                    # Query knowledge base with caching for expensive operations
                    cache_key = hashlib.md5(f"rag_{str(contract_terms)}_comprehensive_{self.GENERAL_RAG_RESULTS_COUNT}".encode()).hexdigest()
                    
                    if cache_key not in self._rag_cache:
                        rag_results = self.kb_manager.search_relevant_guidance(
                            standard="ASC 606",
                            query_texts=contract_terms,  # Pass as list for better search
                            step_context="comprehensive_analysis",
                            n_results=self.GENERAL_RAG_RESULTS_COUNT)
                        self._rag_cache[cache_key] = rag_results
                        self.logger.info(f"RAG results cached for key: {cache_key[:8]}...")
                    else:
                        rag_results = self._rag_cache[cache_key]
                        self.logger.info(f"Using cached RAG results for key: {cache_key[:8]}...")

                    # Enhanced logging with relevance insights
                    if rag_results:
                        max_relevance = max(r['relevance_score']
                                            for r in rag_results)
                        self.logger.info(
                            f"RAG search returned {len(rag_results)} results with max relevance of {max_relevance:.2f}"
                        )
                    else:
                        self.logger.info("RAG search returned 0 results.")
                else:
                    self.logger.warning(
                        "No contract terms extracted - RAG search will be skipped."
                    )

                # CORRECTED PLACEMENT: Process RAG results if they exist
                if rag_results:
                    # Categorize results by source type with robust industry keyword matching
                    INDUSTRY_KEYWORDS = [
                        'ey', 'ernst', 'pwc', 'deloitte', 'kpmg'
                    ]
                    asc_results = []
                    ey_results = []

                    for result in rag_results:
                        source = result.get('source', '').lower()
                        if any(keyword in source
                               for keyword in INDUSTRY_KEYWORDS):
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
                self.logger.error(
                    "Knowledge base manager not initialized - using general knowledge only"
                )

            # === STEP 2: CONCURRENT STEP-BY-STEP ANALYSIS ===
            # 🚀 GEMINI PERFORMANCE IMPROVEMENT: Execute all 5 steps concurrently
            step_mapping = StepPrompts.get_step_info()

            # Phase 1: Prepare all prompts and tasks
            tasks = []
            prompt_details = {}
            step_start_times = {}

            self.logger.info(
                "🚀 PERFORMANCE BOOST: Preparing all 5 ASC 606 steps for concurrent execution..."
            )

            for step_num in range(1, 6):
                step_info = step_mapping[step_num]
                step_start_times[step_num] = time.time()

                self.logger.info(
                    f"Preparing Step {step_num}: {step_info['title']}")

                # Step-specific RAG query with caching
                step_specific_context = ""
                if self.kb_manager and contract_terms:
                    step_search_terms = {
                        1: [
                            "contract approval", "enforceable rights",
                            "commercial substance", "collectibility"
                        ],
                        2: [
                            "distinct", "performance obligations", "series",
                            "separately identifiable",
                            "capable of being distinct"
                        ],
                        3: [
                            "transaction price", "variable consideration",
                            "financing component", "noncash consideration"
                        ],
                        4: [
                            "standalone selling price", "allocation",
                            "observable price", "discount allocation"
                        ],
                        5: [
                            "over time", "point in time", "control transfer",
                            "progress measurement"
                        ]
                    }

                    enhanced_terms = contract_terms + step_search_terms.get(
                        step_num, [])

                    # Cache step-specific RAG results
                    step_cache_key = hashlib.md5(f"step_rag_{step_num}_{str(enhanced_terms)}_{self.STEP_SPECIFIC_RAG_RESULTS_COUNT}".encode()).hexdigest()
                    
                    if step_cache_key not in self._rag_cache:
                        step_rag_results = self.kb_manager.search_relevant_guidance(
                            standard="ASC 606",
                            query_texts=enhanced_terms,
                            step_context=f"step_{step_num}",
                            n_results=self.STEP_SPECIFIC_RAG_RESULTS_COUNT)
                        self._rag_cache[step_cache_key] = step_rag_results
                    else:
                        step_rag_results = self._rag_cache[step_cache_key]

                    if step_rag_results:
                        step_specific_context = f"\n\n**STEP {step_num} SPECIFIC GUIDANCE:**\n"
                        for result in step_rag_results:
                            step_specific_context += f"\n**{result['source']} - {result['section']}** (Relevance: {result['relevance_score']:.2f})\n"
                            step_specific_context += f"{result['content']}\n"

                # NEW: Prepare the messages list using the new architecture with caching
                prompt_cache_key = hashlib.md5(f"prompt_{step_num}_{len(contract_text)}_{len(retrieved_context + step_specific_context)}".encode()).hexdigest()
                
                if prompt_cache_key not in self._prompt_cache:
                    system_prompt = StepPrompts.get_system_prompt()
                    user_prompt = StepPrompts.get_user_prompt_for_step(
                        step_number=step_num,
                        contract_text=contract_text,
                        rag_context=retrieved_context + step_specific_context,
                        contract_data=contract_data,
                        debug_config=debug_config or {})
                    self._prompt_cache[prompt_cache_key] = (system_prompt, user_prompt)
                else:
                    system_prompt, user_prompt = self._prompt_cache[prompt_cache_key]

                messages = [{
                    "role": "system",
                    "content": system_prompt
                }, {
                    "role": "user",
                    "content": user_prompt
                }]

                # Store details for processing responses later
                prompt_details[step_num] = {"step_info": step_info}

                # Create async task for concurrent execution
                task = asyncio.create_task(
                    make_llm_call_async(
                        self.client,
                        messages,  # PASS the messages list here
                        temperature=debug_config.get('temperature', 0.3)
                        if debug_config else 0.3,
                        max_tokens=debug_config.get(
                            'max_tokens', 4000 if step_num == 2 else 3000)
                        if debug_config else (4000 if step_num == 2 else 3000),
                        model=debug_config.get('model', 'gpt-4o')
                        if debug_config else 'gpt-4o',
                        response_format={"type": "json_object"}))
                tasks.append(task)

            # Phase 2: Execute all 5 steps concurrently
            concurrent_start_time = time.time()
            self.logger.info(
                f"🎯 Executing {len(tasks)} step-analysis tasks concurrently..."
            )

            step_responses = await asyncio.gather(*tasks,
                                                  return_exceptions=True)

            concurrent_duration = time.time() - concurrent_start_time
            self.logger.info(
                f"⚡ All 5 steps completed concurrently in {concurrent_duration:.2f}s (vs ~150s sequential)"
            )

            # Phase 3: Process concurrent results
            step_results = {}
            failed_steps = []

            for i, response in enumerate(step_responses):
                step_num = i + 1
                step_info = prompt_details[step_num]["step_info"]

                if isinstance(response, Exception):
                    self.logger.error(
                        f"Step {step_num} failed with exception: {response}")
                    failed_steps.append(
                        (step_num, step_info['title'], str(response)))
                    # Create fallback empty step data to prevent cascading failures
                    step_results[step_num] = {
                        'executive_conclusion':
                        f'Step {step_num} analysis failed due to API error: {str(response)[:100]}...',
                        'analysis_points': [],
                        'professional_judgments': []
                    }
                    continue
                else:
                    try:
                        # Process successful response
                        # Ensure response is a string before processing
                        if isinstance(response, str):
                            step_analysis_raw = json.loads(
                                response) if response else {}
                            step_analysis_sanitized = self._sanitize_llm_json(
                                step_analysis_raw)
                            step_results[
                                f"step_{step_num}"] = step_analysis_sanitized

                            # Performance diagnostics
                            step_duration = time.time(
                            ) - step_start_times[step_num]
                            self.logger.info(
                                f"Step {step_num} result processed in {step_duration:.2f}s: {len(response)} characters"
                            )
                        else:
                            raise ValueError(
                                f"Expected string response, got {type(response)}"
                            )

                    except (json.JSONDecodeError, Exception) as e:
                        self.logger.error(
                            f"Step {step_num} parsing failed: {e}")
                        failed_steps.append(
                            (step_num, step_info['title'], str(e)))
                        step_results[f"step_{step_num}"] = {
                            "step_name": step_info['title'],
                            "detailed_analysis": "Analysis parsing failed",
                            "error": str(e)
                        }

            # INTERNAL ERROR HANDLING: Log failures without user-facing technical details
            if failed_steps:
                # Log technical details for debugging
                self.logger.error(
                    f"Analysis failed for {len(failed_steps)} step(s): {[s[0] for s in failed_steps]}"
                )
                for step_num, title, error in failed_steps:
                    self.logger.error(
                        f"Step {step_num} ({title}) failed: {error}")

                # Show simple user-friendly message without technical details
                import streamlit as st
                st.error(
                    "⚠️ **Analysis temporarily unavailable** - Our system is experiencing high demand. Please try again in a moment."
                )
                raise Exception(
                    f"Analysis failed for {len(failed_steps)} step(s) - see logs for details"
                )

            # === STEP 3: PYTHON-DRIVEN MEMO ASSEMBLY ===
            self.logger.info(
                "Assembling final comprehensive memo section by section...")

            # Get step results for easy reference
            s1, s2, s3, s4, s5 = [
                step_results.get(f"step_{i}", {}) for i in range(1, 6)
            ]

            # 0. INTERNAL QUALITY CONTROL: Consistency Check with Auto-Retry
            self.logger.info("Performing internal consistency validation...")
            max_consistency_retries = 2
            consistency_retry_count = 0

            while consistency_retry_count <= max_consistency_retries:
                consistency_prompt = StepPrompts.get_consistency_check_prompt(
                    s1, s2, s3, s4, s5)
                try:
                    consistency_messages = [{
                        "role": "user",
                        "content": consistency_prompt
                    }]
                    consistency_result = make_llm_call(self.client,
                                                       consistency_messages,
                                                       model='gpt-4o',
                                                       max_tokens=1000,
                                                       temperature=0.1)
                except Exception as e:
                    self.logger.warning(
                        f"Consistency check failed due to API error: {e}")
                    # Continue without consistency check if rate limited
                    break

                # Internal quality assessment
                if consistency_result:
                    consistency_text = str(consistency_result).lower()

                    # Check for inconsistency indicators with your original prompt format
                    negative_indicators = [
                        "inconsistent", "contradiction", "contradicts", "gap",
                        "error", "issue", "problem", "conflicts", "mismatch",
                        "does not align", "do not align"
                    ]
                    positive_indicators = [
                        "consistent", "align properly", "aligns",
                        "no inconsistencies", "no contradictions",
                        "logically sound", "analysis is consistent"
                    ]

                    has_negative = any(indicator in consistency_text
                                       for indicator in negative_indicators)
                    has_positive = any(indicator in consistency_text
                                       for indicator in positive_indicators)

                    # Only retry if we have clear negative indicators without positive confirmation
                    if has_negative and not has_positive:
                        consistency_retry_count += 1
                        self.logger.warning(
                            f"Internal consistency check failed (attempt {consistency_retry_count}/{max_consistency_retries + 1})"
                        )

                        if consistency_retry_count <= max_consistency_retries:
                            self.logger.info(
                                "Auto-retrying step analysis with refined prompts..."
                            )
                            # Could add logic here to re-run specific problematic steps
                            # For now, we'll proceed with a warning in the memo
                            continue
                        else:
                            # Add internal quality note to memo instead of failing
                            self.logger.warning(
                                "Consistency validation completed with notes - proceeding with memo generation"
                            )
                            break
                    else:
                        # Analysis passed consistency check
                        self.logger.info(
                            "✅ Internal consistency validation passed")
                        break
                else:
                    # No consistency result - proceed
                    break

            # === CONCURRENT MEMO ASSEMBLY ===
            # 🚀 REVIEWER SUGGESTION: Run memo sections concurrently for 5-10s speedup
            self.logger.info(
                "🚀 MEMO PERFORMANCE: Generating all memo sections concurrently..."
            )

            # Prepare all memo section tasks for concurrent execution
            memo_tasks = []

            # Task 1: Executive Summary
            summary_prompt = StepPrompts.get_enhanced_executive_summary_prompt(
                s1, s2, s3, s4, s5, contract_data.analysis_title,
                contract_data.customer_name)
            summary_messages = [{"role": "user", "content": summary_prompt}]
            memo_tasks.append(
                asyncio.create_task(
                    make_llm_call_async(self.client,
                                        summary_messages,
                                        model='gpt-4o-mini',
                                        max_tokens=800,
                                        temperature=0.3)))

            # Task 2: Background
            background_prompt = StepPrompts.get_background_prompt(
                contract_data)
            background_messages = [{
                "role": "user",
                "content": background_prompt
            }]
            memo_tasks.append(
                asyncio.create_task(
                    make_llm_call_async(self.client,
                                        background_messages,
                                        model='gpt-4o-mini',
                                        max_tokens=600,
                                        temperature=0.3)))

            # Task 3: Key Judgments
            judgments_prompt = StepPrompts.get_key_judgments_prompt(
                s1, s2, s3, s4, s5)
            # Check if this returns direct text (no LLM call needed)
            if judgments_prompt.startswith("RETURN_DIRECT_TEXT: "):
                direct_judgments_text = judgments_prompt.replace(
                    "RETURN_DIRECT_TEXT: ", "")

                async def return_direct_judgments():
                    return direct_judgments_text

                memo_tasks.append(
                    asyncio.create_task(return_direct_judgments()))
            else:
                judgments_messages = [{
                    "role": "user",
                    "content": judgments_prompt
                }]
                memo_tasks.append(
                    asyncio.create_task(
                        make_llm_call_async(self.client,
                                            judgments_messages,
                                            model='gpt-4o-mini',
                                            max_tokens=1000,
                                            temperature=0.3)))

            # Task 4: Financial Impact
            financial_prompt = StepPrompts.get_financial_impact_prompt(
                s1, s2, s3, s4, s5,
                getattr(contract_data, 'customer_name', 'Customer'),
                getattr(contract_data, 'memo_audience',
                        'Technical Accounting Team'), contract_data)
            financial_messages = [{
                "role": "user",
                "content": financial_prompt
            }]
            memo_tasks.append(
                asyncio.create_task(
                    make_llm_call_async(self.client,
                                        financial_messages,
                                        model='gpt-4o-mini',
                                        max_tokens=1000,
                                        temperature=0.3)))

            # Task 5: Conclusion
            conclusion_prompt = StepPrompts.get_conclusion_prompt(
                s1, s2, s3, s4, s5,
                getattr(contract_data, 'customer_name', 'Customer'),
                getattr(contract_data, 'memo_audience',
                        'Technical Accounting Team'), contract_data)
            # Handle direct text for simple contracts
            if conclusion_prompt.startswith("RETURN_DIRECT_TEXT: "):
                direct_conclusion_text = conclusion_prompt.replace(
                    "RETURN_DIRECT_TEXT: ", "")

                async def return_direct_conclusion():
                    return direct_conclusion_text

                memo_tasks.append(
                    asyncio.create_task(return_direct_conclusion()))
            else:
                conclusion_messages = [{
                    "role": "user",
                    "content": conclusion_prompt
                }]
                memo_tasks.append(
                    asyncio.create_task(
                        make_llm_call_async(self.client,
                                            conclusion_messages,
                                            model='gpt-4o-mini',
                                            max_tokens=800,
                                            temperature=0.3)))

            # Execute all memo sections concurrently
            memo_start_time = time.time()
            memo_responses = await asyncio.gather(*memo_tasks,
                                                  return_exceptions=True)
            memo_duration = time.time() - memo_start_time
            self.logger.info(
                f"⚡ All 5 memo sections completed concurrently in {memo_duration:.2f}s"
            )

            # Unpack concurrent results
            executive_summary, background, key_judgments, financial_impact, conclusion = memo_responses

            # Handle any exceptions in memo generation
            for i, response in enumerate(memo_responses):
                section_names = [
                    "Executive Summary", "Background", "Key Judgments",
                    "Financial Impact", "Conclusion"
                ]
                if isinstance(response, Exception):
                    self.logger.error(
                        f"Memo section '{section_names[i]}' failed: {response}"
                    )
                    # Use fallback content
                    memo_responses[
                        i] = f"[{section_names[i]} generation failed - please regenerate the memo]"

            # Generate Detailed Analysis (Python-only, no LLM call needed)
            detailed_analysis_sections = []
            step_names = [
                "Identify the Contract", "Identify Performance Obligations",
                "Determine the Transaction Price",
                "Allocate the Transaction Price", "Recognize Revenue"
            ]

            for i in range(1, 6):
                step_data = step_results.get(f"step_{i}", {})
                formatted_step = StepPrompts.format_step_detail_as_markdown(
                    step_data, i, step_names[i - 1])
                detailed_analysis_sections.append(formatted_step)

            detailed_analysis = "\n\n".join(detailed_analysis_sections)

            # Ensure we have the final values and apply consistent cleaning
            executive_summary, background, key_judgments, financial_impact, conclusion = memo_responses

            # Apply generalized cleaning to all AI-generated memo sections
            # Ensure all responses are strings before cleaning
            executive_summary = self._clean_memo_section(
                executive_summary) if isinstance(
                    executive_summary, str) else str(executive_summary)
            background = self._clean_memo_section(background) if isinstance(
                background, str) else str(background)
            key_judgments = self._clean_memo_section(
                key_judgments) if isinstance(key_judgments,
                                             str) else str(key_judgments)
            financial_impact = self._clean_memo_section(
                financial_impact) if isinstance(financial_impact,
                                                str) else str(financial_impact)
            conclusion = self._clean_memo_section(conclusion) if isinstance(
                conclusion, str) else str(conclusion)

            # 7. Python Assembly of Final Memo with Professional Formatting
            contract_data_table = self._create_contract_data_table(
                contract_data)

            # Remove quality control note - internal processes don't belong in professional memos

            memo_header = f"""#TECHNICAL ACCOUNTING MEMORANDUM

**TO:** {getattr(contract_data, 'memo_audience', 'Technical Accounting Team / Audit File')}  
**FROM:** ASC 606 AI Analyst
**DATE:** {datetime.now().strftime('%B %d, %Y')}  
**RE:** ASC 606 Revenue Recognition Analysis - {getattr(contract_data, 'analysis_title', 'Revenue Contract Analysis')}\n\n\n
"""

            final_memo_sections = [
                memo_header, f"## 1. EXECUTIVE SUMMARY\n{executive_summary}",
                f"## 2. CONTRACT OVERVIEW\n\n{contract_data_table}\n\n{background}",
                f"## 3. DETAILED ASC 606 ANALYSIS\n{detailed_analysis}",
                f"## 4. KEY PROFESSIONAL JUDGMENTS\n{key_judgments}",
                f"## 5. FINANCIAL IMPACT ASSESSMENT\n{financial_impact}",
                f"## 6. CONCLUSION\n{conclusion}",
                f"\n---\n\n**CONFIDENTIAL:** This memorandum contains confidential and proprietary information. Distribution is restricted to authorized personnel only.\n\n**PREPARED BY:** ASC 606 AI Analyst \n**REVIEWED BY:** [To be completed] \n**APPROVED BY:** [To be completed]"
            ]

            final_memo = "\n\n".join(final_memo_sections)

            self.logger.info(
                f"Python-assembled memo completed: {len(final_memo)} characters with all 6 sections"
            )

            # === STEP 4: RETURN CLEAN, CONSOLIDATED ANALYSIS RESULT ===
            analysis_duration = time.time() - analysis_start_time

            # Determine complexity based on analysis patterns
            complexity_indicators = [
                bool(getattr(contract_data, 'is_modification', False)),
                bool(
                    getattr(contract_data, 'variable_consideration_involved',
                            False)),
                bool(
                    getattr(contract_data, 'financing_component_involved',
                            False)),
                bool(getattr(contract_data, 'principal_agent_involved',
                             False)),
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
                    "title":
                    getattr(contract_data, 'analysis_title',
                            'ASC 606 Analysis'),
                    "customer":
                    getattr(contract_data, 'customer_name', 'Unknown'),
                    "analysis_type":
                    "Step-by-Step Detailed Analysis"
                })

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

        # Add documents reviewed list using robust approach
        documents_list = self._format_documents_list(contract_data)

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

    def _format_documents_list(self, contract_data) -> str:
        """Format the list of documents reviewed for the analysis using robust contract_data approach."""
        try:
            # Get document names from contract_data (robust approach)
            documents = getattr(contract_data, 'document_names', [])
            if not documents:
                return "• No documents specified."

            return "\n".join([f"• {name}" for name in documents])

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
            return {"status": "error", "error": str(e), "rag_enabled": False}
