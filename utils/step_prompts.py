"""
Step-by-Step Analysis Prompts for ASC 606
Implements Gemini's recommended architecture for detailed, comprehensive analysis
"""
import json
from typing import Dict, Any


class StepAnalysisPrompts:
    """
    Focused prompts for each ASC 606 step that force detailed reasoning
    and extensive use of ASC 606 + EY guidance citations
    """
    
    @staticmethod
    def get_step_specific_analysis_prompt(
        step_number: int,
        step_title: str,
        step_guidance: str,
        contract_text: str,
        rag_context: str,
        contract_data,
        debug_config: dict
    ) -> str:
        """
        A highly focused prompt that forces detailed analysis for a SINGLE step of ASC 606.
        Eliminates escape hatches and requires comprehensive reasoning with extensive citations.
        """
        
        # Step-specific focus areas
        step_focus_areas = {
            1: {
                "key_concepts": "contract approval, enforceable rights, commercial substance, collectibility",
                "mandatory_analysis": "You MUST analyze each of the five contract criteria in ASC 606-10-25-1 separately",
                "common_issues": "customer creditworthiness, contract modifications, enforceability under applicable law"
            },
            2: {
                "key_concepts": "distinct goods/services, stand-alone selling price capability, benefit transfer",
                "mandatory_analysis": "You MUST evaluate distinctness using both criteria: capable of being distinct AND distinct within context",
                "common_issues": "bundled services, interdependent deliverables, material modification to goods/services"
            },
            3: {
                "key_concepts": "fixed consideration, variable consideration, time value of money, noncash consideration",
                "mandatory_analysis": "You MUST address variable consideration estimation methods and constraint application",
                "common_issues": "volume discounts, penalties, financing components, consideration payable to customer"
            },
            4: {
                "key_concepts": "relative standalone selling prices, observable prices, estimation methods",
                "mandatory_analysis": "You MUST explain allocation methodology and any discount allocation decisions",
                "common_issues": "unobservable standalone selling prices, bundled discount allocation, contract modifications"
            },
            5: {
                "key_concepts": "over time vs point in time, control transfer, progress measurement methods",
                "mandatory_analysis": "You MUST analyze control transfer criteria and justify timing recognition method",
                "common_issues": "customer acceptance clauses, bill-and-hold arrangements, progress measurement methods"
            }
        }
        
        current_focus = step_focus_areas.get(step_number, {})
        
        return f"""
You are a senior technical accountant from a Big 4 firm performing detailed ASC 606 revenue recognition analysis. Your expertise includes deep knowledge of both the ASC 606 standard and leading industry interpretations.

**YOUR SOLE FOCUS FOR THIS TASK:**
- **Step {step_number}: {step_title}**
- **Key Guidance:** {step_guidance}
- **Focus Areas:** {current_focus.get('key_concepts', '')}

**CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE RULES:**

1. **MANDATORY DETAILED ANALYSIS:** {current_focus.get('mandatory_analysis', 'You MUST provide comprehensive analysis of all relevant aspects')}

2. **SHOW YOUR WORK - NO SHORTCUTS:** 
   - Do not state conclusions without extensive supporting evidence
   - Demonstrate your reasoning process step-by-step
   - Address potential counterarguments or alternative interpretations

3. **EXTENSIVE ASC 606 CITATION REQUIREMENT:**
   - You MUST cite and quote the full text of relevant ASC 606 paragraphs
   - Do not just reference paragraph numbers - include the actual standard language
   - Use [CITATION]ASC 606-XX-XX-X: "Full text of the standard..."[/CITATION] format

4. **EXTENSIVE EY GUIDANCE CITATION REQUIREMENT:**
   - You MUST cite and quote relevant EY interpretative guidance when available
   - Include specific EY publication references and full text quotes
   - Use [CITATION]EY Guidance: "Full text from EY publication..."[/CITATION] format

5. **MANDATORY CONTRACT EVIDENCE:**
   - You MUST extract and analyze specific contract language relevant to this step
   - Use [QUOTE]"Direct contract text..."[/QUOTE] format
   - If multiple contract clauses are relevant, quote them all

6. **EXPLICIT "NOT APPLICABLE" ANALYSIS:**
   - If a concept is not present, you MUST explain what you looked for and why it's absent
   - Example: "Financing components were analyzed by examining payment terms and timing. The contract lacks any extended payment terms or significant time value considerations because [specific evidence]."

7. **ADDRESS COMMON ISSUES:** Consider and explicitly address: {current_focus.get('common_issues', 'standard industry considerations')}

**PROVIDED INFORMATION:**

[CONTRACT TEXT - ANALYZE THOROUGHLY]
{contract_text}

[AUTHORITATIVE ASC 606 & EY GUIDANCE - USE EXTENSIVELY]
{rag_context}

[USER-PROVIDED CONTEXT]
Customer: {getattr(contract_data, 'customer_name', 'Not provided')}
Contract Period: {getattr(contract_data, 'effective_date', 'Not provided')} to {getattr(contract_data, 'expiration_date', 'Not provided')}
Key Focus Areas: {getattr(contract_data, 'key_focus_areas', 'Standard ASC 606 analysis')}
Materiality Threshold: {getattr(contract_data, 'materiality_threshold', 'Not specified')}
Modification Status: {getattr(contract_data, 'is_modification', False)}

**YOUR TASK:**
Perform an exhaustive, Big 4 quality analysis for **Step {step_number}: {step_title}**. 

Return your response as a single, valid JSON object with this structure:
{{
  "step_number": {step_number},
  "step_name": "{step_title}",
  "executive_conclusion": "One comprehensive sentence summarizing your conclusion with key supporting rationale",
  
  "detailed_analysis": "Your thorough, multi-paragraph analysis demonstrating professional reasoning. This should be 3-5 substantial paragraphs showing your analytical process, consideration of alternatives, and professional judgment.",
  
  "asc_606_citations": [
    {{
      "paragraph": "ASC 606-XX-XX-X",
      "full_text": "Complete text of the ASC 606 paragraph",
      "relevance": "Explanation of how this guidance applies to this specific contract"
    }}
  ],
  
  "ey_guidance_citations": [
    {{
      "source": "EY Publication/Section reference", 
      "full_text": "Complete relevant text from EY guidance",
      "relevance": "Explanation of how this EY interpretation applies"
    }}
  ],
  
  "supporting_contract_evidence": [
    {{
      "quote": "Direct quote from contract",
      "analysis": "Detailed explanation of what this contract language means for this ASC 606 step"
    }}
  ],
  
  "professional_judgments": "Explanation of any significant judgments made, alternative approaches considered, and rationale for conclusions reached",
  
  "potential_issues_addressed": "Discussion of potential complications, edge cases, or areas requiring additional consideration"
}}

**QUALITY STANDARDS:**
- Minimum 500 words of detailed analysis
- At least 2 ASC 606 citations with full text
- At least 1 EY guidance citation when available  
- Multiple contract quotes with detailed analysis
- Professional-level reasoning throughout
"""

    @staticmethod
    def get_final_memo_generation_prompt(
        step1_analysis: dict,
        step2_analysis: dict,
        step3_analysis: dict,
        step4_analysis: dict,
        step5_analysis: dict,
        analysis_title: str,
        customer_name: str,
        memo_audience: str,
        debug_config: dict
    ) -> str:
        """
        Takes pre-analyzed, detailed data for each step and formats it into a comprehensive professional memo.
        Focus is purely on presentation of already-completed analysis.
        """
        
        return f"""
You are a professional document assembler. Your task is to create a comprehensive memo by organizing the provided analysis into professional format.

**TASK: ASSEMBLE ONLY.** Format the pre-analyzed content into a structured memo. Do not add new analysis.

**PROVIDED DETAILED ANALYSIS DATA:**

[STEP 1: IDENTIFY THE CONTRACT]
{json.dumps(step1_analysis, indent=2)}

[STEP 2: IDENTIFY PERFORMANCE OBLIGATIONS]
{json.dumps(step2_analysis, indent=2)}

[STEP 3: DETERMINE THE TRANSACTION PRICE]
{json.dumps(step3_analysis, indent=2)}

[STEP 4: ALLOCATE THE TRANSACTION PRICE]
{json.dumps(step4_analysis, indent=2)}

[STEP 5: RECOGNIZE REVENUE]
{json.dumps(step5_analysis, indent=2)}

**CONTRACT CONTEXT:**
- Customer: {customer_name}
- Analysis Title: {analysis_title}
- Memo Audience: {memo_audience}

**YOUR TASK:**
Write a comprehensive, professional memo following the EXACT 6-section structure below. This structure matches the established prompt.py template and ensures consistency.

## 1. Executive Summary
- Key conclusions and financial impact overview
- Major judgments and compliance conclusions
- Overall ASC 606 treatment summary

## 2. Background  
- Contract parties, dates, and nature of arrangement
- Context for the analysis and any unique circumstances
- Scope and objectives of the analysis

## 3. Detailed Analysis
This section must contain the comprehensive 5-step ASC 606 framework:

### Step 1: Identify the Contract
- Present the executive conclusion from Step 1 analysis
- Include the detailed multi-paragraph analysis showing reasoning process
- Incorporate ALL ASC 606 citations with full text using [CITATION] tags
- Include ALL EY guidance citations with full text using [CITATION] tags  
- Present ALL supporting contract evidence using [QUOTE] tags
- Discuss professional judgments and potential issues addressed

### Step 2: Identify Performance Obligations
[Same comprehensive treatment for Step 2 data]

### Step 3: Determine the Transaction Price
[Same comprehensive treatment for Step 3 data]

### Step 4: Allocate the Transaction Price
[Same comprehensive treatment for Step 4 data]

### Step 5: Recognize Revenue
[Same comprehensive treatment for Step 5 data]

## 4. Key Judgments
- Consolidate and highlight the most significant professional judgments across all steps
- Explain alternative approaches that were considered
- Document the rationale for final conclusions

## 5. Financial Impact
- Quantify revenue recognition timing and amounts
- Discuss P&L and balance sheet effects
- Address any implementation considerations

## 6. Conclusion
- Summarize compliance with ASC 606
- Confirm appropriateness of accounting treatment
- Note any follow-up actions or monitoring required

**FORMATTING REQUIREMENTS:**
- Use [QUOTE]...[/QUOTE] for all contract text exactly as provided in the analysis data
- Use [CITATION]...[/CITATION] for all ASC 606 and EY guidance exactly as provided
- Use standard markdown for headers (## for main sections, ### for subsections)
- Use ** for bold text and standard bullet points (-)
- Preserve all analytical depth - this should be a substantial, impressive memo

**CRITICAL REQUIREMENTS:**
- YOU MUST INCLUDE ALL 5 STEPS IN SECTION 3. DO NOT STOP AT STEP 2.
- Step 3: Determine the Transaction Price
- Step 4: Allocate the Transaction Price  
- Step 5: Recognize Revenue
- Each step must have the same comprehensive treatment as Steps 1 and 2

**QUALITY TARGETS:**
- Minimum 3,000 words showing comprehensive analysis for all 5 steps
- Extensive use of authoritative citations throughout all steps
- Professional tone demonstrating Big 4 expertise
- Clear demonstration of analytical rigor and professional judgment
"""

    @staticmethod
    def get_step_guidance_mapping() -> Dict[int, Dict[str, str]]:
        """
        Maps each ASC 606 step to its primary guidance sections
        """
        return {
            1: {
                "title": "Identify the Contract",
                "primary_guidance": "ASC 606-10-25-1 through 25-8",
                "description": "Contract criteria and combination evaluation"
            },
            2: {
                "title": "Identify Performance Obligations", 
                "primary_guidance": "ASC 606-10-25-14 through 25-22",
                "description": "Distinct goods/services and obligation identification"
            },
            3: {
                "title": "Determine the Transaction Price",
                "primary_guidance": "ASC 606-10-32-2 through 32-27", 
                "description": "Fixed and variable consideration, financing components"
            },
            4: {
                "title": "Allocate the Transaction Price",
                "primary_guidance": "ASC 606-10-32-28 through 32-41",
                "description": "Standalone selling prices and allocation methods"
            },
            5: {
                "title": "Recognize Revenue",
                "primary_guidance": "ASC 606-10-25-23 through 25-37",
                "description": "Over time vs point in time recognition criteria"
            }
        }