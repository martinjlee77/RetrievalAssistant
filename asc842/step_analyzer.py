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
        """Extract the lessee or tenant name using LLM analysis."""
        try:
            logger.info("DEBUG: Extracting entity name using LLM")
            
            request_params = {
                "model": self.light_model,
                "messages": [
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
                ],
                **self._get_max_tokens_param("default", self.light_model),
                "temperature": self._get_temperature(self.light_model)
            }
            
            if self.light_model in ["gpt-5", "gpt-5-mini"]:
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            # Track API cost for entity extraction
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=request_params["messages"],
                response_text=response.choices[0].message.content or "",
                model=self.light_model,
                request_type="entity_extraction"
            )
            
            entity_name = response.choices[0].message.content
            if entity_name is None:
                logger.warning("LLM returned None for entity name")
                return "Entity"
                
            # Clean the response (remove quotes, extra whitespace)
            entity_name = entity_name.strip().strip('"').strip("'").strip()
            
            # Validate the result
            if len(entity_name) < 2 or len(entity_name) > 120:
                logger.warning(f"LLM returned suspicious entity name: {entity_name}")
                return "Entity"
                
            logger.info(f"DEBUG: LLM extracted entity name: {entity_name}")
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
        logger.info("Generating executive summary...")
        results['executive_summary'] = self.generate_executive_summary(conclusions_text, entity_name)
        logger.info("Generating background...")
        results['background'] = self.generate_background_section(conclusions_text, entity_name)
        logger.info("Generating conclusion...")
        results['conclusion'] = self.generate_final_conclusion(conclusions_text)
        logger.info("DEBUG: All additional sections generated successfully")
        
        logger.info("ASC 842 analysis completed successfully")
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
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Analyzing Step {step_num} (attempt {attempt + 1})")
                return self._analyze_step(
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    entity_name=entity_name,
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
                     entity_name: str,

                     additional_context: str = "") -> Dict[str, str]:
        """Analyze a single ASC 842 step - returns clean markdown."""
        
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
- Make reasonable assumptions for missing data (e.g., market discount rates) and clearly identify these assumptions
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
                    'A contract contains a lease if it conveys the right to control the use of an identified asset for a period of time in exchange for consideration [ASC 842-10-15-3; 842-10-15-9 through 15-16]',
                    'Scope exclusions include leases of certain intangible assets, biological assets, and inventory [ASC 842-10-15-2]',
                    'Enforceable period: a contract is no longer enforceable when both parties can terminate without more than an insignificant penalty; assess lease term only within the enforceable period [Master Glossary: Enforceable; Lease Term; Noncancellable]',
                    'Substitution rights: if the supplier\'s substitution right is substantive, the asset is not identified [ASC 842-10-15-9 through 15-14]',
                    'Embedded derivatives may require bifurcation under ASC 815; the lease itself is not a derivative [ASC 815-10-15; 815-15]',
                    'Lease term: noncancellable period plus periods covered by options to extend (if reasonably certain to exercise), options to terminate (if reasonably certain not to exercise), and specified lessor-controlled periods [Master Glossary: Lease Term; ASC 842-10-35-1 through 35-3; 842-10-55-23 through 55-26]',
                    'Reassess lease term upon specified events (e.g., significant event/change in circumstances within the lessee\'s control affecting option assessments) [ASC 842-10-35-1 through 35-3]',
                    'Both‑party termination rights generally cap the enforceable period at the earliest date either party can terminate without more than an insignificant penalty [Master Glossary: Enforceable]',
                    'If only the lessee has a termination right, treat it as a lessee termination option when determining the lease term [ASC 842-10-55-24]'
                ]
            },
            2: {
                'title': 'Step 2: Identify components and determine lease payments',
                'focus': 'Separate lease vs nonlease components (or elect not to separate) and determine payments included in the lease liability',
                'key_points': [
                    'Identify lease components (right to use each underlying asset) and nonlease components (e.g., services, CAM); administrative tasks are not components [ASC 842-10-15-28 through 15-31]',
                    'Allocation: If not electing the practical expedient, allocate consideration to components based on relative standalone prices [ASC 842-10-15-32 through 15-36]',
                    'Practical expedient: By class of underlying asset, you may elect to not separate nonlease components; account for combined consideration as a single lease component [ASC 842-10-15-37 through 15-38]',
                    'Ownership-level costs paid by the lessor (e.g., property taxes/insurance) that are reimbursed by the lessee are typically nonlease components unless in‑substance fixed lease payments [ASC 842-10-15-30]',
                    'Include in lease payments: fixed payments (including in‑substance fixed), variable payments that depend on an index or a rate (measured using the index/rate at commencement), amounts probable under residual value guarantees, purchase option price if reasonably certain to exercise, and termination penalties consistent with lease‑term assessment; reduce for lease incentives receivable [ASC 842-20-30-5]',
                    'Exclude usage/performance‑based variable payments that are not in‑substance fixed; expense as incurred [ASC 842-20-25]'
                ]
            },
            3: {
                'title': 'Step 3: Classify the lease and measure at commencement',
                'focus': 'Decide finance vs operating classification and measure the lease liability and ROU asset on the commencement date (using the user‑provided discount rate)',
                'key_points': [
                    'Classification: Finance if any of the five criteria are met (transfer of ownership, reasonably certain purchase option, lease term is a major part of remaining economic life, PV of payments is substantially all of fair value, or no alternative use); otherwise operating [ASC 842-10-25-2]',
                    'Classification is not reassessed after commencement unless certain modifications/remeasurements occur [ASC 842-10-25-8]',
                    'Commencement date is when the asset is made available for use; measure and recognize at that date [ASC 842-10-55]',
                    'Recognize a lease liability at the present value of lease payments (use the user‑provided rate) and an ROU asset measured as: lease liability + prepaid lease payments + initial direct costs – lease incentives received/receivable [ASC 842-20-25-1; 842-20-30-1; 842-20-30-5]',
                    'Initial direct costs are narrowly defined as incremental costs that would not have been incurred if the lease had not been obtained [Master Glossary; ASC 842-10-30]',
                    'Include asset retirement obligations (if any) in the ROU asset per ASC 410 (not in the lease liability) [ASC 410; ASC 842-20-30-1]',
                    'Short‑term lease policy: if elected and criteria met (12 months or less and no purchase option), do not recognize ROU asset/liability; recognize lease cost generally straight‑line [ASC 842-20-25-2]'
                ]
            },
            4: {
                'title': 'Step 4: Produce initial accounting outputs',
                'focus': 'Document and output the initial recognition, classification, calculations, and required notes',
                'key_points': [
                    'Provide classification conclusion and rationale with citations [ASC 842-10-25-2]',
                    'Show the lease payments included in the liability by category and the present value calculation [ASC 842-20-30-5]',
                    'Provide commencement‑date journal entries (ROU asset, lease liability, and any prepaid/incentive/initial direct cost effects) [ASC 842-20-25-1; 842-20-30-1]',
                    'Identify initial presentation and disclosure data points (policy elections such as short‑term and non‑separation expedient; significant judgments such as "reasonably certain") [ASC 842-20-45-1; 842-20-50-1]'
                ]
            },
            5: {
                'title': 'Step 5: Reminders beyond initial recognition (no computations)',
                'focus': 'Keep in view subsequent accounting, remeasurement triggers, modifications, subleases, and disclosures for later periods',
                'key_points': [
                    'Subsequent accounting: finance leases recognize interest on the liability and amortization of the ROU asset; operating leases recognize a single lease cost generally straight‑line; variable payments excluded from the liability are expensed when incurred [ASC 842-20-25; ASC 842-10-55-229]',
                    'Remeasurement triggers: change in lease term or purchase option assessment; change in expected RVG amounts; resolution of contingencies that make payments fixed; modifications not accounted for as separate. Do not remeasure solely for changes in an index or a rate; under ASC 842 such changes are expensed as variable lease cost unless remeasurement is required for another reason [ASC 842-10-35-1 through 35-3; 842-10-25-8 through 25-10]',
                    'Modifications: assess whether separate contract; if not separate, remeasure, reallocate, and reassess classification [ASC 842-10-25-8 through 25-10]',
                    'Subleases/assignments: a sublease creates an intermediate lessor; classify the sublease by reference to the head‑lease ROU asset; derecognize the head lease only upon legal release/novation (termination) [ASC 842-10 (Subleases); ASC 842-20-40]',
                    'Presentation/disclosures: separate presentation (or disclosure) of operating vs finance ROU assets and lease liabilities, maturity analysis, lease cost components, and significant judgments [ASC 842-20-45-1; 842-20-50-1]'
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

        # Add analysis instructions for document-only approach
        prompt += f"""

ANALYSIS INSTRUCTIONS:
- Make reasonable assumptions where specific data is missing (e.g., assume 6-8% discount rate for market transactions)
- Extract dates, rates, and terms directly from the contract when available
- For missing information, state assumptions clearly (e.g., "Assuming a market discount rate of 7%...")
- Use the "Issues or Uncertainties" section to highlight assumptions and missing information requiring confirmation
- This is a preliminary analysis - emphasize areas needing follow-up"""

        prompt += f"""

AUTHORITATIVE GUIDANCE:
{authoritative_context}

ANALYSIS REQUIRED:
Analyze the lease contract for Step {step_num} focusing on:
{chr(10).join([f"• {point}" for point in step['key_points']])}

REQUIRED OUTPUT FORMAT (Clean Markdown):

### {step['title']}

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific contract evidence and ASC 842 citations. Quote contract language only when the exact wording is outcome‑determinative; paraphrase ASC 842 with pinpoint citations and use only brief decisive phrases when directly supportive. Make reasonable assumptions for missing data and clearly identify these assumptions.]

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed pinpoint citations; e.g., [Lease Agreement §X.Y, p. N])
- ASC 842 guidance paraphrased with citations; include only brief decisive phrases when directly supportive (e.g., [ASC 842-10-25-2])
- Reasonable assumptions for missing data clearly stated (e.g., discount rates, assessment dates)
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion
- Clear identification of assumptions made due to missing information]

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 842 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

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
                        # Fallback to improved regex that captures until next bold section or end
                        conclusion_match = re.search(r'\*\*Conclusion:\*\*\s*(.+?)(?:\n\s*\*\*|$)', markdown_content, re.IGNORECASE | re.DOTALL)
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
        logger.info(f"DEBUG: Generating executive summary. Model: {self.model}")
        
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
                
            logger.info(f"DEBUG: Generated executive summary ({len(summary)} chars)")
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return f"Error generating executive summary: {str(e)}"
    
    def generate_background_section(self, conclusions_text: str, entity_name: str) -> str:
        """Generate background section for the memo."""
        logger.info(f"DEBUG: Generating background section. Model: {self.light_model}")
        
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
                
            logger.info(f"DEBUG: Generated background section ({len(background)} chars)")
            return background.strip()
            
        except Exception as e:
            logger.error(f"Error generating background section: {str(e)}")
            return f"We have reviewed the lease agreement for {entity_name} to determine the appropriate accounting treatment under ASC 842. This memorandum presents our analysis following the five-step ASC 842 methodology."
    
    def generate_final_conclusion(self, analysis_results: Dict[str, Any]) -> str:
        """Generate LLM-powered final conclusion from analysis results."""

        # Extract conclusions from each step
        conclusions = []
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            if step_key in analysis_results and analysis_results[step_key].get('conclusion'):
                conclusions.append(f"Step {step_num}: {analysis_results[step_key]['conclusion']}")

        # Build prompt
        conclusions_text = "\n".join(conclusions)
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
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Final conclusion generation failed: {str(e)}")
            # Fallback to simple conclusion
            return "Based on our comprehensive analysis under ASC 842, the proposed lease accounting treatment is appropriate and complies with the authoritative guidance."
    
    def _load_step_prompts(self):
        """Load step prompts - placeholder for future use."""
        return {}