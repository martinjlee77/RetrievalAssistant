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
    Performs 2-step analysis: (1) Scoping & Incremental Test, (2) Amortization & Impairment.
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
        
        # Initialize component
    
    def extract_entity_name_llm(self, contract_text: str) -> str:
        """Extract the company name using LLM analysis."""
        try:
            logger.info("🏢 Extracting company name from documents...")
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at identifying the company name in sales commissions or service contracts. Your task is to identify the name of the company that is paying the costs to botain a contract from the user-uploaded documents."
                },
                {
                    "role": "user",
                    "content": f"""Based on the user-provided documents, what is the name of the company paying the costs to obtain a contract (e.g., commissions)?

Please identify:
- The company that is responsible for the costs to obtain a contract
- The name including suffixes like Inc., LLC, Corp., etc.
- Ignore addresses, reference numbers, or other non-company identifiers

Contract Text:
{contract_text[:4000]}

Respond with ONLY the company name, nothing else."""
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
                logger.warning("LLM returned None for company entity name")
                return "Company"
                
            # Clean the response (remove quotes, extra whitespace)
            entity_name = entity_name.strip().strip('"').strip("'").strip()
            
            # Validate the result
            if len(entity_name) < 2 or len(entity_name) > 120:
                logger.warning(f"LLM returned suspicious company entity name: {entity_name}")
                return "Company"
            
            logger.info(f"✓ Company identified: {entity_name}")
            return entity_name
            
        except Exception as e:
            logger.error(f"Error extracting company entity name with LLM: {str(e)}")
            return "Company"
    
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
        Perform complete 2-step ASC 340-40 analysis.
        
        Args:
            contract_text: The contract document text
            authoritative_context: Retrieved ASC 340-40 guidance
            customer_name: Customer/company name
            analysis_title: Analysis title
            additional_context: Optional user-provided context
            
        Returns:
            Dictionary containing analysis results for each step
        """
        analysis_start_time = time.time()
        logger.info(f"Starting ASC 340-40 analysis for {customer_name}")
        
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
                for step_num in range(1, 3)
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
        logger.info("Starting additional section generation")
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
        logger.info(f"✓ ASC 340-40 analysis completed successfully in {total_time:.1f}s")
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
                
                # Validate the output for quality assurance
                validation_result = self.validate_step_output(markdown_content, step_num)
                if not validation_result["valid"]:
                    logger.warning(f"Step {step_num} validation issues: {validation_result['issues']}")
                    # Append validation issues to the Issues section
                    if "**Issues or Uncertainties:**" in markdown_content:
                        issues_section = "\n\n**Validation Notes:** " + "; ".join(validation_result["issues"])
                        markdown_content = markdown_content.replace(
                            "**Issues or Uncertainties:**", 
                            "**Issues or Uncertainties:**" + issues_section + "\n\n**Original Issues:**"
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
                'title': 'Step 1: Scoping and Incremental Test',
                'focus': 'Determine whether the commission plan is within the scope and capitalizable under ASC 340-40',
                'key_points': [
                    'Any consideration payable to a customer (ASC 606-10-32-25 through 32-27) is outside the scope of ASC 340-40, for example rebates, credits, referral or marketing fees paid to a customer or the customer’s customer. Evaluate whether the recipient of the commission is an employee or agent (third party) or a customer.',
                    'This analysis does not cover the costs incurred in fulfilling a contract with a customer (ASC 340-40-25-5 to 25-8)',
                    'Capitalize (i.e., recognize an asset) if and only if incremental: the cost is incurred solely because a specific contract is obtained, and recovery is expected (ASC 340-40-25-1 to 25-3).',
                    'Expense if not incremental or recovery not expected (ASC 340-40-25-3).',
                    'Common capitalizable costs (assuming recovery expected): commissions paid on execution, booking or activation of a specific contract,  third-party agent commissions success-based on a specific contract, accelerators triggered by the specific contract crossing a threshold (capitalize the incremental portion attributable to that contract), recoverable draws when they settle into a commission on a specific contract (capitalize at the point the commission is earned/incurred), employer payroll taxes on capitalized commissions.',
                    'Common expense (typically not incremental): base salary, contests based on aggregate metrics not tied to specific contracts, nonrecoverable draws/guarantees, training, recruiting, enablement stipends, SPIFFs not contingent on a specific contract or that can be earned absent a specific contract.'
                ]
            },
            2: {
                'title': 'Step 2: Guidance for Amortization, Practical Expedient, and Impairment',
                'focus': 'Provide policy boilerplate and guidance only; no calculations or anlaysis.',
                'key_points': [
                    'Capitalized costs to obtain are amortized on a systematic basis consistent with the transfer of the goods or services to which the asset relates. If renewals are commensurate with initial commissions, entities often amortize each commission over the related contract term; otherwise, amortize initial commission over the expected period of benefit. The period of benefit should reflect the expected duration the asset provides benefit, considering customer life, churn/renewal rates, and economic factors.',
                    'Practical expedient: expense the cost as incurred if the amortization period would be one year or less. Application can be by portfolio; document the policy.',
                    'Changes in estimates: adjust amortization prospectively when the expected period of benefit changes (e.g., churn/renewal assumptions).',
                    'At each reporting date, recognize impairment if the carrying amount exceeds the remaining amount of consideration expected to be received (less costs related to providing those goods/services). Reversals are not permitted.',
                'Note that a portfolio approach can be applied if it would not materially differ from a contract-by-contract approach (e.g., for determining amortization periods and impairment).'
                ]
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
- Explicit reasoning with "Because..." statements that connect the evidence to the conclusion]
- Contract evidence with direct quotes only when specific terms drive the conclusion (use "quotation marks" and bracketed citations)
- Contract citations must reference actual text from the document:
    Good: [Commission Plan, Incentive Payout]
    Bad: [Commission Plan §4.2], [Commission Plan, p. 15] (unless these exact references appear in the contract text)
- Only cite section numbers/page numbers if they are explicitly visible in the contract text
- ASC 340-40 guidance paraphrased with citations; include only brief decisive phrases when directly supportive (e.g., [ASC 340-40-25-1])


**Conclusion:** [2–3 sentence conclusion summarizing the findings for this step, with at least one bracketed ASC 340-40 citation.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly and explain potential impact. Otherwise, state "None identified."]

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
    
    # REMOVED: _fix_formatting_issues - using clean GPT-4o markdown directly
    # REMOVED: _parse_step_response - unused method (replaced by direct markdown approach)
    
    def _get_step_title(self, step_num: int) -> str:
        """Get the title for a step."""
        titles = {
            1: "Step 1: Scoping and Incremental Test",
            2: "Step 2: Guidance for Amortization, Practical Expedient, and Impairment"
        }
        return titles.get(step_num, f"Step {step_num}")
    
    # REMOVED: _apply_basic_formatting - using clean GPT-4o markdown directly
    
    def _extract_conclusions_from_steps(self, steps_data: Dict[str, Any]) -> str:
        """Extract conclusion text from all completed steps."""
        conclusions = []
        logger.info(f"Extracting conclusions from {len(steps_data)} steps")
        logger.info(f"DEBUG: steps_data keys: {list(steps_data.keys())}")
        
        for step_num in range(1, 3):
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
                        logger.info(f"DEBUG: Failed to extract conclusion from Step {step_num}")
                        logger.info(f"DEBUG: Step {step_num} content contains '**Conclusion:**': {'**Conclusion:**' in markdown_content}")
                        logger.info(f"DEBUG: Step {step_num} content sample: {markdown_content[:100]}...")
                else:
                    logger.warning(f"Step {step_num} data structure: {type(step_data)}, keys: {step_data.keys() if isinstance(step_data, dict) else 'N/A'}")
        
        conclusions_text = '\n\n'.join(conclusions)
        logger.info(f"Total conclusions extracted: {len(conclusions)}, text length: {len(conclusions_text)}")
        
        # If still no conclusions, generate fallback from step summaries
        if len(conclusions) == 0:
            logger.warning("No conclusions extracted - using fallback summary generation")
            for step_num in range(1, 3):
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
    
    def generate_executive_summary(self, conclusions_text: str, customer_name: str) -> str:
        """Generate executive summary using clean LLM call."""
        logger.info("→ Generating executive summary...")
        
        prompt = f"""Generate a professional executive summary for an ASC 340-40 analysis for {customer_name}.

Step Conclusions:
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
            
            # Track API cost for executive summary
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=params["messages"],
                response_text=response.choices[0].message.content or "",
                model=params["model"],
                request_type="executive_summary"
            )
            
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
        
        prompt = f"""Generate a professional 2-3 sentence background for an ASC 340-40 memo.

Company: {customer_name}
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
            
            # Track API cost for background section
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=params["messages"],
                response_text=response.choices[0].message.content or "",
                model=params["model"],
                request_type="background_generation"
            )
            
            content = response.choices[0].message.content
            if content:
                content = content.strip()
                logger.info(f"✓ Background section generated ({len(content)} chars)")
                return content
            else:
                logger.error("Empty background response")
                return f"We have reviewed the contract cost documents provided by {customer_name} to determine the appropriate accounting treatment under ASC 340-40."
            
        except Exception as e:
            logger.error(f"Error generating background: {str(e)}")
            return f"We have reviewed the contract cost documents provided by {customer_name} to determine the appropriate accounting treatment under ASC 340-40."
    
    
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
            
            # Track API cost for final conclusion
            from shared.api_cost_tracker import track_openai_request
            track_openai_request(
                messages=request_params["messages"],
                response_text=response.choices[0].message.content or "",
                model=self.light_model,
                request_type="final_conclusion"
            )
            
            conclusion = response.choices[0].message.content.strip()
            logger.info(f"✓ Final conclusion generated ({len(conclusion)} chars)")
            return conclusion
            
        except Exception as e:
            logger.error(f"Final conclusion generation failed: {str(e)}")
            # Fallback to simple conclusion
            return "Based on our comprehensive analysis under ASC 340-40, the proposed accounting treatment is appropriate and complies with the authoritative guidance."

    
    def _load_step_prompts(self) -> Dict[str, str]:
        """Load step-specific prompts if available."""
        # For now, return empty dict - prompts are built dynamically
        # In the future, could load from templates/step_prompts.txt
        return {}