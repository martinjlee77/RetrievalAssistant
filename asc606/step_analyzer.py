"""
ASC 606 Step Analyzer

This module handles the 5-step ASC 606 revenue recognition analysis.
Simplified, natural language approach with clear reasoning chains.

Author: Accounting Platform Team
"""

import openai
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

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
        
        # Load step prompts
        self.step_prompts = self._load_step_prompts()
    
    def analyze_contract(self, 
                        contract_text: str,
                        authoritative_context: str,
                        customer_name: str,
                        analysis_title: str) -> Dict[str, Any]:
        """
        Perform complete 5-step ASC 606 analysis.
        
        Args:
            contract_text: The contract document text
            authoritative_context: Retrieved ASC 606 guidance
            customer_name: Customer name
            analysis_title: Analysis title
            
        Returns:
            Dictionary containing analysis results for each step
        """
        logger.info(f"Starting ASC 606 analysis for {customer_name}")
        
        results = {
            'customer_name': customer_name,
            'analysis_title': analysis_title,
            'analysis_date': datetime.now().strftime("%B %d, %Y"),
            'steps': {}
        }
        
        # Analyze each step sequentially
        for step_num in range(1, 6):
            try:
                logger.info(f"Analyzing Step {step_num}")
                
                step_result = self._analyze_step(
                    step_num=step_num,
                    contract_text=contract_text,
                    authoritative_context=authoritative_context,
                    customer_name=customer_name
                )
                
                results['steps'][f'step_{step_num}'] = step_result
                logger.info(f"Completed Step {step_num}")
                
            except Exception as e:
                logger.error(f"Error in Step {step_num}: {str(e)}")
                results['steps'][f'step_{step_num}'] = {
                    'title': self._get_step_title(step_num),
                    'analysis': f"Error analyzing this step: {str(e)}",
                    'conclusion': "Analysis incomplete due to error"
                }
        
        # Generate overall analysis summary
        results['executive_summary'] = self.generate_executive_summary(results, customer_name)
        results['issues_for_investigation'] = self._identify_issues(results, contract_text)
        
        logger.info("ASC 606 analysis completed successfully")
        return results
    
    def _analyze_step(self, 
                     step_num: int,
                     contract_text: str,
                     authoritative_context: str,
                     customer_name: str) -> Dict[str, str]:
        """Analyze a single ASC 606 step."""
        
        # Get step-specific prompt
        prompt = self._get_step_prompt(
            step_num=step_num,
            contract_text=contract_text,
            authoritative_context=authoritative_context,
            customer_name=customer_name
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
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_completion_tokens": 8000 if self.model == "gpt-5" else 2000
            }
            
            # Add response_format only for GPT-5
            if self.model == "gpt-5":
                request_params["response_format"] = {"type": "text"}
            
            response = self.client.chat.completions.create(**request_params)
            
            analysis_text = response.choices[0].message.content
            
            # Debug: Log the full response
            logger.info(f"DEBUG: Full API response for Step {step_num}: {response}")
            logger.info(f"DEBUG: Response content type: {type(analysis_text)}")
            logger.info(f"DEBUG: Response content is None: {analysis_text is None}")
            
            if analysis_text is None:
                logger.error(f"ERROR: GPT-5 returned None content for Step {step_num}")
                analysis_text = f"Error: GPT-5 returned empty response for Step {step_num}. Please try with GPT-4o instead."
            else:
                analysis_text = analysis_text.strip()
            
            # Parse the natural language response
            return self._parse_step_response(step_num, analysis_text)
            
        except Exception as e:
            logger.error(f"API error in step {step_num}: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the analyzer."""
        return """You are an expert technical accountant from a Big 4 firm, specializing in ASC 606 revenue recognition. 

Your analysis must be:
- Audit-ready and professional
- Clear and understandable 
- Based on authoritative guidance
- Include explicit reasoning with "because" statements
- Acknowledge any limitations or gaps in information

You will analyze contracts step-by-step following ASC 606 methodology. For each step, provide:
1. Clear analysis with supporting evidence from the contract
2. Citations to relevant ASC 606 guidance  
3. Explicit reasoning connecting evidence to conclusions
4. Professional conclusion for the step

When contract information is ambiguous or missing, acknowledge this and state your analytical approach."""
    
    def _get_step_prompt(self, 
                        step_num: int,
                        contract_text: str, 
                        authoritative_context: str,
                        customer_name: str) -> str:
        """Generate prompt for a specific step."""
        
        step_info = {
            1: {
                'title': 'Identify the Contract',
                'focus': 'Determine if a valid contract exists under ASC 606-10-25-1 criteria',
                'key_points': [
                    'Approval and commitment by parties',
                    'Identification of rights and obligations', 
                    'Payment terms identification',
                    'Commercial substance',
                    'Collectibility assessment'
                ]
            },
            2: {
                'title': 'Identify Performance Obligations', 
                'focus': 'Identify distinct goods or services using ASC 606-10-25-19 and 25-21',
                'key_points': [
                    'Promised goods and services in the contract',
                    'Capability of being distinct (ASC 606-10-25-19a)',
                    'Separately identifiable (ASC 606-10-25-21 factors)',
                    'Final performance obligation determination'
                ]
            },
            3: {
                'title': 'Determine the Transaction Price',
                'focus': 'Establish the transaction price per ASC 606-10-32-2',
                'key_points': [
                    'Fixed consideration amounts',
                    'Variable consideration and constraints',
                    'Significant financing components',
                    'Noncash consideration',
                    'Total transaction price'
                ]
            },
            4: {
                'title': 'Allocate the Transaction Price',
                'focus': 'Allocate price to performance obligations based on standalone selling prices',
                'key_points': [
                    'Standalone selling price determination',
                    'Price allocation methodology',
                    'Discount allocation considerations',
                    'Final allocation amounts'
                ]
            },
            5: {
                'title': 'Recognize Revenue',
                'focus': 'Determine when revenue should be recognized for each performance obligation',
                'key_points': [
                    'Over time vs. point in time assessment',
                    'Control transfer analysis',
                    'Measurement of progress (if over time)',
                    'Revenue recognition timing'
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
{contract_text}

AUTHORITATIVE GUIDANCE:
{authoritative_context}

ANALYSIS REQUIRED:
Analyze the contract for Step {step_num} focusing on:
{chr(10).join([f"• {point}" for point in step['key_points']])}

RESPONSE FORMAT:
Provide your analysis in the following structure:

**ANALYSIS:**
[Detailed analysis with contract evidence, ASC 606 citations, and explicit "because" reasoning]

**CONCLUSION:**
[Clear, definitive conclusion for this step]

**ISSUES OR UNCERTAINTIES:**
[Any areas requiring further investigation or clarification]

Remember to:
- Quote specific contract language as evidence
- Cite relevant ASC 606 paragraphs  
- Use "because" statements to show reasoning
- Acknowledge any information gaps or ambiguities
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
                
                if any(keyword in line_upper for keyword in ['ANALYSIS:', 'STEP ANALYSIS:']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'analysis'
                    current_content = []
                elif any(keyword in line_upper for keyword in ['CONCLUSION:', 'STEP CONCLUSION:']):
                    if current_section and current_content:
                        result[current_section] = '\n'.join(current_content).strip()
                    current_section = 'conclusion'
                    current_content = []
                elif any(keyword in line_upper for keyword in ['ISSUES:', 'UNCERTAINTIES:']):
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
        
        # Last resort: put everything in analysis if parsing failed
        if not result['analysis'] and not result['conclusion']:
            if response_text and response_text.strip():
                result['analysis'] = response_text.strip()
                result['conclusion'] = "Analysis completed. See detailed reasoning above."
            else:
                result['analysis'] = "ERROR: Empty response received from AI model. This may indicate a problem with GPT-5 compatibility."
                result['conclusion'] = "Unable to complete analysis due to empty AI response."
        
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
1. Write a 3-5 sentence executive summary
2. Highlight any significant findings or issues  
3. State whether the proposed accounting treatment is consistent with ASC 606
4. Use professional accounting language"""

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
1. Write 2-3 sentences assessing ASC 606 compliance
2. Be direct - if there are concerns, state them clearly
3. Focus on compliance assessment
4. Use professional accounting language"""

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
    
    def _identify_issues(self, results: Dict[str, Any], contract_text: str) -> List[str]:
        """Identify issues for further investigation based on the analysis."""
        
        issues = []
        
        # Collect issues from each step
        for step_key, step_data in results.get('steps', {}).items():
            if isinstance(step_data, dict) and step_data.get('issues'):
                step_issues = step_data['issues']
                if step_issues and step_issues.strip() and 'none' not in step_issues.lower():
                    issues.append(f"Step {step_key.split('_')[1]}: {step_issues}")
        
        # Add standard issues if none were identified
        if not issues:
            issues = [
                "Validate completeness of contract documentation and any amendments",
                "Confirm implementation timeline and system capability requirements",
                "Review final accounting treatment with external auditors prior to implementation"
            ]
        
        return issues
    
    def _load_step_prompts(self) -> Dict[str, str]:
        """Load step-specific prompts if available."""
        # For now, return empty dict - prompts are built dynamically
        # In the future, could load from templates/step_prompts.txt
        return {}