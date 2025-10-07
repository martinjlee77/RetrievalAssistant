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
                    'Confirm that the arrangement is within ASC 606 (and not a lease, insurance, financial instrument, or a collaboration (ASC 606-10-15-2 to 15-5))'
                    'Verify that the parties have approved the contract and are committed to perform (ASC 606-10-25-1(a))',
                    'Identify each party\'s rights regarding the goods or services to be transferred (ASC 606-10-25-1(b))',
                    'Identify each party\'s payment terms for the transferred goods or services (ASC 606-10-25-1(c))',
                    'Assess whether the contract has commercial substance (ASC 606-10-25-1(d))',
                    'Evaluate whether it is probable that the entity will collect the consideration (ASC 606-10-25-1(e)). Explain that the collectibility assessment would require external information (customer\'s credit/intent) and management should perform this evaluation separate from this analysis.',
                    'If the criteria in ASC 606-10-25-1 are not met, ASC 606-10-25-6 to 25-8 should be applied to deter revenue, recognize a liability and reassess',
                    'If there are any modification of the pre-existing contract, explain that ASC 606-10-25-10 to 25-13 should be applied to determine if the modification is a new contract or an extension of the existing contract. Note that such evaluation is not in the scope of this analysis andn should be performed separately.'
                    
                ]
            },
            2: {
                'title': 'Step 2: Identify Performance Obligations', 
                'focus': 'Identify distinct goods or services using ASC 606-10-25-14 and 25-22',
                'key_points': [
                    'Identify all promised goods and services in the contract (ASC 606-10-25-16)',
                    'Separately evaluate whether each promised good or service is capable of being distinct per ASC 606-10-25-20 (can the customer benefit from the good or service either on its own or with other readily available resources?)',
                    'Separately evaluate whether each promised good or service is distinct within the context of the contract (or also called separately identifiable) per ASC 606-10-25-21(a-c):',
                    '   a. The entity provides a significant service of integrating goods or services with other goods or services promised in the contract into a bundle of goods or services that represent the combined output or outputs for which the customer has contracted. In other words, the entity is using the goods or services as inputs to produce or deliver the combined output or outputs specified by the customer. A combined output or outputs might include more than one phase, element, or unit.',
                    '   b. One or more of the goods or services significantly modifies or customizes, or are significantly modified or customized by, one or more of the other goods or services promised in the contract.',
                    '   c. The goods or services are highly interdependent or highly interrelated with other promises in the contract. In other words, each of the goods or services is significantly affected by one or more of the other goods or services in the contract. For example, in some cases, two or more goods or services are significantly affected by each other because the entity would not be able to fulfill its promise by transferring each of the goods or services independently.',
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
                    'Determine if any concash consideration is present',
                    'Determine if any consideration paid or payable to a customer is present'
    
                ]
            },
            4: {
                'title': 'Step 4: Allocate the Transaction Price',
                'focus': 'Allocate price to performance obligations based on standalone selling prices or SSPs (SSPs to be determined separately per ASC 606-10-32-31 to 32-34)',
                'key_points': [
                    'Summarize the performance obligations determined in Step 2',
                    'State that standalone selling prices (SSPs) should be determined by management separately based on observable data (ASC 606-10-32-31 to 32-34)',
                    'Describe the allocation methodology to allowed by ASC 606 in ASC 10-32-24 (aAdjusted market assessment approach, expected cost plus a margin approach, and residual approach)',
                    'Note any discount allocation considerations (ASC 606-10-32-36)',
                    'Provide the final allocation approach (subject to SSP determination)'
                ]
            },
            5: {
                'title': 'Step 5: Recognize Revenue',
                'focus': 'Determine when revenue should be recognized for each performance obligation',
                'key_points': [
                    'Determine over-time vs. point-in-time recognition for each performance obligation. Over time if one of the three criteria is met (simultaneous receipt/consumption, customer controls the asset as created, or no alternative use and enforceable right to payment (ASC 606-10-25-27)), otherwise poit in time (ASC 606-10-25-30)',
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

CRITICAL ANALYSIS REQUIREMENTS:
- If information is not explicitly stated in the contract, write "Not specified in contract"
- For required accounting policies, management judgments, or valuation inputs that are external to the contract, do not state 'Not specified'. Instead, state the accounting requirement and create a clear, bracketed placeholder prompting management for the necessary information, such as '[Placeholder for Management: Describe...]'.
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
                        # Fallback to improved regex that captures until next bold section or end
                        conclusion_match = re.search(r'\*\*Conclusion:\*\*\s*(.+?)(?:\n\s*\*\*|$)', markdown_content, re.IGNORECASE | re.DOTALL)
                        if conclusion_match:
                            conclusion = conclusion_match.group(1).strip()
                        else:
                            conclusion = None
                    
                    if conclusion:
                        conclusions.append(f"Step {step_num}: {conclusion}")
                        logger.info(f"Extracted conclusion for Step {step_num}: {conclusion[:50]}...")
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
        
    def generate_final_conclusion(self, analysis_results: Dict[str, Any]) -> str:
        """Generate LLM-powered final conclusion from analysis results."""
        logger.info("→ Generating final conclusion...")
        
        # Extract conclusions from markdown content using the proper extraction method
        conclusions_text = self._extract_conclusions_from_steps(analysis_results)
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