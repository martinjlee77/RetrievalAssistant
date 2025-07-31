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