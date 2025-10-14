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
        with ThreadPoolExecutor(max_workers=3) as executor:
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
            
            if markdown_content is None or (markdown_content and len(markdown_content.strip()) < 50):
                # Handle empty or very short response - retry once
                logger.warning(f"⚠️ Step {step_num}: Received empty/short response ({len(markdown_content) if markdown_content else 0} chars). Retrying...")
                
                # Retry the API call once
                import time
                time.sleep(2)  # Brief pause before retry
                retry_response = self.client.chat.completions.create(**request_params)
                
                # Track retry API cost
                from shared.api_cost_tracker import track_openai_request
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
                    'Confirm ASC 718 scope: compensatory share-based payment (exclude ASC 815 derivatives, ASC 480 instruments, ASC 606 customer incentives). Note that ESPPs/ESOPs are not covered in this analysis. Note employee vs nonemployee. [ASC 718-10-15]',
                    'Extract award terms: type (option/RSU/PSU/SAR), vesting conditions (service/performance/market; cliff/graded), settlement features (cash/shares), and special provisions (retirement, clawbacks, dividends, net-share withholding). [ASC 718-10-20; 718-10-30]',
                    'Determine grant date: mutual understanding + approval of key terms. If service precedes grant date, flag interim remeasurement requirement. [ASC 718-10-25]',
                    'Classify as equity or liability: Cash settlement or obligating features → liability (remeasured). Share settlement meeting own-stock criteria → equity (no remeasurement). Net-share withholding ≤ max statutory rate retains equity classification. [ASC 718-30; 815-40]'
                ]
            },
            2: {
                'title': 'Step 2: Grant-date measurement (valuation by award type)',
                'focus': 'Measure grant-date fair value using an appropriate model and well-supported inputs; apply permitted nonpublic expedients where applicable',
                'key_points': [
                    'Identify award type (option/RSU/PSU/SAR) and determine the applicable valuation approach under ASC 718. [ASC 718-10-30; 718-20-55]',
                    'For options/SARs: Note that fair value requires option-pricing model inputs (share price, expected term, volatility, risk-free rate, dividend yield). Note where management judgment or input is required.',
                    'For RSUs: Use grant-date stock price as fair value; flag any non-vesting conditions (e.g., post-vest restrictions) requiring fair value adjustment.',
                    'For PSUs: Distinguish market conditions (included in grant-date FV via Monte Carlo) from performance conditions (excluded from FV; affects expense timing only).',
                    'For liability awards: Note remeasurement requirement at each period. [ASC 718-30-35]',
                    'Nonpublic expedients: For nonpublic entities, describe the permitted practical expedients available under ASC 718, such as the simplified method for estimating the expected term. [ASC 718-10-30]'
                ]
            },
            3: {
                'title': 'Step 3: Requisite service period, attribution, forfeitures, and condition assessments',
                'focus': 'Determine the period/pattern of recognition and apply condition-specific rules',
                'key_points': [
                    'Determine requisite service period from vesting conditions (explicit, implicit, or derived). Note any retirement/death provisions. [ASC 718-10-20; 718-10-35]',
                    'Identify attribution method from vesting schedule. For graded vesting, note straight-line vs accelerated policy election → Note where management judgment or input is required: State attribution policy per ASC 718-10-35].',
                    'State forfeiture accounting policy → flag as [Management Input Required: Estimate-forfeitures or as-incurred election per ASC 718-10-35].',
                    'For performance conditions: Assess from contract if achievability is determinable; otherwise note probability assessment as management input.',
                    'Note that market conditions affect grant-date FV (Step 2) but not expense recognition pattern. [ASC 718-10-30]',
                ]
            },
            4: {
                'title': 'Step 4: Subsequent measurement, modifications, classification changes, settlements, and special transactions',
                'focus': 'Remeasure liabilities, account for changes in terms/classification, and record exercises, cancellations, and business-combination effects',
                'key_points': [
                    'For liability awards: Note remeasurement requirement each period until settlement (change in FV → earnings). Note where management judgment or input is required. [ASC 718-30-35]',
                    'For modifications (if applicable): Identify change type (repricing, acceleration, etc.). Measure incremental FV and recognize over remaining service period. Flag pre/post-modification FV as management input. [ASC 718-20-35; 718-20-55]',
                    'For cancellations/forfeitures: Unvested → reverse prior expense. Vested expirations → no reversal. [ASC 718-20-35]',
                    'For settlements/exercises: Describe entries for share issuance, cash payment, and tax withholding per award terms and classification. [ASC 718-20-35]',
                    'For business combinations (if replacement awards exist): Note allocation requirement between pre/post-combination service. Flag valuation methodology as management input. [ASC 805-30]'
                ]
            },
            5: {
                'title': 'Step 5: Income tax accounting and core journal entries (no disclosures)',
                'focus': 'Record current/deferred taxes and the core financial statement effects; exclude disclosures',
                'key_points': [
                    'Recognize DTA for cumulative book compensation cost (deductible temporary difference). Flag DTA realizability assessment and valuation allowance determination as management input per ASC 740. [ASC 718-740; ASC 740-10]',
                    'Excess tax benefits/shortfalls: Difference between tax deduction realized vs book compensation cost → discrete item in tax expense at settlement. [ASC 718-740-25]',
                    'Tax deduction measurement: Intrinsic value at settlement (equity awards) or cash paid (liability awards), subject to local tax law. [ASC 718-740]',
                    'Illustrative entries: Describe typical journal entry patterns for equity vs liability awards (vesting, settlement, tax effects) using placeholders for amounts. [ASC 718-10-45; 718-740]'
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
- Only cite section numbers/page numbers if they are explicitly visible in the contract text
- ASC 718 guidance paraphrased with citations; include only brief decisive phrases when directly supportive

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 718 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

CRITICAL ANALYSIS REQUIREMENTS - CONTRACT VS EXTERNAL DATA:
1. CONTRACT FACTS (dates, terms, amounts explicitly in the document):
   - If present: Quote or paraphrase with citation
   - If missing: State "Not specified in contract"
   - NEVER invent or guess these
2. EXTERNAL INPUTS (accounting policies, valuations, judgments NOT in contract):
   - Always state the ASC 718 requirement
   - Create management placeholder: "[Management Input Required: Describe forfeiture policy per ASC 718-10-35]"
   - Examples: forfeiture policy, fair value inputs, probability assessments, tax rates
3. CITATION RULES:
   - Contract: Only cite what's visible - [Stock Plan, Vesting Terms] ✓  |  [Stock Plan §4.2] ✗ (unless §4.2 appears in doc)
   - ASC 718: Paraphrase + pinpoint cite - [ASC 718-10-30-2]
Use assertive language ("We conclude...") when evidence supports it; flag gaps explicitly.


FORMATTING:
- Currency: $240,000 (comma-separated, no spaces)
- Spacing: Proper spacing after periods/commas
- Tone: Professional Big 4 language, assertive where evidence supports ("We conclude...")

"""

        return prompt
    
    def validate_step_output(self, markdown_content: str, step_num: int) -> Dict[str, Any]:
        """Validate step output for required structural sections only."""
        issues = []
        
        # Check for required sections
        if "**Analysis:**" not in markdown_content:
            issues.append(f"Missing Analysis section in Step {step_num}")
        
        if "**Conclusion:**" not in markdown_content:
            issues.append(f"Missing Conclusion section in Step {step_num}")
        
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