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
        """Extract the customer entity name using LLM analysis."""
        try:
            logger.info("DEBUG: Extracting customer entity name using LLM")
            
            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at identifying customer names in revenue contracts. Your task is to identify the name of the customer company from the contract document."
                    },
                    {
                        "role": "user",
                        "content": f"""Based on this revenue contract, what is the name of the customer company?

Please identify:
- The company that is purchasing goods or services (the customer, not the vendor)
- The name including suffixes like Inc., LLC, Corp., etc.
- Ignore addresses, reference numbers, or other non-company identifiers

Contract Text:
{contract_text[:4000]}

Respond with ONLY the customer name, nothing else."""
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
                logger.warning(f"LLM returned suspicious customer name: {entity_name}")
                return "Customer"
                
            logger.info(f"DEBUG: LLM extracted customer name: {entity_name}")
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
                    'Verify that the parties have approved the contract and are committed to perform (ASC 606-10-25-1(a))',
                    'Identify each party\'s rights regarding the goods or services to be transferred (ASC 606-10-25-1(b))',
                    'Identify each party\'s payment terms for the transferred goods or services (ASC 606-10-25-1(c))',
                    'Assess whether the contract has commercial substance (ASC 606-10-25-1(d))',
                    'Evaluate whether it is probable that the entity will collect the consideration (ASC 606-10-25-1(e))'
                ]
            },
            2: {
                'title': 'Step 2: Identify Performance Obligations', 
                'focus': 'Identify distinct goods or services using ASC 606-10-25-14 and 25-22',
                'key_points': [
                    'Identify all promised goods and services in the contract (ASC 606-10-25-16)',
                    'Evaluate whether each promised good or service is capable of being distinct per ASC 606-10-25-20 (can the customer benefit from the good or service either on its own or with other readily available resources?)',
                    'Evaluate whether each promised good or service is distinct within the context of the contract per ASC 606-10-25-21(a-c):',
                    '   a. The good or service is regularly sold separately',
                    '   b. The customer can benefit from the good or service on its own or with other readily available resources',
                    '   c. The good or service is not highly interdependent with other promises in the contract',
                    'Combine non-distinct goods/services into single performance obligations (ASC 606-10-25-22)',
                    'Determine final list of performance obligations',
                    'Consider principal vs. agent determination if third parties are involved (ASC 606-10-25-75 to 25-79)',
                    'Identify any customer options for additional goods/services or material rights (ASC 606-10-25-20)'
                ]
            },
            3: {
                'title': 'Step 3: Determine the Transaction Price',
                'focus': 'Establish the transaction price per ASC 606-10-32-2',
                'key_points': [
                    'Fixed consideration amounts',
                    'Variable consideration amounts (ASC 606-10-32-5 to 32-10)',
                    'Constraints on variable consideration require separate management evaluation per ASC 606-10-32-11 to 32-14',
                    'Total transaction price calculation',
                    'Significant financing components (if present)',
                    'Noncash consideration (if present)',
                    'Consideration paid or payable to a customer (if present)'
                ]
            },
            4: {
                'title': 'Step 4: Allocate the Transaction Price',
                'focus': 'Allocate price to performance obligations based on standalone selling prices (SSPs to be determined separately per ASC 606-10-32-31 to 32-34)',
                'key_points': [
                    'Summarize Identify the performance obligations determined in Step 2',
                    'State that standalone selling prices (SSPs) should be determined separately based on observable data (ASC 606-10-32-31 to 32-34)',
                    'Describe the allocation methodology to be used (proportional to SSPs)',
                    'Note any discount allocation considerations (ASC 606-10-32-36)',
                    'Provide the final allocation approach (subject to SSP determination)'
                ]
            },
            5: {
                'title': 'Step 5: Recognize Revenue',
                'focus': 'Determine when revenue should be recognized for each performance obligation',
                'key_points': [
                    'Determine over-time vs. point-in-time recognition for each performance obligation',
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
Contract Analysis: Analyze the contract with the customer {customer_name} to determine the appropriate revenue recognition treatment under ASC 606 for the company.

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

**Conclusion:** [Write single paragraph conclusion stating the specific outcome for this step]

END OUTPUT"""

        return prompt
    
    def _get_step_title(self, step_num: int) -> str:
        """Get the title for a specific step."""
        titles = {
            1: "Step 1: Identify the Contract",
            2: "Step 2: Identify Performance Obligations", 
            3: "Step 3: Determine the Transaction Price",
            4: "Step 4: Allocate the Transaction Price",
            5: "Step 5: Recognize Revenue"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    def _load_step_prompts(self) -> Dict[int, str]:
        """Load step-specific prompts (placeholder for future use)."""
        return {}
    
    def generate_executive_summary(self, conclusions_text: str, customer_name: str) -> str:
        """Generate executive summary from step conclusions."""
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
            summary = response.choices[0].message.content
            
            if summary is None:
                logger.warning("LLM returned None for executive summary")
                return f"Executive summary for {customer_name} revenue recognition analysis could not be generated."
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return f"Executive summary for {customer_name} revenue recognition analysis could not be generated due to an error."
    
    def generate_background_section(self, conclusions_text: str, customer_name: str) -> str:
        """Generate background section from step conclusions."""
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
            background = response.choices[0].message.content
            
            if background is None:
                logger.warning("LLM returned None for background section")
                return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology."
            
            return background.strip()
            
        except Exception as e:
            logger.error(f"Error generating background section: {str(e)}")
            return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology."
    
    def generate_conclusion_section(self, conclusions_text: str) -> str:
        """Generate conclusion section from step conclusions."""
        try:
            prompt = f"""Generate a conclusion section for an ASC 606 revenue recognition memorandum.

Based on these step conclusions:

{conclusions_text}

Requirements:
- Synthesize the overall revenue recognition treatment
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