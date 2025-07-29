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
   - Use [QUOTE]"Direct contract text..." - Source: [Document Name, Page/Section][/QUOTE] format
   - If multiple contract clauses are relevant, quote them all with their sources

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
    "ASC 606-XX-XX-X | Complete text of the ASC 606 paragraph | Explanation of how this guidance applies to this specific contract"
  ],
  
  "ey_guidance_citations": [
    "EY Publication/Section reference | Complete relevant text from EY guidance | Explanation of how this EY interpretation applies"
  ],
  
  "supporting_contract_evidence": [
    "Direct quote from contract (cite source file and section if available) | Detailed explanation of what this contract language means for this ASC 606 step"
  ],
  
  "professional_judgments": [
    "A string explaining a single professional judgment.",
    "Another string for a second judgment."
  ],
  
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

        """
    
    @staticmethod
    def format_step_detail_as_markdown(step_data: dict, step_num: int, step_name: str) -> str:
        """Formats the rich JSON of a single step into professional markdown prose."""
        if not step_data or step_data.get('error'):
            return f"### Step {step_num}: {step_name}\n\n**Error:** Analysis failed for this step.\n"
        
        parts = []
        parts.append(f"### Step {step_num}: {step_name}")
        parts.append("")  # Add spacing
        
        # Executive conclusion with enhanced formatting
        if step_data.get('executive_conclusion'):
            parts.append("**CONCLUSION:**")
            conclusion_text = step_data.get('executive_conclusion', '').strip()
            if conclusion_text:
                parts.append(conclusion_text)
            parts.append("")
        
        # Detailed analysis
        parts.append("**Detailed Analysis & Reasoning:**")
        parts.append("")
        analysis_text = step_data.get('detailed_analysis', 'N/A')
        # Clean up any formatting issues in the analysis text
        if isinstance(analysis_text, str):
            # Fix any character splitting issues
            analysis_text = analysis_text.replace('\n\n', '\n').strip()
        parts.append(str(analysis_text))
        parts.append("")

        # Supporting contract evidence (enhanced formatting)
        if step_data.get('supporting_contract_evidence'):
            parts.append("**Supporting Contract Evidence:**")
            parts.append("")
            for evidence in step_data.get('supporting_contract_evidence', []):
                if isinstance(evidence, str):
                    evidence_parts = evidence.split('|', 1)  # Split only once
                    quote = evidence_parts[0].strip()
                    analysis = evidence_parts[1].strip() if len(evidence_parts) > 1 else ""
                    if quote:
                        parts.append(f"> *{quote}*")
                        parts.append("")
                    if analysis:
                        parts.append(f"**Analysis:** {analysis}")
                        parts.append("")
                elif isinstance(evidence, dict):
                    # Fallback for old format
                    quote = evidence.get('quote', '').strip()
                    analysis = evidence.get('analysis', '').strip()
                    if quote:
                        parts.append(f"> *{quote}*")
                        parts.append("")
                    if analysis:
                        parts.append(f"**Analysis:** {analysis}")
                        parts.append("")

        # ASC 606 Citations (enhanced formatting with spacing)
        if step_data.get('asc_606_citations'):
            parts.append("**Authoritative Guidance:**")
            parts.append("")
            for citation in step_data.get('asc_606_citations', []):
                if isinstance(citation, str):
                    citation_parts = citation.split('|', 2)  # Split max twice
                    paragraph = citation_parts[0].strip()
                    full_text = citation_parts[1].strip() if len(citation_parts) > 1 else ""
                    relevance = citation_parts[2].strip() if len(citation_parts) > 2 else ""
                    if paragraph and full_text:
                        # Truncate very long citations to prevent formatting issues
                        if len(full_text) > 500:
                            full_text = full_text[:500] + "..."
                        parts.append(f"**{paragraph}:** *{full_text}*")
                        parts.append("")
                    if relevance:
                        parts.append(f"**Application:** {relevance}")
                        parts.append("")
                elif isinstance(citation, dict):
                    # Fallback for old format
                    paragraph = citation.get('paragraph', '').strip()
                    full_text = citation.get('full_text', '').strip()
                    if paragraph and full_text:
                        if len(full_text) > 500:
                            full_text = full_text[:500] + "..."
                        parts.append(f"**{paragraph}:** *{full_text}*")
                        parts.append("")

        # Professional judgments (reduce bullet overuse)
        if step_data.get('professional_judgments'):
            parts.append("**Key Professional Judgments:**")
            parts.append("")
            for i, judgment in enumerate(step_data.get('professional_judgments', []), 1):
                if isinstance(judgment, str):
                    clean_judgment = judgment.strip()
                    if clean_judgment:
                        parts.append(f"{i}. {clean_judgment}")
                        parts.append("")
                else:
                    parts.append(f"{i}. {str(judgment)}")
                    parts.append("")

        return "\n".join(parts)

    @staticmethod
    def get_executive_summary_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, contract_data) -> str:
        """Generates focused prompt for executive summary only."""
        conclusions = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            conclusion = step.get('executive_conclusion', 'N/A')
            conclusions.append(f"Step {i}: {conclusion}")
        
        return f"""Write a professional executive summary for an ASC 606 technical accounting memo.

CONTRACT CONTEXT:
- Customer: {getattr(contract_data, 'customer_name', 'Unknown')}
- Analysis: {getattr(contract_data, 'analysis_title', 'ASC 606 Analysis')}

STEP CONCLUSIONS:
{chr(10).join(conclusions)}

Write 2-3 paragraphs synthesizing these conclusions into a cohesive executive summary that:
- States the overall ASC 606 compliance conclusion
- Highlights key judgments and financial impacts
- Provides clear guidance for decision makers

Use professional accounting language appropriate for technical staff."""

    @staticmethod 
    def get_background_prompt(contract_data) -> str:
        """Generates focused prompt for background section only."""
        return f"""Write a professional background section for an ASC 606 technical accounting memo.

CONTRACT INFORMATION:
- Customer: {getattr(contract_data, 'customer_name', 'Unknown')}
- Analysis Title: {getattr(contract_data, 'analysis_title', 'ASC 606 Analysis')}
- Contract Start: {getattr(contract_data, 'contract_start_date', 'Not specified')}
- Contract End: {getattr(contract_data, 'contract_end_date', 'Not specified')}
- Modification: {getattr(contract_data, 'is_modification', False)}

Write 1-2 paragraphs covering:
- Contract parties and key dates
- Nature of the arrangement and services
- Scope and objectives of this ASC 606 analysis
- Any unique circumstances requiring special consideration

Keep this section factual and concise."""

    @staticmethod
    def get_consistency_check_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict) -> str:
        """CRITICAL: Check for contradictions and inconsistencies across all 5 steps."""
        step_conclusions = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            conclusion = step.get('executive_conclusion', 'N/A')
            step_conclusions.append(f"Step {i}: {conclusion}")
        
        return f"""You are a senior accounting partner reviewing ASC 606 analysis for consistency.

INDIVIDUAL STEP CONCLUSIONS:
{chr(10).join(step_conclusions)}

CRITICAL TASK: Identify any contradictions or inconsistencies between these 5 steps.

Check for these common issues:
- Step 1 says "single contract" but Step 2 identifies multiple unrelated obligations
- Step 2 identifies distinct services but Step 4 allocates to combined obligation  
- Step 3 determines fixed price but Step 5 recognizes over variable timeline
- Transaction price in Step 3 doesn't match allocation in Step 4
- Recognition timing in Step 5 conflicts with obligation identification in Step 2

RESPONSE FORMAT:
If inconsistencies found: List each contradiction clearly with recommended resolution
If consistent: State "ANALYSIS CONSISTENT - All steps align logically"

Be thorough - audit-quality analysis depends on step consistency."""

    @staticmethod
    def get_key_judgments_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict) -> str:
        """Generates focused prompt for key judgments section only."""
        judgments = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            step_judgments = step.get('professional_judgments', [])
            for judgment in step_judgments:
                judgment_text = judgment if isinstance(judgment, str) else str(judgment)
                judgments.append(f"Step {i}: {judgment_text}")
        
        return f"""Write a professional key judgments section for an ASC 606 technical accounting memo.

PROFESSIONAL JUDGMENTS FROM ANALYSIS:
{chr(10).join(judgments)}

Transform these into 3-4 well-structured judgment statements that:
- State each critical accounting position clearly
- Provide rationale for the judgment
- Reference relevant ASC 606 guidance
- Address potential alternative treatments considered

Use numbered paragraphs (not bullets) and maintain professional accounting tone."""

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

    @staticmethod
    def get_financial_impact_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str) -> str:
        """Generates focused prompt for financial impact section with suggested journal entries."""
        
        # Extract transaction price and timing details
        transaction_price = "Not specified"
        revenue_timing = "Not specified"
        
        if s3.get('executive_conclusion'):
            conclusion = s3.get('executive_conclusion', '')
            # Try to extract price information
            import re
            price_match = re.search(r'\$[\d,]+\.?\d*', conclusion)
            if price_match:
                transaction_price = price_match.group()
        
        if s5.get('executive_conclusion'):
            revenue_timing = s5.get('executive_conclusion', '')
        
        return f"""Write a meaningful financial impact section for an ASC 606 technical accounting memo.

TRANSACTION DETAILS:
- Customer: {customer_name}
- Transaction Price: {transaction_price}
- Revenue Recognition: {revenue_timing}

Create a comprehensive financial impact analysis that includes:

**Revenue Recognition Impact:**
Total contract value and timing of recognition, impact on financial statement presentation, any deferred revenue or contract asset implications.

**Suggested Journal Entries:**
Provide specific journal entries with realistic account names and amounts:
- Contract inception entries (if applicable)
- Revenue recognition entries
- Any performance obligation and contract asset/liability entries

**Key Financial Statement Effects:**
Income statement impact (revenue, timing), balance sheet impact (contract assets, deferred revenue), cash flow statement considerations.

Use clear paragraphs (not bullets) and professional accounting language suitable for {memo_audience.lower()}."""

    @staticmethod
    def get_conclusion_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str) -> str:
        """Generates focused prompt for meaningful conclusion section."""
        
        # Extract key conclusions from each step
        key_points = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            conclusion = step.get('executive_conclusion', '')
            if conclusion:
                key_points.append(f"Step {i}: {conclusion}")
        
        return f"""Write a meaningful conclusion section for an ASC 606 technical accounting memo.

KEY CONCLUSIONS FROM ANALYSIS:
{chr(10).join(key_points)}

Create a comprehensive conclusion that:

**Overall Compliance Assessment:**
Summarize whether the contract complies with ASC 606 and any areas of concern or complexity.

**Key Takeaways for {memo_audience}:**
Highlight the most important implications for the intended audience, focusing on actionable insights.

**Implementation Considerations:**
Any practical next steps, documentation requirements, or monitoring needed.

Use clear, decisive language that provides closure and actionable guidance. Avoid simply repeating earlier analysis."""

    @staticmethod 
    def get_enhanced_executive_summary_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, analysis_title: str, customer_name: str) -> str:
        """Generates enhanced executive summary with professional dashboard format."""
        
        conclusions = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            conclusion = step.get('executive_conclusion', 'N/A')
            conclusions.append(f"Step {i}: {conclusion}")
        
        return f"""Write a professional executive summary for an ASC 606 technical accounting memo using a structured dashboard format.

ANALYSIS RESULTS:
- Analysis: {analysis_title}
- Customer: {customer_name}
- Step Conclusions: {chr(10).join(conclusions)}

Create an executive summary using this professional structure:

**OVERALL CONCLUSION**
[Single paragraph stating overall ASC 606 compliance and revenue recognition approach]

**KEY FINDINGS**
• Contract Status: [Valid/Invalid under ASC 606-10-25-1]
• Performance Obligations: [Number and nature of distinct obligations]
• Transaction Price: [Amount and any variable consideration]
• Revenue Recognition: [Over time/Point in time with timing]
• Critical Judgments: [1-2 most significant accounting decisions]

**FINANCIAL IMPACT SUMMARY**
• Total Contract Value: [Amount]
• Recognition Pattern: [Monthly/Quarterly/Annual timing]
• Balance Sheet Impact: [Contract assets/liabilities if any]

Use bullet points for clarity and include specific amounts/dates where available."""