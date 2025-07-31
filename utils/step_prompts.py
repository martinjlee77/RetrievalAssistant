"""
Enhanced step-by-step prompt templates for ASC 606 analysis.
"""

class StepPrompts:
    """Enhanced prompts with proportional complexity handling."""
    
    @staticmethod
    def get_step_info() -> dict:
        """Returns information about each ASC 606 step."""
        return {
            1: {
                "title": "Identify the Contract",
                "primary_guidance": "ASC 606-10-25-1 through 25-8",
                "description": "Contract identification and combination criteria"
            },
            2: {
                "title": "Identify Performance Obligations",
                "primary_guidance": "ASC 606-10-25-14 through 25-22",
                "description": "Distinct goods or services identification"
            },
            3: {
                "title": "Determine the Transaction Price",
                "primary_guidance": "ASC 606-10-32-2 through 32-27",
                "description": "Fixed and variable consideration determination"
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
        """Generates proportional financial impact prompt based on transaction complexity."""
        
        # Robust data extraction logic
        price_details = "Not specified"
        recognition_summary = "Not specified"
        
        # ENHANCED: Prioritize structured data from Step 4 allocation
        if s4_allocation := s4.get('allocation_details'):
            import json
            try:
                if isinstance(s4_allocation, dict):
                    price_details = json.dumps(s4_allocation, indent=2)
                else:
                    price_details = str(s4_allocation)
            except (TypeError, ValueError):
                price_details = str(s4_allocation)
        # Fallback to regex extraction from Step 3
        elif s3_conclusion := s3.get('executive_conclusion', ''):
            import re
            if price_match := re.search(r'\$[\d,]+\.?\d*', s3_conclusion):
                price_details = f"Total Transaction Price: {price_match.group()}"
        
        # Get recognition summary from Step 5
        recognition_summary = s5.get('executive_conclusion', 'Not specified')

        # Logic to determine transaction complexity
        is_complex = "multiple performance obligations" in s2.get('executive_conclusion', '').lower() or \
                     "variable consideration" in s3.get('executive_conclusion', '').lower() or \
                     "financing component" in s3.get('executive_conclusion', '').lower()

        return f"""You are a corporate controller writing the "Financial Impact" section of an ASC 606 memo. Your response must be concise and proportional to the complexity of the transaction.

CONTEXT FROM ANALYSIS:
- Price & Allocation Details: {price_details}
- Revenue Recognition Summary: {recognition_summary}
- Is the transaction complex (e.g., multiple POs, variable consideration)? {"Yes" if is_complex else "No"}

YOUR TASK:
Write a concise financial impact analysis.

**CRITICAL RULE: Be Proportional.**
- **For SIMPLE transactions** (like a standard, single-element subscription): Provide a very brief, 1-2 sentence summary of the accounting treatment and one summary journal entry. DO NOT write a lengthy narrative or explain basic accounting principles.
- **For COMPLEX transactions:** Provide a more detailed analysis, including separate sections for Financial Statement Impact and Illustrative Journal Entries as described below.

---
**IF THE TRANSACTION IS COMPLEX, follow this structure:**

1.  **Financial Statement Impact:** In a narrative paragraph, describe the expected impact on the income statement and balance sheet (e.g., creation of contract assets or multiple deferred revenue liabilities).

2.  **Illustrative Journal Entries:** Provide key journal entries in a clear, tabular Markdown format. Use standard account names.

    | Date       | Account                          | Debit     | Credit    |
    |------------|----------------------------------|-----------|-----------|
    | ...        | ...                              | ...       | ...       |

3.  **Internal Control & Process Considerations:** Briefly mention any operational considerations required for accurate accounting (e.g., the need to track usage for variable revenue, or new processes to monitor the satisfaction of performance obligations over time).

---
**IF THE TRANSACTION IS SIMPLE, follow this structure:**

The $XX.XX fee will be recorded as a deferred revenue liability upon receipt and recognized as revenue on a straight-line basis over the service period.

**Illustrative Journal Entry:**
| Account                      | Debit     | Credit    |
|------------------------------|-----------|-----------|
| Cash / Accounts Receivable   | $XX.XX    |           |
| Deferred Revenue             |           | $XX.XX    |
| *To record contract inception* | | |

---

Begin writing the financial impact section, strictly adhering to the proportionality rule.
"""

    @staticmethod
    def get_conclusion_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict, customer_name: str, memo_audience: str) -> str:
        """Generates a proportional and meaningful conclusion prompt."""

        # Logic to determine transaction complexity
        is_complex = "multiple performance obligations" in s2.get('executive_conclusion', '').lower() or \
                     "variable consideration" in s3.get('executive_conclusion', '').lower() or \
                     "financing component" in s3.get('executive_conclusion', '').lower()

        return f"""You are an accounting manager writing the final "Conclusion and Recommendations" section of an ASC 606 memo. Your response must be professional, decisive, and proportional to the complexity of the transaction.

CONTEXT FROM ANALYSIS:
- Is the transaction complex? {"Yes" if is_complex else "No"}

YOUR TASK:
Write a final concluding section for the memo, strictly adhering to the proportionality rule below.

**CRITICAL RULE: Be Proportional and Avoid Generic Boilerplate.**

---
**IF THE TRANSACTION IS COMPLEX, follow this structure:**

### Conclusion
In a single paragraph, state that the accounting treatment outlined in the memo is appropriate and in accordance with ASC 606. Briefly reiterate the core revenue recognition conclusion.

### Recommendations
Based on the analysis, provide a bulleted list of specific, practical next steps derived directly from the complexities of this contract. Focus on items like:
- "The process for estimating the variable consideration for [specific bonus] must be documented and reviewed quarterly."
- "The ERP system must be configured to handle the allocation of the transaction price to the three distinct performance obligations."

---
**IF THE TRANSACTION IS SIMPLE, your ENTIRE output must be the following two paragraphs ONLY:**

### Conclusion
The accounting treatment for this straightforward arrangement is appropriate and in accordance with ASC 606. Revenue will be recognized as described in the analysis above.

### Recommendations
It is recommended that this memorandum and the supporting contract documentation be retained as audit evidence for the transaction. No other specific actions are required as a result of this analysis.

---

Begin writing the "Conclusion and Recommendations" section. Do not add any other text, summaries, or boilerplate language.
"""

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
• Expected Revenue: [Amount and timing]
• Implementation Requirements: [Key operational changes needed]

Keep this professional, concise, and focused on executive-level insights."""

    @staticmethod
    def get_step_specific_analysis_prompt(step_number: int, step_title: str, step_guidance: str, 
                                        contract_text: str, rag_context: str, 
                                        contract_data=None, debug_config=None) -> str:
        """Generate step-specific analysis prompt."""
        return f"""You are an expert in ASC 606 revenue recognition. Analyze this contract for Step {step_number}: {step_title}.

PRIMARY GUIDANCE: {step_guidance}

AUTHORITATIVE GUIDANCE CONTEXT:
{rag_context}

ADDITIONAL GUIDANCE:
(Available in RAG context above)

CONTRACT TEXT TO ANALYZE:
{contract_text}

CONTRACT DATA:
Customer: {getattr(contract_data, 'customer_name', 'N/A') if contract_data else 'N/A'}
Analysis Focus: {getattr(contract_data, 'key_focus_areas', 'General ASC 606 compliance') if contract_data else 'General ASC 606 compliance'}

Provide a detailed analysis including:
1. **Executive Conclusion**: Clear determination for this step
2. **Supporting Analysis**: Detailed reasoning with ASC 606 citations
3. **Contract Evidence**: Specific quotes from the contract that support your conclusion
4. **Key Considerations**: Any complexities or judgment areas

Return your response as a JSON object with the keys: executive_conclusion, supporting_analysis, contract_evidence, key_considerations."""

    @staticmethod
    def get_consistency_check_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict) -> str:
        """Generate consistency check prompt for all 5 steps."""
        return f"""Review the logical consistency of this ASC 606 analysis across all 5 steps:

STEP 1 - CONTRACT IDENTIFICATION:
{s1.get('executive_conclusion', 'N/A')}

STEP 2 - PERFORMANCE OBLIGATIONS:
{s2.get('executive_conclusion', 'N/A')}

STEP 3 - TRANSACTION PRICE:
{s3.get('executive_conclusion', 'N/A')}

STEP 4 - ALLOCATION:
{s4.get('executive_conclusion', 'N/A')}

STEP 5 - RECOGNITION:
{s5.get('executive_conclusion', 'N/A')}

CRITICAL REVIEW TASK:
1. Check if the number of performance obligations in Step 2 matches the allocation approach in Step 4
2. Verify that the transaction price in Step 3 aligns with the allocation amounts in Step 4
3. Ensure the recognition timing in Step 5 matches the nature of obligations identified in Step 2
4. Look for any logical contradictions between steps

RESPONSE FORMAT:
If you find ANY inconsistencies, contradictions, or logical gaps, start your response with "INCONSISTENCY DETECTED:" and explain the specific issues.

If the analysis is logically consistent across all steps, provide a brief confirmation that the steps align properly."""

    @staticmethod
    def get_background_prompt(contract_data) -> str:
        """Generate background section prompt."""
        return f"""Write a professional background section for an ASC 606 memo.

CONTRACT DETAILS:
- Customer: {getattr(contract_data, 'customer_name', 'N/A')}
- Contract Date: {getattr(contract_data, 'contract_date', 'N/A')}
- Services/Products: {getattr(contract_data, 'arrangement_description', 'N/A')}
- Analysis Focus: {getattr(contract_data, 'key_focus_areas', 'General ASC 606 compliance')}

Create a background section that includes:
1. Contract parties and key dates
2. Nature of the arrangement
3. Scope of this analysis
4. Key terms relevant to revenue recognition

Keep it professional and concise."""

    @staticmethod
    def get_key_judgments_prompt(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict) -> str:
        """Generate key judgments prompt."""
        judgments = []
        for i, step in enumerate([s1, s2, s3, s4, s5], 1):
            considerations = step.get('key_considerations', '')
            if considerations and 'judgment' in considerations.lower():
                judgments.append(f"Step {i}: {considerations}")
        
        judgment_text = '\n'.join(judgments) if judgments else "No significant professional judgments identified in the analysis."
        
        return f"""Identify and explain the key professional judgments in this ASC 606 analysis:

POTENTIAL JUDGMENT AREAS:
{judgment_text}

For each significant judgment area:
1. **What**: Describe the judgment made
2. **Why**: Explain the rationale and ASC 606 guidance applied
3. **Alternatives**: Note any alternative treatments considered
4. **Impact**: Assess the materiality of the judgment

If no significant judgments are required, state that the contract follows standard ASC 606 treatments."""

    @staticmethod
    def format_step_detail_as_markdown(step_data: dict, step_number: int, step_name: str) -> str:
        """Format step analysis as markdown."""
        if not step_data:
            return f"## Step {step_number}: {step_name}\n\nNo analysis available.\n"
        
        conclusion = step_data.get('executive_conclusion', 'N/A')
        analysis = step_data.get('supporting_analysis', 'N/A')
        evidence = step_data.get('contract_evidence', 'N/A')
        considerations = step_data.get('key_considerations', 'N/A')
        
        return f"""## Step {step_number}: {step_name}

**Executive Conclusion:**
{conclusion}

**Supporting Analysis:**
{analysis}

**Contract Evidence:**
{evidence}

**Key Considerations:**
{considerations}

---
"""