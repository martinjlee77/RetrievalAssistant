"""
ASC 340-40 Commission Analyzer

This module handles the ASC 340-40 sales commission analysis.
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

class ASC340StepAnalyzer:
    """
    Simplified ASC 340-40 step-by-step analyzer using natural language output.
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
        
        # Initialize component
    
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
                        company_name: str,
                        analysis_title: str,
                        additional_context: str = "") -> Dict[str, Any]:
        """
        Perform complete 3-step ASC 340-40 analysis.
        
        Args:
            contract_text: The contract document text
            authoritative_context: Retrieved ASC 340-40 guidance
            company_name: Company name
            analysis_title: Analysis title
            additional_context: Optional user-provided context
            
        Returns:
            Dictionary containing analysis results for each step
        """
        logger.info(f"Starting ASC 340-40 analysis for {company_name}")
        
        # Add large contract warning
        word_count = len(contract_text.split())
        if word_count > 50000:
            logger.warning(f"Large contract ({word_count} words). Consider splitting if analysis fails.")
        
        results = {
            'company_name': company_name,
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
                    company_name=company_name,
                    additional_context=additional_context
                ): step_num
                for step_num in range(1, 4)
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
        
        logger.info("ASC 340-40 analysis completed successfully")
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
                    company_name=company_name,
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
        """Analyze a single ASC 340-40 step - returns clean markdown."""
        
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
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 340-40 Contract Costs. 

Generate professional accounting analysis in clean markdown format. Your output will be displayed directly using markdown rendering.

Your analysis must be:
- Audit-ready and professional
- Clear and understandable
- Based on the evidence provided in the contract text
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
- Support your analysis with specific contract text and authoritative citations
- Use direct quotes from the contract document only when the exact wording is outcome-determinative
- Paraphrase ASC 340-40 with pinpoint citations; brief decisive phrases may be quoted when directly supportive
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
                'title': 'Step 1: Scope',
                'focus': 'Determine whether each plan element (commissions or compensation) is within the scope of ASC 340-40',
                'key_points': [
                    'Verify that the commissions costs are related to the incremental costs of obtaining a contract with a customer within the scope of ASC 606 on revenue from contracts with customers (ASC 340-40-15-2)',
                    'Note that this analysis does not cover the costs incurred in fulfilling a contract with a customer (ASC 340-40-25-2 to 15-8)',
                    'Note that this analysis does not cover consideration payable to a customer (ASC 606-10-32-25 through 32-27): rebates, credits, referral or marketing fees paid to a customer or the customer’s customer; treat as contra revenue unless a distinct good/service is received at fair value.',
                    'Note that this analysis does not cover share-based compensation (ASC 718): equity or equity-classified awards and associated accounting are under ASC 718; not 340-40',
                    'If plan terms clearly indicate recoverability is not expected (rare for commissions), flag for expense'
                ]
            },
            2: {
                'title': 'Step 2: Incremental Costs of Obtaining a Contract', 
                'focus': 'Determine whether the cost should be recognized as an asset or expense (ASC 340-40-25-1 to 25-4',
                'key_points': [
                    'Capitalize (i.e., recognize an asset) if and only if incremental: the cost is incurred solely because a specific contract is obtained, and recovery is expected (ASC 340-40-25-1 to 25-3).',
                    'Expense if not incremental or recovery not expected (ASC 340-40-25-3).',
                    'Common capitalizable costs (assuming recovery expected): commissions paid on execution/booking/activation of a specific contract,  third-party agent commissions success-based on a specific contract, accelerators triggered by the specific contract crossing a threshold (capitalize the incremental portion attributable to that contract, recoverable draws when they settle into a commission on a specific contract (capitalize at the point the commission is earned/incurred), employer payroll taxes on capitalized commissions if entity policy elects to include.',
                    'Common expense (typically not incremental): base salary, contests based on aggregate metrics not tied to specific contracts, nonrecoverable draws/guarantees, training, recruiting, enablement stipends, SPIFFs not contingent on a specific contract or that can be earned absent a specific contract.'
                ]
            },
            3: {
                'title': 'Step 3: Guidance for Amortization, Practical Expedient, and Impairment',
                'focus': 'Provide policy boilerplate and guidance only; no calculations or anlaysis.',
                'key_points': [
                    'Capitalized costs to obtain are amortized on a systematic basis consistent with the transfer of the goods or services to which the asset relates. If renewals are commensurate with initial commissions, entities often amortize each commission over the related contract term; otherwise, amortize initial commission over the expected period of benefit. The period of benefit should reflect the expected duration the asset provides benefit, considering customer life, churn/renewal rates, and economic factors.',
                    'Practical expedient: expense the cost as incurred if the amortization period would be one year or less. Application can be by portfolio; document the policy.',
                    'Changes in estimates: adjust amortization prospectively when the expected period of benefit changes (e.g., churn/renewal assumptions).',
                    'At each reporting date, recognize impairment if the carrying amount exceeds the remaining amount of consideration expected to be received (less costs related to providing those goods/services). Reversals are not permitted.']
            }
        }
        
        step = step_info[step_num]
        
        prompt = f"""
STEP {step_num}: {step['title'].upper()}

OBJECTIVE: {step['focus']}

COST INFORMATION:
Cost Analysis: Analyze the documents to determine the appropriate accounting for the sales commission under ASC 340-40 for the company.

Instructions: Analyze the user-provided documents from the company's perspective. 

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
Analyze the contract cost documents for Step {step_num} focusing on:
{chr(10).join([f"• {point}" for point in step['key_points']])}

REQUIRED OUTPUT FORMAT (Clean Markdown):

### {step['title']}

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific evidence from user-provided documents and ASC 340-40 citations. Quote language from user-provided documents only when the exact wording is outcome‑determinative; paraphrase ASC 340-40 with pinpoint citations and use only brief decisive phrases when directly supportive.]

**Analysis:** [Detailed analysis with supporting evidence. Include:
- Evidence from user-provided documents with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed pinpoint citations; e.g., [Document §X.Y, p. N])
- ASC 340-40 guidance paraphrased with citations; include only brief decisive phrases when directly supportive (e.g., [ASC 340-40-25-1])
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion]

**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 340-40 citation.]

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
            1: "Step 1: Scope",
            2: "Step 2: Incremental Costs of Obtaining a Contract", 
            3: "Step 3: Guidance for Amortization, Practical Expedient, and Impairment"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    # REMOVED: _apply_basic_formatting - using clean GPT-4o markdown directly
    
    def _extract_conclusions_from_steps(self, steps_data: Dict[str, Any]) -> str:
        """Extract conclusion text from all completed steps."""
        conclusions = []
        logger.info(f"Extracting conclusions from {len(steps_data)} steps")
        logger.info(f"DEBUG: steps_data keys: {list(steps_data.keys())}")
        
        for step_num in range(1, 4):
            step_key = f'step_{step_num}'
            if step_key in steps_data:
                step_data = steps_data[step_key]
                if isinstance(step_data, dict) and 'markdown_content' in step_data:
                    # Extract conclusion from markdown content
                    content = step_data['markdown_content']
                    
                    # Try multiple conclusion patterns - be more flexible
                    conclusion = None
                    
                    # First try exact patterns
                    for pattern in ['**Conclusion:**', 'Conclusion:']:
                        if pattern in content:
                            parts = content.split(pattern, 1)
                            if len(parts) == 2:
                                conclusion_part = parts[1]
                                # Stop at next major section
                                for end_pattern in ['**Issues or Uncertainties:**', 'Issues or Uncertainties:', '**Issues**', 'Issues:']:
                                    if end_pattern in conclusion_part:
                                        conclusion_part = conclusion_part.split(end_pattern)[0]
                                        break
                                conclusion = conclusion_part.strip()
                                break
                    
                    # If no conclusion found, extract from the end of analysis section
                    if not conclusion and '**Analysis:**' in content:
                        # Get everything after **Analysis:** and extract the last substantive paragraph
                        analysis_part = content.split('**Analysis:**', 1)[1]
                        if analysis_part:
                            # Split into paragraphs and get the last substantial one
                            paragraphs = [p.strip() for p in analysis_part.split('\n\n') if p.strip()]
                            if paragraphs:
                                # Take the last paragraph as conclusion
                                conclusion = paragraphs[-1]
                    
                    if conclusion:
                        conclusions.append(f"Step {step_num}: {conclusion}")
                        logger.info(f"Extracted conclusion for Step {step_num}: {conclusion[:50]}...")
                    else:
                        logger.info(f"DEBUG: Failed to extract conclusion from Step {step_num}")
                        logger.info(f"DEBUG: Step {step_num} content contains '**Conclusion:**': {'**Conclusion:**' in content}")
                        logger.info(f"DEBUG: Step {step_num} content sample: {content[:100]}...")
                else:
                    logger.warning(f"Step {step_num} data structure: {type(step_data)}, keys: {step_data.keys() if isinstance(step_data, dict) else 'N/A'}")
        
        conclusions_text = '\n\n'.join(conclusions)
        logger.info(f"Total conclusions extracted: {len(conclusions)}, text length: {len(conclusions_text)}")
        
        # If still no conclusions, generate fallback from step summaries
        if len(conclusions) == 0:
            logger.warning("No conclusions extracted - using fallback summary generation")
            for step_num in range(1, 4):
                step_key = f'step_{step_num}'
                if step_key in steps_data:
                    step_data = steps_data[step_key]
                    if isinstance(step_data, dict) and 'markdown_content' in step_data:
                        content = step_data['markdown_content']
                        # Extract the title and create a simple summary
                        if '### Step' in content and '**Analysis:**' in content:
                            # Get a brief summary from the content
                            summary = f"Step {step_num} completed - analysis of the provided documents under ASC 340-40."
                            conclusions.append(summary)
        
        return conclusions_text
    
    def generate_executive_summary(self, conclusions_text: str, company_name: str) -> str:
        """Generate executive summary using clean LLM call."""
        prompt = f"""Generate a professional executive summary for an ASC 340-40 analysis for {company_name}.

Step Conclusions:
{conclusions_text}

Requirements:
1. Write 3-5 sentences with proper paragraph breaks
2. Format all currency as $XXX,XXX (no spaces in numbers)
3. Use professional accounting language
4. Include specific number of performance obligations identified
5. State compliance conclusion clearly
6. Highlight any significant findings or issues
7. Use double line breaks between paragraphs for readability
8. ALWAYS format currency with $ symbol (e.g., $240,000, not 240,000)
9. Include proper spacing after commas and periods
10. DO NOT include any title or header like "Executive Summary:" - only provide the summary content"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing executive summaries for ASC 340-40 analyses. Provide clean, professional content with proper currency formatting."},
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
    
    def generate_background_section(self, conclusions_text: str, company_name: str) -> str:
        """Generate background section using clean LLM call."""
        prompt = f"""Generate a professional 2-3 sentence background for an ASC 340-40 memo.

Company: {company_name}
Contract Summary: {conclusions_text}

Instructions:
1. Describe what type of arrangement was reviewed (high-level)
2. Mention key cost elements if evident
3. State the purpose of the ASC 340-40 analysi
4. Professional accounting language
5. Keep it high-level, no specific amounts or detailed terms"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing background sections for ASC 340-40 memos. Provide clean, professional content."},
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
                return f"We have reviewed the contract cost documents provided by {company_name} to determine the appropriate accounting treatment under ASC 340-40."
            
        except Exception as e:
            logger.error(f"Error generating background: {str(e)}")
            return f"We have reviewed the contract cost documents provided by {company_name} to determine the appropriate accounting treatment under ASC 340-40."
    
    def generate_conclusion_section(self, conclusions_text: str) -> str:
        """Generate conclusion section using clean LLM call."""
        prompt = f"""Generate a professional final conclusion for an ASC 340-40 analysis.

Step Conclusions:
{conclusions_text}

Instructions:
1. Write 2-3 sentences assessing ASC 340-40 compliance
2. Format all currency as $XXX,XXX (no spaces in numbers)
3. Be direct - if there are concerns, state them clearly
4. Focus on compliance assessment
5. Use professional accounting language
6. Use proper paragraph spacing"""

        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a senior accounting analyst preparing final conclusions for ASC 340-40 analyses. Provide clean, professional content with proper currency formatting."},
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
                return "The analysis indicates compliance with ASC 340-40 requirements. Implementation should proceed as outlined in the step-by-step analysis above."
            
        except Exception as e:
            logger.error(f"Error generating conclusion: {str(e)}")
            return "The analysis indicates compliance with ASC 340-40 requirements. Implementation should proceed as outlined in the step-by-step analysis above."
    
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
        prompt = f"""Generate a professional final conclusion for an ASC 340-40 analysis.

Step Conclusions:
{conclusions_text}

Instructions:
1. Write 2-3 sentences in narrative paragraph format assessing ASC 340-40 compliance
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
                        "content": "You are an expert technical accountant specializing in ASC 340-40 contract costs."
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
            return "Based on our comprehensive analysis under ASC 340-40, the proposed accounting treatment is appropriate and complies with the authoritative guidance."
    
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
        
        prompt = f"""Generate a professional 2-3 sentence background for an ASC 340-40 memo.

Company: {company_name}
Contract Summary: {conclusions_text}

Instructions:
1. Describe what type of arrangement was reviewed (high-level)
2. Mention key cost elements if evident
3. State the purpose of the ASC 340-40 analysis
4. Professional accounting language
5. Keep it high-level, no specific amounts or detailed terms"""

        # Call LLM API
        try:
            request_params = {
                "model": self.light_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert technical accountant specializing in ASC 340-40 contract costs."
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
            return f"We have reviewed the contract cost documents provided by {clean_customer_name} to determine the appropriate accounting treatment under ASC 340-40. This memorandum presents our analysis following the ASC 340-40 methodology.."
    

    
    def _load_step_prompts(self) -> Dict[str, str]:
        """Load step-specific prompts if available."""
        # For now, return empty dict - prompts are built dynamically
        # In the future, could load from templates/step_prompts.txt
        return {}