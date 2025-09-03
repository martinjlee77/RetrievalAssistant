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
        
        # Load step prompts (currently unused - prompts are generated dynamically in _get_step_prompt)
        self.step_prompts = self._load_step_prompts()
    
    def extract_entity_name_llm(self, contract_text: str) -> str:
        """Extract the granting entity name using LLM analysis."""
        try:
            logger.info("DEBUG: Extracting granting entity name using LLM")
            
            request_params = {
                "model": self.light_model,
                "messages": [
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
                ],
                **self._get_max_tokens_param("default", self.light_model),
                "temperature": self._get_temperature(self.light_model)
            }
            
            if self.light_model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            entity_name = response.choices[0].message.content
            if entity_name is None:
                logger.warning("LLM returned None for customer name")
                return "Customer"
                
            # Clean the response (remove quotes, extra whitespace)
            entity_name = entity_name.strip().strip('"').strip("'").strip()
            
            # Validate the result
            if len(entity_name) < 2 or len(entity_name) > 120:
                logger.warning(f"LLM returned suspicious granting entity name: {entity_name}")
                return "Granting Entity"
                
            logger.info(f"DEBUG: LLM extracted granting entity name: {entity_name}")
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
                "step_analysis": 8000,
                "executive_summary": 8000,
                "background": 8000,
                "conclusion": 8000,
                "default": 8000
            }
            return {"max_completion_tokens": token_limits.get(request_type, 8000)}
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
        with ThreadPoolExecutor(max_workers=2) as executor:
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
        logger.info("Generating executive summary...")
        results['executive_summary'] = self.generate_executive_summary(conclusions_text, customer_name)
        logger.info("Generating background...")
        results['background'] = self.generate_background_section(conclusions_text, customer_name)
        logger.info("Generating conclusion...")
        results['conclusion'] = self.generate_conclusion_section(conclusions_text)
        logger.info("DEBUG: All additional sections generated successfully")
        
        logger.info("ASC 606 analysis completed successfully")
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
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Analyzing Step {step_num} (attempt {attempt + 1})")
                return self._analyze_step(
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name,
                    additional_context=additional_context
                )
            except openai.RateLimitError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Rate limit exceeded for Step {step_num} after {max_retries} attempts")
                    raise RuntimeError(f"OpenAI API rate limit exceeded. Please try again in a few minutes or contact support if this persists.")
                
                # Exponential backoff with jitter for rate limits
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limit hit for Step {step_num}. Waiting {delay:.1f}s before retry {attempt + 2}")
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
            
            markdown_content = response.choices[0].message.content
            
            if markdown_content is None:
                logger.error(f"ERROR: GPT-5 returned None content for Step {step_num}")
                markdown_content = f"## Step {step_num}: Analysis Error\n\nError: GPT-5 returned empty response. Please try with GPT-4o instead."
            else:
                # Content received successfully
                
                # ONLY strip whitespace - NO OTHER PROCESSING
                markdown_content = markdown_content.strip()
                
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
                        customer_name: str,
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
                    'Options and share-settled SARs (equity): Use a recognized option-pricing model (e.g., Black-Scholes, lattice). Document current price, expected term, volatility, risk-free rate, and dividends; reflect relevant features (e.g., market conditions, restrictions). [ASC 718-10-30; 718-20-55]',
                    'RSUs/restricted stock: Measure at grant-date FV of the underlying equity; incorporate non-vesting conditions in FV (e.g., post-vesting sale restrictions). [ASC 718-10-30]',
                    'PSUs: Non-market performance conditions: exclude from grant-date FV; recognition based on probable outcome/quantity expected to vest. Market conditions: include in grant-date FV (e.g., Monte Carlo); subsequent recognition is not adjusted for (non)achievement of the market condition, subject to service requirements. [ASC 718-10-20; 718-10-35; 718-20-55; 718-10-30]',
                    'Liability-classified awards (e.g., cash-settled SARs): Measure at FV each reporting date until settlement (remeasure through earnings). [ASC 718-30-35]',
                    'Nonpublic expedients: Consider permitted expedients (e.g., determining current price input; use of peer-group volatility when appropriate). Document judgments and sources. [ASC 718-10-30]'
                ]
            },
            3: {
                'title': 'Step 3: Requisite service period, attribution, forfeitures, and condition assessments',
                'focus': 'Determine the period/pattern of recognition and apply condition-specific rules',
                'key_points': [
                    'Requisite service period: Evaluate explicit, implicit, and derived service periods (including for market conditions and retirement eligibility). [ASC 718-10-20; 718-10-35]',
                    'Attribution: Apply straight-line or graded attribution consistent with policy and award terms. [ASC 718-10-35]',
                    'Forfeitures: Elect to estimate forfeitures or account for them as they occur; apply consistently and true-up. [ASC 718-10-35]',
                    'Non-market performance conditions: Recognize expense only when achievement is probable; update cumulative expense as probabilities change; reverse if no longer probable before vesting. [ASC 718-10-35; 718-20-55]',
                    'Market conditions: Recognition driven by service requirements; market effect is incorporated in grant-date FV. [ASC 718-10-30; 718-20-55]',
                    'Non-vesting conditions: Do not assess for "probable"; reflect in grant-date FV. [ASC 718-10-30]',
                    'Dividends/dividend equivalents: If forfeitable, recognize as compensation cost over the requisite service; if non-forfeitable prior to vesting, adjust accounting consistent with guidance. [ASC 718-10-35; 718-20]',
                    'Employer payroll taxes: Accrue when the taxable event occurs (typically at vesting/settlement). [ASC 718-10-25/35]'
                ]
            },
            4: {
                'title': 'Step 4: Subsequent measurement, modifications, classification changes, settlements, and special transactions',
                'focus': 'Remeasure liabilities, account for changes in terms/classification, and record exercises, cancellations, and business-combination effects',
                'key_points': [
                    'Liability-classified awards: Remeasure FV at each reporting date through settlement; recognize changes in earnings. [ASC 718-30-35]',
                    'Equity-classified awards: No remeasurement after grant date except for modifications; continue to apply forfeiture policy and performance-probability updates. [ASC 718-20-35]',
                    'Modifications (repricing, acceleration, extension, settlement-method change, performance condition changes): Identify a modification; measure incremental FV and recognize over remaining requisite service (or immediately if vested). Treat equity↔liability classification changes as modifications. [ASC 718-20-35; 718-20-55]',
                    'Cancellations/forfeitures/expirations: Reverse unrecognized cost for unvested awards; vested expirations generally do not create additional expense/benefit. [ASC 718-20-35]',
                    'Settlements/exercises: Record share issuance or cash settlement; handle net share withholding and any cash remitted for taxes appropriately. [ASC 718-20-35; 718-10-25]',
                    'Business combinations (replacement awards): Allocate the replacement award's FV between pre-combination service (consideration transferred) and post-combination service (compensation expense); then account under the modified terms going forward. [ASC 805-30; ASC 718-20-35]'
                ]
            },
            5: {
                'title': 'Step 5: Income tax accounting and core journal entries (no disclosures)',
                'focus': 'Record current/deferred taxes and the core financial statement effects; exclude disclosures',
                'key_points': [
                    'Deferred taxes: Recognize DTAs for deductible temporary differences arising from compensation cost; adjust DTAs as expense is recognized and expected tax deductions change. Assess valuation allowance as needed. [ASC 718-740; ASC 740-10]',
                    'Excess tax benefits/shortfalls: Recognize in income tax expense when they occur; adjust DTAs accordingly. Track by jurisdiction. [ASC 718-740-25]',
                    'Tax deduction measurement: For equity awards, the tax deduction typically equals intrinsic value at settlement; for liability awards, follows cash paid. Align with local tax law. [ASC 718-740]',
                    'Core entries: Equity-classified: Dr compensation expense / Cr APIC during vesting; at settlement, record common stock/APIC and any net share withholding cash remittance; record DTA activity and any excess/shortfall to tax expense. Liability-classified: Dr compensation expense / Cr liability during vesting and remeasurement; settle liability in cash at payment and release related DTA. [ASC 718-10-45; 718-740; 718-30-35]'
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

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific award evidence and ASC 718 citations. Quote award language only when the exact wording is outcome-determinative; paraphrase ASC 718 with pinpoint citations and use only brief decisive phrases when directly supportive.]

**Conclusion:** [Write single paragraph conclusion stating the specific outcome for this step]

END OUTPUT"""

        return prompt
    
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
    
    def generate_executive_summary(self, conclusions_text: str, customer_name: str) -> str:
        """Generate executive summary from step conclusions."""
        try:
            prompt = f"""Generate an executive summary for an ASC 718 stock compensation memorandum for {customer_name}.

Based on these step conclusions:

{conclusions_text}

Requirements:
- Start with the overall stock compensation accounting conclusion (classification, measurement, and recognition)
- Summarize the key findings from each step in 2-3 bullet points
- Keep professional but concise (3-4 paragraphs maximum)
- Focus on business impact and implementation guidance
- Use the exact entity name: {customer_name}

Format as clean markdown - no headers, just paragraphs and bullet points."""

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
            summary = response.choices[0].message.content
            
            if summary is None:
                logger.warning("LLM returned None for executive summary")
                return f"Executive summary for {customer_name} stock compensation analysis could not be generated."
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return f"Executive summary for {customer_name} stock compensation analysis could not be generated due to an error."
    
    def generate_background_section(self, conclusions_text: str, customer_name: str) -> str:
        """Generate background section from step conclusions."""
        try:
            prompt = f"""Generate a background section for an ASC 718 stock compensation memorandum for {customer_name}.

Based on these step conclusions:

{conclusions_text}

Requirements:
- Explain what award documents were reviewed
- Briefly describe the nature of the share-based payment arrangement (award type and terms)
- State the purpose of this memo (ASC 718 stock compensation analysis)
- Keep it factual and professional (2-3 paragraphs)
- Use the exact entity name: {customer_name}

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
            background = response.choices[0].message.content
            
            if background is None:
                logger.warning("LLM returned None for background section")
                return f"We have reviewed the stock compensation award documents provided by {customer_name} to determine the appropriate accounting treatment under ASC 718. This memorandum presents our analysis following the five-step ASC 718 methodology."
            
            return background.strip()
            
        except Exception as e:
            logger.error(f"Error generating background section: {str(e)}")
            return f"We have reviewed the stock compensation award documents provided by {customer_name} to determine the appropriate accounting treatment under ASC 718. This memorandum presents our analysis following the five-step ASC 718 methodology."
    
    def generate_conclusion_section(self, conclusions_text: str) -> str:
        """Generate conclusion section from step conclusions."""
        try:
            prompt = f"""Generate a conclusion section for an ASC 718 stock compensation memorandum.

Based on these step conclusions:

{conclusions_text}

Requirements:
- Synthesize the overall stock compensation accounting treatment
- Highlight any key implementation considerations
- Note any areas requiring further analysis or judgment
- Provide clear next steps or recommendations
- Keep professional and decisive (2-3 paragraphs)

Format as clean markdown - no headers, just paragraphs."""

            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert technical accountant generating conclusions for ASC 606 memos. Write clearly and professionally."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **self._get_max_tokens_param("conclusion", self.light_model),
                "temperature": self._get_temperature(self.light_model)
            }
            
            if self.light_model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            conclusion = response.choices[0].message.content
            
            if conclusion is None:
                logger.warning("LLM returned None for conclusion section")
                return "Based on our analysis, the revenue recognition treatment should follow the methodology outlined in this memo. Management should review and implement these conclusions in consultation with external auditors."
            
            return conclusion.strip()
            
        except Exception as e:
            logger.error(f"Error generating conclusion section: {str(e)}")
            return "Based on our analysis, the revenue recognition treatment should follow the methodology outlined in this memo. Management should review and implement these conclusions in consultation with external auditors."
    
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
                    
                    # Extract conclusion from markdown content
                    if '**Conclusion:**' in content:
                        # Find the conclusion section
                        conclusion_start = content.find('**Conclusion:**')
                        if conclusion_start != -1:
                            conclusion_text = content[conclusion_start:].strip()
                            # Get just the conclusion paragraph (until next section or end)
                            lines = conclusion_text.split('\n')
                            conclusion_paragraph = lines[0] if lines else conclusion_text
                            conclusions.append(f"Step {step_num}: {conclusion_paragraph}")
                            logger.info(f"DEBUG: Extracted conclusion for {step_key}: {conclusion_paragraph[:100]}...")
                        else:
                            logger.warning(f"DEBUG: Found 'Conclusion:' but couldn't extract for {step_key}")
                    else:
                        # Fallback: use last paragraph as conclusion
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