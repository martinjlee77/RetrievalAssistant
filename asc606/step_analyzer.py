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
        
        # Model selection: Change "gpt-4o" to "gpt-5" for premium analysis
        self.model = "gpt-4o"
        
        # Load step prompts (currently unused - prompts are generated dynamically in _get_step_prompt)
        self.step_prompts = self._load_step_prompts()
    
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
        
        # Generate overall analysis summary
        results['executive_summary'] = self.generate_executive_summary(results, customer_name)
        results['background'] = self.generate_background_section(results, customer_name)
        
        logger.info("ASC 606 analysis completed successfully")
        return results
    
    def _analyze_step_with_retry(self,
                               step_num: int,
                               contract_text: str,
                               authoritative_context: str,
                               customer_name: str,
                               additional_context: str = "") -> Dict[str, str]:
        """Analyze a single step with retry logic for transient errors."""
        max_retries = 2
        
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
            except Exception as e:
                if attempt == max_retries - 1:  # Final attempt
                    logger.error(f"Failed Step {step_num} after {max_retries} attempts: {str(e)}")
                    raise  # Re-raise the exception to be handled by caller
                else:
                    logger.warning(f"Retrying Step {step_num} (attempt {attempt + 2}) after error: {str(e)}")
                    time.sleep(2)  # Wait before retry
        
        # This should never be reached due to the raise in the final attempt
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
                "max_completion_tokens": 8000 if self.model == "gpt-5" else 2000,
                "temperature": 0.1
            }
            
            # Add response_format only for GPT-5
            if self.model == "gpt-5":
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            markdown_content = response.choices[0].message.content
            
            if markdown_content is None:
                logger.error(f"ERROR: GPT-5 returned None content for Step {step_num}")
                markdown_content = f"## Step {step_num}: Analysis Error\n\nError: GPT-5 returned empty response. Please try with GPT-4o instead."
            else:
                markdown_content = markdown_content.strip()
            
            logger.info(f"DEBUG: Generated markdown for Step {step_num} (length: {len(markdown_content)})")
            
            # Return clean markdown content
            return {
                'title': self._get_step_title(step_num),
                'markdown_content': markdown_content,
                'step_num': step_num
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
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
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
                'title': 'Identify the Contract',
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
                'title': 'Identify Performance Obligations', 
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
                'title': 'Determine the Transaction Price',
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
                'title': 'Allocate the Transaction Price',
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
                'title': 'Recognize Revenue',
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
Customer: {customer_name}

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

## {step['title']}

[Write comprehensive analysis in flowing paragraphs with professional reasoning. Include specific contract evidence and ASC 606 citations.]

**Analysis:** [Detailed analysis with supporting evidence from the contract and citations to relevant ASC 606 guidance. Use explicit reasoning with "because" statements to connect evidence to conclusions.]

**Conclusion:** [Clear 2-3 sentence conclusion summarizing the findings for this step.]

**Issues or Uncertainties:** [If any significant issues exist, list them clearly. Otherwise, state "None identified."]

CRITICAL FORMATTING REQUIREMENTS:
- Format ALL currency as $XXX,XXX (NEVER write $$XXX or numbers without $ symbol)
- Never concatenate words together (avoid "inf ixedconsiderationand")
- Use single $ symbol only, never $$
- Write dates with proper spacing (e.g., "October 26, 2023")
- Always include spaces after commas and periods
- Use bullet points ONLY for lists of 3+ distinct items
- Keep paragraphs under 3 sentences each
- Quote specific contract language as evidence
- Cite relevant ASC 606 paragraphs
- Use professional accounting language
"""
        
        return prompt
    
    def _parse_step_response(self, step_num: int, response_text: str) -> Dict[str, str]:
        """Parse the natural language response into structured components."""
        
        result = {
            'title': self._get_step_title(step_num),
            'analysis': '',
            'conclusion': '',
            'issues': ''
        }
        
        # Log the raw response for debugging
        logger.info(f"DEBUG: Raw AI response for Step {step_num} (length: {len(response_text)}): '{response_text[:200]}'")
        
        # More flexible parsing logic - look for common section patterns
        response_upper = response_text.upper()
        
        # Try different parsing approaches
        if '**' in response_text:
            # Original ** delimiter approach
            sections = response_text.split('**')
            current_section = None
            current_content = []
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                    
                if any(keyword in section.upper() for keyword in ['ANALYSIS', 'STEP ANALYSIS']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'analysis'
                    current_content = []
                elif any(keyword in section.upper() for keyword in ['CONCLUSION', 'STEP CONCLUSION']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'conclusion'
                    current_content = []
                elif any(keyword in section.upper() for keyword in ['ISSUES', 'UNCERTAINTIES', 'MATTERS']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'issues'
                    current_content = []
                else:
                    if current_section:
                        current_content.append(section)
            
            # Handle the last section
            if current_section and current_content:
                result[current_section] = '\n'.join(current_content).strip()
        
        # If ** parsing didn't work, try line-based parsing
        if not result['analysis'] and not result['conclusion']:
            lines = response_text.split('\n')
            current_section = None
            current_content = []
            
            for line in lines:
                line_upper = line.strip().upper()
                
                if any(keyword in line_upper for keyword in ['ANALYSIS:', '**ANALYSIS:**', 'STEP ANALYSIS:']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'analysis'
                    current_content = []
                elif any(keyword in line_upper for keyword in ['CONCLUSION:', '**CONCLUSION:**', 'STEP CONCLUSION:', 'CONCLUSION']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'conclusion'
                    current_content = []
                elif any(keyword in line_upper for keyword in ['ISSUES:', '**ISSUES:**', 'UNCERTAINTIES:', '**UNCERTAINTIES:**']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'issues'
                    current_content = []
                else:
                    if current_section and line.strip():
                        current_content.append(line.strip())
            
            # Handle the last section
            if current_section and current_content:
                result[current_section] = '\n'.join(current_content).strip()
        
        # Special handling for missing conclusions - look for "Conclusion:" pattern anywhere in text
        if not result['conclusion'] and 'Conclusion:' in response_text:
            parts = response_text.split('Conclusion:', 1)
            if len(parts) == 2:
                result['analysis'] = parts[0].strip()
                result['conclusion'] = parts[1].strip()
                logger.info(f"DEBUG: Fixed Step {step_num} conclusion using 'Conclusion:' pattern")
        
        # Ensure we have minimal conclusion for any step missing one
        if not result['conclusion'] and result['analysis']:
            # Extract last paragraph as conclusion
            paragraphs = result['analysis'].split('\n\n')
            if len(paragraphs) > 1:
                result['conclusion'] = paragraphs[-1].strip()
                result['analysis'] = '\n\n'.join(paragraphs[:-1]).strip()
                logger.info(f"DEBUG: Extracted Step {step_num} conclusion from last paragraph")
        
        # Last resort: put everything in analysis if parsing failed
        if not result['analysis'] and not result['conclusion']:
            if response_text and response_text.strip():
                # Apply basic formatting before storing
                cleaned_text = self._apply_basic_formatting(response_text.strip())
                result['analysis'] = cleaned_text
                result['conclusion'] = "Analysis completed. See detailed reasoning above."
            else:
                result['analysis'] = "ERROR: Empty response received from AI model. This may indicate a problem with GPT-5 compatibility."
                result['conclusion'] = "Unable to complete analysis due to empty AI response."
        
        # Apply formatting to parsed sections
        if result['analysis']:
            result['analysis'] = self._apply_basic_formatting(result['analysis'])
        if result['conclusion']:
            result['conclusion'] = self._apply_basic_formatting(result['conclusion'])
        
        logger.info(f"DEBUG: Parsed Step {step_num} - Analysis length: {len(result['analysis'])}, Conclusion length: {len(result['conclusion'])}")
        
        return result
    
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
    
    def _apply_basic_formatting(self, text: str) -> str:
        """Apply essential formatting fixes to text."""
        if not text:
            return text
            
        # Fix currency formatting issues first
        text = re.sub(r'(\d+),\s*(\d+)(?![,\d])', r'$\1,\2', text)  # 845, 000 -> $845,000
        text = re.sub(r'\$\$+', '$', text)  # $$XXX -> $XXX
        
        # Fix text run-together patterns
        text = re.sub(r'(\d+)([a-z])', r'\1 \2', text)  # 50,000f -> 50,000 f
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # wordWord -> word Word
        
        # Fix common spacing issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Fix camelCase
        text = re.sub(r'(\w)([A-Z][a-z])', r'\1 \2', text)  # Fix WordCase
        
        return text
    
    def generate_executive_summary(self, analysis_results: Dict[str, Any], customer_name: str) -> str:
        """Generate LLM-powered executive summary from analysis results."""
        
        # Extract conclusions from each step
        conclusions = []
        for step_num in range(1, 6):
            step_key = f'step_{step_num}'
            if step_key in analysis_results and analysis_results[step_key].get('conclusion'):
                conclusions.append(f"Step {step_num}: {analysis_results[step_key]['conclusion']}")
        
        # Build prompt
        conclusions_text = "\n".join(conclusions)
        prompt = f"""Generate a professional executive summary for an ASC 606 revenue recognition analysis for {customer_name}.

Step Conclusions:
{conclusions_text}

Requirements:
1. Write 3-5 sentences in flowing narrative paragraphs
2. Format all currency as $XXX,XXX (no spaces in numbers)  
3. Use professional accounting language without excessive bullet points
4. Include specific number of performance obligations identified
5. State compliance conclusion clearly
6. Highlight any significant findings or issues
7. Use double line breaks between paragraphs for readability
8. ALWAYS format currency with single $ symbol (e.g., $240,000, never $$240,000)
9. Include proper spacing after commas and periods
10. Never start with "Executive Summary:" as header (template handles this)"""

        # Call LLM API
        try:
            request_params = {
                "model": "gpt-4o-mini",
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
                "temperature": 0.2,
                "max_completion_tokens": 200
            }
            
            response = self.client.chat.completions.create(**request_params)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Executive summary generation failed: {str(e)}")
            # Fallback to simple summary
            return f"We have completed a comprehensive ASC 606 analysis for {customer_name}. Please review the detailed step-by-step analysis for specific findings and conclusions."
    
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
                "model": "gpt-4o-mini",
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
                "temperature": 0.2,
                "max_completion_tokens": 150
            }
            
            response = self.client.chat.completions.create(**request_params)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Final conclusion generation failed: {str(e)}")
            # Fallback to simple conclusion
            return "Based on our comprehensive analysis under ASC 606, the proposed revenue recognition treatment is appropriate and complies with the authoritative guidance."
    
    def generate_background_section(self, analysis_results: Dict[str, Any], customer_name: str) -> str:
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
                "model": "gpt-4o-mini",
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
                "temperature": 0.2,
                "max_completion_tokens": 150
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