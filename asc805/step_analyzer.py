"""
ASC 805 Step Analyzer

This module handles the 5-step ASC 805 business combinations analysis.
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

class ASC805StepAnalyzer:
    """
    Simplified ASC 805 step-by-step analyzer using natural language output.
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
        self.use_premium_models = True
        
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
        
        # Load step prompts (currently unused - prompts are generated dynamically in _get_step_prompt)
        self.step_prompts = self._load_step_prompts()
    
    def extract_entity_name_llm(self, contract_text: str) -> str:
        """Extract the target company/acquiree entity name using LLM analysis."""
        try:
            logger.info("🏢 Extracting target company name from transaction documents...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying target company names in business combination transactions. Your task is to identify the name of the target company being acquired from the transaction documents."
                },
                {
                    "role": "user",
                    "content": f"""Based on this business combination transaction, what is the name of the target company being acquired?

Please identify:
- The company that is being acquired/purchased (the target, not the acquirer)
- The name including suffixes like Inc., LLC, Corp., etc.
- Ignore addresses, reference numbers, or other non-company identifiers

Transaction Documents:
{contract_text[:4000]}

Respond with ONLY the target company name, nothing else."""
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
                logger.warning("LLM returned None for customer name")
                return "Customer"
                
            # Clean the response (remove quotes, extra whitespace)
            entity_name = entity_name.strip().strip('"').strip("'").strip()
            
            # Validate the result
            if len(entity_name) < 2 or len(entity_name) > 120:
                logger.warning(f"LLM returned suspicious target company name: {entity_name}")
                return "Target Company"
            
            logger.info(f"✓ Target company identified: {entity_name}")
            return entity_name
            
        except Exception as e:
            logger.error(f"Error extracting target company name with LLM: {str(e)}")
            return "Target Company"
    
    def extract_party_names_llm(self, contract_text: str) -> Dict[str, Optional[str]]:
        """
        Extract BOTH party names from business combination agreement for de-identification.
        
        Returns:
            dict: {
                'acquirer': str,    # The company acquiring/purchasing (buyer)
                'target': str       # The company being acquired (seller/target)
            }
        """
        try:
            logger.info("🔒 Extracting both party names for de-identification...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying the two main parties in business combination transactions, including merger agreements, acquisition agreements, stock purchase agreements, and asset purchase agreements."
                },
                {
                    "role": "user",
                    "content": f"""Analyze this business combination transaction and identify the TWO main contracting parties:

1. ACQUIRER: The company acquiring/purchasing the business (may be called acquirer, buyer, purchaser, or just "Party A")
2. TARGET: The company being acquired/sold (may be called target, seller, acquired company, or just "Party B")

INSTRUCTIONS:
- Look for language like "by and between [Company X] and [Company Y]", "Party A/Party B", or companies mentioned in signature blocks
- Extract full legal names with suffixes (Inc., LLC, Corp., Ltd., etc.)
- Ignore addresses, reference numbers, contact names, or other non-company identifiers
- If the agreement uses neutral terminology (Party A/B), identify which one is acquiring vs being acquired based on the transaction structure

Transaction Documents:
{contract_text[:4000]}

Respond with ONLY a JSON object in this exact format:
{{"acquirer": "Acquiring Company Name Inc.", "target": "Target Company Name LLC"}}"""
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
                return {"acquirer": None, "target": None}
            
            # Log raw response for debugging
            logger.info(f"Raw LLM response for party extraction: {response_content[:200]}")
            
            # Parse JSON response
            response_content = response_content.strip()
            
            # Handle code block formatting if present
            if response_content.startswith("```"):
                response_content = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_content, flags=re.MULTILINE)
            
            party_data = json.loads(response_content)
            
            # Validate and clean
            acquirer = party_data.get("acquirer", "").strip().strip('"').strip("'").strip()
            target = party_data.get("target", "").strip().strip('"').strip("'").strip()
            
            # Validation checks
            acquirer_valid = acquirer and 2 <= len(acquirer) <= 120
            target_valid = target and 2 <= len(target) <= 120
            
            if not acquirer_valid:
                logger.warning(f"Invalid acquirer name extracted: {acquirer}")
                acquirer = None
            
            if not target_valid:
                logger.warning(f"Invalid target name extracted: {target}")
                target = None
            
            logger.info(f"✓ Parties extracted - Acquirer: {acquirer}, Target: {target}")
            
            return {"acquirer": acquirer, "target": target}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in party extraction: {str(e)}")
            return {"acquirer": None, "target": None}
        except Exception as e:
            logger.error(f"Error extracting party names: {str(e)}")
            return {"acquirer": None, "target": None}
    
    def deidentify_contract_text(self, contract_text: str, acquirer_name: Optional[str], target_name: Optional[str]) -> dict:
        """
        Replace both party names with generic terms for privacy.
        Handles whitespace variations, line breaks, hyphenated line wraps, and punctuation differences.
        
        Strategy: Normalize both text and party names consistently, then do pattern matching.
        
        Args:
            contract_text: Original contract text
            acquirer_name: Acquirer/buyer company name to replace
            target_name: Target/seller company name to replace
            
        Returns:
            Dict with keys:
                - success (bool): Whether de-identification succeeded
                - text (str): De-identified text (or original if failed)
                - acquirer_name (str): Original acquirer name
                - target_name (str): Original target name
                - replacements (list): List of replacement descriptions
                - error (str): Error message if failed, None otherwise
        """
        if not acquirer_name and not target_name:
            logger.warning("⚠️ No party names to de-identify, returning original text")
            return {
                "success": False,
                "text": contract_text,
                "acquirer_name": acquirer_name,
                "target_name": target_name,
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
        normalized_acquirer = normalize_text(acquirer_name) if acquirer_name else None
        normalized_target = normalize_text(target_name) if target_name else None
        
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
        
        # Replace acquirer with "the Company"
        if normalized_acquirer:
            # First replace the full name
            pattern = create_flexible_pattern(normalized_acquirer)
            matches = list(re.finditer(pattern, deidentified_text, flags=re.IGNORECASE))
            match_count = len(matches)
            
            if match_count > 0:
                deidentified_text = re.sub(pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                replacements_made.append(f"acquirer '{acquirer_name}' → 'the Company' ({match_count} occurrences)")
                replacement_count['acquirer'] = match_count
            else:
                logger.warning(f"⚠️ Acquirer name '{acquirer_name}' (normalized: '{normalized_acquirer}') not found in contract text")
                replacement_count['acquirer'] = 0
            
            # Also replace base company name (e.g., "Netflix" from "Netflix, Inc.")
            base_acquirer_name = extract_base_company_name(normalized_acquirer)
            if base_acquirer_name:
                base_pattern = create_flexible_pattern(base_acquirer_name)
                base_matches = list(re.finditer(base_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(base_matches) > 0:
                    deidentified_text = re.sub(base_pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced acquirer base name '{base_acquirer_name}' ({len(base_matches)} occurrences)")
            
            # Also replace aliases found in the text (e.g., "InnovateTech" from "InnovateTech Solutions Inc. ('InnovateTech')")
            aliases = extract_aliases_from_text(normalized_acquirer, normalized_text)
            for alias in aliases:
                alias_pattern = create_flexible_pattern(alias)
                alias_matches = list(re.finditer(alias_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(alias_matches) > 0:
                    deidentified_text = re.sub(alias_pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced acquirer alias '{alias}' ({len(alias_matches)} occurrences)")
        
        # Replace target with "the Target"
        if normalized_target:
            # First replace the full name
            pattern = create_flexible_pattern(normalized_target)
            matches = list(re.finditer(pattern, deidentified_text, flags=re.IGNORECASE))
            match_count = len(matches)
            
            if match_count > 0:
                deidentified_text = re.sub(pattern, "the Target", deidentified_text, flags=re.IGNORECASE)
                replacements_made.append(f"target '{target_name}' → 'the Target' ({match_count} occurrences)")
                replacement_count['target'] = match_count
            else:
                logger.warning(f"⚠️ Target name '{target_name}' (normalized: '{normalized_target}') not found in contract text")
                replacement_count['target'] = 0
            
            # Also replace base company name (e.g., "Martin" from "Martin, LLC")
            base_target_name = extract_base_company_name(normalized_target)
            if base_target_name:
                base_pattern = create_flexible_pattern(base_target_name)
                base_matches = list(re.finditer(base_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(base_matches) > 0:
                    deidentified_text = re.sub(base_pattern, "the Target", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced target base name '{base_target_name}' ({len(base_matches)} occurrences)")
            
            # Also replace aliases found in the text
            aliases = extract_aliases_from_text(normalized_target, normalized_text)
            for alias in aliases:
                alias_pattern = create_flexible_pattern(alias)
                alias_matches = list(re.finditer(alias_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(alias_matches) > 0:
                    deidentified_text = re.sub(alias_pattern, "the Target", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced target alias '{alias}' ({len(alias_matches)} occurrences)")
        
        # Check if de-identification succeeded
        if not replacements_made:
            error_msg = (
                f"Privacy extraction did not detect party names in the transaction document text. "
                f"Extracted names (acquirer: '{acquirer_name}', target: '{target_name}') "
                f"were not found in the contract."
            )
            logger.warning(f"⚠️ {error_msg}")
            return {
                "success": False,
                "text": contract_text,  # Return original text
                "acquirer_name": acquirer_name,
                "target_name": target_name,
                "replacements": [],
                "error": error_msg
            }
        
        # Log success
        logger.info(f"✓ De-identification complete: {', '.join(replacements_made)}")
        
        return {
            "success": True,
            "text": deidentified_text,
            "acquirer_name": acquirer_name,
            "target_name": target_name,
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
        Perform complete 5-step ASC 805 analysis.
        
        Args:
            contract_text: The transaction document text
            authoritative_context: Retrieved ASC 805 guidance
            customer_name: Target company name
            analysis_title: Analysis title
            additional_context: Optional user-provided context
            
        Returns:
            Dictionary containing analysis results for each step
        """
        analysis_start_time = time.time()
        logger.info(f"Starting ASC 805 analysis for {customer_name}")
        
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
                for step_num in range(1, 6)
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
        logger.info("DEBUG: Starting additional section generation...")
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
        logger.info(f"✓ ASC 805 analysis completed successfully in {total_time:.1f}s")
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
        """Analyze a single ASC 606 step - returns clean markdown."""
        
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
    
    def _get_markdown_system_prompt(self) -> str:
        """Get the system prompt for markdown generation."""
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 805 business combinations. 

Generate professional accounting analysis in clean markdown format. Your output will be displayed directly using markdown rendering.

Your analysis must be:
- Audit-ready and professional
- Clear and understandable
- Based on the evidence provided in the transaction documents
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
- Support your analysis with specific transaction evidence and authoritative citations
- Use direct quotes from the transaction documents only when the exact wording is outcome-determinative
- Paraphrase ASC 805 with pinpoint citations; brief decisive phrases may be quoted when directly supportive
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
                'title': 'Step 1: Scope, "business" assessment, acquirer, and acquisition date',
                'focus': 'Confirm ASC 805 acquisition method applies, determine if the acquired set is a business, identify the acquirer, and establish the acquisition date',
                'key_points': [
                    'Confirm scope: ASC 805 acquisition method vs asset acquisition (ASC 805-50), joint venture (ASC 805-60), or NFP combination (ASC 958-805).',
                    'Assess if acquired set is a business: Apply optional screen test or substantive processes framework. Document judgment with reference to implementation examples. [ASC 805-10-55]',
                    'Identify acquirer (consider VIE primary beneficiary) and assess reverse acquisition possibility. [ASC 805-10; ASC 810]',
                    'Determine acquisition date (control transfer) and document specific control-transfer events. [ASC 805-10]',
                    'For step acquisitions: Note requirement to remeasure previously held interest at FV on acquisition date. [ASC 805-10]',
                    'For acquiree standalone statements (if applicable): Evaluate pushdown accounting election. [ASC 805-50]'
                ]
            },
            2: {
                'title': 'Step 2: Consideration and items not part of the exchange',
                'focus': 'Measure consideration at fair value, classify contingent consideration, and separate transactions that are not part of the business combination exchange',
                'key_points': [
                    'Identify consideration transferred components: cash, liabilities incurred, assets transferred, equity issued, contingent consideration. Flag fair value measurements as [Management Input Required: FV of consideration per ASC 805-30]. [ASC 805-30]',
                    'Note NCI measurement: Acquisition-date FV (full goodwill method). Flag as management input. [ASC 805-30]',
                    'For step acquisitions: Note requirement to remeasure previously held interest to FV → recognize gain/loss + recycle AOCI. Flag FV measurement as management input. [ASC 805-10; ASC 220/815/320]',
                ]
            },
            3: {
                'title': 'Step 3: Recognize and measure identifiable assets and liabilities; compute goodwill or bargain purchase',
                'focus': 'Identify assets acquired and liabilities assumed, document measurement requirements and exceptions, and establish goodwill calculation framework',
                'key_points': [
                    'Identify 100% of assets acquired and liabilities assumed at acquisition date (list from transaction documents). [ASC 805-20]',
                    'Note measurement requirement: Acquisition-date FV per ASC 820. Flag as [Management Input Required: Fair value measurements and valuation approaches for identified items per ASC 805-20/820]. [ASC 805-20; ASC 820]',
                    'Apply measurement exceptions: Revenue contracts → measure per ASC 606 as if acquirer originated (ASU 2021-08). Leases → apply ASC 842 (no separate favorable/unfavorable intangibles). Financial assets with credit deterioration → CECL (ASC 326). [ASC 805-20]',
                    'Identify intangible assets meeting separability or contractual-legal criteria → recognize separately from goodwill. Exclude assembled workforce. [ASC 805-20-25/-55]',
                    'For special intangibles: Reacquired rights → amortize over remaining contractual term (ignore renewals). IPR&D → capitalize as indefinite-lived, subject to impairment. [ASC 805-20; ASC 350]',
                    'Recognize contingencies at acquisition-date FV when meeting asset/liability definition. [ASC 805-20; ASC 450/460]',
                    'Record tax effects: DTAs/DTLs for basis differences, UTPs, valuation allowances. [ASC 740]',
                    'Describe the goodwill calculation framework. Note where management judgment or input is required. [ASC 805-30]'
                ]
            },
            4: {
                'title': 'Step 4: Record the acquisition, apply the measurement period, and handle subsequent measurement',
                'focus': 'Post acquisition-date entries, manage provisional amounts within the measurement period, and perform required remeasurements',
                'key_points': [
                    'Record acquisition-date journal entries for all recognized items (including goodwill or bargain purchase gain). [ASC 805-30]',
                    'Use provisional amounts if initial accounting incomplete. Within measurement period (≤1 year): Record retrospective adjustments for acquisition-date facts → adjust goodwill + revise comparatives. Disclose. [ASC 805-10]',
                    'Distinguish measurement period adjustments from subsequent estimate changes or events. Retain acquisition-date assumption evidence. [ASC 805-10]',
                    'Remeasure contingent consideration: Liability/derivative-classified → through earnings each period. Equity-classified → no remeasurement. [ASC 805-30-35; ASC 480/815]',
                    'Apply postcombination accounting: Amortize finite-lived intangibles, test goodwill/indefinite-lived for impairment (ASC 350), CECL (ASC 326), lease accounting (ASC 842), hedge relationships (ASC 815). [Multiple Topics]',
                    'For acquiree standalone reporting (if applicable): Assess and elect pushdown accounting with required disclosures. [ASC 805-50]'
                ]
            },
            5: {
                'title': 'Step 5: Prepare required disclosures and the technical memo',
                'focus': 'Provide complete ASC 805 disclosures and document judgments, measurements, and conclusions supporting the acquisition method',
                'key_points': [
                    'Describe the ASC 805 disclosures requirements specific to this business combination as applicable: Acquisition date + reasons; goodwill qualitative factors; consideration by major class; assets/liabilities by major class; contingent consideration + indemnification details; acquiree revenue/earnings since acquisition; pro forma information as if acquired at period start. [ASC 805-10-50; ASC 805-30-50]',
                    'For immaterial combinations material in aggregate: Disclose combined amounts. [ASC 805-10-50]',
                    'For step acquisitions: Disclose FV of previously held interest, gain/loss recognized, AOCI reclassifications. [ASC 805-10; ASC 220]',
                    'For bargain purchases: Disclose gain amount and reasons. [ASC 805-30-50]',
                    'Disclose measurement period adjustments or note if initial accounting incomplete. [ASC 805-10-50]',
                    'For SEC registrants: Consider Article 11 pro forma and Rule 3-05 significance testing (outside ASC 805).',
                    'Technical memo structure: Scope/"business" assessment, acquirer/acquisition date, consideration breakdown, asset/liability measurements (including exceptions), intangibles, goodwill/bargain purchase, measurement period plan, disclosure checklist. [ASC 805-10-50]'
                ]
            }
        }
        
        step = step_info[step_num]
        
        prompt = f"""
STEP {step_num}: {step['title'].upper()}

OBJECTIVE: {step['focus']}

TRANSACTION INFORMATION:
Business Combination Analysis: Analyze the transaction involving {customer_name} to determine the appropriate business combination accounting treatment under ASC 805 for the acquirer.

Instructions: Analyze this transaction from the acquirer's perspective. {customer_name} is the target company being acquired.

TRANSACTION DOCUMENTS:
{contract_text}"""

        if additional_context.strip():
            prompt += f"""

ADDITIONAL CONTEXT:
{additional_context}"""

        prompt += f"""

AUTHORITATIVE GUIDANCE:
{authoritative_context}

ANALYSIS REQUIRED:
Analyze the transaction for Step {step_num} focusing on:
{chr(10).join([f"• {point}" for point in step['key_points']])}

REQUIRED OUTPUT FORMAT (Clean Markdown):

### {step['title']}

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific transaction evidence and ASC 805 citations. Quote transaction language only when the exact wording is outcome‑determinative; paraphrase ASC 805 with pinpoint citations and use only brief decisive phrases when directly supportive.]

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion]
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed citations)
- Contract citations must reference actual text from the document:
    Good: [Purchase Agreement, Assets Acquired], [Purchase Agreement, 'purchase price of']
    Bad: [Purchase Agreement, §4.2], [Purchase Agreement, p. 15] (unless these exact references appear in the contract text)
- Only cite section numbers/page numbers if they are explicitly visible in the contract text
- ASC 805 guidance paraphrased with citations; include only brief decisive phrases when directly supportive.

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 805 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

CRITICAL ANALYSIS REQUIREMENTS - CONTRACT VS EXTERNAL DATA:

1. CONTRACT FACTS (dates, terms, amounts explicitly in the document):
   - If present: Quote or paraphrase with citation
   - If missing: State "Not specified in contract"
   - NEVER invent or guess these

2. EXTERNAL INPUTS (accounting policies, valuations, judgments NOT in contract):
   - Always state the ASC 805 requirement
   - Create management placeholder: "[Management Input Required: Provide fair value measurement for X per ASC 805-30]"
   - Examples: fair value measurements, NCI measurement election, acquisition-date assessments

3. CITATION RULES:
   - Contract: Only cite what's visible - [Purchase Agreement, Assets Acquired] ✓  |  [Agreement §3.1] ✗ (unless §3.1 appears)
   - ASC 805: Paraphrase + pinpoint cite - [ASC 805-30-25-2]

Use assertive language ("We conclude...") when evidence supports it; flag gaps explicitly.

FORMATTING:
- Format currency as: $240,000 (with comma, no spaces)
- Use proper spacing after periods and commas
- Use professional accounting language
- Double-check all currency amounts for correct formatting"""

        return prompt
    
    def validate_step_output(self, markdown_content: str, step_num: int) -> Dict[str, Any]:
        """Validate step output for required structural sections only."""
        import re
        issues = []
        
        # Check for required sections - accept both bold and non-bold formats at line start
        # Pattern matches: **Analysis:** or Analysis: at the start of a line  
        if not re.search(r'^(\*\*)?Analysis:\s*(\*\*)?', markdown_content, re.MULTILINE):
            issues.append(f"Missing Analysis section in Step {step_num}")
        
        if not re.search(r'^(\*\*)?Conclusion:\s*(\*\*)?', markdown_content, re.MULTILINE):
            issues.append(f"Missing Conclusion section in Step {step_num}")
        
        return {"valid": len(issues) == 0, "issues": issues}
    
    def _get_step_title(self, step_num: int) -> str:
        """Get the title for a specific step."""
        titles = {
            1: "Step 1: Scope, Business Assessment, Acquirer, and Acquisition Date",
            2: "Step 2: Consideration and Items Not Part of the Exchange", 
            3: "Step 3: Recognize and Measure Assets and Liabilities; Compute Goodwill",
            4: "Step 4: Record Acquisition, Measurement Period, and Subsequent Measurement",
            5: "Step 5: Prepare Required Disclosures and Technical Memo"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    def _load_step_prompts(self) -> Dict[int, str]:
        """Load step-specific prompts (placeholder for future use)."""
        return {}
    
    def generate_executive_summary(self, conclusions_text: str, customer_name: str) -> str:
        """Generate executive summary from step conclusions."""
        logger.info("→ Generating executive summary...")
        
        try:
            prompt = f"""Generate an executive summary for an ASC 606 revenue recognition memorandum for {customer_name}.

Based on these step conclusions:

{conclusions_text}

Requirements:
- Start with the overall revenue recognition conclusion (how and when revenue should be recognized)
- Summarize the key findings from each step in 2-3 bullet points
- Keep professional but concise (3-4 paragraphs maximum)
- Focus on business impact and implementation guidance
- Use the exact customer name: {customer_name}

Format as clean markdown - no headers, just paragraphs and bullet points."""

            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert technical accountant generating executive summaries for ASC 606 memos. Write clearly and professionally."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **self._get_max_tokens_param("executive_summary", self.light_model),
                "temperature": self._get_temperature(self.light_model)
            }
            
            if self.light_model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            # Track API cost for executive summary
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=request_params["messages"],
                response_text=response.choices[0].message.content or "",
                model=self.light_model,
                request_type="executive_summary"
            )
            
            summary = response.choices[0].message.content
            
            if summary is None:
                logger.warning("LLM returned None for executive summary")
                return f"Executive summary for {customer_name} revenue recognition analysis could not be generated."
            
            summary = summary.strip()
            logger.info(f"✓ Executive summary generated ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return f"Executive summary for {customer_name} revenue recognition analysis could not be generated due to an error."
    
    def generate_background_section(self, conclusions_text: str, customer_name: str) -> str:
        """Generate background section from step conclusions."""
        logger.info("→ Generating background section...")
        
        try:
            prompt = f"""Generate a background section for an ASC 606 revenue recognition memorandum for {customer_name}.

Based on these step conclusions:

{conclusions_text}

Requirements:
- Explain what contract documents were reviewed
- Briefly describe the nature of the arrangement (goods/services being provided)
- State the purpose of this memo (ASC 606 revenue recognition analysis)
- Keep it factual and professional (2-3 paragraphs)
- Use the exact customer name: {customer_name}

Format as clean markdown - no headers, just paragraphs."""

            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert technical accountant generating background sections for ASC 606 memos. Write clearly and professionally."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **self._get_max_tokens_param("background", self.light_model),
                "temperature": self._get_temperature(self.light_model)
            }
            
            if self.light_model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            # Track API cost for background section
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=request_params["messages"],
                response_text=response.choices[0].message.content or "",
                model=self.light_model,
                request_type="background_generation"
            )
            
            background = response.choices[0].message.content
            
            if background is None:
                logger.warning("LLM returned None for background section")
                return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology."
            
            background = background.strip()
            logger.info(f"✓ Background section generated ({len(background)} chars)")
            return background
            
        except Exception as e:
            logger.error(f"Error generating background section: {str(e)}")
            return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology."
    
    def generate_final_conclusion(self, conclusions_text: str) -> str:
        """Generate LLM-powered final conclusion from step conclusions.
        
        Args:
            conclusions_text: Pre-extracted conclusions from all steps
        """
        logger.info("→ Generating final conclusion...")
        prompt = f"""Generate a professional final conclusion for an ASC 805 analysis.

    Step Conclusions:
    {conclusions_text}

    Instructions:
    1. Write 2-3 sentences in narrative paragraph format assessing ASC 805 compliance
    2. Format all currency as $XXX,XXX (no spaces in numbers)
    3. Base your conclusion ONLY on the actual findings from the step conclusions provided above
    4. Only mention concerns if they are explicitly identified in the step analysis - do not invent or infer new issues
    5. If no significant issues are found in the steps, state compliance with ASC 805
    6. Focus on compliance assessment
    7. Use professional accounting language without bullet points
    8. Use proper paragraph spacing
    9. ALWAYS format currency with single $ symbol (never $$)
    10. Include proper spacing after commas and periods"""

        # Call LLM API
        try:
            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert technical accountant specializing in ASC 805 business combinations."
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
            conclusion = response.choices[0].message.content.strip()
            logger.info(f"✓ Final conclusion generated ({len(conclusion)} chars)")
            return conclusion

        except Exception as e:
            logger.error(f"Final conclusion generation failed: {str(e)}")
            # Fallback to simple conclusion
            return "Based on our comprehensive analysis under ASC 805, the proposed business combination accounting treatment is appropriate and complies with the authoritative guidance."
    
    def _extract_conclusions_from_steps(self, steps_data: Dict[str, Any]) -> str:
        """Extract conclusion text from all step analyses for summary generation."""
        conclusions = []
        
        logger.info(f"DEBUG: Extracting conclusions from {len(steps_data)} steps")
        
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            if step_key in steps_data:
                step_data = steps_data[step_key]
                logger.info(f"DEBUG: Processing {step_key}, type: {type(step_data)}")
                
                if isinstance(step_data, dict) and 'markdown_content' in step_data:
                    content = step_data['markdown_content']
                    logger.info(f"DEBUG: {step_key} has markdown content of length {len(content)}")
                    
                    # Extract conclusion from markdown content - try markers first, then improved regex
                    import re
                    
                    # Try markers first ([BEGIN_CONCLUSION]...[END_CONCLUSION])
                    marker_match = re.search(r'\[BEGIN_CONCLUSION\](.*?)\[END_CONCLUSION\]', content, re.DOTALL)
                    if marker_match:
                        conclusion_text = marker_match.group(1).strip()
                        conclusions.append(f"Step {step_num}: {conclusion_text}")
                        logger.info(f"DEBUG: Extracted conclusion for {step_key} (length: {len(conclusion_text)} chars)")
                    else:
                        # Try all four conclusion patterns for maximum robustness
                        # Pattern 1: **Conclusion:** (bold with colon)
                        conclusion_match = re.search(r'\*\*Conclusion:\*\*\s*(.+?)(?:\n\s*\*\*|$)', content, re.IGNORECASE | re.DOTALL)
                        if not conclusion_match:
                            # Pattern 2: Conclusion: (plain text with colon)
                            conclusion_match = re.search(r'^Conclusion:\s*(.+?)(?:\n\s*(?:\*\*|[A-Z][a-z]+:)|$)', content, re.IGNORECASE | re.DOTALL | re.MULTILINE)
                        if not conclusion_match:
                            # Pattern 3: **Conclusion** (bold without colon)
                            conclusion_match = re.search(r'\*\*Conclusion\*\*\s+(.+?)(?:\n\s*\*\*|$)', content, re.IGNORECASE | re.DOTALL)
                        if not conclusion_match:
                            # Pattern 4: Conclusion (plain text without colon)
                            conclusion_match = re.search(r'^Conclusion\s+(.+?)(?:\n\s*(?:\*\*|[A-Z][a-z]+:)|$)', content, re.IGNORECASE | re.DOTALL | re.MULTILINE)
                        
                        if conclusion_match:
                            conclusion_text = conclusion_match.group(1).strip()
                            conclusions.append(f"Step {step_num}: {conclusion_text}")
                            logger.info(f"DEBUG: Extracted conclusion for {step_key} (length: {len(conclusion_text)} chars)")
                        else:
                            # Final fallback: use last paragraph as conclusion
                            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                            if paragraphs:
                                last_paragraph = paragraphs[-1]
                                conclusions.append(f"Step {step_num}: {last_paragraph}")
                                logger.info(f"DEBUG: Used last paragraph as conclusion for {step_key} (length: {len(last_paragraph)} chars)")
                            else:
                                logger.warning(f"DEBUG: No content found for {step_key}")
                else:
                    logger.warning(f"DEBUG: {step_key} missing markdown_content. Available keys: {list(step_data.keys()) if isinstance(step_data, dict) else 'Not a dict'}")
            else:
                logger.warning(f"DEBUG: {step_key} not found in steps_data. Available keys: {list(steps_data.keys())}")
        
        combined_conclusions = '\n\n'.join(conclusions)
        logger.info(f"DEBUG: Combined conclusions length: {len(combined_conclusions)} chars")
        return combined_conclusions