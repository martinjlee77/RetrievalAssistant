"""
ASC 340-40 Contract Costs Analyzer - Following proven ASC 606 pattern
Implements full Retrieval-Augmented Generation workflow for contract costs policy analysis
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

from core.models import ASC340Analysis
from utils.llm import make_llm_call, make_llm_call_async, extract_contract_terms
from core.knowledge_base import get_knowledge_base_manager
from utils.asc340_step_prompts import ASC340StepPrompts


class ASC340Analyzer:
    """ASC 340-40 analyzer using hybrid RAG with ChromaDB knowledge base - following ASC 606 pattern"""

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
            self.logger.info("ASC 340-40 knowledge base manager initialized successfully")
        except Exception as e:
            self.logger.error(f"ASC 340-40 knowledge base manager initialization failed: {e}")
            self.kb_manager = None

    @lru_cache(maxsize=128)
    def _clean_memo_section(self, text: str) -> str:
        """Clean formatting issues in ASC 340-40 policy memo text"""
        if not isinstance(text, str):
            return text

        cleaned_text = text

        # Remove duplicate headers
        unwanted_headers = [
            "# ACCOUNTING POLICY MEMORANDUM", "## ACCOUNTING POLICY MEMORANDUM", 
            "### ACCOUNTING POLICY MEMORANDUM", "**ACCOUNTING POLICY MEMORANDUM**",
            "# SCOPE ASSESSMENT", "## SCOPE ASSESSMENT", "### SCOPE ASSESSMENT",
            "# COST CLASSIFICATION", "## COST CLASSIFICATION", "### COST CLASSIFICATION"
        ]
        
        lines = cleaned_text.split('\n')
        filtered_lines = []
        for line in lines:
            line = line.lstrip('> ')
            line_stripped = line.strip()
            
            if not any(header in line_stripped.upper() for header in [h.upper() for h in unwanted_headers]):
                filtered_lines.append(line)
        
        cleaned_text = '\n'.join(filtered_lines)

        # Clean markdown and excessive whitespace
        cleaned_text = re.sub(r'\*{3,}', '', cleaned_text)
        cleaned_text = re.sub(r'#{1,6}\s*', '', cleaned_text)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        cleaned_text = re.sub(r'^\s*\n', '', cleaned_text, flags=re.MULTILINE)

        return cleaned_text.strip()

    async def extract_policy_terms(self, document_text: str) -> Dict[str, Any]:
        """
        Extract key policy terms from uploaded documents using targeted LLM call.
        This feeds into Step 3 analysis for grounded policy methodology.
        """
        if not document_text or len(document_text.strip()) < 100:
            return {"extracted_terms": [], "note": "Insufficient document content for policy term extraction"}
        
        try:
            system_prompt = """You are an expert at extracting contract cost policy terms from business documents. Extract specific policy clauses, rates, thresholds, and methodologies that would inform ASC 340-40 contract costs accounting policy development."""
            
            user_prompt = f"""Extract key policy terms from this document that would be relevant for ASC 340-40 contract costs policy development.

DOCUMENT TEXT:
{document_text}

Focus on extracting:
1. Commission rates or percentages
2. Fixed fees or amounts
3. Cost categories mentioned
4. Timing of cost recognition
5. Amortization periods mentioned
6. Capitalization criteria
7. Any existing policy language

Return the extracted terms as a JSON object with this structure:
{{
  "commission_rates": ["Any commission rates or percentages found"],
  "fixed_amounts": ["Any fixed dollar amounts mentioned"],
  "cost_categories": ["Types of costs mentioned"],
  "timing_criteria": ["When costs are recognized or capitalized"],
  "amortization_periods": ["Any amortization periods mentioned"],
  "policy_language": ["Existing policy statements found"],
  "other_relevant_terms": ["Any other relevant policy terms"]
}}"""
            
            response = await make_llm_call_async(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gpt-4o",
                json_mode=True
            )
            
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"Policy term extraction failed: {str(e)}")
            return {"error": f"Policy term extraction failed: {str(e)}"}

    def _get_rag_context(self, query: str, specific_keywords: List[str] = None) -> Dict[str, Any]:
        """Retrieve relevant context from ASC 340-40 knowledge base using hybrid search"""
        if not self.kb_manager:
            self.logger.warning("Knowledge base manager not initialized")
            return {"context": "Knowledge base unavailable", "sources": []}

        # Cache key for expensive RAG operations
        cache_key = hashlib.md5(f"{query}_{specific_keywords}".encode()).hexdigest()
        if cache_key in self._rag_cache:
            return self._rag_cache[cache_key]

        try:
            # Get ASC 340-40 collection
            collection = self.kb_manager.get_collection("ASC 340-40")
            
            # Build enhanced query with keywords
            enhanced_query = query
            if specific_keywords:
                enhanced_query += " " + " ".join(specific_keywords)

            # Perform semantic search
            results = collection.query(
                query_texts=[enhanced_query],
                n_results=self.GENERAL_RAG_RESULTS_COUNT,
                include=["documents", "metadatas"]
            )

            if not results['documents'][0]:
                return {"context": "No relevant guidance found", "sources": []}

            # Format context with source attribution
            context_parts = []
            sources = []
            
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                source_info = {
                    'source': metadata.get('source', 'Unknown'),
                    'source_type': metadata.get('source_type', 'unknown'),
                    'section': metadata.get('section', 'Unknown'),
                    'chunk_index': metadata.get('chunk_index', 0)
                }
                sources.append(source_info)
                
                # Add source attribution to context
                source_name = metadata.get('source', 'ASC 340-40')
                context_parts.append(f"{doc}\n(Source: {source_name})")

            context = "\n\n".join(context_parts)
            
            # Cache the result
            result = {"context": context, "sources": sources}
            self._rag_cache[cache_key] = result
            
            return result

        except Exception as e:
            self.logger.error(f"RAG context retrieval failed: {e}")
            return {"context": "RAG system error", "sources": []}

    async def analyze_step(self, step_number: int, contract_text: str, contract_data) -> Dict[str, Any]:
        """Analyze a specific ASC 340-40 step with enhanced RAG context"""
        try:
            # Get step-specific RAG context
            step_info = ASC340StepPrompts.get_step_info()[step_number]
            step_keywords = self._get_step_keywords(step_number)
            
            query = f"ASC 340-40 {step_info['title']} {' '.join(step_keywords)}"
            rag_context = self._get_rag_context(query, step_keywords)

            # Generate analysis using step prompts
            system_prompt = ASC340StepPrompts.get_system_prompt()
            user_prompt = ASC340StepPrompts.get_user_prompt_for_step(
                step_number=step_number,
                contract_text=contract_text,
                rag_context=rag_context['context'],
                contract_data=contract_data
            )

            # Make LLM call
            response = await make_llm_call_async(
                client=self.client,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                model="gpt-4o"  # Using latest model as specified in replit.md
            )

            # Parse and validate response
            try:
                analysis_result = json.loads(response)
                
                # Add metadata
                analysis_result['step_number'] = step_number
                analysis_result['timestamp'] = datetime.now().isoformat()
                analysis_result['rag_sources'] = rag_context['sources']
                
                return analysis_result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse step {step_number} JSON response: {e}")
                return {"error": f"JSON parsing failed: {str(e)}", "raw_response": response}

        except Exception as e:
            self.logger.error(f"Step {step_number} analysis failed: {e}")
            return {"error": f"Analysis failed: {str(e)}"}

    def _get_step_keywords(self, step_number: int) -> List[str]:
        """Get keywords for enhanced RAG query for each step"""
        keyword_map = {
            1: ["scope", "contract costs", "incremental costs", "fulfillment costs", "within scope"],
            2: ["cost classification", "incremental", "fulfillment", "capitalize", "expense"],
            3: ["measurement", "amortization", "recognition", "systematic basis", "impairment"],
            4: ["policy documentation", "controls", "financial impact", "disclosure"]
        }
        return keyword_map.get(step_number, [])

    async def analyze_contract_costs_policy(self, contract_data) -> ASC340Analysis:
        """Main analysis method - generate complete ASC 340-40 policy analysis"""
        try:
            self.logger.info("Starting ASC 340-40 contract costs policy analysis")
            
            # Extract contract text
            contract_text = self._extract_contract_text(contract_data.documents)
            
            # Run all 4 steps concurrently
            step_tasks = []
            for step_num in range(1, 5):  # Steps 1-4
                task = asyncio.create_task(
                    self.analyze_step(step_num, contract_text, contract_data)
                )
                step_tasks.append(task)
            
            # Execute all steps
            step_results = await asyncio.gather(*step_tasks, return_exceptions=True)
            
            # Process results
            analysis_data = {
                "contract_data": contract_data,
                "step1_scope_assessment": step_results[0] if not isinstance(step_results[0], Exception) else {"error": str(step_results[0])},
                "step2_cost_classification": step_results[1] if not isinstance(step_results[1], Exception) else {"error": str(step_results[1])},
                "step3_measurement_policy": step_results[2] if not isinstance(step_results[2], Exception) else {"error": str(step_results[2])},
                "step4_illustrative_impact": step_results[3] if not isinstance(step_results[3], Exception) else {"error": str(step_results[3])},
                "analysis_timestamp": datetime.now().isoformat(),
                "analyzer_version": "ASC340_v1.0"
            }
            
            # Create initial analysis object
            asc340_analysis = ASC340Analysis(**analysis_data)
            
            # Generate the professional memo
            professional_memo = await self.generate_full_memo(asc340_analysis)
            
            # Update analysis data with generated memo
            analysis_data["professional_memo"] = professional_memo
            
            # Create final analysis object with memo
            final_analysis = ASC340Analysis(**analysis_data)
            
            self.logger.info("ASC 340-40 analysis completed successfully")
            return final_analysis
            
        except Exception as e:
            self.logger.error(f"ASC 340-40 analysis failed: {e}")
            raise

    def _extract_contract_text(self, documents: List[Dict[str, Any]]) -> str:
        """Extract and combine text from uploaded documents"""
        if not documents:
            return ""
        
        combined_text = []
        for doc in documents:
            if 'text' in doc and doc['text']:
                combined_text.append(doc['text'])
        
        return "\n\n--- DOCUMENT SEPARATOR ---\n\n".join(combined_text)

    async def generate_full_memo(self, analysis: ASC340Analysis) -> str:
        """Generate complete ASC 340-40 accounting policy memorandum"""
        try:
            # Get memo generation context
            rag_context = self._get_rag_context("accounting policy memorandum disclosure requirements")
            
            system_prompt = ASC340StepPrompts.get_memo_generation_system_prompt()
            user_prompt = ASC340StepPrompts.get_memo_generation_user_prompt(
                analysis=analysis,
                rag_context=rag_context['context']
            )

            # Generate memo
            memo_response = await make_llm_call_async(
                client=self.client,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="gpt-4o"
            )

            # Clean formatting
            cleaned_memo = self._clean_memo_section(memo_response)
            
            return cleaned_memo
            
        except Exception as e:
            self.logger.error(f"Memo generation failed: {e}")
            return f"Error generating memo: {str(e)}"

    def get_analysis_summary(self, analysis: ASC340Analysis) -> Dict[str, Any]:
        """Generate analysis summary for display"""
        return {
            "contract_title": analysis.contract_data.analysis_title,
            "analysis_date": analysis.analysis_timestamp,
            "scope_determination": self._extract_scope_result(analysis.step1_scope_assessment),
            "cost_categories": self._extract_cost_categories(analysis.step2_cost_classification),
            "policy_framework": self._extract_policy_summary(analysis.step3_measurement_policy),
            "total_steps_completed": sum([
                1 if not analysis.step1_scope_assessment.get("error") else 0,
                1 if not analysis.step2_cost_classification.get("error") else 0,
                1 if not analysis.step3_measurement_policy.get("error") else 0,
                1 if not analysis.step4_illustrative_impact.get("error") else 0
            ])
        }

    def _extract_scope_result(self, step1_data: Dict[str, Any]) -> str:
        """Extract scope determination from step 1"""
        if step1_data.get("error"):
            return "Analysis error"
        
        # Look for scope conclusion in analysis points
        analysis_points = step1_data.get("analysis_points", [])
        if analysis_points:
            return "In Scope" if "in scope" in str(analysis_points[0]).lower() else "Requires Review"
        
        return "Not determined"

    def _extract_cost_categories(self, step2_data: Dict[str, Any]) -> List[str]:
        """Extract identified cost categories from step 2"""
        if step2_data.get("error"):
            return ["Analysis error"]
        
        categories = []
        analysis_points = step2_data.get("analysis_points", [])
        
        for point in analysis_points:
            if isinstance(point, dict) and "analysis_text" in point:
                text = point["analysis_text"].lower()
                if "incremental" in text:
                    categories.append("Incremental Costs")
                if "fulfillment" in text:
                    categories.append("Fulfillment Costs")
        
        return categories if categories else ["To be determined"]

    def _extract_policy_summary(self, step3_data: Dict[str, Any]) -> str:
        """Extract policy framework summary from step 3"""
        if step3_data.get("error"):
            return "Analysis error"
        
        # Look for amortization approach in analysis
        analysis_points = step3_data.get("analysis_points", [])
        if analysis_points and isinstance(analysis_points[0], dict):
            return "Systematic amortization policy established"
        
        return "Policy framework defined"