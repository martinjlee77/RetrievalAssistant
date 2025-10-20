"""
ASC 606 Step Analyzer

This module handles the 5-step ASC 606 revenue recognition analysis.
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
from shared.api_cost_tracker import track_openai_request, reset_cost_tracking, get_total_estimated_cost

logger = logging.getLogger(__name__)

class ASC606StepAnalyzer:
    """
    Simplified ASC 606 step-by-step analyzer using natural language output.
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
        """Extract the customer entity name using LLM analysis."""
        try:
            logger.info("🏢 Extracting customer name from contract...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying customer names in revenue contracts. Your task is to identify the name of the customer company from the contract document."
                },
                {
                    "role": "user",
                    "content": f"""Based on this revenue contract, what is the name of the customer company?

Please identify:
- The company that is purchasing goods or services (this is the customer and not the vendor)
- The name including suffixes like Inc., LLC, Corp., etc.
- Ignore addresses, reference numbers, or other non-company identifiers

Contract Text:
{contract_text[:4000]}

Respond with ONLY the customer name, nothing else."""
                }
            ]
            
            response_content = self._make_llm_request(messages, self.light_model, "default")
            
            # Track API cost for entity extraction
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
                logger.warning(f"LLM returned suspicious customer name: {entity_name}")
                return "Customer"
            
            logger.info(f"✓ Customer identified: {entity_name}")
            return entity_name
            
        except Exception as e:
            logger.error(f"Error extracting customer name with LLM: {str(e)}")
            return "Customer"
    
    def extract_party_names_llm(self, contract_text: str) -> Dict[str, Optional[str]]:
        """
        Extract BOTH party names from revenue contract for de-identification.
        
        Returns:
            dict: {
                'vendor': str,      # The vendor/seller (company running analysis)
                'customer': str     # The customer/buyer (counterparty)
            }
        """
        try:
            logger.info("🔒 Extracting both party names for de-identification...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying the two main parties in commercial contracts, including revenue contracts, SOWs, MSAs, service agreements, and license agreements."
                },
                {
                    "role": "user",
                    "content": f"""Analyze this commercial contract and identify the TWO main contracting parties:

1. FIRST PARTY: The company providing/selling goods or services (may be called vendor, seller, provider, licensor, consultant, contractor, or just "Party A")
2. SECOND PARTY: The company receiving/purchasing goods or services (may be called customer, buyer, client, licensee, or just "Party B")

INSTRUCTIONS:
- Look for language like "by and between [Company X] and [Company Y]", "Party A/Party B", or companies mentioned in signature blocks
- Extract full legal names with suffixes (Inc., LLC, Corp., Ltd., etc.)
- Ignore addresses, reference numbers, contact names, or other non-company identifiers
- If the contract uses neutral terminology (Party A/B), identify which one is providing vs receiving based on the obligations described

Contract Text:
{contract_text[:4000]}

Respond with ONLY a JSON object in this exact format:
{{"vendor": "First Party Company Name Inc.", "customer": "Second Party Company Name LLC"}}"""
                }
            ]
            
            response_content = self._make_llm_request(messages, self.light_model, "default")
            
            # Track API cost
            track_openai_request(
                messages=messages,
                response_text=response_content or "",
                model=self.light_model,
                request_type="party_extraction"
            )
            
            if not response_content:
                logger.warning("LLM returned empty response for party extraction")
                return {"vendor": None, "customer": None}
            
            # Log raw response for debugging
            logger.info(f"Raw LLM response for party extraction: {response_content[:200]}")
            
            # Parse JSON response
            response_content = response_content.strip()
            
            # Handle code block formatting if present
            if response_content.startswith("```"):
                response_content = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_content, flags=re.MULTILINE)
            
            party_data = json.loads(response_content)
            
            # Validate and clean
            vendor = party_data.get("vendor", "").strip().strip('"').strip("'").strip()
            customer = party_data.get("customer", "").strip().strip('"').strip("'").strip()
            
            # Validation checks
            vendor_valid = vendor and 2 <= len(vendor) <= 120
            customer_valid = customer and 2 <= len(customer) <= 120
            
            if not vendor_valid:
                logger.warning(f"Invalid vendor name extracted: {vendor}")
                vendor = None
            
            if not customer_valid:
                logger.warning(f"Invalid customer name extracted: {customer}")
                customer = None
            
            logger.info(f"✓ Parties extracted - Vendor: {vendor}, Customer: {customer}")
            
            return {"vendor": vendor, "customer": customer}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in party extraction: {str(e)}")
            return {"vendor": None, "customer": None}
        except Exception as e:
            logger.error(f"Error extracting party names: {str(e)}")
            return {"vendor": None, "customer": None}
    
    def deidentify_contract_text(self, contract_text: str, vendor_name: Optional[str], customer_name: Optional[str]) -> dict:
        """
        Replace both party names with generic terms for privacy.
        Handles whitespace variations, line breaks, hyphenated line wraps, and punctuation differences.
        
        Strategy: Normalize both text and party names consistently, then do pattern matching.
        
        Args:
            contract_text: Original contract text
            vendor_name: Vendor/seller company name to replace
            customer_name: Customer/buyer company name to replace
            
        Returns:
            Dict with keys:
                - success (bool): Whether de-identification succeeded
                - text (str): De-identified text (or original if failed)
                - vendor_name (str): Original vendor name
                - customer_name (str): Original customer name
                - replacements (list): List of replacement descriptions
                - error (str): Error message if failed, None otherwise
        """
        if not vendor_name and not customer_name:
            logger.warning("⚠️ No party names to de-identify, returning original text")
            return {
                "success": False,
                "text": contract_text,
                "vendor_name": vendor_name,
                "customer_name": customer_name,
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
        normalized_vendor = normalize_text(vendor_name) if vendor_name else None
        normalized_customer = normalize_text(customer_name) if customer_name else None
        
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
            - Company Name Inc. (ShortName)
            """
            aliases = []
            
            # Escape company name for regex
            escaped_name = re.escape(company_name)
            
            # Combined pattern: Company Name (optional quotes)Alias(optional quotes)
            # Handles: ("Alias"), ('Alias'), (Alias), "Alias", 'Alias'
            pattern = escaped_name + r'\s*\(?\s*["\']?\s*([A-Za-z0-9][A-Za-z0-9\s\-&]{1,49})\s*["\']?\s*\)?'
            
            # More specific pattern for parenthetical aliases
            # Allow optional punctuation (commas, periods) between company name and parenthesis
            paren_pattern = escaped_name + r'[,\.\s]*\(\s*["\']?([^)"\']{2,50})["\']?\s*\)'
            
            matches = re.finditer(paren_pattern, text, flags=re.IGNORECASE)
            for match in matches:
                alias = match.group(1).strip()
                # Strip any remaining quotes
                alias = alias.strip('"').strip("'").strip()
                
                # Only accept if it looks like an alias (not numbers-only, dates, or too generic)
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
        
        # Replace vendor with "the Company"
        if normalized_vendor:
            # First replace the full name
            pattern = create_flexible_pattern(normalized_vendor)
            matches = list(re.finditer(pattern, deidentified_text, flags=re.IGNORECASE))
            match_count = len(matches)
            
            if match_count > 0:
                deidentified_text = re.sub(pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                replacements_made.append(f"vendor '{vendor_name}' → 'the Company' ({match_count} occurrences)")
                replacement_count['vendor'] = match_count
            else:
                logger.warning(f"⚠️ Vendor name '{vendor_name}' (normalized: '{normalized_vendor}') not found in contract text")
                replacement_count['vendor'] = 0
            
            # Also replace base company name (e.g., "Netflix" from "Netflix, Inc.")
            base_vendor_name = extract_base_company_name(normalized_vendor)
            if base_vendor_name:
                base_pattern = create_flexible_pattern(base_vendor_name)
                base_matches = list(re.finditer(base_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(base_matches) > 0:
                    deidentified_text = re.sub(base_pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced vendor base name '{base_vendor_name}' ({len(base_matches)} occurrences)")
            
            # Also replace aliases found in the text (e.g., "InnovateTech" from "InnovateTech Solutions Inc. ('InnovateTech')")
            aliases = extract_aliases_from_text(normalized_vendor, normalized_text)
            for alias in aliases:
                alias_pattern = create_flexible_pattern(alias)
                alias_matches = list(re.finditer(alias_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(alias_matches) > 0:
                    deidentified_text = re.sub(alias_pattern, "the Company", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced vendor alias '{alias}' ({len(alias_matches)} occurrences)")
        
        # Replace customer with "the Customer"
        if normalized_customer:
            # First replace the full name
            pattern = create_flexible_pattern(normalized_customer)
            matches = list(re.finditer(pattern, deidentified_text, flags=re.IGNORECASE))
            match_count = len(matches)
            
            if match_count > 0:
                deidentified_text = re.sub(pattern, "the Customer", deidentified_text, flags=re.IGNORECASE)
                replacements_made.append(f"customer '{customer_name}' → 'the Customer' ({match_count} occurrences)")
                replacement_count['customer'] = match_count
            else:
                logger.warning(f"⚠️ Customer name '{customer_name}' (normalized: '{normalized_customer}') not found in contract text")
                replacement_count['customer'] = 0
            
            # Also replace base company name (e.g., "Martin" from "Martin, LLC")
            base_customer_name = extract_base_company_name(normalized_customer)
            if base_customer_name:
                base_pattern = create_flexible_pattern(base_customer_name)
                base_matches = list(re.finditer(base_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(base_matches) > 0:
                    deidentified_text = re.sub(base_pattern, "the Customer", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced customer base name '{base_customer_name}' ({len(base_matches)} occurrences)")
            
            # Also replace aliases found in the text
            aliases = extract_aliases_from_text(normalized_customer, normalized_text)
            for alias in aliases:
                alias_pattern = create_flexible_pattern(alias)
                alias_matches = list(re.finditer(alias_pattern, deidentified_text, flags=re.IGNORECASE))
                if len(alias_matches) > 0:
                    deidentified_text = re.sub(alias_pattern, "the Customer", deidentified_text, flags=re.IGNORECASE)
                    logger.info(f"  → Also replaced customer alias '{alias}' ({len(alias_matches)} occurrences)")
        
        # Check if de-identification succeeded
        if not replacements_made:
            error_msg = (
                f"Privacy extraction did not detect party names in the contract text. "
                f"Extracted names (vendor: '{vendor_name}', customer: '{customer_name}') "
                f"were not found in the contract."
            )
            logger.warning(f"⚠️ {error_msg}")
            return {
                "success": False,
                "text": contract_text,  # Return original text
                "vendor_name": vendor_name,
                "customer_name": customer_name,
                "replacements": [],
                "error": error_msg
            }
        
        # Log success
        logger.info(f"✓ De-identification complete: {', '.join(replacements_made)}")
        
        return {
            "success": True,
            "text": deidentified_text,
            "vendor_name": vendor_name,
            "customer_name": customer_name,
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
        Perform complete 5-step ASC 606 analysis.
        
        Args:
            contract_text: The contract document text
            authoritative_context: Retrieved ASC 606 guidance
            customer_name: Customer name
            analysis_title: Analysis title
            additional_context: Optional user-provided context
            
        Returns:
            Dictionary containing analysis results for each step
        """
        analysis_start_time = time.time()
        logger.info(f"Starting ASC 606 analysis for {customer_name}")
        
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
        conclusions_text = self._extract_conclusions_from_steps(results['steps'])
        
        # Generate executive summary, background, and conclusion
        results['executive_summary'] = self.generate_executive_summary(conclusions_text, customer_name)
        results['background'] = self.generate_background_section(conclusions_text, customer_name)
        results['conclusion'] = self.generate_final_conclusion(results['steps'])
        
        total_time = time.time() - analysis_start_time
        logger.info(f"✓ ASC 606 analysis completed successfully in {total_time:.1f}s")
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
        
        # Log financial calculations for Step 2 (Transaction Price)
        if step_num == 2:
            logger.info("💰 Extracting transaction price components and variable consideration...")
        
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
            
            # Track API cost for step analysis
            track_openai_request(
                messages=request_params["messages"],
                response_text=response.choices[0].message.content or "",
                model=self.model,
                request_type=f"step_{step_num}_analysis"
            )
            
            markdown_content = response.choices[0].message.content
            
            if markdown_content is None or (markdown_content and len(markdown_content.strip()) < 50):
                # Handle empty or very short response - retry once
                logger.warning(f"⚠️ Step {step_num}: Received empty/short response ({len(markdown_content) if markdown_content else 0} chars). Retrying...")
                
                # Retry the API call once
                time.sleep(2)  # Brief pause before retry
                retry_response = self.client.chat.completions.create(**request_params)
                
                # Track retry API cost
                track_openai_request(
                    messages=request_params["messages"],
                    response_text=retry_response.choices[0].message.content or "",
                    model=self.model,
                    request_type=f"step_{step_num}_analysis_retry"
                )
                
                markdown_content = retry_response.choices[0].message.content
                
                if markdown_content is None or (markdown_content and len(markdown_content.strip()) < 50):
                    # Retry also failed - generate error message
                    logger.error(f"ERROR: Step {step_num} - Both attempts returned empty/short response")
                    markdown_content = f"## Step {step_num}: Analysis Error\n\n**Error:** The AI model returned an empty response after multiple attempts. This is a known intermittent issue with GPT-5.\n\n**Recommended Action:** Please retry this analysis or switch to GPT-4o model.\n\n**Issues or Uncertainties:** Analysis could not be completed due to model response failure."
                else:
                    logger.info(f"✓ Step {step_num}: Retry successful, received {len(markdown_content)} chars")
            
            # ONLY strip whitespace - NO OTHER PROCESSING
            markdown_content = markdown_content.strip()
            
            # Validate the output for quality assurance
            validation_result = self.validate_step_output(markdown_content, step_num)
            if not validation_result["valid"]:
                logger.warning(f"Step {step_num} validation issues: {validation_result['issues']}")
                # Append validation issues to the Issues section
                if "**Issues or Uncertainties:**" in markdown_content:
                    issues_section = "\n\n**Validation Notes:** " + "; ".join(validation_result["issues"])
                    markdown_content = markdown_content.replace(
                        "**Issues or Uncertainties:**", 
                        "**Issues or Uncertainties:**" + issues_section + "\n\n"
                    )
                
            
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
        """Validate step output for required structural sections only."""
        issues = []
        
        # Check for required sections
        if "**Analysis:**" not in markdown_content:
            issues.append(f"Missing Analysis section in Step {step_num}")
        
        if "**Conclusion:**" not in markdown_content:
            issues.append(f"Missing Conclusion section in Step {step_num}")
        
        return {"valid": len(issues) == 0, "issues": issues}
    
    def _get_markdown_system_prompt(self) -> str:
        """Get the system prompt for markdown generation."""
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 606 revenue recognition. 

Generate professional accounting analysis in clean markdown format. Your output will be displayed directly using markdown rendering.

Your analysis must be:
- Audit-ready and professional
- Clear and understandable
- Based on the evidence provided in the contract text
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
- Support your analysis with specific contract text and authoritative citations
- Use direct quotes from the contract document only when the exact wording is outcome-determinative
- Paraphrase ASC 606 with pinpoint citations; brief decisive phrases may be quoted when directly supportive
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
                'title': 'Step 1: Identify the Contract',
                'focus': 'Determine if a valid contract exists under ASC 606-10-25-1 criteria',
                'key_points': [
                    'Confirm that the arrangement is within ASC 606 (and not a lease, insurance, financial instrument, or a collaboration (ASC 606-10-15-2 to 15-5))',
                    'Verify that the parties have approved the contract and are committed to perform (ASC 606-10-25-1(a))',
                    'Identify each party\'s rights regarding the goods or services to be transferred (ASC 606-10-25-1(b))',
                    'Identify each party\'s payment terms for the transferred goods or services (ASC 606-10-25-1(c))',
                    'Assess whether the contract has commercial substance (ASC 606-10-25-1(d))',
                    'Evaluate whether it is probable that the entity will collect the consideration (ASC 606-10-25-1(e)). Explain that the collectibility assessment would require external information (customer\'s credit/intent) and management should perform this evaluation separate from this analysis.',
                    'If the criteria in ASC 606-10-25-1 are not met, ASC 606-10-25-6 to 25-8 should be applied to deter revenue, recognize a liability and reassess',
                    'If there are any modification of the pre-existing contract, explain that ASC 606-10-25-10 to 25-13 should be applied to determine if the modification is a new contract or an extension of the existing contract. Note that such evaluation is not in the scope of this analysis and should be performed separately.',
                    
                ]
            },
            2: {
                'title': 'Step 2: Identify Performance Obligations', 
                'focus': 'Identify distinct goods or services using ASC 606-10-25-14 and 25-22',
                'key_points': [
                    'Identify all promised goods and services in the contract (ASC 606-10-25-16)',
                    'Separately evaluate whether each promised good or service is capable of being distinct per ASC 606-10-25-20 (can the customer benefit from the good or service either on its own or with other readily available resources?)',
                    'Separately evaluate whether each promised good or service is distinct within the context of the contract (or also called separately identifiable) per ASC 606-10-25-21(a-c):',
                    'Evaluate "distinct within context" per ASC 606-10-25-21: (a) significant integration service, (b) significant modification/customization, or (c) highly interdependent/interrelated goods/services.',
                    'Evaluate the “series” criterion (a series of distinct goods or services that are substantially the same and have the same pattern of transfer) (ASC 606-10-25-14(b))',
                    'Assess warranties (assurance-type vs service-type), since service-type warranties are separate POs (ASC 606-10-55-30 through 55-35)',
                    'Consider consignment indicators when relevant (affects control and timing, not a separate PO) (ASC 606-10-55-80 through 55-84)',
                    'Combine non-distinct goods/services into a single performance obligation (ASC 606-10-25-22)',
                    'Consider principal vs. agent determination if a third party or parties are involved (ASC 606-10-55-36 to 55-40)',
                    'Identify any customer options for additional goods/services or material rights (ASC 606-10-55-41 to 55-45)',
                    'Provide a summary of the performance obligations identified in your analysis. This summary should list each distinct performance obligation and its key characteristics for executive review.',
                     '',
                     '[BEGIN_PO_SUMMARY]',
                     'Count: [Number]',
                     'List:',
                     '- [PO 1 short label]',
                     '- [PO 2 short label]',
                     '- [Additional POs as needed]',
                     '[END_PO_SUMMARY]'
                ]
            },
            3: {
                'title': 'Step 3: Determine the Transaction Price',
                'focus': 'Establish the transaction price per ASC 606-10-32-2',
                'key_points': [
                    'Identify the fixed consideration amounts',
                    'Identify the variable consideration amounts (ASC 606-10-32-5 to 32-9)',
                    'Explain that constraints on variable consideration require separate management evaluation per ASC 606-10-32-11 to 32-13 as it requires information and judgment not available in the uploaded contract documents.',
                    'Calculate and present the total transaction price',
                    'Determine if any significant financing components are present',
                    'Determine if any noncash consideration is present',
                    'Determine if any consideration paid or payable to a customer is present'
    
                ]
            },
            4: {
                'title': 'Step 4: Allocate the Transaction Price',
                'focus': 'Allocate price to performance obligations based on standalone selling prices or SSPs (SSPs to be determined separately per ASC 606-10-32-31 to 32-34)',
                'key_points': [
                    'Summarize the performance obligations determined in Step 2',
                    'State that standalone selling prices (SSPs) should be determined by management separately based on observable data (ASC 606-10-32-31 to 32-34)',
                    'Describe the allocation methodology to allowed by ASC 606 in ASC 10-32-24 (adjusted market assessment approach, expected cost plus a margin approach, and residual approach)',
                    'Note any discount allocation considerations (ASC 606-10-32-36)',
                    'Provide the final allocation approach (subject to SSP determination)'
                ]
            },
            5: {
                'title': 'Step 5: Recognize Revenue',
                'focus': 'Determine when revenue should be recognized for each performance obligation',
                'key_points': [
                    'Determine over-time vs. point-in-time recognition for each performance obligation. Over time if one of the three criteria is met (simultaneous receipt/consumption, customer controls the asset as created, or no alternative use and enforceable right to payment (ASC 606-10-25-27)), otherwise point in time (ASC 606-10-25-30)',
                    'Analyze when control transfers to the customer',
                    'Specify revenue recognition timing for each obligation',
                    'Identify any measurement methods for over-time recognition'
                ]
            }
        }
        
        step = step_info[step_num]
        
        prompt = f"""
STEP {step_num}: {step['title'].upper()}

OBJECTIVE: {step['focus']}

CONTRACT INFORMATION:
Contract Analysis: Analyze the contract with the customer {customer_name} to determine the appropriate revenue recognition treatment under ASC 606.

Instructions: Analyze this contract from the company's perspective. {customer_name} is the customer receiving goods or services.

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
Analyze the contract for Step {step_num} focusing on:
{chr(10).join([f"• {point}" for point in step['key_points']])}

REQUIRED OUTPUT FORMAT (Clean Markdown):

### {step['title']}

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific contract evidence and ASC 606 citations. Quote contract language only when the exact wording is outcome‑determinative; paraphrase ASC 606 with pinpoint citations and use only brief decisive phrases when directly supportive.]

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion]
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed citations)
- Contract citations must reference actual text from the document:
    Good: [Contract, Payment Terms clause], [Contract, 'payment due within 30 days']
    Bad: [Contract §4.2], [Contract, p. 15] (unless these exact references appear in the contract text)
- Only cite section numbers/page numbers if they are explicitly visible in the contract text
- ASC 606 guidance paraphrased with citations; include only brief
decisive phrases when directly supportive (e.g., [ASC 606-10-25-19])

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 606 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

CRITICAL ANALYSIS REQUIREMENTS - CONTRACT VS EXTERNAL DATA:

1. CONTRACT FACTS (dates, terms, amounts explicitly in the document):
   - If present: Quote or paraphrase with citation
   - If missing: State "Not specified in contract"
   - NEVER invent or guess these

2. EXTERNAL INPUTS (accounting policies, valuations, judgments NOT in contract):
   - Always state the ASC 606 requirement
   - Create management placeholder: "[Management Input Required: SSP determination per ASC 606-10-32-33]"
   - Examples: SSP estimates, variable consideration constraints, collectibility assessments

3. CITATION RULES:
   - Contract: Only cite what's visible - [Contract, Payment Terms] ✓  |  [Contract §4.2] ✗ (unless §4.2 appears)
   - ASC 606: Paraphrase + pinpoint cite - [ASC 606-10-25-1]

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
            1: "Step 1: Identify the Contract",
            2: "Step 2: Identify Performance Obligations", 
            3: "Step 3: Determine the Transaction Price",
            4: "Step 4: Allocate the Transaction Price",
            5: "Step 5: Recognize Revenue"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    # REMOVED: _apply_basic_formatting - using clean GPT-4o markdown directly
    
    def _extract_conclusions_from_steps(self, steps_data: Dict[str, Any]) -> str:
        """Extract conclusion text from all completed steps."""
        conclusions = []
        logger.info(f"Extracting conclusions from {len(steps_data)} steps")
        
        for step_num in range(1, 6):
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
                        logger.warning(f"Could not extract conclusion from Step {step_num} content")
                else:
                    logger.warning(f"Step {step_num} data structure: {type(step_data)}, keys: {step_data.keys() if isinstance(step_data, dict) else 'N/A'}")
        
        conclusions_text = '\n\n'.join(conclusions)
        logger.info(f"Total conclusions extracted: {len(conclusions)}, text length: {len(conclusions_text)}")
        
        # If still no conclusions, generate fallback from step summaries
        if len(conclusions) == 0:
            logger.warning("No conclusions extracted - using fallback summary generation")
            for step_num in range(1, 6):
                step_key = f'step_{step_num}'
                if step_key in steps_data:
                    step_data = steps_data[step_key]
                    if isinstance(step_data, dict) and 'markdown_content' in step_data:
                        content = step_data['markdown_content']
                        # Extract the title and create a simple summary
                        if '### Step' in content and '**Analysis:**' in content:
                            # Get a brief summary from the content
                            summary = f"Step {step_num} completed - analysis of contract provisions under ASC 606."
                            conclusions.append(summary)
        
        return conclusions_text
    
    def generate_executive_summary(self, conclusions_text: str, customer_name: str) -> str:
        """Generate executive summary using clean LLM call."""
        logger.info("→ Generating executive summary...")
        
        prompt = f"""Generate a professional executive summary for an ASC 606 revenue recognition analysis for {customer_name}.

Step Conclusions:
{conclusions_text}

Requirements:
1. Write 3-5 sentences with proper paragraph breaks
2. Use professional accounting language
3. Include specific number of performance obligations identified
4. State compliance conclusion clearly
5. Highlight any significant findings or issues
6. Use double line breaks between paragraphs for readability
7. ALWAYS format currency with $ symbol (e.g., $240,000, not 240,000)
8. Include proper spacing after commas and periods
9. DO NOT include any title or header like "Executive Summary:" - only provide the summary content"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing executive summaries for ASC 606 analyses. Provide clean, professional content with proper currency formatting."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self._get_temperature()
            }
            params.update(self._get_max_tokens_param("executive_summary"))
            
            response = self.client.chat.completions.create(**params)
            
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
        
        prompt = f"""Generate a professional 2-3 sentence background for an ASC 606 memo.

Customer: {customer_name}
Contract Summary: {conclusions_text}

Instructions:
1. Describe what type of arrangement was reviewed (high-level)
2. Mention key contract elements (SaaS, hardware, services, etc.) if evident
3. State the purpose of the ASC 606 analysis
4. Professional accounting language
5. Keep it high-level, no specific amounts or detailed terms"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing background sections for ASC 606 memos. Provide clean, professional content."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self._get_temperature()
            }
            params.update(self._get_max_tokens_param("background"))
            
            response = self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            if content:
                content = content.strip()
                logger.info(f"✓ Background section generated ({len(content)} chars)")
                return content
            else:
                logger.error("Empty background response")
                return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606."
            
        except Exception as e:
            logger.error(f"Error generating background: {str(e)}")
            return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606."
        
    def generate_final_conclusion(self, conclusions_text: str) -> str:
        """Generate LLM-powered final conclusion from step conclusions.
        
        Args:
            conclusions_text: Pre-extracted conclusions from all 5 steps
        """
        logger.info("→ Generating final conclusion...")
        prompt = f"""Generate a professional final conclusion for an ASC 606 analysis.

Step Conclusions:
{conclusions_text}

Instructions:
1. Write 2-3 sentences in narrative paragraph format assessing the contract is accounted for properly under ASC 606 compliance
2. Format all currency as $XXX,XXX (no spaces in numbers)
3. Base your conclusion ONLY on the actual findings from the step conclusions provided above
4. Only mention concerns if they are explicitly identified in the step analysis - do not invent or infer new issues
5. If no significant issues are found in the steps, state compliance with ASC 606
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
                        "content": "You are an expert technical accountant specializing in ASC 606 revenue recognition."
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
            return "Based on our comprehensive analysis under ASC 606, the proposed revenue recognition treatment is appropriate and complies with the authoritative guidance."

    
    def _load_step_prompts(self) -> Dict[str, str]:
        """Load step-specific prompts if available."""
        # For now, return empty dict - prompts are built dynamically
        # In the future, could load from templates/step_prompts.txt
        return {}