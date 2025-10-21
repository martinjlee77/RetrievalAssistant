"""
ASC 340-40 Commission Analyzer

This module handles the ASC 340-40 sales commission analysis.
Simplified, natural language approach with clear reasoning chains.
"""

import openai
import os
import logging
import time
import re
import random
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ASC340StepAnalyzer:
    """
    Simplified ASC 340-40 step-by-step analyzer using natural language output.
    Performs 2-step analysis: (1) Scoping & Incremental Test, (2) Amortization & Impairment.
    No complex JSON schemas - just clear, professional analysis.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        # Set up OpenAI client  
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # ===== MODEL CONFIGURATION (CHANGE HERE TO SWITCH MODELS) =====
        # Set use_premium_models to True for GPT-5/GPT-5-mini, False for GPT-4o/GPT-4o-mini
        self.use_premium_models = False
        
        # Model selection based on configuration
        if self.use_premium_models:
            self.main_model = "gpt-5"           # For 5-step analysis
            self.light_model = "gpt-5-mini"     # For summaries/background
        else:
            self.main_model = "gpt-4o"          # For 5-step analysis  
            self.light_model = "gpt-4o-mini"    # For summaries/background
            
        # Backward compatibility
        self.model = self.main_model
        
        # Log model selection
        logger.info(f"🤖 Using {'GPT-5' if self.use_premium_models else 'GPT-4o'} for main analysis, {'GPT-5-mini' if self.use_premium_models else 'GPT-4o-mini'} for light tasks")
        
        # Initialize component
    
    def extract_entity_name_llm(self, contract_text: str) -> str:
        """Extract the company name using LLM analysis."""
        try:
            logger.info("🏢 Extracting company name from documents...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying the company name in sales commissions or service contracts. Your task is to identify the name of the company that is paying the costs to botain a contract from the user-uploaded documents."
                },
                {
                    "role": "user",
                    "content": f"""Based on the user-provided documents, what is the name of the company paying the costs to obtain a contract (e.g., commissions)?

Please identify:
- The company that is responsible for the costs to obtain a contract
- The name including suffixes like Inc., LLC, Corp., etc.
- Ignore addresses, reference numbers, or other non-company identifiers

Contract Text:
{contract_text[:4000]}

Respond with ONLY the company name, nothing else."""
                }
            ]
            
            response_content = self._make_llm_request(messages, self.light_model, "default")
            
            # Track API cost for entity extraction
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=messages,
                response_text=response_content or "",
                model=self.light_model,
                request_type="entity_extraction"
            )
            
            entity_name = response_content
            if entity_name is None:
                logger.warning("LLM returned None for company entity name")
                return "Company"
                
            # Clean the response (remove quotes, extra whitespace)
            entity_name = entity_name.strip().strip('"').strip("'").strip()
            
            # Validate the result
            if len(entity_name) < 2 or len(entity_name) > 120:
                logger.warning(f"LLM returned suspicious company entity name: {entity_name}")
                return "Company"
            
            logger.info(f"✓ Company identified: {entity_name}")
            return entity_name
            
        except Exception as e:
            logger.error(f"Error extracting company entity name with LLM: {str(e)}")
            return "Company"
    
    def extract_party_names_llm(self, contract_text: str) -> Dict[str, Optional[str]]:
        """
        Extract party names from commission capitalization agreement for de-identification.
        
        Returns:
            dict: {
                'company': str,              # The company capitalizing commissions
                'counterparty': str,         # The employee or third-party receiving commissions
                'counterparty_type': str     # 'employee' or 'third_party'
            }
        """
        try:
            logger.info("🔒 Extracting party names for de-identification...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying parties in commission agreements, employment contracts, and contractor agreements."
                },
                {
                    "role": "user",
                    "content": f"""Analyze this commission agreement and identify the TWO main parties:

1. COMPANY: The organization capitalizing sales commissions (paying commissions to obtain customer contracts)
2. COUNTERPARTY: The individual or entity receiving the commissions (may be an employee or third-party contractor/agent)

INSTRUCTIONS:
- Identify the company name with full legal suffixes (Inc., LLC, Corp., Ltd., etc.)
- Identify the counterparty (person or company receiving commissions)
- Determine if the counterparty is an "employee" or "third_party" based on the relationship described
- Look for language like employment agreement, contractor agreement, commission plan, sales compensation
- Ignore addresses, reference numbers, contact details

Contract Text:
{contract_text[:4000]}

Respond with ONLY a JSON object in this exact format:
{{"company": "Company Name Inc.", "counterparty": "John Doe", "counterparty_type": "employee"}}

OR if it's a third-party contractor:
{{"company": "Company Name Inc.", "counterparty": "Sales Agency LLC", "counterparty_type": "third_party"}}"""
                }
            ]
            
            response_content = self._make_llm_request(messages, self.light_model, "default")
            
            # Track API cost
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=messages,
                response_text=response_content or "",
                model=self.light_model,
                request_type="party_extraction"
            )
            
            if not response_content:
                logger.warning("LLM returned empty response for party extraction")
                return {"company": None, "counterparty": None, "counterparty_type": None}
            
            # Log raw response for debugging
            logger.info(f"Raw LLM response for party extraction: {response_content[:200]}")
            
            # Parse JSON response
            response_content = response_content.strip()
            
            # Handle code block formatting if present
            if response_content.startswith("```"):
                response_content = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_content, flags=re.MULTILINE)
            
            party_data = json.loads(response_content)
            
            # Validate and clean
            company = party_data.get("company", "").strip().strip('"').strip("'").strip()
            counterparty = party_data.get("counterparty", "").strip().strip('"').strip("'").strip()
            counterparty_type = party_data.get("counterparty_type", "").strip().lower()
            
            # Validation checks
            company_valid = company and 2 <= len(company) <= 120
            counterparty_valid = counterparty and 2 <= len(counterparty) <= 120
            type_valid = counterparty_type in ["employee", "third_party"]
            
            if not company_valid:
                logger.warning(f"Invalid company name extracted: {company}")
                company = None
            
            if not counterparty_valid:
                logger.warning(f"Invalid counterparty name extracted: {counterparty}")
                counterparty = None
            
            if not type_valid:
                logger.warning(f"Invalid counterparty type extracted: {counterparty_type}, defaulting to 'employee'")
                counterparty_type = "employee"
            
            logger.info(f"✓ Parties extracted - Company: {company}, Counterparty: {counterparty} ({counterparty_type})")
            
            return {"company": company, "counterparty": counterparty, "counterparty_type": counterparty_type}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in party extraction: {str(e)}")
            return {"company": None, "counterparty": None, "counterparty_type": None}
        except Exception as e:
            logger.error(f"Error extracting party names: {str(e)}")
            return {"company": None, "counterparty": None, "counterparty_type": None}
    
    def deidentify_contract_text(self, contract_text: str, company_name: Optional[str], counterparty_name: Optional[str], counterparty_type: Optional[str] = "employee") -> dict:
        """
        Replace party names with generic terms for privacy.
        Handles whitespace variations, line breaks, hyphenated line wraps, and punctuation differences.
        
        Strategy: Normalize both text and party names consistently, then do pattern matching.
        
        Args:
            contract_text: Original contract text
            company_name: Company name to replace with "the Company"
            counterparty_name: Counterparty name to replace with "the Employee" or "the Third Party"
            counterparty_type: 'employee' or 'third_party' to determine replacement term
            
        Returns:
            Dict with keys:
                - success (bool): Whether de-identification succeeded
                - text (str): De-identified text (or original if failed)
                - company_name (str): Original company name
                - counterparty_name (str): Original counterparty name
                - counterparty_type (str): Type of counterparty
                - replacements (list): List of replacement descriptions
                - error (str): Error message if failed, None otherwise
        """
        if not company_name and not counterparty_name:
            logger.warning("⚠️ No party names to de-identify, returning original text")
            return {
                "success": False,
                "text": contract_text,
                "company_name": company_name,
                "counterparty_name": counterparty_name,
                "counterparty_type": counterparty_type,
                "replacements": [],
                "error": "No party names were extracted for de-identification"
            }
        
        # Helper function for text normalization
        def normalize_text(text: str) -> str:
            """
            Normalize text to handle PDF/Word extraction artifacts.
            - Removes soft hyphens (Unicode U+00AD)
            - Converts smart quotes to ASCII quotes
            - Collapses hyphen + newline (line wraps) into space
            - Normalizes multiple whitespace to single space
            """
            # Remove Unicode soft hyphen character
            text = text.replace('\u00AD', '')
            
            # Convert smart quotes (Word/PDF) to regular ASCII quotes
            # Opening/closing double quotes → "
            text = text.replace('\u201C', '"').replace('\u201D', '"')
            # Opening/closing single quotes → '
            text = text.replace('\u2018', "'").replace('\u2019', "'")
            
            # Replace hyphen + newline/whitespace with single space
            # This handles line-wrapped text like "Smith-\nJones LLC" → "Smith Jones LLC"
            text = re.sub(r'-\s*\n\s*', ' ', text)
            
            # Normalize multiple whitespace to single space
            text = re.sub(r'\s+', ' ', text)
            
            return text
        
        # STEP 1: Normalize contract text
        normalized_text = normalize_text(contract_text)
        
        # STEP 2: Normalize extracted party names
        normalized_company = normalize_text(company_name) if company_name else None
        normalized_counterparty = normalize_text(counterparty_name) if counterparty_name else None
        
        deidentified_text = normalized_text
        replacements_made = []
        replacement_count = {}
        
        # Helper function to create flexible pattern
        def create_flexible_pattern(name: str) -> str:
            """
            Create regex pattern that handles:
            - Whitespace variations (spaces, tabs, newlines)
            - Hyphen/space equivalence (handles line-wrapped hyphenated names)
            - Punctuation variations (periods, commas)
            """
            # Escape the name
            escaped = re.escape(name)
            
            # Replace escaped hyphens with pattern matching hyphen OR space
            # This handles: "Smith-Jones" matching "Smith Jones" or "Smith-Jones"
            escaped = escaped.replace(r'\-', r'(?:-|\s)')
            
            # Replace escaped spaces with pattern matching space OR hyphen
            # This handles: "Smith Jones" matching "Smith-Jones" or "Smith Jones"
            escaped = escaped.replace(r'\ ', r'(?:\s+|-)')
            
            # Make periods optional (handles "Inc." vs "Inc")
            escaped = escaped.replace(r'\.', r'\.?')
            
            # Make commas optional (handles "Corp," vs "Corp")
            escaped = escaped.replace(r'\,', r'\,?\s*')
            
            # Word boundary at start and end
            return r'\b' + escaped + r'\b'
        
        # Helper function to extract base company name
        def extract_base_company_name(company_name: str) -> str | None:
            """
            Extract base company name by removing legal suffixes.
            Examples:
            - "Netflix, Inc." → "Netflix"
            - "Acme Corporation" → "Acme"
            - "Smith & Associates LLC" → "Smith & Associates"
            
            Returns None if base name would be too short/generic or same as input.
            """
            # Common legal suffixes (case-insensitive)
            suffixes = [
                r',?\s+Inc\.?',
                r',?\s+LLC\.?',
                r',?\s+L\.?L\.?C\.?',
                r',?\s+Corp\.?',
                r',?\s+Corporation',
                r',?\s+Ltd\.?',
                r',?\s+Limited',
                r',?\s+Co\.?',
                r',?\s+Company',
                r',?\s+L\.?P\.?',
                r',?\s+LLP\.?',
                r',?\s+P\.?L\.?L\.?C\.?',
                r',?\s+S\.?A\.?',
                r',?\s+N\.?V\.?',
                r',?\s+A\.?G\.?',
                r',?\s+GmbH',
                r',?\s+PLC'
            ]
            
            base_name = company_name
            
            # Try removing each suffix
            for suffix_pattern in suffixes:
                # Match suffix at end of string
                pattern = suffix_pattern + r'$'
                base_name = re.sub(pattern, '', base_name, flags=re.IGNORECASE).strip()
            
            # Also remove trailing commas/periods if left over
            base_name = base_name.rstrip('.,').strip()
            
            # Only return if:
            # 1. It's different from original (we actually removed something)
            # 2. It's at least 3 characters (avoid overly generic like "A", "XY")
            # 3. It contains at least one letter (not just numbers/symbols)
            if (base_name != company_name and 
                len(base_name) >= 3 and 
                re.search(r'[A-Za-z]', base_name)):
                return base_name
            
            return None
        
        # Helper function to extract aliases from text patterns
        def extract_aliases_from_text(company_name: str, text: str) -> list:
            """
            Find actual aliases used in the text for this company.
            Looks for patterns like: 
            - Company Name Inc. ("ShortName")
            - Company Name Inc. ('ShortName')
            - Company Name Inc. ("Alias1" or "Alias2")
            """
            aliases = []
            
            # Escape company name for regex
            escaped_name = re.escape(company_name)
            
            # More specific pattern for parenthetical aliases
            # Allow optional punctuation (commas, periods) between company name and parenthesis
            paren_pattern = escaped_name + r'[,\.\s]*\(([^)]{2,200})\)'
            
            matches = re.finditer(paren_pattern, text, flags=re.IGNORECASE)
            for match in matches:
                content = match.group(1).strip()
                
                # Extract all quoted strings from the parenthetical content
                # This focuses on actual aliases and avoids false positives from descriptive clauses
                quoted_aliases = re.findall(r'["\']([A-Za-z0-9\s\-&]{2,50})["\']', content)
                
                for alias in quoted_aliases:
                    alias = alias.strip()
                    # Only accept if it looks like an alias (not numbers-only)
                    if alias and 2 <= len(alias) <= 50:
                        if re.match(r'^[A-Za-z0-9\s\-&]+$', alias) and not re.match(r'^\d+$', alias):
                            aliases.append(alias)
            
            return list(set(aliases))  # Remove duplicates
        
        # Replace company with "the Company"
        if normalized_company:
            # First replace the full name
            pattern = create_flexible_pattern(normalized_company)
            matches = list(re.finditer(pattern, deidentified_text, flags=re.IGNORECASE))
            match_count = len(matches)
            
            if match_count > 0:
                deidentified_text = re.sub(pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                replacements_made.append(f"company '{company_name}' → 'the Company' ({match_count} occurrences)")
                replacement_count['company'] = match_count
            else:
                logger.warning(f"⚠️ Company name '{company_name}' (normalized: '{normalized_company}') not found in contract text")
                replacement_count['company'] = 0
            
            # Also replace base company name (e.g., "Netflix" from "Netflix, Inc.")
            base_company_name = extract_base_company_name(normalized_company)
            if base_company_name:
                base_pattern = create_flexible_pattern(base_company_name)
                base_matches = list(re.finditer(base_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(base_matches) > 0:
                    deidentified_text = re.sub(base_pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced company base name '{base_company_name}' ({len(base_matches)} occurrences)")
            
            # Also replace aliases found in the text (e.g., "InnovateTech" from "InnovateTech Solutions Inc., ('InnovateTech')")
            aliases = extract_aliases_from_text(normalized_company, normalized_text)
            for alias in aliases:
                alias_pattern = create_flexible_pattern(alias)
                alias_matches = list(re.finditer(alias_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(alias_matches) > 0:
                    deidentified_text = re.sub(alias_pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced company alias '{alias}' ({len(alias_matches)} occurrences)")
        
        # Replace counterparty with "the Employee" or "the Third Party"
        counterparty_replacement = "the Employee" if counterparty_type == "employee" else "the Third Party"
        
        if normalized_counterparty:
            # First replace the full name
            pattern = create_flexible_pattern(normalized_counterparty)
            matches = list(re.finditer(pattern, deidentified_text, flags=re.IGNORECASE))
            match_count = len(matches)
            
            if match_count > 0:
                deidentified_text = re.sub(pattern, counterparty_replacement, deidentified_text, flags=re.IGNORECASE)
                replacements_made.append(f"counterparty '{counterparty_name}' → '{counterparty_replacement}' ({match_count} occurrences)")
                replacement_count['counterparty'] = match_count
            else:
                logger.warning(f"⚠️ Counterparty name '{counterparty_name}' (normalized: '{normalized_counterparty}') not found in contract text")
                replacement_count['counterparty'] = 0
            
            # Also replace base counterparty name if it's a company
            base_counterparty_name = extract_base_company_name(normalized_counterparty)
            if base_counterparty_name:
                base_pattern = create_flexible_pattern(base_counterparty_name)
                base_matches = list(re.finditer(base_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(base_matches) > 0:
                    deidentified_text = re.sub(base_pattern, counterparty_replacement, deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced counterparty base name '{base_counterparty_name}' ({len(base_matches)} occurrences)")
            
            # Also replace aliases found in the text
            aliases = extract_aliases_from_text(normalized_counterparty, normalized_text)
            for alias in aliases:
                alias_pattern = create_flexible_pattern(alias)
                alias_matches = list(re.finditer(alias_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(alias_matches) > 0:
                    deidentified_text = re.sub(alias_pattern, counterparty_replacement, deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced counterparty alias '{alias}' ({len(alias_matches)} occurrences)")
        
        # Check if de-identification succeeded
        if not replacements_made:
            error_msg = (
                f"Privacy extraction did not detect party names in the contract text. "
                f"Extracted names (company: '{company_name}', counterparty: '{counterparty_name}') "
                f"were not found in the contract."
            )
            logger.warning(f"⚠️ {error_msg}")
            return {
                "success": False,
                "text": contract_text,  # Return original text
                "company_name": company_name,
                "counterparty_name": counterparty_name,
                "counterparty_type": counterparty_type,
                "replacements": [],
                "error": error_msg
            }
        
        # Log success
        logger.info(f"✓ De-identification complete: {', '.join(replacements_made)}")
        
        return {
            "success": True,
            "text": deidentified_text,
            "company_name": company_name,
            "counterparty_name": counterparty_name,
            "counterparty_type": counterparty_type,
            "replacements": replacements_made,
            "error": None
        }
    
    def _get_temperature(self, model_name=None):
        """Get appropriate temperature based on model."""
        target_model = model_name or self.model
        if target_model in ["gpt-5", "gpt-5-mini"]:
            return 1  # GPT-5 models only support default temperature of 1
        else:
            return 0.3  # GPT-4o models can use 0.3
    
    def _get_max_tokens_param(self, request_type="default", model_name=None):
        """Get appropriate max tokens parameter based on model and request type."""
        target_model = model_name or self.model
        if target_model in ["gpt-5", "gpt-5-mini"]:
            # GPT-5 models need high token counts due to reasoning overhead
            token_limits = {
                "step_analysis": 10000,
                "executive_summary": 10000,
                "background": 10000,
                "conclusion": 10000,
                "default": 10000
            }
            return {"max_completion_tokens": token_limits.get(request_type, 10000)}
        else:
            # GPT-4o models use standard limits
            token_limits = {
                "step_analysis": 2000,
                "executive_summary": 1000,
                "background": 500,
                "conclusion": 800,
                "default": 2000
            }
            return {"max_tokens": token_limits.get(request_type, 2000)}
    
    def _make_llm_request(self, messages, model=None, request_type="default"):
        """Helper method to route between Responses API (GPT-5) and Chat Completions API (GPT-4o)."""
        target_model = model or self.model
        
        if target_model in ["gpt-5", "gpt-5-mini"]:
            # Use Responses API for GPT-5 models
            response = self.client.responses.create(
                model=target_model,
                input=messages,
                max_output_tokens=10000,  # GPT-5 uses max_output_tokens
                reasoning={"effort": "medium"}
            )
            # Access response content from Responses API format
            return response.output_text
        else:
            # Use Chat Completions API for GPT-4o models
            request_params = {
                "model": target_model,
                "messages": messages,
                "temperature": self._get_temperature(target_model),
                **self._get_max_tokens_param(request_type, target_model)
            }
            response = self.client.chat.completions.create(**request_params)
            return response.choices[0].message.content
    
    def analyze_contract(self, 
                        contract_text: str,
                        authoritative_context: str,
                        customer_name: str,
                        analysis_title: str,
                        additional_context: str = "") -> Dict[str, Any]:
        """
        Perform complete 2-step ASC 340-40 analysis.
        
        Args:
            contract_text: The contract document text
            authoritative_context: Retrieved ASC 340-40 guidance
            customer_name: Customer/company name
            analysis_title: Analysis title
            additional_context: Optional user-provided context
            
        Returns:
            Dictionary containing analysis results for each step
        """
        analysis_start_time = time.time()
        logger.info(f"Starting ASC 340-40 analysis for {customer_name}")
        
        # Add large contract warning
        word_count = len(contract_text.split())
        if word_count > 50000:
            logger.warning(f"Large contract ({word_count} words). Consider splitting if analysis fails.")
        
        results = {
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y"),
            'steps': {}
        }
        
        # Analyze steps in parallel with error recovery
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all step analyses
            futures = {
                executor.submit(
                    self._analyze_step_with_retry,
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name,
                    additional_context=additional_context
                ): step_num
                for step_num in range(1, 3)
            }
            
            # Collect results as they complete
            for future in futures:
                step_num = futures[future]
                try:
                    results['steps'][f'step_{step_num}'] = future.result()
                    logger.info(f"Completed Step {step_num}")
                except Exception as e:
                    logger.error(f"Final error in Step {step_num}: {str(e)}")
                    results['steps'][f'step_{step_num}'] = {
                        'title': self._get_step_title(step_num),
                        'analysis': f"Error analyzing this step: {str(e)}",
                        'conclusion': "Analysis incomplete due to error"
                    }
        
        # Generate additional sections using clean LLM calls
        logger.info("Starting additional section generation")
        logger.info(f"DEBUG: Results structure keys: {results.keys()}")
        logger.info(f"DEBUG: Steps data keys: {results['steps'].keys()}")
        
        # DEBUG: Log step data before extraction
        logger.info(f"DEBUG: About to extract conclusions from steps: {list(results['steps'].keys())}")
        for step_key, step_data in results['steps'].items():
            if isinstance(step_data, dict):
                logger.info(f"DEBUG: {step_key} structure: {list(step_data.keys())}")
                if 'markdown_content' in step_data:
                    content = step_data['markdown_content']
                    logger.info(f"DEBUG: {step_key} content length: {len(content)}")
        
        conclusions_text = self._extract_conclusions_from_steps(results['steps'])
        logger.info(f"DEBUG: Extracted conclusions text length: {len(conclusions_text)} chars")
        
        # Generate executive summary, background, and conclusion
        results['executive_summary'] = self.generate_executive_summary(conclusions_text, customer_name)
        results['background'] = self.generate_background_section(conclusions_text, customer_name)
        results['conclusion'] = self.generate_final_conclusion(results['steps'])
        
        total_time = time.time() - analysis_start_time
        logger.info(f"✓ ASC 340-40 analysis completed successfully in {total_time:.1f}s")
        return results
    
    def _analyze_step_with_retry(self,
                               step_num: int,
                               contract_text: str,
                               authoritative_context: str,
                               customer_name: str,
                               additional_context: str = "") -> Dict[str, str]:
        """Analyze a single step with enhanced retry logic for production scalability."""
        max_retries = 4  # Increased from 2
        base_delay = 1
        step_start_time = time.time()
        
        logger.info(f"→ Step {step_num}: Starting analysis using {self.main_model}...")
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retrying Step {step_num} (attempt {attempt + 1})")
                
                result = self._analyze_step(
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name,
                    additional_context=additional_context
                )
                
                step_time = time.time() - step_start_time
                logger.info(f"✓ Step {step_num}: Completed in {step_time:.1f}s")
                return result
            except openai.RateLimitError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Rate limit exceeded for Step {step_num} after {max_retries} attempts")
                    raise RuntimeError(f"OpenAI API rate limit exceeded. Please try again in a few minutes or contact support if this persists.")
                
                # Exponential backoff with jitter for rate limits
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"⚠️ Rate limit hit on Step {step_num}, waiting {delay:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                
            except openai.APITimeoutError as e:
                if attempt == max_retries - 1:
                    logger.error(f"API timeout for Step {step_num} after {max_retries} attempts")
                    raise RuntimeError(f"OpenAI API timeout. Please check your connection and try again.")
                
                delay = base_delay * (1.5 ** attempt)
                logger.warning(f"API timeout for Step {step_num}. Retrying in {delay:.1f}s")
                time.sleep(delay)
                
            except openai.APIConnectionError as e:
                if attempt == max_retries - 1:
                    logger.error(f"API connection error for Step {step_num} after {max_retries} attempts")
                    raise RuntimeError(f"Unable to connect to OpenAI API. Please check your internet connection.")
                
                delay = base_delay * (1.5 ** attempt)
                logger.warning(f"Connection error for Step {step_num}. Retrying in {delay:.1f}s")
                time.sleep(delay)
                
            except openai.APIError as e:
                # Handle other API errors
                error_msg = str(e).lower()
                if "rate" in error_msg or "quota" in error_msg:
                    # Treat as rate limit even if not caught above
                    if attempt == max_retries - 1:
                        raise RuntimeError(f"OpenAI API quota/rate limit issue. Please try again later.")
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"API quota issue for Step {step_num}. Waiting {delay:.1f}s")
                    time.sleep(delay)
                else:
                    logger.error(f"OpenAI API error for Step {step_num}: {str(e)}")
                    raise RuntimeError(f"OpenAI API error: {str(e)}")
                    
            except Exception as e:
                # Check for context length errors
                error_str = str(e).lower()
                if "context_length" in error_str or "token" in error_str:
                    logger.error(f"✗ Step {step_num}: Context window exceeded - contract too large")
                    raise RuntimeError(f"Step {step_num}: Context window exceeded - contract too large")
                
                if attempt == max_retries - 1:
                    logger.error(f"Unexpected error for Step {step_num} after {max_retries} attempts: {str(e)}")
                    raise RuntimeError(f"Analysis failed for Step {step_num}: {str(e)}")
                else:
                    delay = base_delay * (1.2 ** attempt)
                    logger.warning(f"Unexpected error for Step {step_num}. Retrying in {delay:.1f}s: {str(e)}")
                    time.sleep(delay)
        
        # This should never be reached
        raise RuntimeError(f"Unexpected error: Step {step_num} analysis failed without proper error handling")
    
    def _analyze_step(self, 
                     step_num: int,
                     contract_text: str,
                     authoritative_context: str,
                     customer_name: str,
                     additional_context: str = "") -> Dict[str, str]:
        """Analyze a single ASC 340-40 step - returns clean markdown."""
        
        # Get step-specific prompt for markdown output
        prompt = self._get_step_markdown_prompt(
            step_num=step_num,
            contract_text=contract_text,
            authoritative_context=authoritative_context,
            customer_name=customer_name,
            additional_context=additional_context
        )
        
        # Make API call
        try:
            logger.info(f"DEBUG: Making API call to {self.model} for Step {step_num}")
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self._get_markdown_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                **self._get_max_tokens_param("step_analysis"),
                "temperature": self._get_temperature()
            }
            
            # Add response_format only for GPT-5
            if self.model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            # Track API cost for this request
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=request_params["messages"],
                response_text=response.choices[0].message.content or "",
                model=self.model,
                request_type=f"step_{step_num}_analysis"
            )
            
            markdown_content = response.choices[0].message.content
            
            if markdown_content is None or not markdown_content.strip():
                error_msg = f"GPT-5 returned empty/None content for Step {step_num}"
                logger.error(f"ERROR: {error_msg}")
                raise ValueError(error_msg)  # Raise exception to trigger retry
            
            # Content received successfully - strip whitespace
            markdown_content = markdown_content.strip()
            
            # Check for suspiciously short response (< 100 chars likely indicates incomplete response)
            if len(markdown_content) < 100:
                error_msg = f"Step {step_num}: Response too short ({len(markdown_content)} chars) - likely incomplete"
                logger.warning(f"⚠️ {error_msg}")
                raise ValueError(error_msg)  # Raise exception to trigger retry
            
            # Validate the output for quality assurance
            validation_result = self.validate_step_output(markdown_content, step_num)
            if not validation_result["valid"]:
                logger.warning(f"Step {step_num} validation issues: {validation_result['issues']}")
                
                # Check for critical missing sections (Analysis or Conclusion)
                critical_issues = [issue for issue in validation_result['issues'] 
                                 if 'Missing Analysis section' in issue or 'Missing Conclusion section' in issue]
                
                if critical_issues:
                    # Critical sections missing - trigger retry
                    error_msg = f"Step {step_num}: Critical sections missing - {'; '.join(critical_issues)}"
                    logger.error(f"⚠️ {error_msg}")
                    raise ValueError(error_msg)  # Raise exception to trigger retry
                
                # For non-critical issues, append validation notes
                if "**Issues or Uncertainties:**" in markdown_content:
                    issues_section = "\n\n**Validation Notes:** " + "; ".join(validation_result["issues"])
                    markdown_content = markdown_content.replace(
                        "**Issues or Uncertainties:**", 
                        "**Issues or Uncertainties:**" + issues_section + "\n\n"
                    )
            
            # Log sample of clean content for verification
            logger.info(f"DEBUG: Clean markdown for Step {step_num} (length: {len(markdown_content)} chars)")
            
            # Return clean markdown content - NO PROCESSING
            return {
                'title': self._get_step_title(step_num),
                'markdown_content': markdown_content,
                'step_num': str(step_num)
            }
            
        except Exception as e:
            logger.error(f"API error in step {step_num}: {str(e)}")
            raise
    
    def validate_step_output(self, markdown_content: str, step_num: int) -> Dict[str, Any]:
        """Validate step output for required sections and formatting issues."""
        issues = []
        
        # Check for required sections - accept both bold and non-bold formats at line start
        # Pattern matches: **Analysis:** or Analysis: at the start of a line
        if not re.search(r'^(\*\*)?Analysis:\s*(\*\*)?', markdown_content, re.MULTILINE):
            issues.append(f"Missing Analysis section in Step {step_num}")
        
        if not re.search(r'^(\*\*)?Conclusion:\s*(\*\*)?', markdown_content, re.MULTILINE):
            issues.append(f"Missing Conclusion section in Step {step_num}")
        
        # Check currency formatting - flag numbers that look like currency but missing $
        bad_currency = re.findall(r'\b\d{1,3}(?:,\d{3})*\b(?!\.\d)', markdown_content)
        # Filter out obvious non-currency (years, quantities, etc.)
        suspicious_currency = [num for num in bad_currency if int(num.replace(',', '')) > 1000]
        if suspicious_currency:
            issues.append(f"Currency potentially missing $ symbol: {suspicious_currency}")
        
        # Flag potentially fabricated citations (section numbers, page numbers)
        fake_citations = re.findall(r'\[Contract\s*§|\bp\.\s*\d+\]', markdown_content)
        if fake_citations:
            issues.append(f"Potentially fabricated citations: {fake_citations}")
        
        return {"valid": len(issues) == 0, "issues": issues}
    
    def _get_markdown_system_prompt(self) -> str:
        """Get the system prompt for markdown generation."""
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 340-40 Contract Costs. 

Generate professional accounting analysis in clean markdown format. Your output will be displayed directly using markdown rendering.

Your analysis must be:
- Audit-ready and professional
- Clear and understandable
- Based on the evidence provided in the contract text
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
- Support your analysis with specific contract text and authoritative citations
- Use direct quotes from the contract document only when the exact wording is outcome-determinative
- Paraphrase ASC 340-40 with pinpoint citations; brief decisive phrases may be quoted when directly supportive
- Acknowledge any limitations or gaps in information
- Formatted as clean, ready-to-display markdown

Follow ALL formatting instructions in the user prompt precisely."""
    
    def _get_step_markdown_prompt(self, 
                        step_num: int,
                        contract_text: str, 
                        authoritative_context: str,
                        customer_name: str,
                        additional_context: str = "") -> str:
        """Generate markdown prompt for a specific step."""
        
        step_info = {
            1: {
                'title': 'Step 1: Scoping and Incremental Test',
                'focus': 'Determine whether the commission plan is within the scope and capitalizable under ASC 340-40',
                'key_points': [
                    'Determine based on the uploaded documents whether there is any consideration payable to a customer (ASC 606-10-32-25 through 32-27), which is outside the scope of ASC 340-40. Examples include rebates, credits, referral, or marketing fees paid to a customer or the customer’s customer. Evaluate whether the recipient of the commission is an employee or agent (third party) or a customer to aid this determination.',
                    'IMPORTANT: This analysis does not cover the costs incurred in fulfilling a contract with a customer (ASC 340-40-25-5 to 25-8). It only covers costs to obtain a contract.',
                    'Evaluate incremental test: Costs incurred solely because contract obtained + recovery expected → capitalize. Otherwise → expense. (ASC 340-40-25-1 to 25-3).',
                    'If not incremental or recovery not expected (ASC 340-40-25-3), expense the cost.',
                    'Common capitalizable (if incremental): Contract-specific commissions, success-based agent fees, accelerators attributable to specific contract, employer payroll taxes on capitalized amounts.',
                    'Common expense (not incremental): Base salary, aggregate-based contests, nonrecoverable draws, training, recruiting, general SPIFFs.'
                ]
            },
            2: {
                'title': 'Step 2: Guidance for Amortization, Practical Expedient, and Impairment',
                'focus': 'Provide policy boilerplate and guidance only; no calculations or analysis.',
                'key_points': [
                    'Describe the amortization approach for capitalized costs (systematic basis, period of benefit considerations, renewal commissions commensurate with initial commissions).',
                    'Mention the practical expedient in which the cost is expensed as incurred if the amortization period would be one year or less. Application can be by portfolio but the policy should be documented.',
                    'Explain that changes in estimates result in adjusting amortization prospectively when the expected period of benefit changes (e.g., churn/renewal assumptions).',
                    'Explain that at each reporting date, recognize impairment if the carrying amount exceeds the remaining amount of consideration expected to be received (less costs related to providing those goods/services). Reversals are not permitted.',
                    'Note that a portfolio approach can be applied if it would not materially differ from a contract-by-contract approach (e.g., for determining amortization periods and impairment).'
                ]
            }
        }
        
        step = step_info[step_num]
        
        prompt = f"""
STEP {step_num}: {step['title'].upper()}

OBJECTIVE: {step['focus']}

COST INFORMATION:
Cost Analysis: Analyze the documents to determine the appropriate accounting for the sales commission under ASC 340-40 for the company.

Instructions: Analyze the user-provided documents from the company's perspective. 

CONTRACT TEXT:
{contract_text}"""

        if additional_context.strip():
            prompt += f"""

ADDITIONAL CONTEXT:
{additional_context}"""

        prompt += f"""

AUTHORITATIVE GUIDANCE:
{authoritative_context}

ANALYSIS REQUIRED:
Analyze the contract cost documents for Step {step_num} focusing on:
{chr(10).join([f"• {point}" for point in step['key_points']])}

REQUIRED OUTPUT FORMAT (Clean Markdown):

### {step['title']}

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific evidence from user-provided documents and ASC 340-40 citations. Quote language from user-provided documents only when the exact wording is outcome‑determinative; paraphrase ASC 340-40 with pinpoint citations and use only brief decisive phrases when directly supportive.]

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion]
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed citations)
- Contract citations must reference actual text from the document:
    Good: [Commission Plan, Incentive Payout]
    Bad: [Commission Plan §4.2], [Commission Plan, p. 15] (unless these exact references appear in the contract text)
- Only cite section numbers/page numbers if they are explicitly visible in the contract text
- ASC 340-40 guidance paraphrased with citations; include only brief decisive phrases when directly supportive (e.g., [ASC 340-40-25-1])


**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 340-40 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

CRITICAL ANALYSIS REQUIREMENTS - CONTRACT VS EXTERNAL DATA:

1. CONTRACT FACTS (dates, terms, amounts explicitly in the document):
   - If present: Quote or paraphrase with citation
   - If missing: State "Not specified in contract"
   - NEVER invent or guess these

2. EXTERNAL INPUTS (accounting policies, valuations, judgments NOT in contract):
   - Always state the ASC 340-40 requirement
   - Create management placeholder: "[Management Input Required: Expected period of benefit per ASC 340-40-35-1]"
   - Examples: amortization period, practical expedient elections, impairment assessments

3. CITATION RULES:
   - Contract: Only cite what's visible - [Commission Plan, Payout Terms] ✓  |  [Plan §3.1] ✗ (unless §3.1 appears)
   - ASC 340-40: Paraphrase + pinpoint cite - [ASC 340-40-25-1]

Use assertive language ("We conclude...") when evidence supports it; flag gaps explicitly.

FORMATTING:
- Format currency as: $240,000 (with comma, no spaces)
- Use proper spacing after periods and commas
- Use professional accounting language
- Double-check all currency amounts for correct formatting

"""
        
        return prompt
    
    # REMOVED: _fix_formatting_issues - using clean GPT-4o markdown directly
    # REMOVED: _parse_step_response - unused method (replaced by direct markdown approach)
    
    def _get_step_title(self, step_num: int) -> str:
        """Get the title for a step."""
        titles = {
            1: "Step 1: Scoping and Incremental Test",
            2: "Step 2: Guidance for Amortization, Practical Expedient, and Impairment"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    # REMOVED: _apply_basic_formatting - using clean GPT-4o markdown directly
    
    def _extract_conclusions_from_steps(self, steps_data: Dict[str, Any]) -> str:
        """Extract conclusion text from all completed steps."""
        conclusions = []
        logger.info(f"Extracting conclusions from {len(steps_data)} steps")
        logger.info(f"DEBUG: steps_data keys: {list(steps_data.keys())}")
        
        for step_num in range(1, 3):
            step_key = f'step_{step_num}'
            if step_key in steps_data:
                step_data = steps_data[step_key]
                if isinstance(step_data, dict) and 'markdown_content' in step_data:
                    # Extract conclusion from markdown content using clean regex approach (ASC 842 pattern)
                    markdown_content = step_data['markdown_content']
                    
                    # Look for conclusion section in markdown - try markers first, then improved regex
                    import re
                    
                    # Try markers first ([BEGIN_CONCLUSION]...[END_CONCLUSION])
                    marker_match = re.search(r'\[BEGIN_CONCLUSION\](.*?)\[END_CONCLUSION\]', markdown_content, re.DOTALL)
                    if marker_match:
                        conclusion = marker_match.group(1).strip()
                    else:
                        # Try all four conclusion patterns for maximum robustness
                        # Pattern 1: **Conclusion:** (bold with colon)
                        conclusion_match = re.search(r'\*\*Conclusion:\*\*\s*(.+?)(?:\n\s*\*\*|$)', markdown_content, re.IGNORECASE | re.DOTALL)
                        if not conclusion_match:
                            # Pattern 2: Conclusion: (plain text with colon)
                            conclusion_match = re.search(r'^Conclusion:\s*(.+?)(?:\n\s*(?:\*\*|[A-Z][a-z]+:)|$)', markdown_content, re.IGNORECASE | re.DOTALL | re.MULTILINE)
                        if not conclusion_match:
                            # Pattern 3: **Conclusion** (bold without colon)
                            conclusion_match = re.search(r'\*\*Conclusion\*\*\s+(.+?)(?:\n\s*\*\*|$)', markdown_content, re.IGNORECASE | re.DOTALL)
                        if not conclusion_match:
                            # Pattern 4: Conclusion (plain text without colon)
                            conclusion_match = re.search(r'^Conclusion\s+(.+?)(?:\n\s*(?:\*\*|[A-Z][a-z]+:)|$)', markdown_content, re.IGNORECASE | re.DOTALL | re.MULTILINE)
                        
                        if conclusion_match:
                            conclusion = conclusion_match.group(1).strip()
                        else:
                            conclusion = None
                    
                    if conclusion:
                        conclusions.append(f"Step {step_num}: {conclusion}")
                        logger.info(f"Extracted conclusion for Step {step_num} (length: {len(conclusion)} chars)")
                    else:
                        logger.info(f"DEBUG: Failed to extract conclusion from Step {step_num}")
                        logger.info(f"DEBUG: Step {step_num} content contains '**Conclusion:**': {'**Conclusion:**' in markdown_content}")
                        logger.info(f"DEBUG: Step {step_num} content length: {len(markdown_content)} chars")
                else:
                    logger.warning(f"Step {step_num} data structure: {type(step_data)}, keys: {step_data.keys() if isinstance(step_data, dict) else 'N/A'}")
        
        conclusions_text = '\n\n'.join(conclusions)
        logger.info(f"Total conclusions extracted: {len(conclusions)}, text length: {len(conclusions_text)}")
        
        # If still no conclusions, generate fallback from step summaries
        if len(conclusions) == 0:
            logger.warning("No conclusions extracted - using fallback summary generation")
            for step_num in range(1, 3):
                step_key = f'step_{step_num}'
                if step_key in steps_data:
                    step_data = steps_data[step_key]
                    if isinstance(step_data, dict) and 'markdown_content' in step_data:
                        content = step_data['markdown_content']
                        # Extract the title and create a simple summary
                        if '### Step' in content and '**Analysis:**' in content:
                            # Get a brief summary from the content
                            summary = f"Step {step_num} completed - analysis of the provided documents under ASC 340-40."
                            conclusions.append(summary)
        
        return conclusions_text
    
    def generate_executive_summary(self, conclusions_text: str, customer_name: str) -> str:
        """Generate executive summary using clean LLM call."""
        logger.info("→ Generating executive summary...")
        
        prompt = f"""Generate a professional executive summary for an ASC 340-40 analysis for {customer_name}.

Step Conclusions:
{conclusions_text}

Requirements:
1. Write 3-5 sentences with proper paragraph breaks
2. Format all currency as $XXX,XXX (no spaces in numbers)
3. Use professional accounting language
4. State whether the nature of the contract costs described in the documents reviewed are incremental and quality for capitalization
5. State compliance conclusion clearly
6. Highlight any significant findings or issues
7. Use double line breaks between paragraphs for readability
8. ALWAYS format currency with $ symbol (e.g., $240,000, not 240,000)
9. Include proper spacing after commas and periods
10. DO NOT include any title or header like "Executive Summary:" - only provide the summary content"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing executive summaries for ASC 340-40 analyses. Provide clean, professional content with proper currency formatting."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self._get_temperature()
            }
            params.update(self._get_max_tokens_param("executive_summary"))
            
            response = self.client.chat.completions.create(**params)
            
            # Track API cost for executive summary
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=params["messages"],
                response_text=response.choices[0].message.content or "",
                model=params["model"],
                request_type="executive_summary"
            )
            
            content = response.choices[0].message.content
            if content:
                content = content.strip()
                logger.info(f"✓ Executive summary generated ({len(content)} chars)")
                return content
            else:
                logger.error("Empty executive summary response")
                return "Executive summary generation failed. Please review individual step analyses below."
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return "Executive summary generation failed. Please review individual step analyses below."
    
    def generate_background_section(self, conclusions_text: str, customer_name: str) -> str:
        """Generate background section using clean LLM call."""
        logger.info("→ Generating background section...")
        
        prompt = f"""Generate a professional 2-3 sentence background for an ASC 340-40 memo.

Company: {customer_name}
Contract Summary: {conclusions_text}

Instructions:
1. Describe what type of arrangement was reviewed (high-level)
2. Mention key cost elements if evident
3. State the purpose of the ASC 340-40 analysi
4. Professional accounting language
5. Keep it high-level, no specific amounts or detailed terms"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing background sections for ASC 340-40 memos. Provide clean, professional content."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self._get_temperature()
            }
            params.update(self._get_max_tokens_param("background"))
            
            response = self.client.chat.completions.create(**params)
            
            # Track API cost for background section
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=params["messages"],
                response_text=response.choices[0].message.content or "",
                model=params["model"],
                request_type="background_generation"
            )
            
            content = response.choices[0].message.content
            if content:
                content = content.strip()
                logger.info(f"✓ Background section generated ({len(content)} chars)")
                return content
            else:
                logger.error("Empty background response")
                return f"We have reviewed the contract cost documents provided by {customer_name} to determine the appropriate accounting treatment under ASC 340-40."
            
        except Exception as e:
            logger.error(f"Error generating background: {str(e)}")
            return f"We have reviewed the contract cost documents provided by {customer_name} to determine the appropriate accounting treatment under ASC 340-40."
    
    
    def generate_final_conclusion(self, conclusions_text: str) -> str:
        """Generate LLM-powered final conclusion from step conclusions.
        
        Args:
            conclusions_text: Pre-extracted conclusions from all steps
        """
        logger.info("→ Generating final conclusion...")
        prompt = f"""Generate a professional final conclusion for an ASC 340-40 analysis.

Step Conclusions:
{conclusions_text}

Instructions:
1. Write 2-3 sentences in narrative paragraph format evaluating whether the costs are accounted for properly under ASC 340-40
2. Format all currency as $XXX,XXX (no spaces in numbers)
3. Be direct - if there are concerns, state them clearly
4. Use professional accounting language without bullet points
5. Use proper paragraph spacing
6. ALWAYS format currency with single $ symbol (never $$)
7. Include proper spacing after commas and periods"""

        # Call LLM API
        try:
            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert technical accountant specializing in ASC 340-40 contract costs."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": self._get_temperature(self.light_model),
                **self._get_max_tokens_param("conclusion", self.light_model)
            }
            
            response = self.client.chat.completions.create(**request_params)
            
            # Track API cost for final conclusion
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=request_params["messages"],
                response_text=response.choices[0].message.content or "",
                model=self.light_model,
                request_type="final_conclusion"
            )
            
            conclusion = response.choices[0].message.content.strip()
            logger.info(f"✓ Final conclusion generated ({len(conclusion)} chars)")
            return conclusion
            
        except Exception as e:
            logger.error(f"Final conclusion generation failed: {str(e)}")
            # Fallback to simple conclusion
            return "Based on our comprehensive analysis under ASC 340-40, the proposed accounting treatment is appropriate and complies with the authoritative guidance."

    
    def _load_step_prompts(self) -> Dict[str, str]:
        """Load step-specific prompts if available."""
        # For now, return empty dict - prompts are built dynamically
        # In the future, could load from templates/step_prompts.txt
        return {}