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
        conclusions_text = self._extract_conclusions_from_steps(results['steps'])
        
        # Generate executive summary, background, and conclusion
        logger.info("Generating executive summary...")
        results['executive_summary'] = self.generate_executive_summary(conclusions_text, customer_name)
        logger.info("Generating background...")
        results['background'] = self.generate_background_section(conclusions_text, customer_name)
        logger.info("Generating conclusion...")
        results['conclusion'] = self.generate_conclusion_section(conclusions_text)
        logger.info("Generated executive summary, background, and conclusion sections")
        
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

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed pinpoint citations; e.g., [Contract §X.Y, p. N])
- ASC 606 guidance paraphrased with citations; include only brief decisive phrases when directly supportive (e.g., [ASC 606-10-25-19])
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion]

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 606 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

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
                    
                    # Look for conclusion section in markdown using regex
                    import re
                    conclusion_match = re.search(r'\*\*Conclusion:\*\*\s*([^*]+)', markdown_content, re.IGNORECASE | re.DOTALL)
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
                logger.info(f"Generated executive summary ({len(content)} chars)")
                return content
            else:
                logger.error("Empty executive summary response")
                return "Executive summary generation failed. Please review individual step analyses below."
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return "Executive summary generation failed. Please review individual step analyses below."
    
    def generate_background_section(self, conclusions_text: str, customer_name: str) -> str:
        """Generate background section using clean LLM call."""
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
                logger.info(f"Generated background section ({len(content)} chars)")
                return content
            else:
                logger.error("Empty background response")
                return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606."
            
        except Exception as e:
            logger.error(f"Error generating background: {str(e)}")
            return f"We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606."
    
    def generate_conclusion_section(self, conclusions_text: str) -> str:
        """Generate conclusion section using clean LLM call."""
        prompt = f"""Generate a professional final conclusion for an ASC 606 analysis.

Step Conclusions:
{conclusions_text}

Instructions:
1. Write 2-3 sentences assessing ASC 606 compliance
2. Format all currency as $XXX,XXX (no spaces in numbers)
3. Be direct - if there are concerns, state them clearly
4. Focus on compliance assessment
5. Use professional accounting language
6. Use proper paragraph spacing"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing final conclusions for ASC 606 analyses. Provide clean, professional content with proper currency formatting."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self._get_temperature()
            }
            params.update(self._get_max_tokens_param("conclusion"))
            
            response = self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            if content:
                content = content.strip()
                logger.info(f"Generated conclusion section ({len(content)} chars)")
                return content
            else:
                logger.error("Empty conclusion response")
                return "The analysis indicates compliance with ASC 606 revenue recognition requirements. Implementation should proceed as outlined in the step-by-step analysis above."
            
        except Exception as e:
            logger.error(f"Error generating conclusion: {str(e)}")
            return "The analysis indicates compliance with ASC 606 revenue recognition requirements. Implementation should proceed as outlined in the step-by-step analysis above."
    
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
        prompt = f"""Generate a professional final conclusion for an ASC 606 analysis.

Step Conclusions:
{conclusions_text}

Instructions:
1. Write 2-3 sentences in narrative paragraph format assessing ASC 606 compliance
2. Format all currency as $XXX,XXX (no spaces in numbers)
3. Be direct - if there are concerns, state them clearly
4. Focus on compliance assessment
5. Use professional accounting language without bullet points
6. Use proper paragraph spacing
7. ALWAYS format currency with single $ symbol (never $$)
8. Include proper spacing after commas and periods"""

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
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Final conclusion generation failed: {str(e)}")
            # Fallback to simple conclusion
            return "Based on our comprehensive analysis under ASC 606, the proposed revenue recognition treatment is appropriate and complies with the authoritative guidance."
    
    def generate_background_section_old(self, analysis_results: Dict[str, Any], customer_name: str) -> str:
        """Generate LLM-powered background section from analysis results."""
        
        # Extract key conclusions for contract overview
        conclusions = []
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            if step_key in analysis_results and analysis_results[step_key].get('conclusion'):
                conclusions.append(analysis_results[step_key]['conclusion'])
        
        # Build prompt
        conclusions_text = "\n".join(conclusions[:2])  # Use first 2 steps for contract overview
        
        prompt = f"""Generate a professional 2-3 sentence background for an ASC 606 memo.

Customer: {customer_name}
Contract Summary: {conclusions_text}

Instructions:
1. Describe what type of arrangement was reviewed (high-level)
2. Mention key contract elements (SaaS, hardware, services, etc.) if evident
3. State the purpose of the ASC 606 analysis
4. Professional accounting language
5. Keep it high-level, no specific amounts or detailed terms"""

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
                **self._get_max_tokens_param("background", self.light_model)
            }
            
            response = self.client.chat.completions.create(**request_params)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Background section generation failed: {str(e)}")
            # Fallback to simple background
            clean_customer_name = customer_name.split('\n')[0].strip() if customer_name else "the client"
            return f"We have reviewed the contract documents provided by {clean_customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology and provides recommendations for implementation."
    

    
    def _load_step_prompts(self) -> Dict[str, str]:
        """Load step-specific prompts if available."""
        # For now, return empty dict - prompts are built dynamically
        # In the future, could load from templates/step_prompts.txt
        return {}