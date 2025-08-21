"""
Simple ASC 606 Analyzer - Raw LLM Output Approach

This analyzer uses a single LLM call to generate complete memos,
leveraging LLM's natural formatting capabilities and Streamlit's markdown rendering.
"""

import openai
import os
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleASC606Analyzer:
    """
    Simplified ASC 606 analyzer using raw LLM output approach.
    Single call, direct markdown display - no complex parsing.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Model selection: Change to "gpt-5" when available
        self.model = "gpt-4o"
    
    def analyze_contract(self, 
                        contract_text: str,
                        authoritative_context: str,
                        customer_name: str,
                        analysis_title: str,
                        additional_context: str = "") -> Dict[str, Any]:
        """
        Generate complete ASC 606 memo using single LLM call.
        
        Returns:
            Dictionary with memo_content key containing raw markdown
        """
        logger.info(f"Starting simplified ASC 606 analysis for {customer_name}")
        
        # Build comprehensive prompt
        prompt = self._build_memo_prompt(
            contract_text=contract_text,
            authoritative_context=authoritative_context,
            customer_name=customer_name,
            analysis_title=analysis_title,
            additional_context=additional_context
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical accountant from a Big 4 firm. Generate professional ASC 606 revenue recognition memos in clean markdown format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_completion_tokens=4000
            )
            
            memo_content = response.choices[0].message.content
            
            if not memo_content:
                raise ValueError("Empty response from LLM")
            
            return {
                'memo_content': memo_content.strip(),
                'customer_name': customer_name,
                'analysis_title': analysis_title,
                'analysis_date': datetime.now().strftime("%B %d, %Y")
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise
    
    def _build_memo_prompt(self, contract_text: str, authoritative_context: str, 
                          customer_name: str, analysis_title: str, additional_context: str) -> str:
        """Build comprehensive prompt for memo generation."""
        
        prompt = f"""Generate a complete ASC 606 revenue recognition memorandum in professional markdown format.

**CONTRACT DETAILS:**
Customer: {customer_name}
Analysis: {analysis_title}

**CONTRACT TEXT:**
{contract_text}

**AUTHORITATIVE GUIDANCE:**
{authoritative_context}

**ADDITIONAL CONTEXT:**
{additional_context}

**REQUIRED OUTPUT FORMAT:**

# ASC 606 REVENUE RECOGNITION MEMORANDUM

**TO:** Chief Accounting Officer  
**FROM:** Technical Accounting Team - AI  
**DATE:** {datetime.now().strftime("%B %d, %Y")}  
**RE:** {analysis_title} - ASC 606 Revenue Recognition Analysis

## EXECUTIVE SUMMARY

[Write 2-3 professional paragraphs summarizing key findings, total transaction price, number of performance obligations, and overall compliance conclusion]

## BACKGROUND

We have reviewed the contract documents provided by {customer_name} to determine the appropriate revenue recognition treatment under ASC 606. This memorandum presents our analysis following the five-step ASC 606 methodology and provides recommendations for implementation.

## ASC 606 ANALYSIS

### Step 1: Identify the Contract

[Analyze whether a valid contract exists under ASC 606-10-25-1 criteria: (a) approval and commitment, (b) rights identification, (c) payment terms, (d) commercial substance, (e) probable collection]

**Conclusion:** [Clear conclusion about contract validity]

### Step 2: Identify Performance Obligations

[Identify distinct goods/services using ASC 606-10-25-14 through 25-22. Evaluate if each promise is capable of being distinct and distinct within context of contract]

**Conclusion:** [State number and nature of distinct performance obligations]

### Step 3: Determine the Transaction Price

[Analyze fixed and variable consideration under ASC 606-10-32-2 through 32-14. Address any financing components, noncash consideration, or constraints on variable consideration]

**Conclusion:** [State total transaction price and treatment of variable consideration]

### Step 4: Allocate the Transaction Price

[Allocate transaction price based on relative standalone selling prices per ASC 606-10-32-28 through 32-35. Address any discounts or variable consideration allocation]

**Conclusion:** [Summarize allocation approach and amounts per performance obligation]

### Step 5: Recognize Revenue

[Determine timing of revenue recognition - over time vs. point in time per ASC 606-10-25-23 through 25-30. Address measurement of progress for over-time obligations]

**Conclusion:** [State revenue recognition timing and method for each performance obligation]

## CONCLUSION

[2-3 sentences providing overall assessment of ASC 606 compliance and key implementation considerations]

---

**PREPARED BY:** [Analyst Name] | [Title] | [Date]  
**REVIEWED BY:** [Reviewer Name] | [Title] | [Date]

*This memorandum represents our preliminary analysis based on the contract documents provided. Final implementation should be reviewed with external auditors and may require additional documentation or analysis of specific implementation details.*

**CRITICAL FORMATTING REQUIREMENTS:**
- Format ALL currency amounts as $XXX,XXX (with proper $ symbol and comma placement)
- Use clean professional language with proper spacing
- Ensure proper paragraph breaks and section organization
- Cite specific ASC 606 paragraphs where applicable
- Use "because" statements to show clear reasoning
- Keep sentences concise and professional
- NEVER use run-together text or missing spaces
- Format dates properly (e.g., "October 26, 2023")
"""
        
        return prompt