"""
ASC 718 Step Analyzer

This module handles the 5-step ASC 718 stock compensation analysis.
Simplified, natural language approach with clear reasoning chains.
"""

import openai
import os
import logging
import time
import re
import random
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ASC718StepAnalyzer:
    """
    Simplified ASC 718 step-by-step analyzer using natural language output.
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
        """Extract the granting entity name using LLM analysis."""
        try:
            logger.info("🏢 Extracting granting entity name from documents...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying company names in stock compensation agreements. Your task is to identify the name of the entity granting the share-based payment award."
                },
                {
                    "role": "user",
                    "content": f"""Based on this stock compensation agreement, what is the name of the company granting the share-based payment award?

Please identify:
- The company that is issuing/granting the stock compensation (the grantor/employer)
- The name including suffixes like Inc., LLC, Corp., etc.
- Ignore addresses, reference numbers, or other non-company identifiers

Stock Compensation Documents:
{contract_text[:4000]}

Respond with ONLY the granting company name, nothing else."""
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
                logger.warning(f"LLM returned suspicious granting entity name: {entity_name}")
                return "Granting Entity"
            
            logger.info(f"✓ Granting entity identified: {entity_name}")
            return entity_name
            
        except Exception as e:
            logger.error(f"Error extracting granting entity name with LLM: {str(e)}")
            return "Granting Entity"
    
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
                        entity_name: str,
                        analysis_title: str,
                        additional_context: str = "") -> Dict[str, Any]:
        """
        Perform complete 5-step ASC 718 analysis.
        
        Args:
            contract_text: The transaction document text
            authoritative_context: Retrieved ASC 718 guidance
            entity_name: Target company name
            analysis_title: Analysis title
            additional_context: Optional user-provided context
            
        Returns:
            Dictionary containing analysis results for each step
        """
        analysis_start_time = time.time()
        logger.info(f"Starting ASC 718 analysis for {entity_name}")
        
        # Add large contract warning
        word_count = len(contract_text.split())
        if word_count > 50000:
            logger.warning(f"Large contract ({word_count} words). Consider splitting if analysis fails.")
        
        results = {
            'entity_name': entity_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y"),
            'steps': {}
        }
        
        # Analyze steps in parallel with error recovery
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all step analyses
            futures = {
                executor.submit(
                    self._analyze_step_with_retry,
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    entity_name=entity_name,
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
        results['executive_summary'] = self.generate_executive_summary(conclusions_text, entity_name)
        results['background'] = self.generate_background_section(conclusions_text, entity_name)
        results['conclusion'] = self.generate_final_conclusion(results['steps'])
        
        total_time = time.time() - analysis_start_time
        logger.info(f"✓ ASC 718 analysis completed successfully in {total_time:.1f}s")
        return results
    
    def _analyze_step_with_retry(self,
                               step_num: int,
                               contract_text: str,
                               authoritative_context: str,
                               entity_name: str,
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
                    entity_name=entity_name,
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
                     entity_name: str,
                     additional_context: str = "") -> Dict[str, str]:
        """Analyze a single ASC 718 step - returns clean markdown."""
        
        # Log financial calculations for Step 2 (Grant-date measurement/valuation)
        if step_num == 2:
            logger.info("💰 Extracting stock grant details and fair value calculations...")
        
        # Get step-specific prompt for markdown output
        prompt = self._get_step_markdown_prompt(
            step_num=step_num,
            contract_text=contract_text,
            authoritative_context=authoritative_context,
            entity_name=entity_name,
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
            
            if markdown_content is None:
                logger.error(f"ERROR: GPT-5 returned None content for Step {step_num}")
                markdown_content = f"## Step {step_num}: Analysis Error\n\nError: GPT-5 returned empty response. Please try with GPT-4o instead."
            else:
                # Content received successfully
                
                # ONLY strip whitespace - NO OTHER PROCESSING
                markdown_content = markdown_content.strip()
                
                # Check for suspiciously short response
                if not markdown_content or len(markdown_content) < 50:
                    logger.warning(f"⚠️ Step {step_num}: Received suspiciously short response ({len(markdown_content) if markdown_content else 0} chars)")
                
                # Log sample of clean content for verification
                logger.info(f"DEBUG: Clean markdown for Step {step_num} (length: {len(markdown_content)}) sample: {markdown_content[:100]}...")
            
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
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 718 stock compensation. 

Generate professional accounting analysis in clean markdown format. Your output will be displayed directly using markdown rendering.

Your analysis must be:
- Audit-ready and professional
- Clear and understandable
- Based on the evidence provided in the stock compensation documents
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
- Support your analysis with specific award evidence and authoritative citations
- Use direct quotes from the award documents only when the exact wording is outcome-determinative
- Paraphrase ASC 718 with pinpoint citations; brief decisive phrases may be quoted when directly supportive
- Acknowledge any limitations or gaps in information
- Formatted as clean, ready-to-display markdown

Follow ALL formatting instructions in the user prompt precisely."""
    
    def _get_step_markdown_prompt(self, 
                        step_num: int,
                        contract_text: str, 
                        authoritative_context: str,
                        entity_name: str,
                        additional_context: str = "") -> str:
        """Generate markdown prompt for a specific step."""
        
        step_info = {
            1: {
                'title': 'Step 1: Scope, terms, grant date, and classification',
                'focus': 'Confirm the arrangement is within ASC 718 and determine equity vs liability classification based on settlement features and own-stock criteria',
                'key_points': [
                    'Scope: Confirm the award is a compensatory share-based payment within ASC 718 (exclude ESPPs/ESOPs, standalone derivatives under ASC 815, ASC 480 instruments, and customer/vendor incentives under ASC 606). [ASC 718-10-15; ASC 815; ASC 480; ASC 606]',
                    'Parties: Identify employee vs nonemployee; post-ASU 2018-07, core recognition/measurement principles are largely aligned (with attribution nuances). [ASC 718-10-15; 718-10-30; 718-10-35]',
                    'Terms inventory: Capture all substantive terms—award type (option/RSU/PSU/SAR), vesting (service vs performance vs market; cliff vs graded), non-vesting conditions (e.g., post-vesting sale restrictions), post-termination/retirement, clawbacks, repurchase/put/call features, reloads, dividend/dividend-equivalent features, settlement alternatives (cash vs shares), and tax withholding/net-share settlement. [ASC 718-10-20; 718-10-30]',
                    'Grant date: Establish grant date (mutual understanding and approval of key terms). If service inception precedes grant date, recognize compensation using FV measured at each reporting date until grant date, then true-up to grant-date FV. [ASC 718-10-20 (definitions); 718-10-25; 718-10-55]',
                    'Classification: Determine equity vs liability. Cash-settled or obligating features → liability (remeasured each period). Share-settled that qualify as equity → equity (no post–grant-date remeasurement). Apply own-stock guidance (indexation and settlement) to confirm equity classification. Net share withholding up to the maximum statutory rate generally retains equity classification. Consider features that could force cash settlement or fail own-stock criteria (may require liability classification). [ASC 718-30; 718-20; 815-40; 718-10-25]'
                ]
            },
            2: {
                'title': 'Step 2: Grant-date measurement (valuation by award type)',
                'focus': 'Measure grant-date fair value using an appropriate model and well-supported inputs; apply permitted nonpublic expedients where applicable',
                'key_points': [
                    'Options and share-settled SARs (equity): Explain that ASC 718 requires grant-date fair value to be measured using a recognized option-pricing model (e.g., Black-Scholes, lattice model). The memo should list the required inputs (current share price, expected term, volatility, risk-free rate, dividend yield) and generate clear placeholders for management to provide each input, its value, and the source/justification. [ASC 718-10-30; 718-20-55]',
                    'RSUs/restricted stock: State that the grant-date fair value is determined based on the fair value of the underlying equity on the grant date. The analysis should note that non-vesting conditions, such as post-vesting sales restrictions, must be factored into the fair value measurement and prompt for management to describe if any such conditions exist and how they were considered. [ASC 718-10-30]',
                    'PSUs: Clearly differentiate the accounting treatment based on the condition type. For non-market performance conditions, explain that they are excluded from the grant-date fair value measurement and instead affect the timing and amount of expense recognized (i.e., recognized only if the condition is probable of achievement). For market conditions, explain that their effect must be included in the grant-date fair value (e.g., via a Monte Carlo simulation) and that compensation cost is recognized regardless of whether the market condition is achieved, provided the service condition is met. [ASC 718-10-20; 718-10-35; 718-20-55; 718-10-30]',
                    'Liability-classified awards (e.g., cash-settled SARs): Explain the requirement to classify the award as a liability and to remeasure its fair value at each reporting date until settlement. State that changes in fair value are recorded in earnings and prompt for management to confirm the process for this recurring valuation. [ASC 718-30-35]',
                    'Nonpublic expedients: If the entity is nonpublic, describe the permitted practical expedients available under ASC 718, such as the simplified method for estimating the expected term. Prompt the user to specify if they are electing any expedients and to provide the necessary justification. [ASC 718-10-30]'
                ]
            },
            3: {
                'title': 'Step 3: Requisite service period, attribution, forfeitures, and condition assessments',
                'focus': 'Determine the period/pattern of recognition and apply condition-specific rules',
                'key_points': [
                    'Requisite service period: Analyze the award terms to identify the explicit, implicit, or derived service period. The analysis should state the determined service period based on the vesting conditions, including any specific considerations for market conditions or retirement eligibility. [ASC 718-10-20; 718-10-35]',
                    'Attribution: Based on the vesting schedule identified in the terms, describe the permissible attribution methods. For awards with graded vesting, explain that the entity can elect, as an accounting policy, to use either the straight-line method for the entire award or the accelerated (graded) method for each tranche. Prompt for management to state its accounting policy. [ASC 718-10-35]',
                    'Forfeitures: Explain that an entity must make an accounting policy election to either (a) estimate the number of awards expected to be forfeited and update the estimate, or (b) account for forfeitures as they occur. Prompt for management to state its policy election. [ASC 718-10-35]',
                    'Non-market performance conditions: Explain that for these conditions, compensation cost is recognized only if and when it is probable the condition will be achieved. The analysis must generate a placeholder for management to document its assessment of probability for each performance condition and the basis for that judgment. [ASC 718-10-35; 718-20-55]',
                    'Market conditions: State that the impact of a market condition is included in the award’s grant-date fair value, and therefore compensation cost is recognized as long as the requisite service is rendered, regardless of whether the market condition is ultimately met. [ASC 718-10-30; 718-20-55]',
                    'Non-vesting conditions: State that these conditions do not affect vesting or the requisite service period, but their financial impact should be reflected in the grant-date fair value of the award. [ASC 718-10-30]',
                    'Dividends/dividend equivalents: Describe the accounting treatment based on the award terms. If dividends are forfeitable with the award, they are accrued as compensation cost. If non-forfeitable, they are accounted for differently. The analysis should reflect the specific terms of the award. [ASC 718-10-35; 718-20]',
                    'Employer payroll taxes: State the requirement to recognize a liability for employer payroll taxes when the underlying taxable event occurs (typically at vesting or exercise/settlement). [ASC 718-10-25/35]'
                ]
            },
            4: {
                'title': 'Step 4: Subsequent measurement, modifications, classification changes, settlements, and special transactions',
                'focus': 'Remeasure liabilities, account for changes in terms/classification, and record exercises, cancellations, and business-combination effects',
                'key_points': [
                    'Liability-classified awards: Explain the requirement to remeasure the fair value of liability-classified awards at each reporting date until settlement. State that the change in fair value is recognized in earnings and generate a placeholder for management to document its periodic remeasurement calculations. [ASC 718-30-35]',
                    'Equity-classified awards: State that equity-classified awards are not remeasured after the grant date, except in the case of a modification. The analysis should note that accounting continues to be subject to the entity\'s policies for forfeitures and assessments of non-market performance conditions. [ASC 718-20-35]',
                    'Modifications: Describe what constitutes a modification under ASC 718 (e.g., repricing, acceleration). Explain the accounting requirement to measure any incremental fair value granted and recognize it over the remaining service period. Generate placeholders for management to input the fair value immediately before and after the modification and the resulting incremental cost. [ASC 718-20-35; 718-20-55]',
                    'Cancellations/forfeitures/expirations: Explain the accounting treatment for these events. For cancellations or forfeitures of unvested awards, state the requirement to reverse any previously recognized compensation cost. For vested awards that expire unexercised, explain that no cost is reversed. [ASC 718-20-35]',
                    'Settlements/exercises: Describe the accounting entries required upon settlement or exercise. The analysis should cover the pattern for issuing shares, paying cash, and accounting for net-share withholding for taxes based on the award’s terms and classification. [ASC 718-20-35; 718-10-25]',
                    'Business combinations (replacement awards): Explain the requirement to allocate the fair value of replacement awards between pre-combination service (accounted for as part of the business combination consideration) and post-combination service (recognized as post-combination compensation cost). Prompt for management to document its valuation and allocation methodology. [ASC 805-30; ASC 718-20-35]'
                ]
            },
            5: {
                'title': 'Step 5: Income tax accounting and core journal entries (no disclosures)',
                'focus': 'Record current/deferred taxes and the core financial statement effects; exclude disclosures',
                'key_points': [
                    'Deferred taxes: Explain the requirement to recognize a Deferred Tax Asset (DTA) for the deductible temporary difference created by the cumulative book compensation cost recognized. State that management must assess this DTA for realizability and determine if a valuation allowance is necessary, consistent with ASC 740. [ASC 718-740; ASC 740-10]',
                    'Excess tax benefits/shortfalls: Explain that any difference between the tax deduction realized upon settlement and the cumulative compensation cost recognized for book purposes is recorded as an excess tax benefit or shortfall. State that this amount is recognized as a discrete item in income tax expense in the period of settlement. [ASC 718-740-25]',
                    'Tax deduction measurement: Describe how the tax deduction is typically measured, noting it is based on the intrinsic value of an equity award at settlement or the cash paid for a liability award. The analysis should note this is subject to local tax law. [ASC 718-740]',
                    'Illustrative entries: Describe the pattern of typical journal entries, using placeholders for amounts. Equity-classified: Dr compensation expense / Cr APIC during vesting; at settlement, record common stock/APIC and any net share withholding cash remittance; record DTA activity and any excess/shortfall to tax expense. Liability-classified: Dr compensation expense / Cr liability during vesting and remeasurement; settle liability in cash at payment and release related DTA. [ASC 718-10-45; 718-740; 718-30-35]'
                ]
            }
        }
        
        step = step_info[step_num]
        
        prompt = f"""
STEP {step_num}: {step['title'].upper()}

OBJECTIVE: {step['focus']}

TRANSACTION INFORMATION:
Share-based Payment Analysis: Analyze the transaction involving {entity_name} to determine the appropriate share-based payment accounting treatment under ASC 718.

Instructions: Analyze this transaction from the entity's perspective.

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

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific award evidence and ASC 718 citations. Quote award language only when the exact wording is outcome-determinative; paraphrase ASC 718 with pinpoint citations and use only brief decisive phrases when directly supportive.]

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion]
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed citations)
- Contract citations must reference actual text from the document:
    Good: [Stock Plan, Vesting Conditions]
    Bad: [Stock Plan §4.2], [Stock Plan, p. 15] (unless these exact references appear in the contract text)
- Only cite section numbers/page numbers if they are explicitly visible in the contract text
- ASC 718 guidance paraphrased with citations; include only brief decisive phrases when directly supportive

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 718 citation.]

CRITICAL ANALYSIS REQUIREMENTS:
- If information is not explicitly stated in the contract, write "Not specified in contract"
- NEVER infer, guess, or invent contract terms, dates, amounts, or section references
- If a required fact is not provided in the contract, state "Not specified in contract" rather than guessing
- Use concise, assertive language ("We conclude...") rather than hedging ("It appears...") unless a gap is material

CRITICAL FORMATTING REQUIREMENTS:
- Format currency as: $240,000 (with comma, no spaces)
- Use proper spacing after periods and commas
- Use professional accounting language
- Double-check all currency amounts for correct formatting

"""

        return prompt
    
    def validate_step_output(self, markdown_content: str, step_num: int) -> Dict[str, Any]:
        """Validate step output for required sections and formatting issues."""
        issues = []
        
        # Check for required sections
        if "**Analysis:**" not in markdown_content:
            issues.append(f"Missing Analysis section in Step {step_num}")
        
        if "**Conclusion:**" not in markdown_content:
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
    
    def _get_step_title(self, step_num: int) -> str:
        """Get the title for a specific step."""
        titles = {
            1: "Step 1: Scope, Terms, Grant Date, and Classification",
            2: "Step 2: Grant-Date Measurement (Valuation by Award Type)", 
            3: "Step 3: Requisite Service Period, Attribution, Forfeitures, and Condition Assessments",
            4: "Step 4: Subsequent Measurement, Modifications, Classification Changes, Settlements, and Special Transactions",
            5: "Step 5: Income Tax Accounting and Core Journal Entries (No Disclosures)"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    def _load_step_prompts(self) -> Dict[int, str]:
        """Load step-specific prompts (placeholder for future use)."""
        return {}
    
    def generate_executive_summary(self, conclusions_text: str, entity_name: str) -> str:
        """Generate executive summary from step conclusions."""
        logger.info("→ Generating executive summary...")
        
        try:
            prompt = f"""Generate an executive summary for an ASC 718 stock compensation memorandum for {entity_name}.

Based on these step conclusions:

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

            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert technical accountant generating executive summaries for ASC 718 memos. Write clearly and professionally."
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
                return f"Executive summary for {entity_name} stock compensation analysis could not be generated."
            
            summary = summary.strip()
            logger.info(f"✓ Executive summary generated ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return f"Executive summary for {entity_name} stock compensation analysis could not be generated due to an error."
    
    def generate_background_section(self, conclusions_text: str, entity_name: str) -> str:
        """Generate background section from step conclusions."""
        logger.info("→ Generating background section...")
        
        try:
            prompt = f"""Generate a 2-3 sentence background section for an ASC 718 stock compensation memorandum for {entity_name}.

Based on these step conclusions:

{conclusions_text}

Requirements:
- Explain what award documents were reviewed
- Briefly describe the nature of the share-based payment arrangement (award type and terms)
- State the purpose of this memo (ASC 718 stock compensation analysis)
- Keep it factual and professional (2-3 paragraphs)
- Use the exact entity name: {entity_name}

Format as clean markdown - no headers, just paragraphs."""

            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert technical accountant generating background sections for ASC 718 memos. Write clearly and professionally."
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
                return f"We have reviewed the stock compensation award documents provided by {entity_name} to determine the appropriate accounting treatment under ASC 718. This memorandum presents our analysis following the five-step ASC 718 methodology."
            
            background = background.strip()
            logger.info(f"✓ Background section generated ({len(background)} chars)")
            return background
            
        except Exception as e:
            logger.error(f"Error generating background section: {str(e)}")
            return f"We have reviewed the stock compensation award documents provided by {entity_name} to determine the appropriate accounting treatment under ASC 718. This memorandum presents our analysis following the five-step ASC 718 methodology."
    
    def generate_final_conclusion(self, analysis_results: Dict[str, Any]) -> str:
        """Generate LLM-powered final conclusion from analysis results."""
        logger.info("→ Generating final conclusion...")

        # Extract conclusions from markdown content using the proper extraction method
        conclusions_text = self._extract_conclusions_from_steps(analysis_results)
        prompt = f"""Generate a professional final conclusion for an ASC 718 analysis.

    Step Conclusions:
    {conclusions_text}

    Instructions:
    1. Write 2-3 sentences in narrative paragraph format assessing ASC 718 compliance
    2. Format all currency as $XXX,XXX (no spaces in numbers)
    3. Base your conclusion ONLY on the actual findings from the step conclusions provided above
    4. Only mention concerns if they are explicitly identified in the step analysis - do not invent or infer new issues
    5. If no significant issues are found in the steps, state compliance with ASC 718
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
                        "content": "You are an expert technical accountant specializing in ASC 718 stock compensation."
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
            return "Based on our comprehensive analysis under ASC 718, the proposed stock compensation treatment is appropriate and complies with the authoritative guidance."
    
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
                        logger.info(f"DEBUG: Extracted conclusion for {step_key}: {conclusion_text[:100]}...")
                    else:
                        # Fallback to improved regex that captures until next bold section or end
                        conclusion_match = re.search(r'\*\*Conclusion:\*\*\s*(.+?)(?:\n\s*\*\*|$)', content, re.IGNORECASE | re.DOTALL)
                        if conclusion_match:
                            conclusion_text = conclusion_match.group(1).strip()
                            conclusions.append(f"Step {step_num}: {conclusion_text}")
                            logger.info(f"DEBUG: Extracted conclusion for {step_key}: {conclusion_text[:100]}...")
                        else:
                            # Final fallback: use last paragraph as conclusion
                            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                            if paragraphs:
                                last_paragraph = paragraphs[-1]
                                conclusions.append(f"Step {step_num}: {last_paragraph}")
                                logger.info(f"DEBUG: Used last paragraph as conclusion for {step_key}: {last_paragraph[:100]}...")
                            else:
                                logger.warning(f"DEBUG: No content found for {step_key}")
                else:
                    logger.warning(f"DEBUG: {step_key} missing markdown_content. Available keys: {list(step_data.keys()) if isinstance(step_data, dict) else 'Not a dict'}")
            else:
                logger.warning(f"DEBUG: {step_key} not found in steps_data. Available keys: {list(steps_data.keys())}")
        
        combined_conclusions = '\n\n'.join(conclusions)
        logger.info(f"DEBUG: Combined conclusions length: {len(combined_conclusions)} chars")
        return combined_conclusions