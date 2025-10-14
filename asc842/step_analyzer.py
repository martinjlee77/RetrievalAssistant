"""
ASC 842 Step Analyzer

This module handles the 5-step ASC 842 lease accounting analysis.
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

class ASC842StepAnalyzer:
    """
    Simplified ASC 842 step-by-step analyzer using natural language output.
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
        """Extract the lessee or tenant name using LLM analysis."""
        try:
            logger.info("🏢 Extracting lessee/tenant name from lease agreement...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying entity names in lease agreements. Your task is to identify the name of the lessee or tenant from the lease document."
                },
                {
                    "role": "user",
                    "content": f"""Based on this lease agreement, what is the name of the lessee or tenant?

Please identify:
- The entity that is leasing or renting the space and NOT THE LANDLORD OR LESSOR
- The full name including suffixes like Inc., LLC, Corp., etc.
- Ignore addresses, reference numbers, or other non-entity identifiers

Lease Agreement Text:
{contract_text[:4000]}

Respond with ONLY the entity name, nothing else."""
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
                logger.warning("LLM returned None for entity name")
                return "Entity"
                
            # Clean the response (remove quotes, extra whitespace)
            entity_name = entity_name.strip().strip('"').strip("'").strip()
            
            # Validate the result
            if len(entity_name) < 2 or len(entity_name) > 120:
                logger.warning(f"LLM returned suspicious entity name: {entity_name}")
                return "Entity"
            
            logger.info(f"✓ Lessee/tenant identified: {entity_name}")
            return entity_name
            
        except Exception as e:
            logger.error(f"Error extracting entity name with LLM: {str(e)}")
            return "Entity"
    
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
    
    def analyze_lease_contract(self, 
                        contract_text: str,
                        authoritative_context: str,
                        entity_name: str,
                        analysis_title: str,
                        additional_context: str = "") -> Dict[str, Any]:
        """
        Perform complete 5-step ASC 842 analysis.
        
        Args:
            contract_text: The lease contract document text
            authoritative_context: Retrieved ASC 842 guidance
            entity_name: Entity name
            analysis_title: Analysis title
            additional_context: Optional user-provided context
            
        Returns:
            Dictionary containing analysis results for each step
        """
        analysis_start_time = time.time()
        logger.info(f"Starting ASC 842 analysis for {entity_name}")
        
        # Add large contract warning
        word_count = len(contract_text.split())
        if word_count > 50000:
            logger.warning(f"Large contract ({word_count} words). Consider splitting if analysis fails.")
        
        results = {
            'customer_name': entity_name,
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
        logger.info(f"✓ ASC 842 analysis completed successfully in {total_time:.1f}s")
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
        """Analyze a single ASC 842 step - returns clean markdown."""
        
        # Log financial calculations for Step 3 (Measurement/ROU asset and lease liability)
        if step_num == 3:
            logger.info("💰 Extracting lease payment schedule and performing NPV calculations...")
        
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
            logger.info(f"DEBUG: Clean markdown for Step {step_num} (length: {len(markdown_content)}) sample: {markdown_content[:100]}...")
            
            # Return clean markdown content - NO PROCESSING
            return {
                'title': self._get_step_title(step_num),
                'markdown_content': markdown_content,
                'step_num': str(step_num)
            }
            
        except Exception as e:
            # Let exceptions propagate to retry logic in _analyze_step_with_retry
            raise
    
    def _get_markdown_system_prompt(self) -> str:
        """Get the system prompt for markdown generation."""
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 842 lease accounting. 

Generate professional accounting analysis in clean markdown format. Your output will be displayed directly using markdown rendering.

Your analysis must be:
- Audit-ready and professional
- Clear and understandable
- Based on the evidence provided in the lease contract text
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
- Support your analysis with specific contract text and authoritative citations
- Use direct quotes from the lease contract only when the exact wording is outcome-determinative
- Paraphrase ASC 842 with pinpoint citations; brief decisive phrases may be quoted when directly supportive
- Flag missing data as "Not specified" or create management input placeholders for external judgments
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
        
        # Define step information based on ASC 842 methodology provided
        step_info = {
            1: {
                'title': 'Step 1: Scope, identify a lease, and determine the enforceable period and lease term',
                'focus': 'Confirm the arrangement is (or contains) a lease and establish the enforceable period and lease term',
                'key_points': [
                    'Confirm lease definition: right to control use of identified asset for a period in exchange for consideration. Check scope exclusions (intangibles, biologicals, inventory). [ASC 842-10-15-2, 15-3, 15-9 to 15-16]',
                    'Identify the asset: If supplier has substantive substitution rights → asset not identified. [ASC 842-10-15-9 to 15-14]',
                    'Determine enforceable period: Contract enforceable until both parties can terminate without more than insignificant penalty. [Master Glossary: Enforceable]',
                    'Determine lease term within enforceable period: Noncancellable period + extension options (if reasonably certain to exercise) + lessor-controlled periods. For lessee-only termination rights → treat as termination option. [ASC 842-10-35-1 to 35-3; 842-10-55-23 to 55-26]',
                    'Note reassessment triggers: Significant event/change in circumstances within control of the lessee affecting option assessments. [ASC 842-10-35-1 to 35-3]'
                ]
            },
            2: {
                'title': 'Step 2: Identify components and determine lease payments',
                'focus': 'Separate lease vs nonlease components (or elect not to separate) and determine payments included in the lease liability',
                'key_points': [
                    'Identify lease components (right to use each asset) vs nonlease components (services, CAM). Note: administrative tasks are not components. [ASC 842-10-15-28 to 15-31]',
                    'Note practical expedient election: By asset class, lessee may elect not to separate nonlease components → account as single lease component. Flag as [Management Input Required: Non-separation expedient election by asset class per ASC 842-10-15-37]. [ASC 842-10-15-37 to 15-38]',
                    'Determine lease payments to include: Fixed (including in-substance fixed), index/rate-based variable (at commencement index/rate), RVG amounts (if probable), purchase option (if reasonably certain), termination penalties (per lease term assessment), less lease incentives receivable. [ASC 842-20-30-5]',
                    'Exclude usage/performance-based variable payments → expense as incurred. [ASC 842-20-25]'
                ]
            },
            3: {
                'title': 'Step 3: Classify the lease and measure at commencement',
                'focus': 'Classify the lease (finance vs operating) and identify measurement requirements for initial recognition',
                'key_points': [
                    'Classify as finance or operating: Finance if any criteria met (ownership transfer, purchase option reasonably certain, lease term = major part of economic life, PV = substantially all FV, or no alternative use to lessor). Otherwise → operating. Not reassessed post-commencement except for modifications. [ASC 842-10-25-2, 25-8]',
                    'Determine commencement date (asset available for use) → measure and recognize at that date. [ASC 842-10-55]',
                    'Measure lease liability: PV of lease payments using discount rate. Flag as [Management Input Required: Incremental borrowing rate or rate implicit in lease per ASC 842-20-30-3]. [ASC 842-20-30-5]',
                    'Measure ROU asset: Lease liability + prepaid + initial direct costs (narrowly defined: incremental costs) – lease incentives + AROs (if any). [ASC 842-20-25-1; 842-20-30-1; ASC 410]',
                    'Note short-term lease policy election (if applicable): ≤12 months, no purchase option → expense straight-line, no ROU/liability. Flag policy election as management input. [ASC 842-20-25-2]'
                ]
            },
            4: {
                'title': 'Step 4: Produce initial accounting outputs',
                'focus': 'Document and output the initial recognition, classification, calculations, and required notes',
                'key_points': [
                    'State classification conclusion (finance/operating) with rationale and citations. [ASC 842-10-25-2]',
                    'Detail lease payments by category and show PV calculation. [ASC 842-20-30-5]',
                    'Provide commencement-date journal entries: ROU asset, lease liability, prepaid/incentives/IDC effects. [ASC 842-20-25-1; 842-20-30-1]',
                    'Flag policy elections and significant judgments for disclosure: short-term expedient, non-separation expedient, "reasonably certain" assessments. [ASC 842-20-45-1; 842-20-50-1]'
                ]
            },
            5: {
                'title': 'Step 5: Reminders beyond initial recognition (no computations)',
                'focus': 'Keep in view subsequent accounting, remeasurement triggers, modifications, subleases, and disclosures for later periods',
                'key_points': [
                    'Note subsequent accounting pattern: Finance → interest + ROU amortization. Operating → single straight-line lease cost. Variable payments (excluded from liability) → expense as incurred. [ASC 842-20-25; 842-10-55-229]',
                    'Remeasurement triggers: Lease term/purchase option change, RVG amount change, contingency resolution making payments fixed, non-separate modifications. Note: index/rate changes → expensed as variable cost (no remeasurement unless another trigger occurs). [ASC 842-10-35-1 to 35-3; 842-10-25-8 to 25-10]',
                    'For modifications: Assess if separate contract. If not → remeasure, reallocate, reassess classification. [ASC 842-10-25-8 to 25-10]',
                    'For subleases: Intermediate lessor created. Classify sublease by reference to head-lease ROU asset. Derecognize head lease only upon legal release. [ASC 842-10; 842-20-40]',
                    'Note presentation/disclosure requirements: Operating vs finance separation, maturity analysis, lease cost components, significant judgments. [ASC 842-20-45-1; 842-20-50-1]'
                ]
            }
        }
        
        step = step_info[step_num]
        
        prompt = f"""
STEP {step_num}: {step['title'].upper()}

OBJECTIVE: {step['focus']}

LEASE CONTRACT INFORMATION:
Contract Analysis: Analyze the lease contract from the lessee perspective for the entity {entity_name} to determine the appropriate lease accounting treatment under ASC 842.

Instructions: Analyze this lease contract from the lessee's perspective. The entity is the lessee receiving the right to use the underlying asset.

LEASE CONTRACT TEXT:
{contract_text}"""

        if additional_context.strip():
            prompt += f"""

ADDITIONAL CONTEXT:
{additional_context}"""


        prompt += f"""

AUTHORITATIVE GUIDANCE:
{authoritative_context}

ANALYSIS REQUIRED:
Analyze the lease contract for Step {step_num} focusing on:
{chr(10).join([f"• {point}" for point in step['key_points']])}

REQUIRED OUTPUT FORMAT (Clean Markdown):

### {step['title']}

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific contract evidence and ASC 842 citations. Quote contract language only when the exact wording is outcome‑determinative; paraphrase ASC 842 with pinpoint citations and use only brief decisive phrases when directly supportive.]

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed citations)
- Contract citations must reference actual text from the document:
    Good: [Lease Agreement, Lease Terms clause], [Lease Agreement, 'payment schedule']
    Bad: [Lease Agreement, §4.2], [Lease Agreement, p. 15] (unless these exact references appear in the contract text)
- ASC 842 guidance paraphrased with citations; include only brief decisive phrases when directly supportive (e.g., [ASC 842-10-25-2])
- Only cite section numbers/page numbers if they are explicitly visible in the contract text

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 842 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

CRITICAL ANALYSIS REQUIREMENTS - CONTRACT VS EXTERNAL DATA:

1. CONTRACT FACTS (dates, terms, amounts explicitly in the document):
   - If present: Quote or paraphrase with citation
   - If missing: State "Not specified in contract"
   - NEVER invent or guess these

2. EXTERNAL INPUTS (accounting policies, valuations, judgments NOT in contract):
   - Always state the ASC 842 requirement
   - Create management placeholder: "[Management Input Required: Specify IBR per ASC 842-20-30-3]"
   - Examples: discount rate, practical expedient elections, "reasonably certain" assessments

3. CITATION RULES:
   - Contract: Only cite what's visible - [Lease Agreement, Payment Terms] ✓  |  [Lease §3.1] ✗ (unless §3.1 appears)
   - ASC 842: Paraphrase + pinpoint cite - [ASC 842-10-25-2]

Use assertive language ("We conclude...") when evidence supports it; flag gaps explicitly.

FORMATTING:
- Format currency as: $240,000 (with comma, no spaces)
- Use proper spacing after periods and commas
- Use professional accounting language
- Double-check all currency amounts for correct formatting

"""
        
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
        """Get the title for a step."""
        titles = {
            1: "Step 1: Scope, identify a lease, and determine the enforceable period and lease term",
            2: "Step 2: Identify components and determine lease payments", 
            3: "Step 3: Classify the lease and measure at commencement",
            4: "Step 4: Produce initial accounting outputs",
            5: "Step 5: Reminders beyond initial recognition"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    def _extract_conclusions_from_steps(self, steps_data: Dict[str, Any]) -> str:
        """Extract conclusion text from all completed steps."""
        conclusions = []
        logger.info(f"Extracting conclusions from {len(steps_data)} steps")
        logger.info(f"DEBUG: steps_data keys: {list(steps_data.keys())}")
        
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            if step_key in steps_data:
                step_data = steps_data[step_key]
                if isinstance(step_data, dict) and 'markdown_content' in step_data:
                    # Extract conclusion from markdown content
                    markdown_content = step_data['markdown_content']
                    
                    # Look for conclusion section in markdown - try markers first, then improved regex
                    import re
                    
                    # Try markers first ([BEGIN_CONCLUSION]...[END_CONCLUSION])
                    marker_match = re.search(r'\[BEGIN_CONCLUSION\](.*?)\[END_CONCLUSION\]', markdown_content, re.DOTALL)
                    if marker_match:
                        conclusion_text = marker_match.group(1).strip()
                        conclusions.append(f"Step {step_num}: {conclusion_text}")
                        logger.info(f"DEBUG: Extracted conclusion for step {step_num}: {conclusion_text[:100]}...")
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
                            conclusion_text = conclusion_match.group(1).strip()
                            conclusions.append(f"Step {step_num}: {conclusion_text}")
                            logger.info(f"DEBUG: Extracted conclusion for step {step_num}: {conclusion_text[:100]}...")
                        else:
                            logger.warning(f"DEBUG: No conclusion found in step {step_num} markdown")
                else:
                    logger.warning(f"DEBUG: Step {step_num} missing markdown_content")
        
        combined_conclusions = "\n\n".join(conclusions)
        logger.info(f"DEBUG: Combined conclusions length: {len(combined_conclusions)}")
        return combined_conclusions
    
    def generate_executive_summary(self, conclusions_text: str, entity_name: str) -> str:
        """Generate executive summary based on step conclusions."""
        logger.info("→ Generating executive summary...")
        
        try:
            request_params = {
                "model": self.light_model,  # Use light model for summary
                "messages": [
                    {
                        "role": "system",
                        "content": "You are generating an executive summary for an ASC 842 lease accounting memorandum. Create a concise, professional summary that captures the key findings and conclusions from the 5-step analysis."
                    },
                    {
                        "role": "user",
                        "content": f"""Based on the following step-by-step analysis conclusions, generate a professional executive summary for an ASC 842 lease accounting memorandum for {entity_name}.

This is a document-only analysis where reasonable assumptions were made for missing data.

Step Conclusions:
{conclusions_text}

Write a concise executive summary (2-3 paragraphs) that:
1. States the overall conclusion about the lease arrangement
2. Highlights the key classification and measurement determinations
3. Notes any significant judgments or policy elections
4. Is suitable for senior management review

Format as clean markdown."""
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
                summary = "Executive summary could not be generated."
            
            summary = summary.strip()
            logger.info(f"✓ Executive summary generated ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return f"Error generating executive summary: {str(e)}"
    
    def generate_background_section(self, conclusions_text: str, entity_name: str) -> str:
        """Generate background section for the memo."""
        logger.info("→ Generating background section...")
        
        try:
            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are generating a background section for an ASC 842 lease accounting memorandum. Create a professional background that sets the context for the analysis."
                    },
                    {
                        "role": "user",
                        "content": f"""Generate a professional background section for an ASC 842 lease accounting memorandum for {entity_name}.

Context:
- Entity: {entity_name}
- Analysis Date: {datetime.now().strftime('%B %Y')}
- Analysis Type: Document-only preliminary analysis
- Approach: Reasonable assumptions made for missing data

Write a brief background section (1 paragraph) that:
1. States the purpose of the memorandum
2. Describes the lease arrangement being analyzed
3. References the ASC 842 methodology being applied
4. Notes that this is a preliminary analysis with reasonable assumptions

Format as clean markdown."""
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
                background = f"We have reviewed the lease agreement for {entity_name} to determine the appropriate accounting treatment under ASC 842."
            
            background = background.strip()
            logger.info(f"✓ Background section generated ({len(background)} chars)")
            return background
            
        except Exception as e:
            logger.error(f"Error generating background section: {str(e)}")
            return f"We have reviewed the lease agreement for {entity_name} to determine the appropriate accounting treatment under ASC 842. This memorandum presents our analysis following the five-step ASC 842 methodology."
    
    def generate_final_conclusion(self, analysis_results: Dict[str, Any]) -> str:
        """Generate LLM-powered final conclusion from analysis results."""
        logger.info("→ Generating final conclusion...")

        # Extract conclusions from markdown content using the proper extraction method
        conclusions_text = self._extract_conclusions_from_steps(analysis_results)
        prompt = f"""Generate a professional final conclusion for an ASC 842 analysis.

    Step Conclusions:
    {conclusions_text}

    Instructions:
    1. Write 2-3 sentences in narrative paragraph format assessing ASC 842 compliance
    2. Format all currency as $XXX,XXX (no spaces in numbers)
    3. Base your conclusion ONLY on the actual findings from the step conclusions provided above
    4. Only mention concerns if they are explicitly identified in the step analysis - do not invent or infer new issues
    5. If no significant issues are found in the steps, state compliance with ASC 842
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
                        "content": "You are an expert technical accountant specializing in ASC 842 lease accounting."
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
            return "Based on our comprehensive analysis under ASC 842, the proposed lease accounting treatment is appropriate and complies with the authoritative guidance."
    
    def _load_step_prompts(self):
        """Load step prompts - placeholder for future use."""
        return {}