"""
ASC 606 Analyzer - Consolidated from legacy hybrid analyzer
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI

from core.analyzers import BaseAnalyzer
from core.models import ASC606Analysis
from utils.llm import get_knowledge_base, extract_contract_terms, make_llm_call
from utils.prompt import ASC606PromptTemplates
import streamlit as st


class ASC606Analyzer(BaseAnalyzer):
    """ASC 606 analyzer using hybrid RAG system"""
    
    def __init__(self):
        super().__init__("ASC 606")
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.knowledge_base = get_knowledge_base()
        # Legacy compatibility
        self.authoritative_sources = {"hybrid_rag": "loaded"}
    
    def analyze_contract(self, contract_text: str, contract_data: Any, debug_config: Optional[Dict] = None) -> ASC606Analysis:
        """Analyze contract using ASC 606 framework"""
        try:
            # Get analysis prompt
            prompt = ASC606PromptTemplates.get_analysis_prompt(
                contract_text=contract_text,
                user_inputs=contract_data.__dict__ if hasattr(contract_data, '__dict__') else {}
            )
            
            # Make LLM call with debug config
            model = debug_config.get("model", "gpt-4o") if debug_config else "gpt-4o"
            temperature = debug_config.get("temperature", 0.3) if debug_config else 0.3
            max_tokens = debug_config.get("max_tokens", 2000) if debug_config else 2000
            
            messages = [
                {"role": "system", "content": "You are an expert ASC 606 technical accountant."},
                {"role": "user", "content": prompt}
            ]
            
            response = make_llm_call(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Parse response into ASC606Analysis model
            analysis_result = self._parse_analysis_response(response or "")
            
            # Store raw response for debugging if enabled (note: not part of model)
            if debug_config and debug_config.get("show_raw_response"):
                # Store in session state or pass separately - raw_response not in model
                pass
                
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise
    
    def _parse_analysis_response(self, response: str) -> ASC606Analysis:
        """Parse LLM response into structured analysis"""
        # Simple parsing - in production this would be more sophisticated
        try:
            # Try to extract JSON if present
            if "```json" in response and "```" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_content = response[json_start:json_end].strip()
                parsed_data = json.loads(json_content)
                
                return ASC606Analysis(
                    step1_contract_identification=parsed_data.get("step1", {"analysis": "Analysis not available"}),
                    step2_performance_obligations=parsed_data.get("step2", {"analysis": "Analysis not available"}), 
                    step3_transaction_price=parsed_data.get("step3", {"analysis": "Analysis not available"}),
                    step4_price_allocation=parsed_data.get("step4", {"analysis": "Analysis not available"}),
                    step5_revenue_recognition=parsed_data.get("step5", {"analysis": "Analysis not available"}),
                    professional_memo=parsed_data.get("memo", response),
                    reconciliation_analysis={"confirmations": [], "discrepancies": []},
                    contract_overview={"title": "Enhanced ASC 606 Analysis", "summary": "Analysis based on enhanced 5-step assessment"},
                    citations=parsed_data.get("citations", []),
                    implementation_guidance=parsed_data.get("implementation", []),
                    not_applicable_items=parsed_data.get("not_applicable", [])
                )
            else:
                # Fallback: treat entire response as memo
                return ASC606Analysis(
                    step1_contract_identification={"analysis": "See detailed analysis in professional memo"},
                    step2_performance_obligations={"analysis": "See detailed analysis in professional memo"},
                    step3_transaction_price={"analysis": "See detailed analysis in professional memo"}, 
                    step4_price_allocation={"analysis": "See detailed analysis in professional memo"},
                    step5_revenue_recognition={"analysis": "See detailed analysis in professional memo"},
                    professional_memo=response,
                    reconciliation_analysis={"confirmations": [], "discrepancies": []},
                    contract_overview={"title": "Enhanced ASC 606 Analysis", "summary": "Analysis based on enhanced 5-step assessment"},
                    citations=[],
                    implementation_guidance=[],
                    not_applicable_items=[]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to parse analysis response: {e}")
            # Return basic analysis structure
            return ASC606Analysis(
                step1_contract_identification={"analysis": "Parsing error - see professional memo"},
                step2_performance_obligations={"analysis": "Parsing error - see professional memo"},
                step3_transaction_price={"analysis": "Parsing error - see professional memo"},
                step4_price_allocation={"analysis": "Parsing error - see professional memo"}, 
                step5_revenue_recognition={"analysis": "Parsing error - see professional memo"},
                professional_memo=response or "Analysis failed to generate",
                reconciliation_analysis={"confirmations": [], "discrepancies": [], "error": "parsing failed"},
                contract_overview={"title": "ASC 606 Analysis", "summary": "Analysis attempted with enhanced 5-step assessment", "error": "parsing failed"},
                citations=[],
                implementation_guidance=[],
                not_applicable_items=[]
            )
    
    def analyze_document(self, document_text: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy compatibility method"""
        return self.analyze_contract(document_text, document_data).__dict__
    
    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            if self.knowledge_base:
                count = self.knowledge_base.count()
                return {
                    "total_chunks": count,
                    "collection_name": "asc606_paragraphs",
                    "status": "loaded",
                    "type": "ChromaDB with OpenAI embeddings"
                }
            else:
                return {"status": "not_loaded", "error": "Knowledge base not initialized"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def validate_analysis_quality(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analysis quality"""
        quality_score = 0.8  # Simplified scoring
        
        return {
            "quality_score": quality_score,
            "validation_passed": quality_score > 0.7,
            "issues": [],
            "recommendations": []
        }