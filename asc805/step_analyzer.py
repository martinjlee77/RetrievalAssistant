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
                    'Determine scope: ASC 805 acquisition method vs (a) asset acquisition or common control under ASC 805-50, (b) joint venture formation under ASC 805-60, (c) not-for-profit combinations under ASC 958-805.',
                    'Assess whether the acquired set is a business using the optional screen test and the full "substantive processes" framework; document judgment using implementation examples (ASC 805-10-55).',
                    'Identify the acquirer (including VIE primary-beneficiary considerations) and assess whether there is a reverse acquisition (ASC 805-10; ASC 810 cross-reference).',
                    'Determine the acquisition date (when control transfers) and document the specific control-transfer event(s) (ASC 805-10).',
                    'If achieved in stages, identify a step acquisition and plan to remeasure the previously held interest at fair value on the acquisition date (ASC 805-10).',
                    'If preparing separate acquiree financial statements, evaluate optional pushdown accounting and related disclosures (ASC 805-50).'
                ]
            },
            2: {
                'title': 'Step 2: Consideration and items not part of the exchange',
                'focus': 'Measure consideration at fair value, classify contingent consideration, and separate transactions that are not part of the business combination exchange',
                'key_points': [
                    'Compile and measure consideration transferred at fair value: cash, liabilities incurred, assets transferred, equity instruments issued, and contingent consideration (ASC 805-30).',
                    'Measure any noncontrolling interest at acquisition-date fair value (full goodwill method) (ASC 805-30).',
                    'For step acquisitions, remeasure the previously held interest to fair value, recognize the gain or loss in earnings, and recycle related AOCI amounts as if the interest were disposed (ASC 805-10; ASC 220/815/320 cross-references).',
                    'Identify and account separately for items not part of the exchange: settlement of preexisting relationships, compensation for future services, and other side arrangements (ASC 805-10).',
                    'Expense acquisition-related costs as incurred; apply other guidance only for debt/equity issuance costs (ASC 805-10; ASC 340/470 and equity guidance).',
                    'Evaluate replacement share-based payment awards and allocate between precombination consideration and postcombination compensation cost (ASC 718; ASC 805-30).',
                    'Identify indemnification arrangements and recognize indemnification assets on the same basis as the related indemnified items (ASC 805-20).',
                    'Classify contingent consideration under ASC 480/815 (equity vs liability/derivative) and apply the corresponding subsequent measurement model (ASC 805-30-35; ASC 480/815).'
                ]
            },
            3: {
                'title': 'Step 3: Recognize and measure identifiable assets and liabilities; compute goodwill or bargain purchase',
                'focus': 'Recognize identifiable assets and liabilities as of the acquisition date, apply ASC 805 measurement principles and exceptions, then compute goodwill or a bargain purchase gain',
                'key_points': [
                    'Recognize 100% of identifiable assets acquired, liabilities assumed, and any NCI as of the acquisition date (ASC 805-20).',
                    'Measure recognized items at acquisition-date fair value, documenting valuation approaches and key assumptions (ASC 805-20; ASC 820 cross-reference).',
                    'Apply key measurement exceptions to fair value: a. Revenue contracts: measure contract assets and contract liabilities under ASC 606 as if the acquirer originated the contracts at the acquisition date (ASU 2021-08; ASC 805-20/606). b. Leases: apply ASC 842 classification and measurement for lessee and lessor arrangements; do not create separate lessee favorable/unfavorable lease intangibles (ASC 842; ASC 805-20 cross-reference). c. Financial assets: identify purchased financial assets with credit deterioration and apply CECL measurement (ASC 326; ASC 805-20).',
                    'Identify intangible assets that meet separability or contractual-legal criteria and recognize them separately from goodwill; explicitly exclude assembled workforce (ASC 805-20-25/-55).',
                    'Address special intangibles: recognize reacquired rights and amortize over the remaining contractual term (ignore renewals), and capitalize in-process R&D as an indefinite-lived intangible subject to impairment (ASC 805-20; ASC 350).',
                    'Recognize and measure contingencies at acquisition-date fair value when they meet the asset/liability definition; apply ASC 450/460 or other relevant Topics thereafter (ASC 805-20; ASC 450/460).',
                    'Record income tax effects: recognize DTAs/DTLs for basis differences, evaluate uncertain tax positions, and assess valuation allowances (ASC 740).',
                    'Compute goodwill or bargain purchase: Goodwill = FV of consideration transferred + FV of NCI + FV of previously held interest − FV of identifiable net assets; if negative, reassess measurements and recognize a bargain purchase gain with required disclosures if still negative (ASC 805-30).'
                ]
            },
            4: {
                'title': 'Step 4: Record the acquisition, apply the measurement period, and handle subsequent measurement',
                'focus': 'Post acquisition-date entries, manage provisional amounts within the measurement period, and perform required remeasurements',
                'key_points': [
                    'Record acquisition-date journal entries for all recognized items, including goodwill or bargain purchase gain (ASC 805-30).',
                    'Use provisional amounts where initial accounting is incomplete; during the measurement period (up to one year), record retrospective adjustments for acquisition-date facts with corresponding goodwill adjustments and revise comparative periods as required; disclose (ASC 805-10).',
                    'Distinguish measurement period adjustments from normal subsequent changes in estimates or events; retain evidence supporting acquisition-date assumptions (ASC 805-10).',
                    'Remeasure contingent consideration through earnings each period if liability-/derivative-classified; do not remeasure equity-classified arrangements; account for settlements (ASC 805-30-35; ASC 480/815).',
                    'Remeasure indemnification assets consistent with the related indemnified items and assess collectibility (ASC 805-20).',
                    'Apply postcombination accounting under other Topics: amortize finite-lived intangibles and test goodwill/indefinite-lived intangibles for impairment (ASC 350); apply CECL to acquired financial assets (ASC 326); continue lease accounting (ASC 842); address hedge relationships (ASC 815); and account for exit/disposal activities (ASC 420).',
                    'If applicable for acquiree standalone reporting, assess and elect pushdown accounting and provide required disclosures (ASC 805-50).'
                ]
            },
            5: {
                'title': 'Step 5: Prepare required disclosures and the technical memo',
                'focus': 'Provide complete ASC 805 disclosures and document judgments, measurements, and conclusions supporting the acquisition method',
                'key_points': [
                    'Prepare required ASC 805 disclosures: acquisition date and primary reasons; qualitative factors giving rise to goodwill; fair value of consideration by major class; recognized amounts for each major class of assets acquired and liabilities assumed; contingent consideration and indemnification details; acquiree revenue and earnings since acquisition; and pro forma information as if the acquisition occurred at the beginning of the periods presented (ASC 805-10-50; ASC 805-30-50).',
                    'Disclose individually immaterial business combinations that are material in the aggregate (ASC 805-10-50).',
                    'For step acquisitions, disclose the fair value of the previously held interest, the resulting gain or loss recognized, and any related AOCI reclassifications (ASC 805-10; ASC 220).',
                    'For bargain purchases, disclose the amount of the gain and the reasons why the transaction resulted in a gain (ASC 805-30-50).',
                    'Disclose the nature and amounts of measurement period adjustments and, if applicable, that initial accounting is incomplete (ASC 805-10-50).',
                    'For SEC registrants, consider Article 11 pro forma requirements and Regulation S-X Rule 3-05 significance testing (outside ASC 805).',
                    'Draft the technical memo: scope and "business" assessment; acquirer and acquisition date; consideration and items not part of the exchange (including contingent consideration classification and OCI recycling); identification and measurement of assets and liabilities (including exceptions for revenue contracts, leases, CECL PCD, and held-for-sale); intangible assets (including IPR&D and reacquired rights); goodwill/bargain purchase; measurement period plan; and a disclosure checklist (ASC 805-10-50).'
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

**Conclusion:** [Write single paragraph conclusion stating the specific outcome for this step]

END OUTPUT"""

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
    
    def generate_final_conclusion(self, analysis_results: Dict[str, Any]) -> str:
        """Generate LLM-powered final conclusion from analysis results."""
        logger.info("→ Generating final conclusion...")

        # Extract conclusions from each step
        conclusions = []
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            if step_key in analysis_results and analysis_results[step_key].get('conclusion'):
                conclusions.append(f"Step {step_num}: {analysis_results[step_key]['conclusion']}")

        # Build prompt
        conclusions_text = "\n".join(conclusions)
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